"""Tests for the 2-level decision cascade, per-sector gating, and arena validation.

TDD: These tests are written BEFORE the implementation (RED phase for Task 1 of Plan 09-02).

Covers:
  - _sector_has_arenas helper
  - Per-sector gating (returns None when last_sector set, no perceptions, no schedule change)
  - 2-level cascade: 1 LLM call for single-arena, 2 for multi-arena sectors
  - Arena validation: unknown arena names fall back to arenas[0]
"""
import pytest
from unittest.mock import AsyncMock, patch, call


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

SAMPLE_SPATIAL_TREE = {
    "agent-town": {
        "cafe": {"seating": [], "counter": [], "kitchen": []},   # 3 arenas
        "park": {"bench-area": []},                               # 1 arena
        "home-alice": {"bedroom": [], "living-room": [], "kitchen": []},  # 3 arenas
        "gym": {},                                                 # 0 arenas
    }
}


def _make_agent_spatial(tree: dict | None = None):
    from backend.schemas import AgentSpatial
    return AgentSpatial(
        address={"home": ["agent-town", "home-alice", "bedroom"]},
        tree=tree if tree is not None else SAMPLE_SPATIAL_TREE,
    )


def _make_agent_scratch():
    from backend.schemas import AgentScratch
    return AgentScratch(
        age=28,
        innate="warm, creative",
        learned="a town resident",
        lifestyle="wakes at 7am",
        daily_plan="work and leisure",
    )


def _make_perception(nearby_agents=None, nearby_events=None, location="park"):
    from backend.schemas import PerceptionResult
    return PerceptionResult(
        nearby_agents=nearby_agents or [],
        nearby_events=nearby_events or [],
        location=location,
    )


def _make_agent_action(destination="cafe", activity="getting coffee", reasoning="want coffee"):
    from backend.schemas import AgentAction
    return AgentAction(destination=destination, activity=activity, reasoning=reasoning)


def _make_arena_action(arena="seating", reasoning="comfortable"):
    from backend.schemas import ArenaAction
    return ArenaAction(arena=arena, reasoning=reasoning)


# ---------------------------------------------------------------------------
# Tests for _sector_has_arenas
# ---------------------------------------------------------------------------


def test_sector_has_arenas_returns_list_for_multi_arena():
    """Test 1: _sector_has_arenas returns list of arena names for sector with 3 arenas."""
    from backend.agents.cognition.decide import _sector_has_arenas

    arenas = _sector_has_arenas("cafe", SAMPLE_SPATIAL_TREE)
    assert arenas == ["seating", "counter", "kitchen"]


def test_sector_has_arenas_returns_empty_for_single_arena():
    """Test 2: _sector_has_arenas returns [] for sector with only 1 arena."""
    from backend.agents.cognition.decide import _sector_has_arenas

    arenas = _sector_has_arenas("park", SAMPLE_SPATIAL_TREE)
    assert arenas == []


def test_sector_has_arenas_returns_empty_for_zero_arenas():
    """Test 3: _sector_has_arenas returns [] for sector with 0 arenas (empty dict)."""
    from backend.agents.cognition.decide import _sector_has_arenas

    arenas = _sector_has_arenas("gym", SAMPLE_SPATIAL_TREE)
    assert arenas == []


# ---------------------------------------------------------------------------
# Tests for per-sector gating (None returns)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gating_returns_none_when_all_conditions_met():
    """Test 4: decide_action returns None when last_sector set, new_perceptions False,
    schedule_changed False — all three gating conditions met."""
    from backend.agents.cognition.decide import decide_action

    scratch = _make_agent_scratch()
    spatial = _make_agent_spatial()
    perception = _make_perception()

    # All three gating conditions: last_sector set, no new perceptions, schedule not changed
    result = await decide_action(
        simulation_id="sim-01",
        agent_name="Alice",
        agent_scratch=scratch,
        agent_spatial=spatial,
        current_activity="idle",
        perception=perception,
        current_schedule=[],
        last_sector="park",
        new_perceptions=False,
        schedule_changed=False,
    )

    assert result is None


@pytest.mark.asyncio
async def test_gating_fires_when_last_sector_is_none():
    """Test 7: When last_sector is None (first tick), gating does NOT skip."""
    from backend.agents.cognition.decide import decide_action

    scratch = _make_agent_scratch()
    spatial = _make_agent_spatial()
    perception = _make_perception()
    mock_action = _make_agent_action("park")

    with patch("backend.agents.cognition.decide.complete_structured", new_callable=AsyncMock, return_value=mock_action):
        with patch("backend.agents.memory.retrieval.retrieve_memories", new_callable=AsyncMock, return_value=[]):
            result = await decide_action(
                simulation_id="sim-01",
                agent_name="Alice",
                agent_scratch=scratch,
                agent_spatial=spatial,
                current_activity="idle",
                perception=perception,
                current_schedule=[],
                last_sector=None,       # first tick — no previous sector
                new_perceptions=False,
                schedule_changed=False,
            )

    assert result is not None


@pytest.mark.asyncio
async def test_gating_fires_when_new_perceptions_true():
    """Test 8: When new_perceptions is True but sector is unchanged, gating does NOT skip."""
    from backend.agents.cognition.decide import decide_action

    scratch = _make_agent_scratch()
    spatial = _make_agent_spatial()
    perception = _make_perception()
    mock_action = _make_agent_action("park")

    with patch("backend.agents.cognition.decide.complete_structured", new_callable=AsyncMock, return_value=mock_action):
        with patch("backend.agents.memory.retrieval.retrieve_memories", new_callable=AsyncMock, return_value=[]):
            result = await decide_action(
                simulation_id="sim-01",
                agent_name="Alice",
                agent_scratch=scratch,
                agent_spatial=spatial,
                current_activity="idle",
                perception=perception,
                current_schedule=[],
                last_sector="park",
                new_perceptions=True,   # new perceptions — must fire
                schedule_changed=False,
            )

    assert result is not None


