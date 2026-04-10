"""Unit tests for SimulationEngine: concurrency, pause/resume, exception isolation.

TDD: Tests written first (RED), then implementation makes them pass (GREEN).
All cognition calls are mocked -- no real LLM calls.
"""
import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

SMALL_MAP_CONFIG = {
    "world": "agent-town",
    "tile_size": 32,
    "size": [10, 10],
    "tile_address_keys": ["world", "sector", "arena"],
    "tiles": [
        # Border walls
        *[{"coord": [x, 0], "collision": True} for x in range(10)],
        *[{"coord": [x, 9], "collision": True} for x in range(10)],
        *[{"coord": [0, y], "collision": True} for y in range(1, 9)],
        *[{"coord": [9, y], "collision": True} for y in range(1, 9)],
        # Named sector "cafe" at tiles (3,3)-(4,4)
        {"coord": [3, 3], "address": ["cafe", "seating"]},
        {"coord": [4, 3], "address": ["cafe", "seating"]},
        {"coord": [3, 4], "address": ["cafe", "counter"]},
        {"coord": [4, 4], "address": ["cafe", "counter"]},
    ],
}


def _make_small_maze():
    """Create a 10x10 Maze with walkable interior and named sector 'cafe'."""
    from backend.simulation.world import Maze
    return Maze(SMALL_MAP_CONFIG)


def _make_agent_config(name: str, coord: tuple[int, int]):
    """Create a minimal AgentConfig with required fields."""
    from backend.schemas import AgentConfig, AgentScratch, AgentSpatial
    return AgentConfig(
        name=name,
        coord=coord,
        currently=f"{name} is standing around",
        scratch=AgentScratch(
            age=30,
            innate="friendly, curious",
            learned=f"{name} is a town resident",
            lifestyle="wakes at 7am, sleeps at 10pm",
            daily_plan="morning routine, work, leisure, rest",
        ),
        spatial=AgentSpatial(
            address={"home": ["agent-town", "home", "bedroom"]},
            tree={"agent-town": {"cafe": {}, "park": {}, "home": {}}},
        ),
    )


# ---------------------------------------------------------------------------
# Task 1: Core SimulationEngine tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agents_run_concurrently():
    """All 3 agents complete within a time window proving parallelism.

    Each agent's step has a 0.05s simulated delay. If sequential, total would
    be ~0.15s; if parallel, it should be well under 0.15s.
    """
    from backend.simulation.engine import SimulationEngine

    maze = _make_small_maze()
    configs = [
        _make_agent_config("Alice", (5, 5)),
        _make_agent_config("Bob", (5, 5)),
        _make_agent_config("Carol", (5, 5)),
    ]
    engine = SimulationEngine(maze=maze, agents=configs, simulation_id="test-concurrent")

    # Pre-populate agent states (normally done in initialize)
    from backend.simulation.engine import AgentState
    for cfg in configs:
        engine._agent_states[cfg.name] = AgentState(
            name=cfg.name,
            config=cfg,
            coord=cfg.coord,
            path=[],
            current_activity=cfg.currently,
            schedule=[],
        )

    agent_delays = []

    async def fake_agent_step(agent_name, state):
        start = time.monotonic()
        await asyncio.sleep(0.05)
        agent_delays.append(time.monotonic() - start)

    engine._agent_step = fake_agent_step

    start_all = time.monotonic()
    async with asyncio.TaskGroup() as tg:
        for name, state in engine._agent_states.items():
            tg.create_task(engine._agent_step_safe(name, state))
    elapsed = time.monotonic() - start_all

    # With parallelism, 3 agents at 0.05s each should finish well under 0.15s
    # (closer to 0.05s + overhead). Use generous bound of 0.14s.
    assert elapsed < 0.14, f"Agents took {elapsed:.3f}s -- expected parallel (<0.14s)"
    assert len(agent_delays) == 3, "All 3 agents should have run"


