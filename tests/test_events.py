"""Unit tests for the Event model and schema backward compatibility.

Tests cover:
  - EVTS-01: Event lifecycle state transitions
  - EVTS-02: Propagation tracking (whisper heard_by, broadcast stays empty)
  - EVTS-03: Tick-based expiry
  - Schema backward compatibility: all existing 'from backend.schemas import X' paths work
  - New domain imports: 'from backend.schemas.events import Event' works
"""
import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# Tests 1-2: Backward-compat imports still work after schema split
# ---------------------------------------------------------------------------

class TestBackwardCompatImports:
    def test_agent_config_import(self):
        """Test 1: from backend.schemas import AgentConfig succeeds."""
        from backend.schemas import AgentConfig
        assert AgentConfig is not None

    def test_ws_models_import(self):
        """Test 2: from backend.schemas import WSMessage, ProviderConfig, LLMTestResponse succeeds."""
        from backend.schemas import WSMessage, ProviderConfig, LLMTestResponse
        assert WSMessage is not None
        assert ProviderConfig is not None
        assert LLMTestResponse is not None

    def test_cognition_models_import(self):
        """Test 3: All cognition models importable from backend.schemas."""
        from backend.schemas import (
            DailySchedule,
            ScheduleEntry,
            SubTask,
            ScheduleRevision,
            PerceptionResult,
            ConversationDecision,
            ConversationTurn,
        )
        assert DailySchedule is not None
        assert ScheduleEntry is not None
        assert SubTask is not None

    def test_event_models_import(self):
        """Test 4: from backend.schemas import Event, Memory, ImportanceScore succeeds."""
        from backend.schemas import Event, Memory, ImportanceScore
        assert Event is not None
        assert Memory is not None
        assert ImportanceScore is not None

    def test_domain_agent_import(self):
        """Test 5: from backend.schemas.agent import AgentConfig succeeds (new domain path)."""
        from backend.schemas.agent import AgentConfig
        assert AgentConfig is not None

    def test_domain_events_import(self):
        """Test 6: from backend.schemas.events import Event succeeds."""
        from backend.schemas.events import Event
        assert Event is not None


# ---------------------------------------------------------------------------
# Tests 7-8: Event lifecycle transitions
# ---------------------------------------------------------------------------

class TestEventLifecycle:
    def test_broadcast_lifecycle(self):
        """Test 7: Broadcast event transitions created -> active -> expired (skips spreading)."""
        from backend.schemas.events import Event
        event = Event(text="Stock prices are rising!", mode="broadcast", created_tick=0, expires_after_ticks=5)
        assert event.status == "created"

        # tick at 1 (not expired): active state, broadcast never goes to spreading
        event.tick(current_tick=1)
        assert event.status == "active"

        # tick at 5 (expired): goes to expired
        event.tick(current_tick=5)
        assert event.status == "expired"

    def test_whisper_lifecycle(self):
        """Test 8: Whisper event transitions created -> active -> spreading -> expired."""
        from backend.schemas.events import Event
        event = Event(text="A secret gossip.", mode="whisper", created_tick=0, expires_after_ticks=10)
        assert event.status == "created"

        # First tick: set to active
        event.tick(current_tick=1)
        assert event.status == "active"

        # Second tick: active -> spreading (whisper mode)
        event.tick(current_tick=2)
        assert event.status == "spreading"

        # tick at 10 (expired)
        event.tick(current_tick=10)
        assert event.status == "expired"


# ---------------------------------------------------------------------------
# Tests 9-10: Tick-based expiry
# ---------------------------------------------------------------------------

class TestEventExpiry:
    def test_is_expired_when_ticks_elapsed(self):
        """Test 9: Event.is_expired() returns True when current_tick - created_tick >= expires_after_ticks."""
        from backend.schemas.events import Event
        event = Event(text="Old news", mode="broadcast", created_tick=5, expires_after_ticks=10)
        # At tick 15: 15 - 5 = 10 >= 10 -> expired
        assert event.is_expired(current_tick=15) is True

    def test_is_not_expired_before_ticks_elapsed(self):
        """Test 10: Event.is_expired() returns False when current_tick - created_tick < expires_after_ticks."""
        from backend.schemas.events import Event
        event = Event(text="Fresh news", mode="broadcast", created_tick=5, expires_after_ticks=10)
        # At tick 14: 14 - 5 = 9 < 10 -> not expired
        assert event.is_expired(current_tick=14) is False


# ---------------------------------------------------------------------------
# Tests 11-12: Propagation tracking
# ---------------------------------------------------------------------------

class TestEventPropagation:
    def test_whisper_heard_by_accumulates(self):
        """Test 11: Whisper Event.heard_by accumulates agent names when appended."""
        from backend.schemas.events import Event
        event = Event(text="A whisper", mode="whisper")
        event.heard_by.append("alice")
        event.heard_by.append("bob")
        assert "alice" in event.heard_by
        assert "bob" in event.heard_by
        assert len(event.heard_by) == 2

    def test_broadcast_heard_by_empty_by_default(self):
        """Test 12: Broadcast Event.heard_by stays empty (list is default empty, D-09)."""
        from backend.schemas.events import Event
        event = Event(text="Town announcement", mode="broadcast")
        assert event.heard_by == []


# ---------------------------------------------------------------------------
# Test 13: Field validation
# ---------------------------------------------------------------------------

class TestEventValidation:
    def test_text_max_length_500(self):
        """Test 13: Event.text validates max_length=500 (Pydantic Field constraint)."""
        from backend.schemas.events import Event
        # Exactly 500 chars: should succeed
        event = Event(text="A" * 500, mode="broadcast")
        assert len(event.text) == 500

        # 501 chars: should fail validation
        with pytest.raises(ValidationError):
            Event(text="A" * 501, mode="broadcast")


# ---------------------------------------------------------------------------
# Test 14: No intra-package circular imports
# ---------------------------------------------------------------------------

class TestNoIntraPackageImports:
    def test_agent_module_no_schemas_import(self):
        """Test 14: Domain files in schemas/ do NOT import from each other."""
        import importlib
        import inspect
        from backend.schemas import agent as agent_mod
        source = inspect.getsource(agent_mod)
        assert "from backend.schemas" not in source, "agent.py must not import from backend.schemas.*"

    def test_cognition_module_no_schemas_import(self):
        from backend.schemas import cognition as cog_mod
        import inspect
        source = inspect.getsource(cog_mod)
        assert "from backend.schemas" not in source, "cognition.py must not import from backend.schemas.*"

    def test_events_module_no_schemas_import(self):
        from backend.schemas import events as ev_mod
        import inspect
        source = inspect.getsource(ev_mod)
        assert "from backend.schemas" not in source, "events.py must not import from backend.schemas.*"

    def test_ws_module_no_schemas_import(self):
        from backend.schemas import ws as ws_mod
        import inspect
        source = inspect.getsource(ws_mod)
        assert "from backend.schemas" not in source, "ws.py must not import from backend.schemas.*"