@pytest.mark.asyncio
async def test_gating_fires_when_schedule_changed():
    """Test 9: When schedule_changed is True, gating does NOT skip."""
    from backend.agents.cognition.decide import decide_action

    scratch = _make_agent_scratch()
    spatial = _make_agent_spatial()
    perception = _make_perception()
    mock_action = _make_agent_action("park")

    with patch("backend.agents.cognition.decide.complete_structured", new_callable=AsyncMock, return_value=mock_action):
        with patch("backend.agents.memory.retrieval.retrieve_memories", new_callable=AsyncMock, return_value=[]):
            result = await decide_action(
                simulation_id="sim-01",
                agent_name="Alice",
                agent_scratch=scratch,
                agent_spatial=spatial,
                current_activity="idle",
                perception=perception,
                current_schedule=[],
                last_sector="park",
                new_perceptions=False,
                schedule_changed=True,   # schedule changed — must fire
            )

    assert result is not None


# ---------------------------------------------------------------------------
# Tests for LLM call count (1 vs 2)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_single_arena_sector_makes_1_llm_call():
    """Test 5: decide_action makes 1 LLM call when destination sector has 1 arena (no arena call)."""
    from backend.agents.cognition.decide import decide_action

    scratch = _make_agent_scratch()
    spatial = _make_agent_spatial()
    perception = _make_perception()
    # LLM selects "park" — only 1 arena so no arena call follows
    mock_action = _make_agent_action("park")

    with patch("backend.agents.cognition.decide.complete_structured", new_callable=AsyncMock, return_value=mock_action) as mock_llm:
        with patch("backend.agents.memory.retrieval.retrieve_memories", new_callable=AsyncMock, return_value=[]):
            result = await decide_action(
                simulation_id="sim-01",
                agent_name="Alice",
                agent_scratch=scratch,
                agent_spatial=spatial,
                current_activity="idle",
                perception=perception,
                current_schedule=[],
                last_sector=None,
                new_perceptions=True,
            )

    assert mock_llm.call_count == 1
    assert result is not None
    assert result.destination == "park"


@pytest.mark.asyncio
async def test_multi_arena_sector_makes_2_llm_calls():
    """Test 6: decide_action makes 2 LLM calls when destination sector has 3 arenas
    (sector call + arena call)."""
    from backend.agents.cognition.decide import decide_action

    scratch = _make_agent_scratch()
    spatial = _make_agent_spatial()
    perception = _make_perception()
    # LLM selects "cafe" (3 arenas) — arena call follows
    mock_sector_action = _make_agent_action("cafe")
    mock_arena_action = _make_arena_action("seating")

    with patch("backend.agents.cognition.decide.complete_structured", new_callable=AsyncMock,
               side_effect=[mock_sector_action, mock_arena_action]) as mock_llm:
        with patch("backend.agents.memory.retrieval.retrieve_memories", new_callable=AsyncMock, return_value=[]):
            result = await decide_action(
                simulation_id="sim-01",
                agent_name="Alice",
                agent_scratch=scratch,
                agent_spatial=spatial,
                current_activity="idle",
                perception=perception,
                current_schedule=[],
                last_sector=None,
                new_perceptions=True,
            )

    assert mock_llm.call_count == 2
    assert result is not None
    assert result.destination == "cafe:seating"


# ---------------------------------------------------------------------------
# Tests for arena validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_arena_validation_uses_fallback_for_unknown_arena():
    """Test 10: When LLM returns unknown arena name, destination uses arenas[0] fallback."""
    from backend.agents.cognition.decide import decide_action

    scratch = _make_agent_scratch()
    spatial = _make_agent_spatial()
    perception = _make_perception()
    mock_sector_action = _make_agent_action("cafe")
    # LLM returns an arena name that is NOT in the known list
    mock_arena_action = _make_arena_action("rooftop")  # unknown!

    with patch("backend.agents.cognition.decide.complete_structured", new_callable=AsyncMock,
               side_effect=[mock_sector_action, mock_arena_action]):
        with patch("backend.agents.memory.retrieval.retrieve_memories", new_callable=AsyncMock, return_value=[]):
            result = await decide_action(
                simulation_id="sim-01",
                agent_name="Alice",
                agent_scratch=scratch,
                agent_spatial=spatial,
                current_activity="idle",
                perception=perception,
                current_schedule=[],
                last_sector=None,
                new_perceptions=True,
            )

    assert result is not None
    # Should fall back to arenas[0] = "seating"
    assert result.destination == "cafe:seating"


@pytest.mark.asyncio
async def test_arena_validation_uses_known_arena():
    """Test 11: When LLM returns a known arena name, destination uses that arena."""
    from backend.agents.cognition.decide import decide_action

    scratch = _make_agent_scratch()
    spatial = _make_agent_spatial()
    perception = _make_perception()
    mock_sector_action = _make_agent_action("cafe")
    mock_arena_action = _make_arena_action("kitchen")  # valid arena

    with patch("backend.agents.cognition.decide.complete_structured", new_callable=AsyncMock,
               side_effect=[mock_sector_action, mock_arena_action]):
        with patch("backend.agents.memory.retrieval.retrieve_memories", new_callable=AsyncMock, return_value=[]):
            result = await decide_action(
                simulation_id="sim-01",
                agent_name="Alice",
                agent_scratch=scratch,
                agent_spatial=spatial,
                current_activity="idle",
                perception=perception,
                current_schedule=[],
                last_sector=None,
                new_perceptions=True,
            )

    assert result is not None
    assert result.destination == "cafe:kitchen"
