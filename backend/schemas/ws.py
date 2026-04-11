"""WebSocket-domain Pydantic schemas for Agent Town backend.

Contains: WSMessage, ProviderConfig, LLMTestResponse
"""
import re
from typing import Literal
from pydantic import BaseModel, Field, model_validator


class WSMessage(BaseModel):
    """WebSocket message contract for Phase 4 real-time communication.

    Outbound types (server -> browser):
      agent_update:        Position + activity change for one agent (D-06)
      conversation:        Multi-turn conversation turns between agents (D-06)
      simulation_status:   Running/paused state change (D-06, D-08)
      snapshot:            Full state snapshot on client connect (D-05)
      event:               User-injected event broadcast (Phase 6)
      pong:                Response to browser ping
      error:               Invalid message or server-side error
      tick_interval_update: Current adaptive tick interval value (Phase 9, D-06)

    Inbound types (browser -> server):
      pause:        Halt the simulation after current tick completes (D-08)
      resume:       Restart simulation from paused state (D-08)
      ping:         Keepalive ping from browser
      inject_event: Inject a user event into agent memory streams (Phase 6)
    """
    type: Literal[
        "agent_update",          # D-06: position + activity change
        "conversation",          # D-06: conversation turns
        "simulation_status",     # D-06: running/paused state
        "snapshot",              # D-05: full state on connect
        "event",                 # existing: injected events (Phase 6)
        "ping",                  # keepalive from browser
        "pong",                  # response to ping
        "error",                 # invalid message or server error
        "pause",                 # D-08: incoming command — pause simulation
        "resume",                # D-08: incoming command — resume simulation
        "inject_event",          # Phase 6: inbound command — inject user event into agent memories
        "tick_interval_update",  # Phase 9: adaptive tick interval broadcast (D-06)
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
