"""WebSocket payload contract test — Phase 7 success criterion 6.

Verifies that get_snapshot() and _emit_agent_update() produce payloads
with identical KEY STRUCTURE (key names + value types) before and after
the OOP refactor. This is structural identity, not byte-level serialization
comparison.

The wire contract:
  snapshot:     {"agents": list[AgentEntry], "simulation_status": str, "tick_count": int}
  AgentEntry:   {"name": str, "coord": list[int, int], "activity": str}
  agent_update: {"type": str, "name": str, "coord": list[int, int], "activity": str}
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.agents.agent import Agent
from backend.simulation.engine import SimulationEngine
from backend.schemas import AgentConfig, AgentScratch, AgentSpatial


def _make_config(name: str, coord: tuple[int, int]) -> AgentConfig:
    """Build a minimal valid AgentConfig for contract testing."""
    scratch = AgentScratch(
        age=30,
        innate="curious",
        learned="works at cafe",
        lifestyle="wakes up early",
        daily_plan="go to work",
    )
    spatial = AgentSpatial(address={}, tree={})
    return AgentConfig(
        name=name,
        coord=coord,
        currently="idle",
        scratch=scratch,
        spatial=spatial,
    )


def test_snapshot_structure_matches_contract():
    """get_snapshot() must return exact keys: agents (list), simulation_status (str), tick_count (int).

    Each entry in agents must have: name (str), coord (list of two ints), activity (str).
    coord must be a list (not tuple) — JSON wire format requirement.
    """
    config = _make_config("Alice", (5, 10))
    engine = SimulationEngine(agents=[config], simulation_id="test-snap")
    # Directly place an Agent in _agents to bypass async initialize()
    engine._agents["Alice"] = Agent(
        name="Alice",
        config=config,
        coord=(5, 10),
        current_activity="reading",
    )

    snapshot = engine.get_snapshot()

    # Top-level keys
    assert "agents" in snapshot, "snapshot missing 'agents' key"
    assert "simulation_status" in snapshot, "snapshot missing 'simulation_status' key"
    assert "tick_count" in snapshot, "snapshot missing 'tick_count' key"

    # Type assertions for top-level values
    assert isinstance(snapshot["agents"], list), "'agents' must be a list"
    assert isinstance(snapshot["simulation_status"], str), "'simulation_status' must be str"
    assert isinstance(snapshot["tick_count"], int), "'tick_count' must be int"

    # Per-agent entry structure
    assert len(snapshot["agents"]) == 1, "Expected exactly one agent entry"
    entry = snapshot["agents"][0]

    assert "name" in entry, "agent entry missing 'name' key"
    assert "coord" in entry, "agent entry missing 'coord' key"
    assert "activity" in entry, "agent entry missing 'activity' key"

    assert isinstance(entry["name"], str), "agent entry 'name' must be str"
    assert isinstance(entry["coord"], list), "agent entry 'coord' must be list (not tuple) for JSON wire"
    assert len(entry["coord"]) == 2, "agent entry 'coord' must have exactly 2 elements"
    assert all(isinstance(v, int) for v in entry["coord"]), "agent entry 'coord' elements must be int"
    assert isinstance(entry["activity"], str), "agent entry 'activity' must be str"

    # Verify values match what was set
    assert entry["name"] == "Alice"
    assert entry["coord"] == [5, 10]
    assert entry["activity"] == "reading"


@pytest.mark.asyncio
async def test_agent_update_payload_structure():
    """_emit_agent_update() must broadcast a payload with exact keys: type (str), name (str), coord (list[int]), activity (str).

    coord must be a list (not tuple) for JSON serialization.
    type must equal "agent_update".
    """
    config = _make_config("Bob", (3, 7))
    captured_payloads: list[dict] = []

    async def capture_broadcast(payload: dict) -> None:
        captured_payloads.append(payload)

    engine = SimulationEngine(agents=[config], simulation_id="test-update")
    engine._agents["Bob"] = Agent(
        name="Bob",
        config=config,
        coord=(3, 7),
        current_activity="walking",
    )
    # Wire the broadcast callback
    engine._broadcast_callback = capture_broadcast

    agent_obj = engine._agents["Bob"]
    await engine._emit_agent_update("Bob", agent_obj)

    assert len(captured_payloads) == 1, "_emit_agent_update must call broadcast exactly once"
    payload = captured_payloads[0]

    # Exact key set
    assert "type" in payload, "agent_update payload missing 'type' key"
    assert "name" in payload, "agent_update payload missing 'name' key"
    assert "coord" in payload, "agent_update payload missing 'coord' key"
    assert "activity" in payload, "agent_update payload missing 'activity' key"

    # Type assertions
    assert isinstance(payload["type"], str), "'type' must be str"
    assert isinstance(payload["name"], str), "'name' must be str"
    assert isinstance(payload["coord"], list), "'coord' must be list (not tuple) for JSON wire"
    assert len(payload["coord"]) == 2, "'coord' must have exactly 2 elements"
    assert all(isinstance(v, int) for v in payload["coord"]), "'coord' elements must be int"
    assert isinstance(payload["activity"], str), "'activity' must be str"

    # Value assertions
    assert payload["type"] == "agent_update"
    assert payload["name"] == "Bob"
    assert payload["coord"] == [3, 7]
    assert payload["activity"] == "walking"
