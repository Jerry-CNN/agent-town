"""Unit and integration tests for event injection pipeline (Phase 6, Plan 01).

TDD: Tests written first (RED), then implementation makes them pass (GREEN).
All cognition calls are mocked -- no real LLM calls or ChromaDB I/O.

Covers:
  - WSMessage schema accepts "inject_event" type (EVT-02, EVT-03)
  - engine.inject_event() broadcast: stores memories for all agents with importance=8
  - engine.inject_event() whisper: stores memory only for named target
  - engine.inject_event() invalid target: logs warning, stores nothing
  - ws.py handler branch: dispatches inject_event, validates empty text, invalid mode
  - ws.py handler: broadcasts type="event" confirmation to all clients
"""
import json
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Shared helpers (mirrors test_simulation.py patterns)
# ---------------------------------------------------------------------------

SMALL_MAP_CONFIG = {
    "world": "agent-town",
    "tile_size": 32,
    "size": [10, 10],
    "tile_address_keys": ["world", "sector", "arena"],
    "tiles": [
        *[{"coord": [x, 0], "collision": True} for x in range(10)],
        *[{"coord": [x, 9], "collision": True} for x in range(10)],
        *[{"coord": [0, y], "collision": True} for y in range(1, 9)],
        *[{"coord": [9, y], "collision": True} for y in range(1, 9)],
        {"coord": [3, 3], "address": ["cafe", "seating"]},
        {"coord": [4, 3], "address": ["cafe", "seating"]},
    ],
}


def _make_small_maze():
    from backend.simulation.world import Maze
    return Maze(SMALL_MAP_CONFIG)


def _make_agent_config(name: str, coord: tuple[int, int]):
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


def _make_lifespan_patches(mock_engine):
    """Return a list of context managers that patch all lifespan dependencies.

    Mirrors the pattern in test_simulation.py _make_lifespan_patches.
    """
    from unittest.mock import AsyncMock, MagicMock, patch
    from backend.simulation.connection_manager import ConnectionManager

    mock_agent = _make_agent_config("Alice", (5, 5))

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


# ---------------------------------------------------------------------------
# Task 1: Schema and engine.inject_event() tests
# ---------------------------------------------------------------------------


def test_ws_message_accepts_inject_event_type():
    """WSMessage Pydantic model should accept type='inject_event' without validation error."""
    from backend.schemas import WSMessage

    msg = WSMessage(
        type="inject_event",
        payload={"text": "stock crash", "mode": "broadcast"},
        timestamp=time.time(),
    )
    assert msg.type == "inject_event"


def test_ws_message_inject_event_serializes():
    """WSMessage with inject_event type can be serialized and deserialized (JSON round-trip)."""
    from backend.schemas import WSMessage

    msg = WSMessage(
        type="inject_event",
        payload={"text": "wedding tomorrow", "mode": "whisper", "target": "Alice"},
        timestamp=1234567890.0,
    )
    serialized = msg.model_dump_json()
    restored = WSMessage.model_validate_json(serialized)
    assert restored.type == "inject_event"
    assert restored.payload["text"] == "wedding tomorrow"
    assert restored.payload["target"] == "Alice"


@pytest.mark.asyncio
async def test_inject_event_broadcast_stores_all_agents():
    """engine.inject_event(mode='broadcast') calls add_memory for ALL agents in _agent_states."""
    from backend.simulation.engine import SimulationEngine, AgentState

    maze = _make_small_maze()
    configs = [
        _make_agent_config("Alice", (5, 5)),
        _make_agent_config("Bob", (5, 6)),
        _make_agent_config("Carol", (5, 7)),
    ]
    engine = SimulationEngine(maze=maze, agents=configs, simulation_id="test-inject-broadcast")

    for cfg in configs:
        engine._agent_states[cfg.name] = AgentState(
            name=cfg.name,
            config=cfg,
            coord=cfg.coord,
            path=[],
            current_activity=cfg.currently,
            schedule=[],
        )

    with patch("backend.simulation.engine.add_memory", new_callable=AsyncMock) as mock_add:
        await engine.inject_event(text="stock crash", mode="broadcast")

    # Must be called once for each of the 3 agents
    assert mock_add.call_count == 3, f"Expected 3 add_memory calls, got {mock_add.call_count}"

    # Each call must use importance=8 and memory_type="event"
    for call in mock_add.call_args_list:
        kwargs = call.kwargs if call.kwargs else {}
        args = call.args if call.args else ()
        # Check via keyword args (the engine uses keyword args per the plan)
        assert kwargs.get("importance") == 8, f"Expected importance=8, got {kwargs.get('importance')}"
        assert kwargs.get("memory_type") == "event", f"Expected memory_type='event', got {kwargs.get('memory_type')}"
        assert "Event: stock crash" in kwargs.get("content", ""), \
            f"Expected content to contain 'Event: stock crash', got {kwargs.get('content')}"

    # All 3 agent names must appear in the calls
    called_agents = {call.kwargs.get("agent_id") for call in mock_add.call_args_list}
    assert called_agents == {"Alice", "Bob", "Carol"}, \
        f"Expected all agents, got {called_agents}"


