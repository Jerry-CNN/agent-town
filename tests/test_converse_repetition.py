"""Tests for conversation repetition detection and MAX_TURNS=6 (Plan 09-02, Task 2).

TDD: These tests are written BEFORE the implementation (RED phase).

Covers:
  - _is_repetition() similarity threshold checks
  - Case-insensitive comparison
  - MAX_TURNS constant value
  - run_conversation early termination when repetition detected
  - terminated_reason field in conversation result
  - Repetition not checked on turn 0 (first round avoidance)
  - Logger call "conversation ended (repetition)"
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _make_scratch(name: str = "Alice"):
    from backend.schemas import AgentScratch
    return AgentScratch(
        age=30,
        innate="curious, friendly",
        learned="a town resident",
        lifestyle="wakes at 7am",
        daily_plan="work and leisure",
    )


def _make_schedule_entry(describe: str = "relax at home"):
    from backend.schemas import ScheduleEntry
    return ScheduleEntry(start_minute=720, duration_minutes=60, describe=describe)


def _make_turn(text: str, end_conversation: bool = False):
    from backend.schemas import ConversationTurn
    return ConversationTurn(text=text, end_conversation=end_conversation)


def _make_revision(entries=None):
    from backend.schemas import ScheduleRevision
    return ScheduleRevision(revised_entries=entries or [], reason="done")


# ---------------------------------------------------------------------------
# Tests for _is_repetition
# ---------------------------------------------------------------------------


def test_is_repetition_similar_texts_returns_true():
    """Test 1: Similar texts (ratio ~0.85) return True."""
    from backend.agents.cognition.converse import _is_repetition

    result = _is_repetition(
        "stock market is interesting",
        "stock market is very interesting",
    )
    assert result is True


def test_is_repetition_dissimilar_texts_returns_false():
    """Test 2: Dissimilar texts (ratio ~0.34) return False."""
    from backend.agents.cognition.converse import _is_repetition

    result = _is_repetition(
        "I heard there's a wedding",
        "Oh really? I should buy a gift",
    )
    assert result is False


def test_is_repetition_identical_texts_returns_true():
    """Test 3: Identical texts (ratio=1.0) return True."""
    from backend.agents.cognition.converse import _is_repetition

    result = _is_repetition("hello world", "hello world")
    assert result is True


def test_is_repetition_case_insensitive():
    """Test 4: _is_repetition is case-insensitive ("HELLO" vs "hello" returns True)."""
    from backend.agents.cognition.converse import _is_repetition

    result = _is_repetition("HELLO", "hello")
    assert result is True


# ---------------------------------------------------------------------------
# Test for MAX_TURNS constant
# ---------------------------------------------------------------------------


def test_max_turns_is_6():
    """Test 5: MAX_TURNS is 6 (raised from 4 per D-12, Plan 09-02)."""
    from backend.agents.cognition.converse import MAX_TURNS

    assert MAX_TURNS == 6


# ---------------------------------------------------------------------------
# Integration tests for run_conversation with repetition detection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_conversation_terminates_on_repetition():
    """Test 6: run_conversation terminates early when repetition detected after turn >= 1.
    Result must contain terminated_reason='repetition'.
    """
    from backend.agents.cognition.converse import run_conversation

    scratch_a = _make_scratch("Alice")
    scratch_b = _make_scratch("Bob")
    schedule = [_make_schedule_entry()]

    # Turn 0: distinct texts (no repetition check on first round)
    # Turn 1: very similar texts (should trigger repetition detection)
    turns_side_effect = [
        _make_turn("Hello Bob, how are you?"),                      # A turn 0
        _make_turn("Hello Alice, I'm fine."),                       # B turn 0
        _make_turn("The stock market is really interesting today"),  # A turn 1
        _make_turn("The stock market is very interesting today"),    # B turn 1 — similar to A!
    ]
    revision = _make_revision(schedule)

    with patch("backend.agents.cognition.converse.complete_structured",
               new_callable=AsyncMock, side_effect=turns_side_effect + [revision, revision]) as mock_cs:
        with patch("backend.agents.memory.store.add_memory", new_callable=AsyncMock):
            with patch("backend.agents.memory.store.score_importance",
                       new_callable=AsyncMock, return_value=5):
                with patch("backend.agents.memory.retrieval.retrieve_memories",
                           new_callable=AsyncMock, return_value=[]):
                    result = await run_conversation(
                        simulation_id="sim-01",
                        agent_a_name="Alice",
                        agent_a_scratch=scratch_a,
                        agent_b_name="Bob",
                        agent_b_scratch=scratch_b,
                        location="cafe",
                        remaining_schedule_a=schedule,
                        remaining_schedule_b=schedule,
                    )

    assert "terminated_reason" in result
    assert result["terminated_reason"] == "repetition"
    # Conversation should end after turn 1 (2 turns completed, not all 6)
    assert len(result["turns"]) <= 4  # at most 2 full rounds (4 utterances)


@pytest.mark.asyncio
async def test_run_conversation_no_repetition_check_on_turn_0():
    """Test 7: run_conversation does NOT check repetition on turn 0 (first round).
    Even if turn 0 texts are identical, conversation continues.
    """
    from backend.agents.cognition.converse import run_conversation

    scratch_a = _make_scratch("Alice")
    scratch_b = _make_scratch("Bob")
    schedule = []

    # Turn 0: identical texts — should NOT trigger termination
    # Turn 1+: distinct texts — no repetition
    turns_side_effect = [
        _make_turn("hello world"),                         # A turn 0
        _make_turn("hello world"),                         # B turn 0 — identical, but no check yet
        _make_turn("What should we do today?"),            # A turn 1 — distinct
        _make_turn("Let's go to the park.", end_conversation=True),  # B turn 1 — ends naturally
    ]
    revision = _make_revision()

    with patch("backend.agents.cognition.converse.complete_structured",
               new_callable=AsyncMock, side_effect=turns_side_effect + [revision, revision]):
        with patch("backend.agents.memory.store.add_memory", new_callable=AsyncMock):
            with patch("backend.agents.memory.store.score_importance",
                       new_callable=AsyncMock, return_value=5):
                with patch("backend.agents.memory.retrieval.retrieve_memories",
                           new_callable=AsyncMock, return_value=[]):
                    result = await run_conversation(
                        simulation_id="sim-01",
                        agent_a_name="Alice",
                        agent_a_scratch=scratch_a,
                        agent_b_name="Bob",
                        agent_b_scratch=scratch_b,
                        location="cafe",
                        remaining_schedule_a=schedule,
                        remaining_schedule_b=schedule,
                    )

    # Should NOT have terminated due to repetition — natural or agent_choice end
    assert result["terminated_reason"] != "repetition"


@pytest.mark.asyncio
async def test_run_conversation_logs_repetition(caplog):
    """Test 8: run_conversation logs "conversation ended (repetition)" when terminated by repetition."""
    import logging
    from backend.agents.cognition.converse import run_conversation

    scratch_a = _make_scratch("Alice")
    scratch_b = _make_scratch("Bob")
    schedule = []

    turns_side_effect = [
        _make_turn("Hello Bob, how are you?"),
        _make_turn("Hello Alice, I'm fine."),
        _make_turn("The weather is very nice today"),   # A turn 1
        _make_turn("The weather is really nice today"), # B turn 1 — similar
    ]
    revision = _make_revision()

    with patch("backend.agents.cognition.converse.complete_structured",
               new_callable=AsyncMock, side_effect=turns_side_effect + [revision, revision]):
        with patch("backend.agents.memory.store.add_memory", new_callable=AsyncMock):
            with patch("backend.agents.memory.store.score_importance",
                       new_callable=AsyncMock, return_value=5):
                with patch("backend.agents.memory.retrieval.retrieve_memories",
                           new_callable=AsyncMock, return_value=[]):
                    with caplog.at_level(logging.INFO, logger="backend.agents.cognition.converse"):
                        result = await run_conversation(
                            simulation_id="sim-01",
                            agent_a_name="Alice",
                            agent_a_scratch=scratch_a,
                            agent_b_name="Bob",
                            agent_b_scratch=scratch_b,
                            location="cafe",
                            remaining_schedule_a=schedule,
                            remaining_schedule_b=schedule,
                        )

    assert result["terminated_reason"] == "repetition"
    assert any("conversation ended (repetition)" in record.message
               for record in caplog.records)
