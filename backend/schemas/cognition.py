"""Cognition-domain Pydantic schemas for Agent Town backend.

Contains: SubTask, ScheduleEntry, DailySchedule, ConversationDecision,
          ConversationTurn, ScheduleRevision, PerceptionResult
"""
from pydantic import BaseModel, Field


class SubTask(BaseModel):
    """A fine-grained sub-task decomposed from a schedule entry (5-15 minutes each)."""
    start_minute: int = Field(ge=0, lt=1440, description="Minutes from midnight")
    duration_minutes: int = Field(ge=5, le=60)
    describe: str


class ScheduleEntry(BaseModel):
    """An hourly block in an agent's daily schedule."""
    start_minute: int = Field(ge=0, lt=1440)
    duration_minutes: int = Field(ge=15, le=120)
    describe: str
    decompose: list[SubTask] = []


class DailySchedule(BaseModel):
    """LLM-generated daily schedule for an agent (D-08)."""
    activities: list[str] = Field(min_length=3)
    wake_hour: int = Field(ge=4, le=11)


class ConversationDecision(BaseModel):
    """LLM decision on whether two agents should initiate a conversation (D-11)."""
    should_talk: bool
    reasoning: str


class ConversationTurn(BaseModel):
    """A single turn in a multi-turn agent conversation (D-12)."""
    text: str
    end_conversation: bool = False


class ScheduleRevision(BaseModel):
    """LLM-generated revision of an agent's remaining daily schedule (D-10, D-13)."""
    revised_entries: list[ScheduleEntry]
    reason: str


class PerceptionResult(BaseModel):
    """Result of an agent's perception sweep over the tile grid (D-06, D-07)."""
    nearby_events: list[dict] = []
    nearby_agents: list[dict] = []
    location: str = ""
