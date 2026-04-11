"""SimulationEngine — core orchestrator for the Agent Town real-time simulation.

Wires together all Phase 3 cognition modules (perceive, decide, converse, plan)
into a running simulation loop with concurrent agent processing, pause/resume
control, and per-agent exception isolation.

Design decisions implemented here:
  - D-01: TICK_INTERVAL = 5 seconds (within the 5-10s range, chosen for responsiveness)
  - D-02: All agents run concurrently via asyncio.TaskGroup (Python 3.11+)
  - D-03: Daily schedules generated for all agents before first tick in initialize()
  - D-07: Pause uses asyncio.Event flag; tick loop blocks on Event.wait()
  - D-09/D-10: One tile per tick along BFS path stored in Agent.path
  - T-04-01: Per-agent exception isolation in _agent_step_safe() — one failure
    never cancels sibling agents or crashes the loop
  - T-04-02: Each agent's initialize step isolated; single failure logged, not fatal
  - Pitfall 1 (04-RESEARCH.md): asyncio.TaskGroup exception handling — agent steps
    catch their own exceptions so sibling tasks are never cancelled
  - Pitfall 5: asyncio.wait_for(timeout=TICK_INTERVAL*2) skips agents whose LLM
    calls exceed 2x tick interval

Reference: GenerativeAgentsCN/generative_agents/modules/run.py (adapted for async)
"""
from __future__ import annotations

import asyncio
import logging
from typing import Callable

from backend.schemas import AgentConfig, ScheduleEntry
from backend.simulation.world import Maze
from backend.agents.agent import Agent
from backend.agents.cognition.perceive import perceive
from backend.agents.cognition.decide import decide_action
from backend.agents.cognition.plan import generate_daily_schedule
from backend.agents.memory.store import add_memory, reset_simulation

logger = logging.getLogger(__name__)

# D-01: Tick interval in seconds. Within the 5-10s decision range from D-01.
# Actual tick duration is max(TICK_INTERVAL, slowest_agent_LLM_time) per D-02.
TICK_INTERVAL: int = 30


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

            try:
                async with asyncio.TaskGroup() as tg:
                    for name, agent in self._agents.items():
                        tg.create_task(self._agent_step_safe(name, agent))
            except* Exception as eg:
                # T-04-01: Log ExceptionGroup details but never crash the loop.
                # _agent_step_safe() absorbs individual agent failures, but we
                # catch ExceptionGroup here as a belt-and-suspenders guard.
                for exc in eg.exceptions:
                    logger.warning(
                        "Unhandled exception in tick loop agent task: %s", exc
                    )

            self._tick_count += 1
            await asyncio.sleep(TICK_INTERVAL)

    async def _agent_step_safe(self, agent_name: str, agent: Agent) -> None:
        """Per-agent step with full exception isolation (T-04-01).

        Wraps _agent_step() in try/except so any failure is absorbed.
        Also applies a timeout of 2x TICK_INTERVAL to skip agents whose LLM
        calls are taking too long (Pitfall 5 mitigation).

        Args:
            agent_name: Agent's name (key into self._agents).
            agent:      The agent object.
        """
        try:
            await asyncio.wait_for(
                self._agent_step(agent_name, agent),
                timeout=TICK_INTERVAL * 2,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Agent %s step timed out after %ds — skipping tick",
                agent_name,
                TICK_INTERVAL * 2,
            )
        except Exception as exc:
            # T-04-01: Critical — absorb ALL exceptions so sibling agents are never cancelled
            logger.warning("Agent %s step failed: %s", agent_name, exc)

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

        # 1. PERCEIVE (pure Python, no LLM — fast)
        perception = perceive(
            agent_coord=agent.coord,
            agent_name=agent_name,
            maze=self.maze,
            all_agents=all_agents_view,
        )

        # 2. MOVEMENT: handled by _movement_loop() (fast 500ms cycle)
        # If agent is still walking, skip LLM decisions this tick
        if agent.path:
            return

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

                # CR-01: Snapshot other agent's schedule before the await.
                # Because all agent steps run concurrently in asyncio.TaskGroup,
                # agent B's step may mutate its own schedule during the conversation.
                schedule_b_snapshot = list(other_agent.schedule)

                result = await agent.converse(other_agent, self.maze, self.simulation_id)
                if result:
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
        action = await decide_action(
            simulation_id=self.simulation_id,
            agent_name=agent_name,
            agent_scratch=config.scratch,
            agent_spatial=config.spatial,
            current_activity=agent.current_activity,
            perception=perception,
            current_schedule=agent.schedule,
        )

        # Resolve destination to tile coordinates and compute BFS path (D-09, D-10)
        if action.destination != "idle":
            dest_coord = self.maze.resolve_destination(action.destination)
            if dest_coord is not None:
                path = self.maze.find_path(agent.coord, dest_coord)
                # Skip first element (current position) so first pop moves to next tile
                agent.path = path[1:] if len(path) > 1 else []

        # Update activity and broadcast state change
        agent.current_activity = action.activity
        await self._emit_agent_update(agent_name, agent)

        # Store action memory for future perception and decision context
        await add_memory(
            simulation_id=self.simulation_id,
            agent_id=agent_name,
            content=(
                f"{agent_name} is {action.activity} at {perception.location}"
            ),
            memory_type="action",
            importance=3,
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
            conversation_result: Dict from run_conversation() with "turns" and "summary".
        """
        if self._broadcast_callback is not None:
            await self._broadcast_callback({
                "type": "conversation",
                "turns": conversation_result.get("turns", []),
                "summary": conversation_result.get("summary", ""),
            })

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
                }
                for name, agent in self._agents.items()
            ],
            "simulation_status": "running" if self._running.is_set() else "paused",
            "tick_count": self._tick_count,
        }
