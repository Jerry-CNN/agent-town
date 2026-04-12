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
    from backend.agents.agent import Agent
    for cfg in configs:
        engine._agents[cfg.name] = Agent(
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
        for name, agent in engine._agents.items():
            tg.create_task(engine._agent_step_safe(name, agent))
    elapsed = time.monotonic() - start_all

    # With parallelism, 3 agents at 0.05s each should finish well under 0.15s
    # (closer to 0.05s + overhead). Use generous bound of 0.14s.
    assert elapsed < 0.14, f"Agents took {elapsed:.3f}s -- expected parallel (<0.14s)"
    assert len(agent_delays) == 3, "All 3 agents should have run"


@pytest.mark.asyncio
async def test_exception_isolation():
    """One agent's RuntimeError does not cancel or fail other agents."""
    from backend.simulation.engine import SimulationEngine
    from backend.agents.agent import Agent

    maze = _make_small_maze()
    configs = [
        _make_agent_config("AgentA", (5, 5)),
        _make_agent_config("AgentB", (5, 5)),
    ]
    engine = SimulationEngine(maze=maze, agents=configs, simulation_id="test-isolation")

    completed_agents = []

    for cfg in configs:
        engine._agents[cfg.name] = Agent(
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
        for name, agent in engine._agents.items():
            tg.create_task(engine._agent_step_safe(name, agent))

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
    from backend.simulation.engine import SimulationEngine
    from backend.agents.agent import Agent

    maze = _make_small_maze()
    cfg = _make_agent_config("Alice", (5, 5))
    engine = SimulationEngine(maze=maze, agents=[cfg], simulation_id="test-resume")

    engine._agents["Alice"] = Agent(
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
    engine._agents["Alice"].current_activity = "paused_test"

    # Resume engine
    engine.resume()
    assert engine._running.is_set()

    # State should be preserved after resume
    assert engine._agents["Alice"].current_activity == "paused_test", \
        "Agent state should not be reset on resume"


def test_agent_dataclass():
    """Agent can be created from AgentConfig with mutable fields."""
    from backend.agents.agent import Agent

    cfg = _make_agent_config("TestAgent", (3, 4))
    agent = Agent(
        name=cfg.name,
        config=cfg,
        coord=cfg.coord,
        path=[(4, 4), (5, 4)],
        current_activity=cfg.currently,
        schedule=[],
    )

    assert agent.name == "TestAgent"
    assert agent.coord == (3, 4)
    assert agent.path == [(4, 4), (5, 4)]
    assert agent.current_activity == cfg.currently

    # Verify mutable -- can update without errors
    agent.coord = (5, 5)
    agent.path.pop(0)
    agent.current_activity = "walking"

    assert agent.coord == (5, 5)
    assert agent.path == [(5, 4)]
    assert agent.current_activity == "walking"


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
        assert len(engine._agents["Alice"].schedule) == 3
        assert len(engine._agents["Bob"].schedule) == 3


@pytest.mark.asyncio
async def test_movement_one_tile_per_tick():
    """Agent advances exactly one tile per tick when a path is set."""
    from backend.simulation.engine import SimulationEngine
    from backend.agents.agent import Agent

    maze = _make_small_maze()
    cfg = _make_agent_config("Alice", (5, 5))
    engine = SimulationEngine(maze=maze, agents=[cfg], simulation_id="test-movement")

    engine._agents["Alice"] = Agent(
        name="Alice",
        config=cfg,
        coord=(5, 5),
        path=[(6, 5), (7, 5), (8, 5)],
        current_activity="walking",
        schedule=[],
    )

    from backend.schemas import PerceptionResult
    mock_perception = PerceptionResult(
        nearby_events=[], nearby_agents=[], location="agent-town:cafe"
    )

    with patch.object(engine._agents["Alice"], "perceive", return_value=mock_perception):
        # First tick — advance one tile
        await engine._agent_step("Alice", engine._agents["Alice"])

    assert engine._agents["Alice"].coord == (6, 5), \
        f"Expected (6,5), got {engine._agents['Alice'].coord}"
    assert engine._agents["Alice"].path == [(7, 5), (8, 5)], \
        f"Expected [(7,5),(8,5)], got {engine._agents['Alice'].path}"

    with patch.object(engine._agents["Alice"], "perceive", return_value=mock_perception):
        # Second tick — advance another tile
        await engine._agent_step("Alice", engine._agents["Alice"])

    assert engine._agents["Alice"].coord == (7, 5), \
        f"Expected (7,5) after second tick, got {engine._agents['Alice'].coord}"


@pytest.mark.asyncio
async def test_movement_skips_decide_when_path_exists():
    """When agent has a path, decide_action is NOT called (movement tick only)."""
    from backend.simulation.engine import SimulationEngine
    from backend.agents.agent import Agent

    maze = _make_small_maze()
    cfg = _make_agent_config("Alice", (5, 5))
    engine = SimulationEngine(maze=maze, agents=[cfg], simulation_id="test-skip-decide")

    engine._agents["Alice"] = Agent(
        name="Alice",
        config=cfg,
        coord=(5, 5),
        path=[(6, 5)],
        current_activity="walking",
        schedule=[],
    )

    from backend.schemas import PerceptionResult
    mock_perception = PerceptionResult(
        nearby_events=[], nearby_agents=[], location="agent-town"
    )

    with (
        patch.object(engine._agents["Alice"], "perceive", return_value=mock_perception),
        patch.object(engine._agents["Alice"], "decide", new_callable=AsyncMock) as mock_decide,
    ):
        await engine._agent_step("Alice", engine._agents["Alice"])

        # decide should NOT be called during a movement tick
        mock_decide.assert_not_called()


@pytest.mark.asyncio
async def test_decide_computes_new_path():
    """When no path exists, decide_action is called and a new path is computed."""
    from backend.simulation.engine import SimulationEngine
    from backend.agents.agent import Agent

    maze = _make_small_maze()
    cfg = _make_agent_config("Alice", (5, 5))
    engine = SimulationEngine(maze=maze, agents=[cfg], simulation_id="test-decide-path")

    engine._agents["Alice"] = Agent(
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

    mock_perception = PerceptionResult(
        nearby_events=[], nearby_agents=[], location="agent-town"
    )

    with (
        patch.object(engine._agents["Alice"], "perceive", return_value=mock_perception),
        patch.object(engine._agents["Alice"], "decide", new_callable=AsyncMock, return_value=mock_action),
        patch("backend.simulation.engine.add_memory", new_callable=AsyncMock),
    ):
        # Mock maze resolve and find_path
        maze.resolve_destination = MagicMock(return_value=(3, 3))
        maze.find_path = MagicMock(return_value=[(5, 5), (4, 5), (3, 5), (3, 4), (3, 3)])

        await engine._agent_step("Alice", engine._agents["Alice"])

    # First element (current position) should be popped — path starts from next tile
    assert engine._agents["Alice"].path == [(4, 5), (3, 5), (3, 4), (3, 3)], \
        f"Expected path without first element, got {engine._agents['Alice'].path}"
    assert engine._agents["Alice"].current_activity == "getting coffee", \
        f"Expected 'getting coffee', got {engine._agents['Alice'].current_activity}"


def test_get_snapshot():
    """get_snapshot() returns correct agent positions, activities, and simulation status."""
    from backend.simulation.engine import SimulationEngine
    from backend.agents.agent import Agent

    maze = _make_small_maze()
    configs = [
        _make_agent_config("Alice", (3, 3)),
        _make_agent_config("Bob", (7, 7)),
    ]
    engine = SimulationEngine(maze=maze, agents=configs, simulation_id="test-snapshot")

    engine._agents["Alice"] = Agent(
        name="Alice",
        config=configs[0],
        coord=(3, 3),
        path=[],
        current_activity="drinking coffee",
        schedule=[],
    )
    engine._agents["Bob"] = Agent(
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


# ---------------------------------------------------------------------------
# Task 1 (Plan 02): ConnectionManager and WebSocket transport tests — TDD RED
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connection_manager_broadcast():
    """ConnectionManager broadcasts to all active connections."""
    from backend.simulation.connection_manager import ConnectionManager

    manager = ConnectionManager()

    received_a = []
    received_b = []

    class MockWS:
        def __init__(self, store):
            self._store = store

        async def send_text(self, text):
            self._store.append(text)

    ws_a = MockWS(received_a)
    ws_b = MockWS(received_b)
    manager.active_connections = [ws_a, ws_b]

    await manager.broadcast("hello")

    assert received_a == ["hello"], f"ws_a should receive 'hello', got {received_a}"
    assert received_b == ["hello"], f"ws_b should receive 'hello', got {received_b}"


@pytest.mark.asyncio
async def test_connection_manager_dead_connection():
    """Dead WebSocket connections are removed silently during broadcast."""
    from backend.simulation.connection_manager import ConnectionManager

    manager = ConnectionManager()

    received_good = []

    class GoodWS:
        async def send_text(self, text):
            received_good.append(text)

    class DeadWS:
        async def send_text(self, text):
            raise RuntimeError("Connection lost")

    good = GoodWS()
    dead = DeadWS()
    manager.active_connections = [dead, good]

    # Should NOT raise — dead connection absorbed silently
    await manager.broadcast("data")

    # Dead connection removed from active list
    assert dead not in manager.active_connections, "Dead WS should be removed"
    assert good in manager.active_connections, "Good WS should remain"
    assert received_good == ["data"], "Good WS should still receive the message"


def _make_lifespan_patches(mock_engine):
    """Return a context manager that patches all lifespan dependencies.

    Patches load_all_agents, generate_town_map, Maze, reset_simulation,
    generate_daily_schedule, add_memory, and SimulationEngine so the real
    lifespan can run without disk access or LLM calls, and app.state.engine
    is set to the provided mock_engine.
    """
    from unittest.mock import AsyncMock, MagicMock, patch
    from backend.simulation.connection_manager import ConnectionManager

    mock_agent = _make_agent_config("Alice", (5, 5))
    mock_manager = ConnectionManager()

    # We'll inject our mock engine into lifespan by replacing SimulationEngine
    # constructor with a factory that returns our mock
    class MockEngineFactory:
        def __new__(cls, *args, **kwargs):
            return mock_engine

    patches = [
        patch("backend.main.load_all_agents", return_value=[mock_agent]),
        patch("backend.main.generate_town_map", return_value={
            "world": "test",
            "tile_size": 32,
            "size": [10, 10],
            "tile_address_keys": ["world", "sector", "arena"],
            "tiles": [],
        }),
        patch("backend.main.Maze", return_value=_make_small_maze()),
        patch("backend.main.SimulationEngine", MockEngineFactory),
        patch("backend.simulation.engine.reset_simulation", new_callable=AsyncMock),
        patch("backend.simulation.engine.generate_daily_schedule", new_callable=AsyncMock, return_value=[]),
        patch("backend.simulation.engine.add_memory", new_callable=AsyncMock),
    ]
    return patches


def test_ws_snapshot_on_connect():
    """First message received by a new WebSocket client is type='snapshot'."""
    import json
    import time
    from unittest.mock import MagicMock, AsyncMock, patch
    from starlette.testclient import TestClient
    from backend.main import app

    mock_engine = MagicMock()
    mock_engine.get_snapshot.return_value = {
        "agents": [{"name": "Alice", "coord": [5, 5], "activity": "walking"}],
        "simulation_status": "running",
        "tick_count": 0,
    }
    mock_engine.initialize = AsyncMock()
    mock_engine.run = AsyncMock()
    mock_engine._broadcast_callback = None

    patches = _make_lifespan_patches(mock_engine)
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
        with TestClient(app) as client:
            with client.websocket_connect("/ws") as ws:
                first_message = ws.receive_text()
                data = json.loads(first_message)
                assert data["type"] == "snapshot", f"Expected 'snapshot', got {data['type']}"
                assert "agents" in data["payload"], "Snapshot payload should contain agents"
                assert "simulation_status" in data["payload"], "Snapshot payload should contain simulation_status"


def test_ws_pause_command():
    """Sending a pause WSMessage via WebSocket calls engine.pause()."""
    import json
    import time
    from unittest.mock import MagicMock, AsyncMock
    from starlette.testclient import TestClient
    from backend.main import app

    mock_engine = MagicMock()
    mock_engine.get_snapshot.return_value = {
        "agents": [],
        "simulation_status": "running",
        "tick_count": 0,
    }
    mock_engine.initialize = AsyncMock()
    mock_engine.run = AsyncMock()
    mock_engine._broadcast_callback = None

    pause_msg = json.dumps({"type": "pause", "payload": {}, "timestamp": time.time()})

    patches = _make_lifespan_patches(mock_engine)
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
        with TestClient(app) as client:
            with client.websocket_connect("/ws") as ws:
                ws.receive_text()  # Consume snapshot
                ws.send_text(pause_msg)

    mock_engine.pause.assert_called_once()


def test_ws_resume_command():
    """Sending a resume WSMessage via WebSocket calls engine.resume()."""
    import json
    import time
    from unittest.mock import MagicMock, AsyncMock
    from starlette.testclient import TestClient
    from backend.main import app

    mock_engine = MagicMock()
    mock_engine.get_snapshot.return_value = {
        "agents": [],
        "simulation_status": "paused",
        "tick_count": 0,
    }
    mock_engine.initialize = AsyncMock()
    mock_engine.run = AsyncMock()
    mock_engine._broadcast_callback = None

    resume_msg = json.dumps({"type": "resume", "payload": {}, "timestamp": time.time()})

    patches = _make_lifespan_patches(mock_engine)
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
        with TestClient(app) as client:
            with client.websocket_connect("/ws") as ws:
                ws.receive_text()  # Consume snapshot
                ws.send_text(resume_msg)

    mock_engine.resume.assert_called_once()


@pytest.mark.asyncio
async def test_broadcast_reaches_all_clients():
    """Engine's broadcast_callback sends agent_update to all connected WS clients."""
    import asyncio
    import time
    from backend.simulation.connection_manager import ConnectionManager
    from backend.schemas import WSMessage

    manager = ConnectionManager()
    received = []

    class MockWS:
        async def send_text(self, text):
            received.append(text)

    ws1 = MockWS()
    ws2 = MockWS()
    manager.active_connections = [ws1, ws2]

    # Simulate what the broadcast callback does
    msg = WSMessage(
        type="agent_update",
        payload={"name": "Alice", "coord": [5, 5], "activity": "walking"},
        timestamp=time.time(),
    )
    await manager.broadcast(msg.model_dump_json())

    assert len(received) == 2, f"Both clients should have received message. got {len(received)}"
    for raw in received:
        import json
        data = json.loads(raw)
        assert data["type"] == "agent_update"


# ---------------------------------------------------------------------------
# Task 2 (Plan 02): Lifespan wiring and full lifecycle integration tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_lifecycle():
    """Integration: initialize engine, verify schedules, snapshot, pause/resume."""
    from unittest.mock import AsyncMock, patch
    from backend.simulation.engine import SimulationEngine
    from backend.simulation.connection_manager import ConnectionManager
    from backend.schemas import ScheduleEntry

    maze = _make_small_maze()
    configs = [
        _make_agent_config("Alice", (5, 5)),
        _make_agent_config("Bob", (3, 3)),
    ]

    mock_schedule = [
        ScheduleEntry(start_minute=420, duration_minutes=60, describe="wake up"),
        ScheduleEntry(start_minute=480, duration_minutes=60, describe="breakfast"),
        ScheduleEntry(start_minute=540, duration_minutes=60, describe="work"),
    ]

    with (
        patch("backend.simulation.engine.reset_simulation", new_callable=AsyncMock),
        patch("backend.simulation.engine.generate_daily_schedule", new_callable=AsyncMock, return_value=mock_schedule),
        patch("backend.simulation.engine.add_memory", new_callable=AsyncMock),
    ):
        engine = SimulationEngine(maze=maze, agents=configs, simulation_id="test-lifecycle")

        # Create and wire ConnectionManager
        manager = ConnectionManager()
        broadcast_received = []

        async def fake_callback(data: dict) -> None:
            broadcast_received.append(data)

        engine._broadcast_callback = fake_callback

        # Initialize — generates schedules for both agents
        await engine.initialize()

        # Both agents should have schedules
        assert len(engine._agents["Alice"].schedule) == 3, "Alice should have 3 schedule entries"
        assert len(engine._agents["Bob"].schedule) == 3, "Bob should have 3 schedule entries"

        # Both agents should have initial coords
        assert engine._agents["Alice"].coord == (5, 5)
        assert engine._agents["Bob"].coord == (3, 3)

        # get_snapshot should return 2 agents with correct data
        snapshot = engine.get_snapshot()
        assert len(snapshot["agents"]) == 2
        agent_names = {a["name"] for a in snapshot["agents"]}
        assert "Alice" in agent_names
        assert "Bob" in agent_names

        # Engine starts paused (before run())
        assert snapshot["simulation_status"] == "paused"

        # Pause/resume cycle
        engine.resume()
        assert engine._running.is_set(), "Engine should be running after resume()"

        engine.pause()
        assert not engine._running.is_set(), "Engine should be paused after pause()"

        # get_snapshot reflects paused state
        snapshot2 = engine.get_snapshot()
        assert snapshot2["simulation_status"] == "paused"

        # Resume again
        engine.resume()
        snapshot3 = engine.get_snapshot()
        assert snapshot3["simulation_status"] == "running"


@pytest.mark.asyncio
async def test_broadcast_callback_integration():
    """Engine._emit_agent_update calls the wired broadcast callback correctly."""
    from unittest.mock import AsyncMock, patch
    from backend.simulation.engine import SimulationEngine
    from backend.agents.agent import Agent
    from backend.main import _make_broadcast_callback
    from backend.simulation.connection_manager import ConnectionManager
    import json

    maze = _make_small_maze()
    cfg = _make_agent_config("Alice", (5, 5))
    engine = SimulationEngine(maze=maze, agents=[cfg], simulation_id="test-callback")

    manager = ConnectionManager()
    broadcast_messages = []

    class CapturingWS:
        async def send_text(self, text):
            broadcast_messages.append(json.loads(text))

    manager.active_connections = [CapturingWS()]
    engine._broadcast_callback = _make_broadcast_callback(manager)

    # Pre-populate agent state
    engine._agents["Alice"] = Agent(
        name="Alice",
        config=cfg,
        coord=(5, 5),
        path=[],
        current_activity="walking",
        schedule=[],
    )

    # Directly call the emit method to trigger the broadcast callback
    await engine._emit_agent_update("Alice", engine._agents["Alice"])

    assert len(broadcast_messages) == 1, f"Expected 1 broadcast message, got {len(broadcast_messages)}"
    msg = broadcast_messages[0]
    assert msg["type"] == "agent_update"
    assert msg["payload"]["name"] == "Alice"
    assert msg["payload"]["coord"] == [5, 5]


def test_lifespan_creates_engine():
    """After app startup via lifespan, app.state.engine and connection_manager exist."""
    from unittest.mock import MagicMock, AsyncMock, patch
    from starlette.testclient import TestClient
    from backend.simulation.engine import SimulationEngine
    from backend.simulation.connection_manager import ConnectionManager

    mock_agent = _make_agent_config("Alice", (5, 5))

    # Use the same _make_lifespan_patches pattern — inject a real-ish mock engine
    mock_engine = MagicMock(spec=SimulationEngine)
    mock_engine.initialize = AsyncMock()
    mock_engine.run = AsyncMock()
    mock_engine._broadcast_callback = None
    mock_engine.get_snapshot.return_value = {
        "agents": [], "simulation_status": "running", "tick_count": 0
    }

    patches = _make_lifespan_patches(mock_engine)
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
        from backend.main import app
        with TestClient(app) as client:
            # App lifespan has run — verify state was set
            assert hasattr(app.state, "engine"), "app.state.engine should be set by lifespan"
            assert hasattr(app.state, "connection_manager"), "app.state.connection_manager should be set by lifespan"
            # engine is our mock (wrapped by MockEngineFactory in _make_lifespan_patches)
            assert app.state.engine is mock_engine, "app.state.engine should be the mock engine"
            assert isinstance(app.state.connection_manager, ConnectionManager)
            # initialize() must have been called
            mock_engine.initialize.assert_called_once()