@pytest.mark.asyncio
async def test_inject_event_whisper_stores_only_target():
    """engine.inject_event(mode='whisper', target='Alice') stores memory ONLY for Alice."""
    from backend.simulation.engine import SimulationEngine, AgentState

    maze = _make_small_maze()
    configs = [
        _make_agent_config("Alice", (5, 5)),
        _make_agent_config("Bob", (5, 6)),
        _make_agent_config("Carol", (5, 7)),
    ]
    engine = SimulationEngine(maze=maze, agents=configs, simulation_id="test-inject-whisper")

    for cfg in configs:
        engine._agent_states[cfg.name] = AgentState(
            name=cfg.name,
            config=cfg,
            coord=cfg.coord,
            path=[],
            current_activity=cfg.currently,
            schedule=[],
        )

    with patch("backend.simulation.engine.add_memory", new_callable=AsyncMock) as mock_add:
        await engine.inject_event(text="secret news", mode="whisper", target="Alice")

    # Must be called exactly once (only Alice)
    assert mock_add.call_count == 1, f"Expected 1 add_memory call (whisper), got {mock_add.call_count}"

    call = mock_add.call_args_list[0]
    kwargs = call.kwargs
    assert kwargs.get("agent_id") == "Alice", f"Expected agent_id='Alice', got {kwargs.get('agent_id')}"
    assert kwargs.get("importance") == 8
    assert kwargs.get("memory_type") == "event"


@pytest.mark.asyncio
async def test_inject_event_invalid_target_stores_nothing():
    """engine.inject_event(mode='whisper', target='NonExistent') logs warning, stores nothing."""
    from backend.simulation.engine import SimulationEngine, AgentState

    maze = _make_small_maze()
    configs = [
        _make_agent_config("Alice", (5, 5)),
        _make_agent_config("Bob", (5, 6)),
    ]
    engine = SimulationEngine(maze=maze, agents=configs, simulation_id="test-inject-invalid")

    for cfg in configs:
        engine._agent_states[cfg.name] = AgentState(
            name=cfg.name,
            config=cfg,
            coord=cfg.coord,
            path=[],
            current_activity=cfg.currently,
            schedule=[],
        )

    with patch("backend.simulation.engine.add_memory", new_callable=AsyncMock) as mock_add:
        await engine.inject_event(text="secret", mode="whisper", target="NonExistent")

    # No add_memory calls should happen for an unknown target
    assert mock_add.call_count == 0, \
        f"Expected 0 add_memory calls for unknown target, got {mock_add.call_count}"


@pytest.mark.asyncio
async def test_inject_event_invalid_mode_stores_nothing():
    """engine.inject_event(mode='invalid') logs warning and stores nothing."""
    from backend.simulation.engine import SimulationEngine, AgentState

    maze = _make_small_maze()
    configs = [_make_agent_config("Alice", (5, 5))]
    engine = SimulationEngine(maze=maze, agents=configs, simulation_id="test-inject-mode")

    for cfg in configs:
        engine._agent_states[cfg.name] = AgentState(
            name=cfg.name,
            config=cfg,
            coord=cfg.coord,
            path=[],
            current_activity=cfg.currently,
            schedule=[],
        )

    with patch("backend.simulation.engine.add_memory", new_callable=AsyncMock) as mock_add:
        await engine.inject_event(text="some event", mode="invalid_mode")

    assert mock_add.call_count == 0, \
        f"Expected 0 add_memory calls for invalid mode, got {mock_add.call_count}"


