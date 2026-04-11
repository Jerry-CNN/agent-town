"""Backward-compatible re-exports for backend.schemas package.

All existing 'from backend.schemas import X' statements continue to work
after the schema split. Import from the domain-specific submodule for new code:
  from backend.schemas.agent import AgentConfig
  from backend.schemas.events import Event
  from backend.schemas.cognition import ScheduleEntry
  from backend.schemas.ws import WSMessage
"""
from backend.schemas.agent import (
    AgentAction,
    AgentScratch,
    AgentSpatial,
    AgentConfig,
)
from backend.schemas.cognition import (
    SubTask,
    ScheduleEntry,
    DailySchedule,
    ConversationDecision,
    ConversationTurn,
    ScheduleRevision,
    PerceptionResult,
)
from backend.schemas.events import (
    ImportanceScore,
    Memory,
    Event,
    EVENT_EXPIRY_TICKS,
)
from backend.schemas.ws import (
    WSMessage,
    ProviderConfig,
    LLMTestResponse,
)

__all__ = [
    # agent domain
    "AgentAction",
    "AgentScratch",
    "AgentSpatial",
    "AgentConfig",
    # cognition domain
    "SubTask",
    "ScheduleEntry",
    "DailySchedule",
    "ConversationDecision",
    "ConversationTurn",
    "ScheduleRevision",
    "PerceptionResult",
    # events domain
    "ImportanceScore",
    "Memory",
    "Event",
    "EVENT_EXPIRY_TICKS",
    # ws domain
    "WSMessage",
    "ProviderConfig",
    "LLMTestResponse",
]
