"""Unit tests for adaptive tick interval computation and cold-start timeout floor.

TDD RED phase — these tests FAIL before the implementation is added to engine.py / agent.py.

Tests:
  1. SimulationEngine.tick_interval returns 10.0 when latency window is empty
  2. SimulationEngine.tick_interval returns 18.0 when gateway._latency_window=[12,12,12]
  3. _agent_step_safe timeout = max(tick_interval * 2, 120)
  4. Cold-start: tick_interval=10 → timeout = max(20, 120) = 120
  5. Slow provider: tick_interval=80 → timeout = max(160, 120) = 160
  6. Agent dataclass has last_sector field defaulting to None
  7. Agent dataclass has had_new_perceptions field defaulting to True
"""
import asyncio
from collections import deque
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from backend import gateway
from backend.simulation.engine import SimulationEngine
from backend.agents.agent import Agent
from backend.schemas import AgentConfig, AgentScratch, AgentSpatial


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_agent_config(name: str = "TestAgent") -> AgentConfig:
    """Return a minimal AgentConfig matching the real AgentScratch/AgentSpatial schema."""
    return AgentConfig(
        name=name,
        coord=(0, 0),
        currently="testing",
        scratch=AgentScratch(
            age=30,
            innate="curious",
            learned="background info",
            lifestyle="wakes at 7am",
            daily_plan="standard daily routine",
        ),
        spatial=AgentSpatial(
            address={"living_area": ["agent-town", f"home-{name.lower()}", "bedroom"]},
            tree={},
        ),
    )


def _make_engine() -> SimulationEngine:
    """Return a SimulationEngine with no maze/agents for unit tests."""
    return SimulationEngine(maze=None, agents=[], simulation_id="test")


# ---------------------------------------------------------------------------
# Test 1: tick_interval returns 10.0 with empty window (cold start / min_interval)
# ---------------------------------------------------------------------------
def test_tick_interval_empty_window_returns_min(monkeypatch):
    """SimulationEngine.tick_interval returns 10.0 when latency window is empty."""
    monkeypatch.setattr(gateway, "_latency_window", deque(maxlen=10))

    engine = _make_engine()
    assert engine.tick_interval == 10.0, (
        f"Expected tick_interval=10.0 (empty window), got {engine.tick_interval}"
    )


# ---------------------------------------------------------------------------
# Test 2: tick_interval returns 18.0 when window=[12,12,12]
# ---------------------------------------------------------------------------
def test_tick_interval_slow_window_returns_scaled(monkeypatch):
    """SimulationEngine.tick_interval returns 18.0 when gateway._latency_window=[12, 12, 12]."""
    window = deque([12.0, 12.0, 12.0], maxlen=10)
    monkeypatch.setattr(gateway, "_latency_window", window)

    engine = _make_engine()
    result = engine.tick_interval
    assert result == 18.0, (
        f"Expected tick_interval=18.0 (avg=12, *1.5=18), got {result}"
    )


# ---------------------------------------------------------------------------
# Test 3: _agent_step_safe uses timeout = max(tick_interval * 2, 120)
# ---------------------------------------------------------------------------
async def test_agent_step_safe_timeout_formula(monkeypatch):
    """_agent_step_safe timeout equals max(tick_interval * 2, 120)."""
    monkeypatch.setattr(gateway, "_latency_window", deque([50.0, 50.0], maxlen=10))

    engine = _make_engine()
    expected_tick = engine.tick_interval  # max(10, 75.0) = 75.0
    expected_timeout = max(expected_tick * 2, 120)  # max(150, 120) = 150

    captured_timeout = None

    async def mock_wait_for(coro, timeout):
        nonlocal captured_timeout
        captured_timeout = timeout
        # Cancel the coroutine immediately to avoid side effects
        coro.close()

    monkeypatch.setattr(asyncio, "wait_for", mock_wait_for)

    cfg = _minimal_agent_config("Alice")
    agent = Agent(name="Alice", config=cfg, coord=(0, 0))

    # Patch _agent_step to be a no-op coroutine
    async def mock_agent_step(agent_name, agent_obj):
        pass

    monkeypatch.setattr(engine, "_agent_step", mock_agent_step)

    await engine._agent_step_safe("Alice", agent)

    assert captured_timeout == expected_timeout, (
        f"Expected timeout={expected_timeout}, got {captured_timeout}"
    )


