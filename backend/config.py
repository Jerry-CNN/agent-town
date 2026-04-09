"""Application configuration and singleton state for Agent Town backend."""
from dataclasses import dataclass, field
from typing import Literal

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_DEFAULT_MODEL = "ollama_chat/llama3.1:8b"
OPENROUTER_DEFAULT_MODEL = "openrouter/meta-llama/llama-3.1-8b-instruct:free"


@dataclass
class AppState:
    provider: Literal["ollama", "openrouter"] = "ollama"
    api_key: str | None = None
    model: str | None = None
    ollama_available: bool = False
    openrouter_configured: bool = False


state = AppState()
