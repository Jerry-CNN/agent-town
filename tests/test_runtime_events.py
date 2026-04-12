"""Integration tests for Event lifecycle and Agent wrapper routing in SimulationEngine.

TDD: Tests written first (RED) to verify requirements EVTS-01, EVTS-02, EVTS-03, ARCH-02.
All cognition calls are mocked — no real LLM calls.

Requirements covered:
  EVTS-01: inject_event() creates Event objects with status='active'
  EVTS-02: heard_by is updated when an agent perceives a whisper event
  EVTS-03: Events older than EVENT_EXPIRY_TICKS are removed from _active_events
  ARCH-02: _agent_step() routes perceive and decide through Agent wrappers
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.schemas.events import Event, EVENT_EXPIRY_TICKS


# ---------------------------------------------------------------------------
# Shared fixtures (matching test_simulation.py patterns)
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


# ---------------------------------------------------------------------------
# EVTS-01: inject_event() creates Event objects in _active_events
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_inject_event_creates_active_event():
    """EVTS-01: inject_event() creates an Event object with status='active' in _active_events."""
    from backend.simulation.engine import SimulationEngine
    from backend.agents.agent import Agent

    maze = _make_small_maze()
    cfg = _make_agent_config("Alice", (5, 5))
    engine = SimulationEngine(maze=maze, agents=[cfg], simulation_id="test-evts-01")
    engine._agents["Alice"] = Agent(
        name="Alice",
        config=cfg,
        coord=(5, 5),
        path=[],
        current_activity="idle",
        schedule=[],
    )

    with patch("backend.simulation.engine.add_memory", new_callable=AsyncMock):
        await engine.inject_event(text="stock crash", mode="broadcast")

    # EVTS-01: An Event must be stored in _active_events
    assert len(engine._active_events) == 1, (
        f"Expected 1 event in _active_events, got {len(engine._active_events)}"
    )
    ev = list(engine._active_events.values())[0]
    assert ev.status == "active", f"Expected status='active', got '{ev.status}'"
    assert ev.text == "stock crash", f"Expected text='stock crash', got '{ev.text}'"
    assert ev.mode == "broadcast", f"Expected mode='broadcast', got '{ev.mode}'"


@pytest.mark.asyncio
async def test_inject_whisper_creates_event_with_target():
    """EVTS-01: inject_event() in whisper mode creates an Event with correct target."""
    from backend.simulation.engine import SimulationEngine
    from backend.agents.agent import Agent

    maze = _make_small_maze()
    cfg = _make_agent_config("Alice", (5, 5))
    engine = SimulationEngine(maze=maze, agents=[cfg], simulation_id="test-evts-01-whisper")
    engine._agents["Alice"] = Agent(
        name="Alice",
        config=cfg,
        coord=(5, 5),
        path=[],
        current_activity="idle",
        schedule=[],
    )

    with patch("backend.simulation.engine.add_memory", new_callable=AsyncMock):
        await engine.inject_event(text="secret meeting tonight", mode="whisper", target="Alice")

    assert len(engine._active_events) == 1, (
        f"Expected 1 event in _active_events, got {len(engine._active_events)}"
    )
    ev = list(engine._active_events.values())[0]
    assert ev.mode == "whisper", f"Expected mode='whisper', got '{ev.mode}'"
    assert ev.target == "Alice", f"Expected target='Alice', got '{ev.target}'"
    assert ev.status == "active", f"Expected status='active', got '{ev.status}'"


# ---------------------------------------------------------------------------
# EVTS-02: heard_by is updated on whisper perception
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_heard_by_updated_on_whisper_perception():
    """EVTS-02: heard_by is updated with agent name after _agent_step perceives a whisper event."""
    from backend.simulation.engine import SimulationEngine
    from backend.agents.agent import Agent
    from backend.schemas import PerceptionResult

    maze = _make_small_maze()
    cfg = _make_agent_config("Alice", (5, 5))
    engine = SimulationEngine(maze=maze, agents=[cfg], simulation_id="test-evts-02")
    engine._agents["Alice"] = Agent(
        name="Alice",
        config=cfg,
        coord=(5, 5),
        path=[(6, 5)],  # path non-empty -> _agent_step returns after perceive
        current_activity="idle",
        schedule=[],
    )

    # Pre-populate a whisper event and a broadcast event
    whisper_event = Event(
        text="secret rumor",
        mode="whisper",
        target="Alice",
        status="active",
        created_tick=0,
        expires_after_ticks=EVENT_EXPIRY_TICKS,
    )
    broadcast_event = Event(
        text="public announcement",
        mode="broadcast",
        status="active",
        created_tick=0,
        expires_after_ticks=EVENT_EXPIRY_TICKS,
    )
    engine._active_events["wkey"] = whisper_event
    engine._active_events["bkey"] = broadcast_event

    mock_perception = PerceptionResult(
        nearby_events=[], nearby_agents=[], location="agent-town:cafe"
    )

    with patch.object(engine._agents["Alice"], "perceive", return_value=mock_perception):
        await engine._agent_step("Alice", engine._agents["Alice"])

    # EVTS-02: heard_by should contain "Alice" for the whisper event
    assert "Alice" in whisper_event.heard_by, (
        f"Expected 'Alice' in whisper_event.heard_by, got {whisper_event.heard_by}"
    )
    # Broadcast events must NOT track heard_by (D-09)
    assert broadcast_event.heard_by == [], (
        f"Expected empty heard_by for broadcast, got {broadcast_event.heard_by}"
    )


# ---------------------------------------------------------------------------
# EVTS-03: Expired events are removed from _active_events
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_expired_events_removed_after_tick():
    """EVTS-03: Events older than EVENT_EXPIRY_TICKS are removed after tick advancement."""
    from backend.simulation.engine import SimulationEngine

    maze = _make_small_maze()
    cfg = _make_agent_config("Alice", (5, 5))
    engine = SimulationEngine(maze=maze, agents=[cfg], simulation_id="test-evts-03")

    # Create event that will expire when _tick_count reaches EVENT_EXPIRY_TICKS
    event = Event(
        text="will expire soon",
        mode="broadcast",
        status="active",
        created_tick=0,
        expires_after_ticks=EVENT_EXPIRY_TICKS,
    )
    engine._active_events["expiry-key"] = event

    # Set tick count so that after increment event is expired:
    # is_expired(tick) = tick - created_tick >= expires_after_ticks
    # After increment: tick = EVENT_EXPIRY_TICKS, 10-0 >= 10 => True
    engine._tick_count = EVENT_EXPIRY_TICKS - 1

    # Advance tick count and call the real engine purge helper (WR-04: don't replicate
    # the loop inline — call the method that _tick_loop actually uses).
    engine._tick_count += 1
    engine._purge_expired_events()

    assert len(engine._active_events) == 0, (
        f"Expected 0 events after expiry, got {len(engine._active_events)}: {engine._active_events}"
    )


# ---------------------------------------------------------------------------
# ARCH-02: _agent_step() uses Agent.perceive() and Agent.decide() wrappers
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_agent_step_uses_agent_perceive():
    """ARCH-02: _agent_step() calls agent.perceive() not the module-level perceive()."""
    from backend.simulation.engine import SimulationEngine
    from backend.agents.agent import Agent
    from backend.schemas import PerceptionResult

    maze = _make_small_maze()
    cfg = _make_agent_config("Alice", (5, 5))
    engine = SimulationEngine(maze=maze, agents=[cfg], simulation_id="test-arch02-perceive")

    engine._agents["Alice"] = Agent(
        name="Alice",
        config=cfg,
        coord=(5, 5),
        path=[(6, 5)],  # path non-empty -> returns after perceive, no decide needed
        current_activity="idle",
        schedule=[],
    )

    mock_perception = PerceptionResult(
        nearby_events=[], nearby_agents=[], location="agent-town:cafe"
    )

    with patch.object(engine._agents["Alice"], "perceive", return_value=mock_perception) as mock_perceive:
        await engine._agent_step("Alice", engine._agents["Alice"])

    # ARCH-02: agent.perceive() must be called with maze= and all_agents=
    mock_perceive.assert_called_once()
    call_kwargs = mock_perceive.call_args
    assert "maze" in call_kwargs.kwargs, (
        f"Expected maze= kwarg in agent.perceive() call, got {call_kwargs}"
    )
    assert "all_agents" in call_kwargs.kwargs, (
        f"Expected all_agents= kwarg in agent.perceive() call, got {call_kwargs}"
    )


@pytest.mark.asyncio
async def test_agent_step_uses_agent_decide():
    """ARCH-02: _agent_step() calls agent.decide() not the module-level decide_action()."""
    from backend.simulation.engine import SimulationEngine
    from backend.agents.agent import Agent
    from backend.schemas import AgentAction, PerceptionResult

    maze = _make_small_maze()
    cfg = _make_agent_config("Alice", (5, 5))
    engine = SimulationEngine(maze=maze, agents=[cfg], simulation_id="test-arch02-decide")

    engine._agents["Alice"] = Agent(
        name="Alice",
        config=cfg,
        coord=(5, 5),
        path=[],  # empty path -> triggers decide phase
        current_activity="idle",
        schedule=[],
    )

    mock_perception = PerceptionResult(
        nearby_events=[], nearby_agents=[], location="agent-town"
    )
    mock_action = AgentAction(
        destination="cafe",
        activity="getting coffee",
        reasoning="want coffee",
    )

    with (
        patch.object(engine._agents["Alice"], "perceive", return_value=mock_perception),
        patch.object(engine._agents["Alice"], "decide", new_callable=AsyncMock, return_value=mock_action) as mock_decide,
        patch("backend.simulation.engine.add_memory", new_callable=AsyncMock),
    ):
        maze.resolve_destination = MagicMock(return_value=(3, 3))
        maze.find_path = MagicMock(return_value=[(5, 5), (4, 5), (3, 3)])

        await engine._agent_step("Alice", engine._agents["Alice"])

    # ARCH-02: agent.decide() must be called (not module-level decide_action)
    mock_decide.assert_called_once()
