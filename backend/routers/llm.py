"""LLM and config API endpoints for Agent Town backend."""
import logging
from fastapi import APIRouter
from backend.schemas import ProviderConfig, LLMTestResponse
from backend.gateway import complete_structured
import backend.config as cfg

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


@router.post("/llm/test")
async def test_llm(provider_config: ProviderConfig) -> LLMTestResponse:
    """
    POST /api/llm/test — test LLM connectivity with the given provider.
    Accepts ProviderConfig body; Pydantic validates (missing openrouter api_key -> 422).
    """
    result = await complete_structured(
        messages=[{"role": "user", "content": "Reply with a one-sentence greeting."}],
        response_model=LLMTestResponse,
        provider_config=provider_config,
    )
    return result


@router.post("/config")
async def update_config(provider_config: ProviderConfig):
    """
    POST /api/config — update the active LLM provider configuration.
    Accepts ProviderConfig body; Pydantic validates (missing openrouter api_key -> 422).
    """
    cfg.state.provider = provider_config.provider
    cfg.state.api_key = provider_config.api_key
    cfg.state.model = provider_config.model
    cfg.state.openrouter_configured = (
        provider_config.provider == "openrouter"
        and bool(provider_config.api_key)
    )
    return {"status": "configured", "provider": provider_config.provider, "model": provider_config.model}
