"""SimulationEngine — core orchestrator for the Agent Town real-time simulation.

Wires together all Phase 3 cognition modules (perceive, decide, converse, plan)
into a running simulation loop with concurrent agent processing, pause/resume
control, and per-agent exception isolation.

Design decisions implemented here:
  - D-04: Adaptive tick interval based on LLM latency rolling window (Phase 9)
  - D-02: All agents run concurrently via asyncio.TaskGroup (Python 3.11+)
  - D-03: Daily schedules generated for all agents before first tick in initialize()
  - D-07: Pause uses asyncio.Event flag; tick loop blocks on Event.wait()
  - D-09/D-10: One tile per tick along BFS path stored in Agent.path
  - T-04-01: Per-agent exception isolation in _agent_step_safe() — one failure
    never cancels sibling agents or crashes the loop
  - T-04-02: Each agent's initialize step isolated; single failure logged, not fatal
  - Pitfall 1 (04-RESEARCH.md): asyncio.TaskGroup exception handling — agent steps
    catch their own exceptions so sibling tasks are never cancelled
  - Pitfall 5: asyncio.wait_for(timeout=max(tick_interval*2, 120)) skips agents
    whose LLM calls exceed 2x tick interval; 120s floor prevents cold-start timeouts

Reference: GenerativeAgentsCN/generative_agents/modules/run.py (adapted for async)
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Callable

from backend.schemas import AgentConfig, ScheduleEntry
from backend.schemas.events import Event, EVENT_EXPIRY_TICKS
from backend.simulation.world import Maze, load_buildings, Building
from backend.agents.agent import Agent
from backend.agents.cognition.decide import _extract_known_locations
from backend.agents.cognition.plan import generate_daily_schedule
from backend.agents.memory.store import add_memory, reset_simulation
from backend.gateway import get_adaptive_tick_interval

logger = logging.getLogger(__name__)


class SimulationEngine:
    """Orchestrates the real-time agent simulation loop.

    Responsibilities:
      - Initialize agent states and generate daily schedules before first tick
      - Run all agents concurrently each tick via asyncio.TaskGroup (D-02)
      - Isolate per-agent exceptions so one LLM failure cannot crash others (T-04-01)
      - Implement pause/resume via asyncio.Event flag (D-07)
      - Drive agent movement one tile per tick along stored BFS paths (D-09, D-10)
      - Emit agent state updates via optional broadcast callback (Plan 02 wiring point)

    Usage:
        engine = SimulationEngine(maze=maze, agents=configs, simulation_id=sim_id)
        await engine.initialize()
        await engine.run()  # enters the tick loop — runs until cancelled
    """

    def __init__(
        self,
        maze: Maze | None = None,
        agents: list[AgentConfig] | None = None,
        simulation_id: str = "",
        broadcast_callback: Callable | None = None,
    ) -> None:
        """Initialize the simulation engine (not yet running).

        Args:
            maze:               The Maze instance providing tile data and pathfinding.
            agents:             List of AgentConfig objects to simulate.
            simulation_id:      Unique identifier for this simulation run.
            broadcast_callback: Optional async callable wired by the caller (e.g.
                                main.py lifespan) to push updates to all connected
                                WebSocket clients.  Passing it here as a constructor
                                argument (WR-03) makes the dependency explicit and
                                avoids external writes to the private ``_broadcast_callback``
                                attribute after construction.
        """
        self.maze = maze
        self.simulation_id = simulation_id
        self._configs: list[AgentConfig] = agents or []

        # D-07: Pause gate. Cleared = paused (blocked), Set = running.
        # Starts cleared so the loop blocks until run() or resume() is called.
        self._running: asyncio.Event = asyncio.Event()

        # Runtime state dict: agent_name -> Agent (ARCH-03: single dict, no dual ownership)
        self._agents: dict[str, Agent] = {}

        # WR-03: Wired via constructor parameter so callers never need to write
        # the private attribute directly.  If None, emit methods are no-ops.
        self._broadcast_callback: Callable | None = broadcast_callback

        self._tick_count: int = 0

        # Simulation time tracking (D-10): starts at 7am, advances 10 sim-minutes per tick
        self._sim_hour: int = 7
        self._sim_minute: int = 0
        # Pitfall 5 guard: ejection runs exactly once per hour change, not every tick
        self._last_ejection_hour: int = -1

        # Load buildings once at init — never per tick (anti-pattern)
        self._buildings: dict[str, Building] = load_buildings()

        # Codex P1-4: Prevent duplicate simultaneous conversations between same pair.
        # Two nearby agents can both pass check_cooldown() before either calls
        # _record_conversation(), causing duplicate conversations and conflicting
        # schedule writes. This set tracks in-flight conversation pairs within a tick.
        self._active_conversations: set[frozenset[str]] = set()

        # EVTS-01: Active event registry — events tracked from inject to expiry
        self._active_events: dict[str, Event] = {}

    @property
    def tick_interval(self) -> float:
        """Adaptive tick interval per D-04: max(10, avg_latency * 1.5)."""
        return get_adaptive_tick_interval(min_interval=10.0)

    async def initialize(self) -> None:
        """Prepare agent states and generate daily schedules (D-03).

        Must be called before run(). Performs:
        1. Resets the simulation's ChromaDB collection for a fresh start (INF-01)
        2. Creates Agent for each config
        3. Generates daily schedules for all agents in parallel (2 LLM calls/agent)
        4. Stores initial observation memories for each agent
        """
        # INF-01: Clear stale ChromaDB data from previous simulation runs
        await reset_simulation(self.simulation_id)

        # Create base Agent for each agent config (no LLM calls yet)
        for cfg in self._configs:
            self._agents[cfg.name] = Agent(
                name=cfg.name,
                config=cfg,
                coord=cfg.coord,
                path=[],
                current_activity=cfg.currently,
                schedule=[],
            )

        # D-03: Generate daily schedules for all agents in parallel before first tick.
        # T-04-02: Individual init failures are logged but don't prevent others from
        # initializing — each agent's initialization is isolated.
        async with asyncio.TaskGroup() as tg:
            for cfg in self._configs:
                tg.create_task(self._init_agent_safe(cfg))

    async def _init_agent_safe(self, cfg: AgentConfig) -> None:
        """Initialize one agent's daily schedule with exception isolation (T-04-02)."""
        try:
            schedule = await generate_daily_schedule(
                agent_name=cfg.name,
                agent_scratch=cfg.scratch,
            )
            self._agents[cfg.name].schedule = schedule

            # Store initial observation memory for context on first tick
            await add_memory(
                simulation_id=self.simulation_id,
                agent_id=cfg.name,
                content=f"{cfg.name} started the day: {cfg.currently}",
                memory_type="observation",
                importance=3,
            )
        except Exception as exc:
            logger.warning(
                "Failed to initialize agent %s: %s — using empty schedule",
                cfg.name,
                exc,
            )

    async def run(self) -> None:
        """Enter the running state and start the tick loop + movement loop.

        Sets the asyncio.Event flag (D-07) then runs both loops concurrently.
        The tick loop handles LLM decisions (every TICK_INTERVAL seconds).
        The movement loop handles visual path walking (every 500ms).
        """
        self._running.set()
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self._tick_loop())
            tg.create_task(self._movement_loop())

    async def _movement_loop(self) -> None:
        """Fast movement loop — moves agents along BFS paths every 500ms.

        Decoupled from the LLM tick so agents walk visually fast while
        decisions happen on a slower cadence.
        """
        while True:
            await self._running.wait()
            for name, agent in self._agents.items():
                if agent.path:
                    next_tile = agent.path.pop(0)
                    agent.coord = next_tile
                    await self._emit_agent_update(name, agent)
            await asyncio.sleep(0.5)

    async def _tick_loop(self) -> None:
        """Main simulation loop — one iteration per tick.

        Flow per tick:
        1. Block on self._running.wait() — pauses here when paused (D-07)
        2. Run all agent steps concurrently via asyncio.TaskGroup (D-02)
        3. Catch ExceptionGroup from TaskGroup but never re-raise (loop must survive)
        4. Increment tick count
        5. Sleep TICK_INTERVAL seconds before next tick

        Exits only when the containing coroutine is cancelled (FastAPI lifespan shutdown).
        """
        while True:
            # D-07: Block here when paused. Resumes immediately when running.
            await self._running.wait()

            # P1 fix: Advance simulation time BEFORE agent steps so that
            # _is_location_open() uses the correct hour on boundary ticks.
            # Previously, agents decided destinations using the old hour,
            # then the clock advanced and ejected them immediately.
            self._sim_minute += 10
            if self._sim_minute >= 60:
                self._sim_minute = 0
                self._sim_hour = (self._sim_hour + 1) % 24

            # Eject agents from buildings that just closed (D-09, Pitfall 5 guard)
            # Runs exactly once per hour change — _last_ejection_hour prevents re-firing
            if self._sim_hour != self._last_ejection_hour:
                self._last_ejection_hour = self._sim_hour
                await self._eject_agents_from_closed_buildings()

            # Codex P1-4: Clear in-flight conversation pairs at start of each tick.
            # Pairs from the previous tick are no longer relevant.
            self._active_conversations.clear()

            # Run all agent steps concurrently (D-02)
            async with asyncio.TaskGroup() as tg:
                for name, agent in self._agents.items():
                    tg.create_task(self._agent_step_safe(name, agent))
            self._tick_count += 1

            # EVTS-03: Advance lifecycle and purge expired events
            self._purge_expired_events()

            current_tick = self.tick_interval
            logger.info("===== Tick %d complete | next in %.1fs =====", self._tick_count, current_tick)

            # Broadcast tick interval update to frontend (D-06)
            if self._broadcast_callback is not None:
                await self._broadcast_callback({
                    "type": "tick_interval_update",
                    "tick_interval": round(current_tick, 1),
                })

            await asyncio.sleep(current_tick)

    def _purge_expired_events(self) -> None:
        """Advance event lifecycle and remove any expired events (EVTS-03).

        Extracted from _tick_loop so tests can call the real purge logic
        directly rather than replicating the loop inline (WR-04).
        Called once per tick after self._tick_count has been incremented.
        """
        for eid, ev in list(self._active_events.items()):
            ev.tick(self._tick_count)
            if ev.is_expired(self._tick_count):
                del self._active_events[eid]
                logger.info(
                    "Event expired and removed: %s (tick %d)",
                    ev.text[:40],
                    self._tick_count,
                )

    async def _agent_step_safe(self, agent_name: str, agent: Agent) -> None:
        """Per-agent step with full exception isolation (T-04-01).

        Wraps _agent_step() in try/except so any failure is absorbed.
        Also applies a timeout of 2x TICK_INTERVAL to skip agents whose LLM
        calls are taking too long (Pitfall 5 mitigation).

        Args:
            agent_name: Agent's name (key into self._agents).
            agent:      The agent object.
        """
        # Codex P1-3 fix: 120s cold-start floor — at cold start tick_interval=10,
        # so tick_interval*2=20s which is not enough for 4+ LLM calls. The floor
        # ensures the agent step never times out before any latency is recorded.
        # WR-01: compute timeout once so the except block logs the actual value.
        timeout = max(self.tick_interval * 2, 120)
        try:
            await asyncio.wait_for(
                self._agent_step(agent_name, agent),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            # Reuse the same timeout variable — do NOT recompute self.tick_interval here
            logger.warning(
                "Agent %s step timed out after %.0fs — skipping tick",
                agent_name,
                timeout,
            )
        except Exception as exc:
            # T-04-01: Critical — absorb ALL exceptions so sibling agents are never cancelled
            logger.warning("Agent %s step failed: %s", agent_name, exc, exc_info=True)

    async def _agent_step(self, agent_name: str, agent: Agent) -> None:
        """Single agent tick: perceive -> move OR converse OR decide.

        Three-phase flow (one phase per tick):
        1. PERCEIVE: scan tile grid for nearby agents and events (no LLM)
        2. MOVEMENT: if path exists, pop one tile and update coord; return early
        3. CONVERSATION: if nearby agents present, attempt conversation; return if started
        4. DECIDE: call LLM to choose next destination and activity

        Args:
            agent_name: Agent's display name.
            agent:      The agent object (mutated in place).
        """
        config = agent.config

        # Build snapshot of all agents' positions and activities for perception scan
        all_agents_view = {
            name: {"coord": a.coord, "current_activity": a.current_activity}
            for name, a in self._agents.items()
        }

        # 1. PERCEIVE via Agent wrapper (ARCH-02)
        perception = agent.perceive(maze=self.maze, all_agents=all_agents_view)

        nearby_names = [a["name"] for a in perception.nearby_agents] if perception.nearby_agents else []
        logger.info(
            "[%s] tick %d | perceive: pos=%s activity='%s' nearby=%s",
            agent_name, self._tick_count, agent.coord, agent.current_activity, nearby_names,
        )

        # EVTS-02: Update heard_by for whisper events (D-09: broadcasts skip heard_by)
        # WR-02: only record the intended target — not every agent that runs _agent_step
        for ev in self._active_events.values():
            if ev.mode == "whisper" and not ev.is_expired(self._tick_count):
                if ev.target == agent_name and agent_name not in ev.heard_by:
                    ev.heard_by.append(agent_name)
                    logger.debug("[%s] heard whisper event '%s...'", agent_name, ev.text[:30])

        # 2. MOVEMENT: handled by _movement_loop() (fast 500ms cycle)
        # If agent is still walking, skip LLM decisions this tick
        if agent.path:
            logger.info("[%s] tick %d | walking (%d tiles left)", agent_name, self._tick_count, len(agent.path))
            return

        # Agent has no path — they've arrived at their destination.
        # Clear last_sector so gating won't skip their next decide call.
        # Gating only saves LLM calls while the agent is en route (path non-empty),
        # which is handled by the early return above.
        if agent.last_sector is not None:
            logger.info("[%s] tick %d | arrived at sector '%s', clearing gate", agent_name, self._tick_count, agent.last_sector)
            agent.last_sector = None

        # 3. CONVERSATION PHASE: check nearby agents, attempt one conversation per tick
        if perception.nearby_agents:
            for nearby in perception.nearby_agents:
                other_name = nearby["name"]
                other_agent = self._agents.get(other_name)
                if other_agent is None:
                    # WR-02: Log data integrity issue — a perceived agent name is not
                    # in _agents (stale perception or name mismatch).  Continue
                    # to the next nearby agent rather than counting this as the one
                    # conversation-check attempt for this tick.
                    logger.warning(
                        "Agent %s perceived unknown agent %s — name not in _agents, skipping",
                        agent_name,
                        other_name,
                    )
                    continue

                # Codex P1-4: Claim this conversation pair before the async await.
                # Both agent A and agent B may pass check_cooldown() simultaneously
                # before either records the conversation. The _active_conversations set
                # prevents both directions from firing in the same tick.
                pair_key = frozenset({agent_name, other_name})
                if pair_key in self._active_conversations:
                    logger.debug(
                        "Conversation %s <-> %s already in flight this tick — skipping",
                        agent_name, other_name,
                    )
                    continue  # Try next nearby agent
                self._active_conversations.add(pair_key)

                # CR-01: Snapshot other agent's schedule before the await.
                # Because all agent steps run concurrently in asyncio.TaskGroup,
                # agent B's step may mutate its own schedule during the conversation.
                schedule_b_snapshot = list(other_agent.schedule)

                logger.info("[%s] tick %d | converse: attempting with %s", agent_name, self._tick_count, other_name)
                result = await agent.converse(other_agent, self.maze, self.simulation_id)
                # Clean up in-flight claim regardless of conversation outcome
                self._active_conversations.discard(pair_key)

                if result:
                    turn_count = len(result.get("turns", []))
                    term_reason = result.get("terminated_reason", "unknown")
                    logger.info(
                        "[%s] tick %d | converse: %s <-> %s completed (%d turns, ended=%s)",
                        agent_name, self._tick_count, agent_name, other_name, turn_count, term_reason,
                    )
                    revised_a = result.get("revised_schedule_a", [])
                    revised_b = result.get("revised_schedule_b", [])
                    if revised_a:
                        agent.schedule = list(revised_a)
                    # CR-01 guard: only apply revised_b if other agent's schedule
                    # was not modified by a concurrent task during the await above.
                    if revised_b and other_agent.schedule == schedule_b_snapshot:
                        other_agent.schedule = list(revised_b)
                    elif revised_b:
                        logger.debug(
                            "Skipped revised schedule write-back for %s: "
                            "schedule was concurrently modified during conversation await",
                            other_agent.name,
                        )

                    await self._emit_conversation(result)
                    return  # conversation tick: no decide call this tick

                # LOAD-BEARING BREAK (D-05): Only attempt one conversation gate check per tick.
                # Removing this break multiplies LLM calls by the number of nearby agents.
                break

        # 4. DECIDE PHASE (LLM — slow): choose next destination and activity
        # Filter destinations to only open buildings (D-08, BLD-03)
        all_locations = _extract_known_locations(config.spatial.tree)
        open_locs = [loc for loc in all_locations if self._is_location_open(loc)]

        # Codex P1-6: Detect schedule block changes for gating.
        # Compare agent's current schedule entry (by sim time) to detect advancement.
        current_schedule_block = self._get_current_schedule_describe(agent)
        schedule_changed = (current_schedule_block != agent._last_schedule_block)
        agent._last_schedule_block = current_schedule_block

        action = await agent.decide(
            simulation_id=self.simulation_id,
            perception=perception,
            open_locations=open_locs,
            last_sector=agent.last_sector,
            new_perceptions=bool(perception.nearby_agents or perception.nearby_events),
            schedule_changed=schedule_changed,
        )

        # D-08: If gating skipped the call, keep current action unchanged
        if action is None:
            logger.info("[%s] tick %d | decide: GATED (sector=%s, no new perceptions/schedule)", agent_name, self._tick_count, agent.last_sector)
            return

        logger.info(
            "[%s] tick %d | decide: dest='%s' activity='%s' reason='%s'",
            agent_name, self._tick_count, action.destination, action.activity, action.reasoning,
        )

        # Update gating state for next tick — but NOT for fallback "idle" actions,
        # which are returned when no API key is configured yet. Setting last_sector
        # to "idle" would cause gating to skip all future LLM calls permanently.
        if action.destination != "idle":
            agent.last_sector = action.destination.split(":")[0] if ":" in action.destination else action.destination

        # Resolve destination to tile coordinates and compute BFS path (D-09, D-10)
        destination_valid = False
        if action.destination != "idle":
            dest_coord = self.maze.resolve_destination(action.destination)
            if dest_coord is not None:
                if dest_coord == agent.coord:
                    # P1 fix: same-tile destination is valid (agent changes activity in place)
                    destination_valid = True
                else:
                    path = self.maze.find_path(agent.coord, dest_coord)
                    if len(path) > 1:
                        agent.path = path[1:]
                        destination_valid = True

        # Only update activity if destination was reachable or same-tile, or agent chose "idle"
        if destination_valid or action.destination == "idle":
            agent.current_activity = action.activity
            await self._emit_agent_update(agent_name, agent)

            # Store action memory only when the action will actually happen
            await add_memory(
                simulation_id=self.simulation_id,
                agent_id=agent_name,
                content=(
                    f"{agent_name} is {action.activity} at {perception.location}"
                ),
                memory_type="action",
                importance=3,
            )
        else:
            logger.debug(
                "Agent %s destination '%s' unreachable — keeping current activity, no memory stored",
                agent_name, action.destination,
            )

    def _is_location_open(self, sector: str) -> bool:
        """Return True if sector has no Building entry or is currently open.

        Unknown sectors (not in buildings.json) are always considered accessible —
        the maze may have non-building destinations like roads.

        Args:
            sector: Sector name without world prefix (e.g. "cafe", "stock-exchange").

        Returns:
            True if agents can navigate to this sector right now.
        """
        building = self._buildings.get(sector)
        if building is None:
            return True  # unknown sectors are always accessible
        return building.is_open(self._sim_hour)

    async def _eject_agents_from_closed_buildings(self) -> None:
        """Eject agents from buildings that just closed (D-09).

        Called ONLY when _sim_hour changes (Pitfall 5 guard prevents LLM call
        multiplication by ensuring ejection runs at most once per hour, not every tick).

        For each agent, checks whether the sector tile they occupy has a Building
        whose is_open() returns False at the current sim hour. If so:
        - Clears the agent's path (so movement loop stops)
        - Sets current_activity to "leaving (building closed)"
        - Emits an agent_update broadcast so clients see the state change immediately

        The agent will get a fresh decide_action call on the next tick, with the
        closed building already excluded from open_locations.

        Agents on road tiles (address length < 2) or tiles with unknown sectors are
        never ejected.
        """
        for name, agent in self._agents.items():
            if not self.maze:
                continue
            try:
                tile = self.maze.tile_at(agent.coord)
            except (IndexError, Exception):
                continue
            if not tile or len(tile.address) < 2:
                continue  # road tile or unenrolled tile — not in a building sector
            sector = tile.address[1]  # e.g. "cafe", "stock-exchange"
            building = self._buildings.get(sector)
            if building and not building.is_open(self._sim_hour):
                agent.path = []
                agent.current_activity = "leaving (building closed)"
                await self._emit_agent_update(name, agent)
                logger.info(
                    "%s ejected from closed %s at sim hour %d",
                    name, sector, self._sim_hour,
                )

    async def _emit_agent_update(self, agent_name: str, agent: Agent) -> None:
        """Broadcast agent position and activity to all connected clients.

        Calls the broadcast callback (attached by Plan 02's ConnectionManager) if set.
        No-op if no callback is registered.

        Args:
            agent_name: Agent's display name.
            agent:      Current Agent (coord and current_activity are broadcast).
        """
        if self._broadcast_callback is not None:
            await self._broadcast_callback({
                "type": "agent_update",
                "name": agent_name,
                "coord": list(agent.coord),
                "activity": agent.current_activity,
            })

    async def _emit_conversation(self, conversation_result: dict) -> None:
        """Broadcast conversation turns and summary to all connected clients.

        Args:
            conversation_result: Dict from run_conversation() with "turns", "summary",
                                 and optionally "terminated_reason".
        """
        if self._broadcast_callback is not None:
            payload = {
                "type": "conversation",
                "turns": conversation_result.get("turns", []),
                "summary": conversation_result.get("summary", ""),
            }
            # D-11 / Codex P2-7: Include terminated_reason if present
            if "terminated_reason" in conversation_result:
                payload["terminated_reason"] = conversation_result["terminated_reason"]
            await self._broadcast_callback(payload)

    def _get_current_schedule_describe(self, agent: "Agent") -> str | None:
        """Return the 'describe' field of the agent's current schedule entry, or None.

        Used by Codex P1-6 schedule_changed gating: compares the current schedule
        block description against the previous tick's value to detect schedule advancement.

        Args:
            agent: The agent whose schedule to inspect.

        Returns:
            The describe string of the most recent schedule entry at or before the
            current simulation minute, or None if no matching entry is found.
        """
        current_minute = self._sim_hour * 60 + self._sim_minute
        for entry in reversed(agent.schedule):
            if hasattr(entry, 'start_minute') and entry.start_minute <= current_minute:
                return getattr(entry, 'describe', None)
        return None

    async def inject_event(self, text: str, mode: str, target: str | None = None) -> None:
        """Inject a user event into agent memory streams (Phase 6).

        Broadcast: stores high-importance memory in ALL agents' streams.
        Whisper:   stores high-importance memory ONLY in the named target agent's stream.

        Hardcodes importance=8 (per research recommendation D-05/D-06) — injected events
        are user-initiated and inherently significant; skipping score_importance() saves
        one LLM call per agent per event injection.

        Text is truncated to 500 chars before storage (T-06-03 DoS mitigation).

        Args:
            text:   The event text to inject. Caller is responsible for non-empty
                    validation (ws.py guards upstream). Truncated to 500 chars here.
            mode:   "broadcast" (all agents) or "whisper" (single named target).
            target: Agent name for whisper mode. Ignored for broadcast. Must be a
                    key in self._agents; unknown names are logged and rejected.
        """
        # T-06-03: Truncate to 500 chars to prevent oversized ChromaDB documents
        text = text[:500]

        if mode == "broadcast":
            targets = list(self._agents.keys())
        elif mode == "whisper" and target and target in self._agents:
            targets = [target]
        else:
            logger.warning(
                "inject_event: invalid mode=%s or unknown target=%s", mode, target
            )
            return

        # EVTS-01: Create Event object with active status
        event_id = str(uuid.uuid4())
        event = Event(
            text=text,
            mode=mode,
            target=target,
            status="created",
            created_tick=self._tick_count,
            expires_after_ticks=EVENT_EXPIRY_TICKS,
        )
        event.tick(self._tick_count)  # transitions created -> active
        self._active_events[event_id] = event

        for agent_name in targets:
            await add_memory(
                simulation_id=self.simulation_id,
                agent_id=agent_name,
                content=f"Event: {text}",
                memory_type="event",
                importance=8,
            )
            # Clear the agent's current path so they make a fresh LLM decision
            # on the next tick instead of continuing to walk to their old destination.
            agent_obj = self._agents.get(agent_name)
            if agent_obj:
                agent_obj.path = []

    def pause(self) -> None:
        """Pause the simulation — blocks the tick loop at the next Event.wait().

        Per D-07: agents finish their current in-progress action but no new tick
        starts until resume() is called. Pause does not interrupt running agent steps.
        """
        self._running.clear()

    def resume(self) -> None:
        """Resume the simulation from paused state (D-07).

        Sets the asyncio.Event flag. The blocked tick loop's Event.wait() returns
        and the next tick begins. No agent state is reset.
        """
        self._running.set()

    def get_snapshot(self) -> dict:
        """Return a snapshot of the current simulation state.

        Used by Plan 02 to send a full state message to newly connected WebSocket
        clients (D-05). The client can reconstruct full state from this snapshot
        plus subsequent delta events.

        Returns:
            Dict with:
              - "agents": list of {"name", "coord", "activity"} for each agent
              - "simulation_status": "running" or "paused"
              - "tick_count": number of ticks completed so far
        """
        return {
            "agents": [
                {
                    "name": name,
                    "coord": list(agent.coord),
                    "activity": agent.current_activity,
                    "occupation": agent.config.scratch.occupation if hasattr(agent.config.scratch, "occupation") else "",
                    "age": agent.config.scratch.age if hasattr(agent.config.scratch, "age") else None,
                    "innate": agent.config.scratch.innate if hasattr(agent.config.scratch, "innate") else "",
                }
                for name, agent in self._agents.items()
            ],
            "simulation_status": "running" if self._running.is_set() else "paused",
            "tick_count": self._tick_count,
            "tick_interval": self.tick_interval,
        }
