"""SimulationEngine — core orchestrator for the Agent Town real-time simulation.

Wires together all Phase 3 cognition modules (perceive, decide, converse, plan)
into a running simulation loop with concurrent agent processing, pause/resume
control, and per-agent exception isolation.

Design decisions implemented here:
  - D-01: TICK_INTERVAL = 5 seconds (within the 5-10s range, chosen for responsiveness)
  - D-02: All agents run concurrently via asyncio.TaskGroup (Python 3.11+)
  - D-03: Daily schedules generated for all agents before first tick in initialize()
  - D-07: Pause uses asyncio.Event flag; tick loop blocks on Event.wait()
  - D-09/D-10: One tile per tick along BFS path stored in AgentState.path
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
from dataclasses import dataclass, field
from typing import Callable

from backend.schemas import AgentConfig, ScheduleEntry
from backend.simulation.world import Maze
from backend.agents.cognition.perceive import perceive
from backend.agents.cognition.decide import decide_action
from backend.agents.cognition.converse import attempt_conversation, run_conversation
from backend.agents.cognition.plan import generate_daily_schedule
from backend.agents.memory.store import add_memory, reset_simulation

logger = logging.getLogger(__name__)

# D-01: Tick interval in seconds. Within the 5-10s decision range from D-01.
# Actual tick duration is max(TICK_INTERVAL, slowest_agent_LLM_time) per D-02.
TICK_INTERVAL: int = 5


@dataclass
class AgentState:
    """Runtime simulation state for one agent — mutable each tick.

    Decoupled from the static AgentConfig loaded from JSON so the simulation
    can track evolving runtime properties (position, path, schedule) separately
    from the agent's fixed personality/background.

    Attributes:
        name:             Agent display name (matches AgentConfig.name).
        config:           Static AgentConfig (personality, spatial knowledge).
        coord:            Current tile position (x, y). Updated each tick.
        path:             Remaining BFS path tiles to traverse (D-10).
                          Each tick pops one tile from the front.
        current_activity: What the agent is doing now (broadcast to clients).
        schedule:         Remaining ScheduleEntry list — modified by conversations.
    """
    name: str
    config: AgentConfig
    coord: tuple[int, int]
    path: list[tuple[int, int]] = field(default_factory=list)
    current_activity: str = ""
    schedule: list = field(default_factory=list)


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
        maze: Maze,
        agents: list[AgentConfig],
        simulation_id: str,
    ) -> None:
        """Initialize the simulation engine (not yet running).

        Args:
            maze:          The Maze instance providing tile data and pathfinding.
            agents:        List of AgentConfig objects to simulate.
            simulation_id: Unique identifier for this simulation run.
        """
        self.maze = maze
        self.simulation_id = simulation_id
        self._configs: list[AgentConfig] = agents

        # D-07: Pause gate. Cleared = paused (blocked), Set = running.
        # Starts cleared so the loop blocks until run() or resume() is called.
        self._running: asyncio.Event = asyncio.Event()

        # Runtime state dict: agent_name -> AgentState
        self._agent_states: dict[str, AgentState] = {}

        # Hook for Plan 02: ConnectionManager can attach its broadcast method here.
        # If None, emit methods are no-ops.
        self._broadcast_callback: Callable | None = None

        self._tick_count: int = 0

    async def initialize(self) -> None:
        """Prepare agent states and generate daily schedules (D-03).

        Must be called before run(). Performs:
        1. Resets the simulation's ChromaDB collection for a fresh start (INF-01)
        2. Creates AgentState for each config
        3. Generates daily schedules for all agents in parallel (2 LLM calls/agent)
        4. Stores initial observation memories for each agent
        """
        # INF-01: Clear stale ChromaDB data from previous simulation runs
        await reset_simulation(self.simulation_id)

        # Create base AgentState for each agent config (no LLM calls yet)
        for cfg in self._configs:
            self._agent_states[cfg.name] = AgentState(
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
            self._agent_states[cfg.name].schedule = schedule

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
        """Enter the running state and start the tick loop.

        Sets the asyncio.Event flag (D-07) then enters _tick_loop().
        This coroutine runs indefinitely until cancelled.
        """
        self._running.set()
        await self._tick_loop()

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
                    for name, state in self._agent_states.items():
                        tg.create_task(self._agent_step_safe(name, state))
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

    async def _agent_step_safe(self, agent_name: str, state: AgentState) -> None:
        """Per-agent step with full exception isolation (T-04-01).

        Wraps _agent_step() in try/except so any failure is absorbed.
        Also applies a timeout of 2x TICK_INTERVAL to skip agents whose LLM
        calls are taking too long (Pitfall 5 mitigation).

        Args:
            agent_name: Agent's name (key into self._agent_states).
            state:      The agent's current AgentState.
        """
        try:
            await asyncio.wait_for(
                self._agent_step(agent_name, state),
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

    async def _agent_step(self, agent_name: str, state: AgentState) -> None:
        """Single agent tick: perceive -> move OR converse OR decide.

        Three-phase flow (one phase per tick):
        1. PERCEIVE: scan tile grid for nearby agents and events (no LLM)
        2. MOVEMENT: if path exists, pop one tile and update coord; return early
        3. CONVERSATION: if nearby agents present, attempt conversation; return if started
        4. DECIDE: call LLM to choose next destination and activity

        Args:
            agent_name: Agent's display name.
            state:      The agent's current AgentState (mutated in place).
        """
        config = state.config

        # Build snapshot of all agents' positions and activities for perception scan
        all_agents_view = {
            name: {"coord": s.coord, "current_activity": s.current_activity}
            for name, s in self._agent_states.items()
        }

        # 1. PERCEIVE (pure Python, no LLM — fast)
        perception = perceive(
            agent_coord=state.coord,
            agent_name=agent_name,
            maze=self.maze,
            all_agents=all_agents_view,
        )

        # 2. MOVEMENT PHASE (D-09, D-10): advance one tile along stored BFS path
        if state.path:
            next_tile = state.path.pop(0)
            state.coord = next_tile
            await self._emit_agent_update(agent_name, state)
            return  # movement tick: no decide/converse call this tick

        # 3. CONVERSATION PHASE: check nearby agents, attempt one conversation per tick
        if perception.nearby_agents:
            for nearby in perception.nearby_agents:
                other_name = nearby["name"]
                other_activity = nearby.get("activity", "")
                other_state = self._agent_states.get(other_name)
                if other_state is None:
                    continue

                should_talk = await attempt_conversation(
                    simulation_id=self.simulation_id,
                    agent_name=agent_name,
                    agent_scratch=config.scratch,
                    other_name=other_name,
                    other_activity=other_activity,
                    agent_current_activity=state.current_activity,
                    location=perception.location,
                )

                if should_talk:
                    convo_result = await run_conversation(
                        simulation_id=self.simulation_id,
                        agent_a_name=agent_name,
                        agent_a_scratch=config.scratch,
                        agent_b_name=other_name,
                        agent_b_scratch=other_state.config.scratch,
                        location=perception.location,
                        remaining_schedule_a=list(state.schedule),
                        remaining_schedule_b=list(other_state.schedule),
                    )

                    # Update both agents' schedules with revised entries
                    revised_a = convo_result.get("revised_schedule_a", [])
                    revised_b = convo_result.get("revised_schedule_b", [])
                    if revised_a:
                        state.schedule = list(revised_a)
                    if revised_b:
                        other_state.schedule = list(revised_b)

                    await self._emit_conversation(convo_result)
                    return  # conversation tick: no decide call this tick

                # Only attempt one conversation per tick per agent
                break

        # 4. DECIDE PHASE (LLM — slow): choose next destination and activity
        action = await decide_action(
            simulation_id=self.simulation_id,
            agent_name=agent_name,
            agent_scratch=config.scratch,
            agent_spatial=config.spatial,
            current_activity=state.current_activity,
            perception=perception,
            current_schedule=state.schedule,
        )

        # Resolve destination to tile coordinates and compute BFS path (D-09, D-10)
        if action.destination != "idle":
            dest_coord = self.maze.resolve_destination(action.destination)
            if dest_coord is not None:
                path = self.maze.find_path(state.coord, dest_coord)
                # Skip first element (current position) so first pop moves to next tile
                state.path = path[1:] if len(path) > 1 else []

        # Update activity and broadcast state change
        state.current_activity = action.activity
        await self._emit_agent_update(agent_name, state)

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

    async def _emit_agent_update(self, agent_name: str, state: AgentState) -> None:
        """Broadcast agent position and activity to all connected clients.

        Calls the broadcast callback (attached by Plan 02's ConnectionManager) if set.
        No-op if no callback is registered.

        Args:
            agent_name: Agent's display name.
            state:      Current AgentState (coord and current_activity are broadcast).
        """
        if self._broadcast_callback is not None:
            await self._broadcast_callback({
                "type": "agent_update",
                "name": agent_name,
                "coord": list(state.coord),
                "activity": state.current_activity,
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
                    "coord": list(state.coord),
                    "activity": state.current_activity,
                }
                for name, state in self._agent_states.items()
            ],
            "simulation_status": "running" if self._running.is_set() else "paused",
            "tick_count": self._tick_count,
        }