# ---------------------------------------------------------------------------
# Test 4: Cold start — tick_interval=10 → timeout = max(20, 120) = 120
# ---------------------------------------------------------------------------
async def test_agent_step_safe_cold_start_floor_120(monkeypatch):
    """Cold-start: tick_interval=10.0 → timeout = max(20, 120) = 120 (not 20)."""
    monkeypatch.setattr(gateway, "_latency_window", deque(maxlen=10))

    engine = _make_engine()
    assert engine.tick_interval == 10.0, "Precondition: tick_interval should be 10.0 at cold start"

    captured_timeout = None

    async def mock_wait_for(coro, timeout):
        nonlocal captured_timeout
        captured_timeout = timeout
        coro.close()

    monkeypatch.setattr(asyncio, "wait_for", mock_wait_for)

    cfg = _minimal_agent_config("Bob")
    agent = Agent(name="Bob", config=cfg, coord=(0, 0))

    async def mock_agent_step(agent_name, agent_obj):
        pass

    monkeypatch.setattr(engine, "_agent_step", mock_agent_step)

    await engine._agent_step_safe("Bob", agent)

    assert captured_timeout == 120, (
        f"Cold-start timeout must be 120 (floor), got {captured_timeout}. "
        f"tick_interval * 2 = 20 is NOT enough for a cold-start agent step."
    )


# ---------------------------------------------------------------------------
# Test 5: Slow provider — tick_interval=80 → timeout = max(160, 120) = 160
# ---------------------------------------------------------------------------
async def test_agent_step_safe_slow_provider_above_floor(monkeypatch):
    """Slow provider: tick_interval=80.0 → timeout = max(160, 120) = 160."""
    # avg=53.33 * 1.5 = 80.0
    window = deque([53.33, 53.33, 53.34], maxlen=10)
    monkeypatch.setattr(gateway, "_latency_window", window)

    engine = _make_engine()
    tick = engine.tick_interval
    # tick_interval = max(10, 80.0) = 80.0
    assert tick == pytest.approx(80.0, rel=0.01), (
        f"Precondition: expected tick_interval≈80.0, got {tick}"
    )

    captured_timeout = None

    async def mock_wait_for(coro, timeout):
        nonlocal captured_timeout
        captured_timeout = timeout
        coro.close()

    monkeypatch.setattr(asyncio, "wait_for", mock_wait_for)

    cfg = _minimal_agent_config("Carol")
    agent = Agent(name="Carol", config=cfg, coord=(0, 0))

    async def mock_agent_step(agent_name, agent_obj):
        pass

    monkeypatch.setattr(engine, "_agent_step", mock_agent_step)

    await engine._agent_step_safe("Carol", agent)

    assert captured_timeout == pytest.approx(160.0, rel=0.01), (
        f"Slow provider timeout should be 160 (floor no longer applies), got {captured_timeout}"
    )


# ---------------------------------------------------------------------------
# Test 6: Agent dataclass has last_sector field defaulting to None
# ---------------------------------------------------------------------------
def test_agent_has_last_sector_field_defaulting_to_none():
    """Agent dataclass has last_sector field defaulting to None (D-08 per-sector gating)."""
    cfg = _minimal_agent_config("Dave")
    agent = Agent(name="Dave", config=cfg, coord=(0, 0))

    assert hasattr(agent, "last_sector"), "Agent must have 'last_sector' field"
    assert agent.last_sector is None, (
        f"Agent.last_sector should default to None, got {agent.last_sector!r}"
    )


# ---------------------------------------------------------------------------
# Test 7: Agent dataclass has had_new_perceptions field defaulting to True
# ---------------------------------------------------------------------------
def test_agent_has_had_new_perceptions_field_defaulting_to_true():
    """Agent dataclass has had_new_perceptions field defaulting to True (D-08 gating)."""
    cfg = _minimal_agent_config("Eve")
    agent = Agent(name="Eve", config=cfg, coord=(0, 0))

    assert hasattr(agent, "had_new_perceptions"), "Agent must have 'had_new_perceptions' field"
    assert agent.had_new_perceptions is True, (
        f"Agent.had_new_perceptions should default to True, got {agent.had_new_perceptions!r}"
    )
