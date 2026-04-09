"""Pydantic v2 schemas for Agent Town backend."""
import re
from typing import Literal
from pydantic import BaseModel, model_validator


class AgentAction(BaseModel):
    """Agent decision schema — used by instructor for structured LLM output in Phase 3."""
    destination: str
    activity: str
    reasoning: str


class WSMessage(BaseModel):
    """WebSocket message contract for Phase 4 real-time communication."""
    type: Literal["agent_update", "event", "ping", "pong", "error"]
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