@pytest.mark.asyncio
async def test_inject_event_truncates_long_text():
    """engine.inject_event() truncates event text to 500 characters (T-06-03 DoS mitigation)."""
    from backend.simulation.engine import SimulationEngine, AgentState

    maze = _make_small_maze()
    cfg = _make_agent_config("Alice", (5, 5))
    engine = SimulationEngine(maze=maze, agents=[cfg], simulation_id="test-inject-truncate")
    engine._agent_states["Alice"] = AgentState(
        name="Alice",
        config=cfg,
        coord=cfg.coord,
        path=[],
        current_activity=cfg.currently,
        schedule=[],
    )

    long_text = "x" * 600  # 600 chars — must be truncated to 500

    with patch("backend.simulation.engine.add_memory", new_callable=AsyncMock) as mock_add:
        await engine.inject_event(text=long_text, mode="broadcast")

    assert mock_add.call_count == 1
    stored_content = mock_add.call_args_list[0].kwargs.get("content", "")
    # Content format is "Event: {text[:500]}" — total length is "Event: " (7) + 500 = 507
    assert len(stored_content) <= 507, \
        f"Content should be at most 507 chars after truncation, got {len(stored_content)}"
    # Verify the text was actually truncated
    assert "x" * 500 in stored_content
    assert "x" * 600 not in stored_content


@pytest.mark.asyncio
async def test_inject_event_broadcast_uses_simulation_id():
    """engine.inject_event() passes self.simulation_id to add_memory."""
    from backend.simulation.engine import SimulationEngine, AgentState

    maze = _make_small_maze()
    cfg = _make_agent_config("Alice", (5, 5))
    engine = SimulationEngine(maze=maze, agents=[cfg], simulation_id="my-sim-42")
    engine._agent_states["Alice"] = AgentState(
        name="Alice",
        config=cfg,
        coord=cfg.coord,
        path=[],
        current_activity=cfg.currently,
        schedule=[],
    )

    with patch("backend.simulation.engine.add_memory", new_callable=AsyncMock) as mock_add:
        await engine.inject_event(text="test event", mode="broadcast")

    assert mock_add.call_count == 1
    kwargs = mock_add.call_args_list[0].kwargs
    assert kwargs.get("simulation_id") == "my-sim-42", \
        f"Expected simulation_id='my-sim-42', got {kwargs.get('simulation_id')}"


# ---------------------------------------------------------------------------
# Task 2: ws.py handler integration tests
# ---------------------------------------------------------------------------


def test_ws_inject_event_broadcast():
    """Sending inject_event WSMessage with mode='broadcast' calls engine.inject_event and
    broadcasts a type='event' confirmation to all connected clients."""
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
    mock_engine.inject_event = AsyncMock()

    inject_msg = json.dumps({
        "type": "inject_event",
        "payload": {"text": "stock crash", "mode": "broadcast"},
        "timestamp": time.time(),
    })

    patches = _make_lifespan_patches(mock_engine)
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
        with TestClient(app) as client:
            with client.websocket_connect("/ws") as ws:
                ws.receive_text()  # Consume snapshot
                ws.send_text(inject_msg)
                # Receive the event broadcast confirmation
                response_text = ws.receive_text()

    data = json.loads(response_text)
    assert data["type"] == "event", f"Expected 'event' confirmation, got {data['type']}"
    assert "stock crash" in data["payload"]["text"], \
        f"Expected event text in payload, got {data['payload']}"
    assert "broadcast" in data["payload"]["text"].lower() or "Event broadcast" in data["payload"]["text"], \
        f"Expected broadcast label format, got {data['payload']['text']}"

    # engine.inject_event must have been awaited with correct args
    mock_engine.inject_event.assert_called_once()
    call_kwargs = mock_engine.inject_event.call_args.kwargs
    assert call_kwargs.get("text") == "stock crash"
    assert call_kwargs.get("mode") == "broadcast"


def test_ws_inject_event_whisper():
    """Sending inject_event with mode='whisper' and target='Alice' calls engine.inject_event
    with the correct arguments."""
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
    mock_engine.inject_event = AsyncMock()

    inject_msg = json.dumps({
        "type": "inject_event",
        "payload": {"text": "secret news", "mode": "whisper", "target": "Alice"},
        "timestamp": time.time(),
    })

    patches = _make_lifespan_patches(mock_engine)
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
        with TestClient(app) as client:
            with client.websocket_connect("/ws") as ws:
                ws.receive_text()  # Consume snapshot
                ws.send_text(inject_msg)
                response_text = ws.receive_text()

    data = json.loads(response_text)
    assert data["type"] == "event", f"Expected 'event' confirmation, got {data['type']}"
    assert "Alice" in data["payload"]["text"], \
        f"Expected Alice in whisper label, got {data['payload']['text']}"

    mock_engine.inject_event.assert_called_once()
    call_kwargs = mock_engine.inject_event.call_args.kwargs
    assert call_kwargs.get("mode") == "whisper"
    assert call_kwargs.get("target") == "Alice"


