"""Pydantic v2 schemas for Agent Town backend."""
import re
from typing import Literal
from pydantic import BaseModel, Field, model_validator


class AgentAction(BaseModel):
    """Agent decision schema — used by instructor for structured LLM output in Phase 3."""
    destination: str
    activity: str
    reasoning: str


class WSMessage(BaseModel):
    """WebSocket message contract for Phase 4 real-time communication.

    Outbound types (server -> browser):
      agent_update:      Position + activity change for one agent (D-06)
      conversation:      Multi-turn conversation turns between agents (D-06)
      simulation_status: Running/paused state change (D-06, D-08)
      snapshot:          Full state snapshot on client connect (D-05)
      event:             User-injected event broadcast (Phase 6)
      pong:              Response to browser ping
      error:             Invalid message or server-side error

    Inbound types (browser -> server):
      pause:        Halt the simulation after current tick completes (D-08)
      resume:       Restart simulation from paused state (D-08)
      ping:         Keepalive ping from browser
      inject_event: Inject a user event into agent memory streams (Phase 6)
    """
    type: Literal[
        "agent_update",       # D-06: position + activity change
        "conversation",       # D-06: conversation turns
        "simulation_status",  # D-06: running/paused state
        "snapshot",           # D-05: full state on connect
        "event",              # existing: injected events (Phase 6)
        "ping",               # keepalive from browser
        "pong",               # response to ping
        "error",              # invalid message or server error
        "pause",              # D-08: incoming command — pause simulation
        "resume",             # D-08: incoming command — resume simulation
        "inject_event",       # Phase 6: inbound command — inject user event into agent memories
    ]
    payload: dict
    timestamp: float


class ProviderConfig(BaseModel):
    """LLM provider configuration with validation."""
    provider: Literal["ollama", "openrouter"]
    api_key: str | None = None  # required when provider == "openrouter"
    model: str | None = None  # uses default if None

    @model_validator(mode="after")
    def validate_openrouter_api_key(self) -> "ProviderConfig":
        """Reject openrouter config without an api_key."""
        if self.provider == "openrouter" and not self.api_key:
            raise ValueError(
                "api_key is required when provider is 'openrouter'"
            )
        return self

    @model_validator(mode="after")
    def validate_model_string(self) -> "ProviderConfig":
        """Validate model string matches expected provider prefix pattern (T-01-04)."""
        if self.model is not None:
            pattern = r"^(ollama_chat/|openrouter/).+"
            if not re.match(pattern, self.model):
                raise ValueError(
                    f"model must match pattern 'ollama_chat/...' or 'openrouter/...', got: {self.model!r}"
                )
        return self


class LLMTestResponse(BaseModel):
    """Response schema for the /api/llm/test endpoint."""
    message: str
    provider: str  # "ollama" | "openrouter"
    model: str


class AgentScratch(BaseModel):
    """Agent personality and background -- the 'scratch pad' from the reference implementation."""
    age: int
    innate: str       # personality traits, comma-separated e.g. "warm, creative, curious"
    learned: str      # background paragraph
    lifestyle: str    # sleep/wake patterns and daily habits
    daily_plan: str   # routine template for LLM to fill in Phase 3


class AgentSpatial(BaseModel):
    """Agent's spatial knowledge -- known locations and their hierarchical structure."""
    address: dict[str, list[str]]  # named addresses e.g. {"living_area": ["agent-town", "home-alice", "bedroom"]}
    tree: dict                     # spatial knowledge tree (nested dict of known locations)


class AgentConfig(BaseModel):
    """Complete agent configuration loaded from a JSON config file.

    Schema mirrors the reference implementation's agent.json format (GenerativeAgentsCN),
    translated to English and extended with Agent Town's thematic locations.
    Consumed by Phase 3 (cognition), Phase 4 (simulation), and Phase 5 (frontend labels).
    """
    name: str
    coord: tuple[int, int]   # spawn position (x, y) on the tile grid
    currently: str            # current situation summary (seed for Phase 3 context)
    scratch: AgentScratch
    spatial: AgentSpatial


# ---------------------------------------------------------------------------
# Phase 3: Agent Cognition schemas
# ---------------------------------------------------------------------------


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


class ImportanceScore(BaseModel):
    """LLM-assigned importance score for a memory (D-03, T-03-01).

    Pydantic enforces the 1-10 range; instructor retries on validation failure.
    """
    score: int = Field(ge=1, le=10)
    reasoning: str = ""


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


class Memory(BaseModel):
    """A single entry in an agent's memory stream stored in ChromaDB (D-01).

    Importance is stored as metadata for composite retrieval scoring (D-02).
    """
    content: str
    agent_id: str
    memory_type: Literal["observation", "conversation", "action", "event"]
    importance: int = Field(ge=1, le=10)
    created_at: float
    last_access: float
