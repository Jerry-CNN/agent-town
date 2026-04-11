"""Event-domain Pydantic schemas for Agent Town backend.

Contains: ImportanceScore, Memory, Event (new with lifecycle tracking)

Security: Event.text validates max_length=500 per T-07-01 / ASVS V5.
"""
from typing import Literal
from pydantic import BaseModel, Field

# D-08: configurable default expiry tick count
EVENT_EXPIRY_TICKS: int = 10


class ImportanceScore(BaseModel):
    """LLM-assigned importance score for a memory (D-03, T-03-01).

    Pydantic enforces the 1-10 range; instructor retries on validation failure.
    """
    score: int = Field(ge=1, le=10)
    reasoning: str = ""


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


class Event(BaseModel):
    """Injected event with lifecycle tracking.

    D-09: Broadcasts do not track propagation (heard_by always empty).
    D-10: created -> active -> [spreading (whisper)] -> expired.
    D-08: Expiry by tick count, not wall clock.
    T-07-01: text field validates max_length=500 (user input from WebSocket inject_event).
    """
    text: str = Field(max_length=500)  # T-07-01 / ASVS V5
    mode: Literal["broadcast", "whisper"]
    target: str | None = None
    status: Literal["created", "active", "spreading", "expired"] = "created"
    created_tick: int = 0
    expires_after_ticks: int = EVENT_EXPIRY_TICKS
    heard_by: list[str] = Field(default_factory=list)

    def is_expired(self, current_tick: int) -> bool:
        """Return True when current_tick - created_tick >= expires_after_ticks."""
        return current_tick - self.created_tick >= self.expires_after_ticks

    def tick(self, current_tick: int) -> None:
        """Advance lifecycle state based on current simulation tick.

        Transitions (D-10):
          - created -> expired (if is_expired)
          - created -> active (not expired, first tick)
          - active -> expired (if is_expired)
          - active -> spreading (whisper only, not expired)
          - spreading -> expired (if is_expired)
          Broadcast events stay in active until expired (skip spreading).
        """
        if self.is_expired(current_tick):
            self.status = "expired"
        elif self.status == "created":
            self.status = "active"
        elif self.mode == "whisper" and self.status == "active":
            self.status = "spreading"