def test_ws_inject_event_empty_text_returns_error():
    """Sending inject_event with empty text returns type='error' and does NOT call engine.inject_event."""
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
    mock_engine.inject_event = AsyncMock()

    inject_msg = json.dumps({
        "type": "inject_event",
        "payload": {"text": "", "mode": "broadcast"},
        "timestamp": time.time(),
    })

    patches = _make_lifespan_patches(mock_engine)
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
        with TestClient(app) as client:
            with client.websocket_connect("/ws") as ws:
                ws.receive_text()  # Consume snapshot
                ws.send_text(inject_msg)
                response_text = ws.receive_text()

    data = json.loads(response_text)
    assert data["type"] == "error", f"Expected 'error' for empty text, got {data['type']}"
    assert "Event text is empty" in data["payload"].get("detail", ""), \
        f"Expected 'Event text is empty' in error detail, got {data['payload']}"

    # engine.inject_event must NOT be called
    mock_engine.inject_event.assert_not_called()


def test_ws_inject_event_whitespace_only_returns_error():
    """Sending inject_event with whitespace-only text returns type='error' (T-06-01)."""
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
    mock_engine.inject_event = AsyncMock()

    inject_msg = json.dumps({
        "type": "inject_event",
        "payload": {"text": "   \t\n  ", "mode": "broadcast"},
        "timestamp": time.time(),
    })

    patches = _make_lifespan_patches(mock_engine)
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
        with TestClient(app) as client:
            with client.websocket_connect("/ws") as ws:
                ws.receive_text()  # Consume snapshot
                ws.send_text(inject_msg)
                response_text = ws.receive_text()

    data = json.loads(response_text)
    assert data["type"] == "error", f"Expected 'error' for whitespace-only text, got {data['type']}"
    mock_engine.inject_event.assert_not_called()


def test_ws_inject_event_invalid_mode_returns_error():
    """Sending inject_event with mode='invalid_mode' returns type='error' (T-06-02)."""
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
    mock_engine.inject_event = AsyncMock()

    inject_msg = json.dumps({
        "type": "inject_event",
        "payload": {"text": "some event", "mode": "invalid_mode"},
        "timestamp": time.time(),
    })

    patches = _make_lifespan_patches(mock_engine)
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
        with TestClient(app) as client:
            with client.websocket_connect("/ws") as ws:
                ws.receive_text()  # Consume snapshot
                ws.send_text(inject_msg)
                response_text = ws.receive_text()

    data = json.loads(response_text)
    assert data["type"] == "error", f"Expected 'error' for invalid mode, got {data['type']}"
    assert "Invalid mode" in data["payload"].get("detail", ""), \
        f"Expected 'Invalid mode' in error detail, got {data['payload']}"

    mock_engine.inject_event.assert_not_called()


def test_ws_inject_event_broadcast_label_format():
    """Broadcast injection sends label 'Event broadcast: {text}' per D-09."""
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
    mock_engine.inject_event = AsyncMock()

    inject_msg = json.dumps({
        "type": "inject_event",
        "payload": {"text": "wedding tomorrow", "mode": "broadcast"},
        "timestamp": time.time(),
    })

    patches = _make_lifespan_patches(mock_engine)
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
        with TestClient(app) as client:
            with client.websocket_connect("/ws") as ws:
                ws.receive_text()  # Consume snapshot
                ws.send_text(inject_msg)
                response_text = ws.receive_text()

    data = json.loads(response_text)
    assert data["payload"]["text"] == "Event broadcast: wedding tomorrow", \
        f"Expected D-09 label format, got {data['payload']['text']}"


def test_ws_inject_event_whisper_label_format():
    """Whisper injection sends label 'Whispered to {target}: {text}' per D-09."""
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
    mock_engine.inject_event = AsyncMock()

    inject_msg = json.dumps({
        "type": "inject_event",
        "payload": {"text": "the mayor is corrupt", "mode": "whisper", "target": "Bob"},
        "timestamp": time.time(),
    })

    patches = _make_lifespan_patches(mock_engine)
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
        with TestClient(app) as client:
            with client.websocket_connect("/ws") as ws:
                ws.receive_text()  # Consume snapshot
                ws.send_text(inject_msg)
                response_text = ws.receive_text()

    data = json.loads(response_text)
    assert data["payload"]["text"] == "Whispered to Bob: the mayor is corrupt", \
        f"Expected D-09 whisper label format, got {data['payload']['text']}"