@pytest.mark.asyncio
async def test_exception_isolation():
    """One agent's RuntimeError does not cancel or fail other agents."""
    from backend.simulation.engine import SimulationEngine, AgentState

    maze = _make_small_maze()
    configs = [
        _make_agent_config("AgentA", (5, 5)),
        _make_agent_config("AgentB", (5, 5)),
    ]
    engine = SimulationEngine(maze=maze, agents=configs, simulation_id="test-isolation")

    completed_agents = []

    for cfg in configs:
        engine._agent_states[cfg.name] = AgentState(
            name=cfg.name,
            config=cfg,
            coord=cfg.coord,
            path=[],
            current_activity=cfg.currently,
            schedule=[],
        )

    async def raise_for_a(agent_name, state):
        if agent_name == "AgentA":
            raise RuntimeError("LLM timeout for AgentA")
        completed_agents.append(agent_name)

    engine._agent_step = raise_for_a

    # Should NOT raise any exception to the caller
    async with asyncio.TaskGroup() as tg:
        for name, state in engine._agent_states.items():
            tg.create_task(engine._agent_step_safe(name, state))

    assert "AgentB" in completed_agents, "AgentB should complete despite AgentA failing"
    assert "AgentA" not in completed_agents, "AgentA raised an error and did not complete"


@pytest.mark.asyncio
async def test_pause_halts_next_tick():
    """After pause(), engine._running is cleared and tick loop blocks on Event.wait()."""
    from backend.simulation.engine import SimulationEngine

    maze = _make_small_maze()
    engine = SimulationEngine(maze=maze, agents=[], simulation_id="test-pause")

    # Engine starts paused (event is cleared)
    assert not engine._running.is_set(), "Engine should start paused"

    # Set running briefly then pause
    engine._running.set()
    assert engine._running.is_set(), "Engine should be running after set()"

    engine.pause()
    assert not engine._running.is_set(), "Engine should be paused after pause()"

    # Confirm that waiting on the event blocks (times out quickly)
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(engine._running.wait(), timeout=0.05)


@pytest.mark.asyncio
async def test_resume_restores_state():
    """After pause+resume, agent state modifications are preserved (no reset on resume)."""
    from backend.simulation.engine import SimulationEngine, AgentState

    maze = _make_small_maze()
    cfg = _make_agent_config("Alice", (5, 5))
    engine = SimulationEngine(maze=maze, agents=[cfg], simulation_id="test-resume")

    engine._agent_states["Alice"] = AgentState(
        name="Alice",
        config=cfg,
        coord=cfg.coord,
        path=[],
        current_activity="working",
        schedule=[],
    )

    # Pause engine
    engine.pause()
    assert not engine._running.is_set()

    # Mutate agent state while paused
    engine._agent_states["Alice"].current_activity = "paused_test"

    # Resume engine
    engine.resume()
    assert engine._running.is_set()

    # State should be preserved after resume
    assert engine._agent_states["Alice"].current_activity == "paused_test", \
        "Agent state should not be reset on resume"


def test_agent_state_dataclass():
    """AgentState can be created from AgentConfig with mutable fields."""
    from backend.simulation.engine import AgentState

    cfg = _make_agent_config("TestAgent", (3, 4))
    state = AgentState(
        name=cfg.name,
        config=cfg,
        coord=cfg.coord,
        path=[(4, 4), (5, 4)],
        current_activity=cfg.currently,
        schedule=[],
    )

    assert state.name == "TestAgent"
    assert state.coord == (3, 4)
    assert state.path == [(4, 4), (5, 4)]
    assert state.current_activity == cfg.currently

    # Verify mutable -- can update without errors
    state.coord = (5, 5)
    state.path.pop(0)
    state.current_activity = "walking"

    assert state.coord == (5, 5)
    assert state.path == [(5, 4)]
    assert state.current_activity == "walking"


