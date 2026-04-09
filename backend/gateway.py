"""Async LLM gateway for Agent Town — single integration point for all LLM calls.

Uses instructor + LiteLLM for structured output with automatic retry and fallback.
Supports Ollama (local) and OpenRouter (cloud) providers.
"""
import asyncio
import logging
from typing import TypeVar, Type

import instructor
import litellm

from backend.schemas import AgentAction, ProviderConfig
from backend import config as cfg

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Disable LiteLLM verbose logging — it's very noisy
litellm.suppress_debug_info = True

FALLBACK_AGENT_ACTION = AgentAction(
    destination="idle",
    activity="waiting",
    reasoning="LLM parse failed",
)

# instructor wraps litellm.acompletion — same interface across providers
_client = instructor.from_litellm(litellm.acompletion)


def _resolve_model(provider_config: ProviderConfig) -> tuple[str, dict]:
    """Returns (model_string, litellm_kwargs) for the given provider config."""
    if provider_config.provider == "ollama":
        model = provider_config.model or cfg.OLLAMA_DEFAULT_MODEL
        return model, {"api_base": cfg.OLLAMA_BASE_URL}
    else:  # openrouter
        model = provider_config.model or cfg.OPENROUTER_DEFAULT_MODEL
        # T-01-02: never log api_key value in full
        if provider_config.api_key:
            key_hint = provider_config.api_key[:8] + "..."
        else:
            key_hint = "(none)"
        logger.debug("Using OpenRouter model %s with key %s", model, key_hint)
        return model, {"api_key": provider_config.api_key}


async def complete_structured(
    messages: list[dict],
    response_model: Type[T],
    provider_config: ProviderConfig | None = None,
    max_retries: int = 3,
) -> T:
    """
    Make an async LLM call and return a validated Pydantic model.

    Uses instructor for automatic retry on validation failure (INF-03).
    Returns a fallback value if all retries fail — never raises (D-06).
    Max retries are bounded to prevent denial-of-service (T-01-03).
    """
    if provider_config is None:
        provider_config = ProviderConfig(
            provider=cfg.state.provider,
            api_key=cfg.state.api_key,
            model=cfg.state.model,
        )

    model_str, litellm_kwargs = _resolve_model(provider_config)

    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            result = await _client.chat.completions.create(
                model=model_str,
                messages=messages,
                response_model=response_model,
                max_retries=1,  # let our loop handle retries
                **litellm_kwargs,
            )
            return result
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "LLM call attempt %d/%d failed: %s",
                attempt,
                max_retries,
                type(exc).__name__,
            )

    # All retries exhausted — return type-safe fallback (T-01-03, D-06)
    # T-01-02: never include api_key in log messages
    logger.warning("LLM call failed after %d retries", max_retries)
    if response_model is AgentAction:
        return FALLBACK_AGENT_ACTION  # type: ignore[return-value]
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("complete_structured: no result and no exception")