# ---------------------------------------------------------------------------
# Task 2: Initialization, movement pacing, and snapshot tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_initialize_generates_schedules():
    """initialize() generates schedules for all agents and calls reset_simulation."""
    from backend.simulation.engine import SimulationEngine
    from backend.schemas import ScheduleEntry

    maze = _make_small_maze()
    configs = [
        _make_agent_config("Alice", (5, 5)),
        _make_agent_config("Bob", (5, 5)),
    ]
    engine = SimulationEngine(maze=maze, agents=configs, simulation_id="test-init")

    mock_schedule = [
        ScheduleEntry(start_minute=420, duration_minutes=60, describe="wake up"),
        ScheduleEntry(start_minute=480, duration_minutes=60, describe="breakfast"),
        ScheduleEntry(start_minute=540, duration_minutes=60, describe="work"),
    ]

    with (
        patch("backend.simulation.engine.reset_simulation", new_callable=AsyncMock) as mock_reset,
        patch("backend.simulation.engine.generate_daily_schedule", new_callable=AsyncMock) as mock_gen,
        patch("backend.simulation.engine.add_memory", new_callable=AsyncMock),
    ):
        mock_gen.return_value = mock_schedule

        await engine.initialize()

        # reset_simulation should be called with the simulation_id
        mock_reset.assert_called_once_with("test-init")

        # Both agents should have schedules generated
        assert mock_gen.call_count == 2, f"Expected 2 schedule calls, got {mock_gen.call_count}"

        # Both agents should have their schedules set
        assert len(engine._agent_states["Alice"].schedule) == 3
        assert len(engine._agent_states["Bob"].schedule) == 3


@pytest.mark.asyncio
async def test_movement_one_tile_per_tick():
    """Agent advances exactly one tile per tick when a path is set."""
    from backend.simulation.engine import SimulationEngine, AgentState

    maze = _make_small_maze()
    cfg = _make_agent_config("Alice", (5, 5))
    engine = SimulationEngine(maze=maze, agents=[cfg], simulation_id="test-movement")

    engine._agent_states["Alice"] = AgentState(
        name="Alice",
        config=cfg,
        coord=(5, 5),
        path=[(6, 5), (7, 5), (8, 5)],
        current_activity="walking",
        schedule=[],
    )

    with (
        patch("backend.simulation.engine.perceive") as mock_perceive,
        patch("backend.simulation.engine.decide_action", new_callable=AsyncMock),
        patch("backend.simulation.engine.attempt_conversation", new_callable=AsyncMock),
    ):
        from backend.schemas import PerceptionResult
        mock_perceive.return_value = PerceptionResult(
            nearby_events=[], nearby_agents=[], location="agent-town:cafe"
        )

        # First tick — advance one tile
        await engine._agent_step("Alice", engine._agent_states["Alice"])

    assert engine._agent_states["Alice"].coord == (6, 5), \
        f"Expected (6,5), got {engine._agent_states['Alice'].coord}"
    assert engine._agent_states["Alice"].path == [(7, 5), (8, 5)], \
        f"Expected [(7,5),(8,5)], got {engine._agent_states['Alice'].path}"

    with (
        patch("backend.simulation.engine.perceive") as mock_perceive,
        patch("backend.simulation.engine.decide_action", new_callable=AsyncMock),
        patch("backend.simulation.engine.attempt_conversation", new_callable=AsyncMock),
    ):
        from backend.schemas import PerceptionResult
        mock_perceive.return_value = PerceptionResult(
            nearby_events=[], nearby_agents=[], location="agent-town:cafe"
        )

        # Second tick — advance another tile
        await engine._agent_step("Alice", engine._agent_states["Alice"])

    assert engine._agent_states["Alice"].coord == (7, 5), \
        f"Expected (7,5) after second tick, got {engine._agent_states['Alice'].coord}"


@pytest.mark.asyncio
async def test_movement_skips_decide_when_path_exists():
    """When agent has a path, decide_action is NOT called (movement tick only)."""
    from backend.simulation.engine import SimulationEngine, AgentState

    maze = _make_small_maze()
    cfg = _make_agent_config("Alice", (5, 5))
    engine = SimulationEngine(maze=maze, agents=[cfg], simulation_id="test-skip-decide")

    engine._agent_states["Alice"] = AgentState(
        name="Alice",
        config=cfg,
        coord=(5, 5),
        path=[(6, 5)],
        current_activity="walking",
        schedule=[],
    )

    with (
        patch("backend.simulation.engine.perceive") as mock_perceive,
        patch("backend.simulation.engine.decide_action", new_callable=AsyncMock) as mock_decide,
        patch("backend.simulation.engine.attempt_conversation", new_callable=AsyncMock),
    ):
        from backend.schemas import PerceptionResult
        mock_perceive.return_value = PerceptionResult(
            nearby_events=[], nearby_agents=[], location="agent-town"
        )

        await engine._agent_step("Alice", engine._agent_states["Alice"])

        # decide_action should NOT be called during a movement tick
        mock_decide.assert_not_called()


@pytest.mark.asyncio
async def test_decide_computes_new_path():
    """When no path exists, decide_action is called and a new path is computed."""
    from backend.simulation.engine import SimulationEngine, AgentState

    maze = _make_small_maze()
    cfg = _make_agent_config("Alice", (5, 5))
    engine = SimulationEngine(maze=maze, agents=[cfg], simulation_id="test-decide-path")

    engine._agent_states["Alice"] = AgentState(
        name="Alice",
        config=cfg,
        coord=(5, 5),
        path=[],  # Empty path — triggers decide
        current_activity="idle",
        schedule=[],
    )

    from backend.schemas import AgentAction, PerceptionResult
    mock_action = AgentAction(
        destination="cafe",
        activity="getting coffee",
        reasoning="want coffee",
    )

    with (
        patch("backend.simulation.engine.perceive") as mock_perceive,
        patch("backend.simulation.engine.decide_action", new_callable=AsyncMock) as mock_decide,
        patch("backend.simulation.engine.attempt_conversation", new_callable=AsyncMock),
        patch("backend.simulation.engine.add_memory", new_callable=AsyncMock),
    ):
        mock_perceive.return_value = PerceptionResult(
            nearby_events=[], nearby_agents=[], location="agent-town"
        )
        mock_decide.return_value = mock_action

        # Mock maze resolve and find_path
        maze.resolve_destination = MagicMock(return_value=(3, 3))
        maze.find_path = MagicMock(return_value=[(5, 5), (4, 5), (3, 5), (3, 4), (3, 3)])

        await engine._agent_step("Alice", engine._agent_states["Alice"])

    # First element (current position) should be popped — path starts from next tile
    assert engine._agent_states["Alice"].path == [(4, 5), (3, 5), (3, 4), (3, 3)], \
        f"Expected path without first element, got {engine._agent_states['Alice'].path}"
    assert engine._agent_states["Alice"].current_activity == "getting coffee", \
        f"Expected 'getting coffee', got {engine._agent_states['Alice'].current_activity}"


def test_get_snapshot():
    """get_snapshot() returns correct agent positions, activities, and simulation status."""
    from backend.simulation.engine import SimulationEngine, AgentState

    maze = _make_small_maze()
    configs = [
        _make_agent_config("Alice", (3, 3)),
        _make_agent_config("Bob", (7, 7)),
    ]
    engine = SimulationEngine(maze=maze, agents=configs, simulation_id="test-snapshot")

    engine._agent_states["Alice"] = AgentState(
        name="Alice",
        config=configs[0],
        coord=(3, 3),
        path=[],
        current_activity="drinking coffee",
        schedule=[],
    )
    engine._agent_states["Bob"] = AgentState(
        name="Bob",
        config=configs[1],
        coord=(7, 7),
        path=[],
        current_activity="reading",
        schedule=[],
    )

    snapshot = engine.get_snapshot()

    assert "agents" in snapshot
    assert len(snapshot["agents"]) == 2, f"Expected 2 agents, got {len(snapshot['agents'])}"

    agent_names = {a["name"] for a in snapshot["agents"]}
    assert "Alice" in agent_names
    assert "Bob" in agent_names

    alice_data = next(a for a in snapshot["agents"] if a["name"] == "Alice")
    assert alice_data["coord"] == [3, 3], f"Expected [3,3], got {alice_data['coord']}"
    assert alice_data["activity"] == "drinking coffee"

    # Engine starts paused
    assert snapshot["simulation_status"] == "paused", \
        f"Expected 'paused', got {snapshot['simulation_status']}"

    assert "tick_count" in snapshot
