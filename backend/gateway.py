"""Async LLM gateway for Agent Town — single integration point for all LLM calls.

Uses instructor + LiteLLM for structured output with automatic retry and fallback.
Supports Ollama (local) and OpenRouter (cloud) providers.
"""
import asyncio
import logging
import time
from collections import deque
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
# Use JSON mode for Ollama compatibility: tool-calling mode causes Llama 3.1
# to stringify arrays instead of producing valid JSON arrays.
_client = instructor.from_litellm(litellm.acompletion, mode=instructor.Mode.JSON)

# T-09-01: Bound concurrent LLM calls to prevent rate-limit queue pileup (D-04 / LLM-04)
_llm_semaphore = asyncio.Semaphore(8)

# D-04: Rolling window of successful LLM call latencies (maxlen=10) for adaptive tick timing
_latency_window: deque[float] = deque(maxlen=10)


def get_adaptive_tick_interval(min_interval: float = 10.0) -> float:
    """Return max(min_interval, avg_latency * 1.5) from recent LLM calls.

    Per D-04: adaptive tick based on rolling window of successful call latencies.
    Returns min_interval when no latency data exists (cold start).
    """
    if not _latency_window:
        return min_interval
    avg = sum(_latency_window) / len(_latency_window)
    return max(min_interval, avg * 1.5)


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
    fallback: T | None = None,
) -> T:
    """
    Make an async LLM call and return a validated Pydantic model.

    Uses instructor for automatic retry on validation failure (INF-03).
    Max retries are bounded to prevent denial-of-service (T-01-03).

    If all retries are exhausted:
    - Returns `fallback` if provided (caller-supplied safe value).
    - Returns FALLBACK_AGENT_ACTION if response_model is AgentAction (D-06).
    - Raises the last exception otherwise — callers must handle or supply a fallback.
    """
    if provider_config is None:
        provider_config = ProviderConfig(
            provider=cfg.state.provider,
            api_key=cfg.state.api_key,
            model=cfg.state.model,
        )

    model_str, litellm_kwargs = _resolve_model(provider_config)

    async with _llm_semaphore:
        # T-09-02: Debug log uses model name only — API key is never logged (T-01-02 preserved)
        logger.debug("LLM semaphore acquired (model=%s)", model_str)

        last_exc: Exception | None = None
        for attempt in range(1, max_retries + 1):
            try:
                # Measure latency of ONLY the successful call (Pitfall 6: no retry overhead)
                t0 = time.perf_counter()
                result = await _client.chat.completions.create(
                    model=model_str,
                    messages=messages,
                    response_model=response_model,
                    max_retries=1,  # let our loop handle retries
                    **litellm_kwargs,
                )
                elapsed = time.perf_counter() - t0
                _latency_window.append(elapsed)
                logger.debug("LLM semaphore released (latency=%.2fs)", elapsed)
                return result
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "LLM call attempt %d/%d failed: %s",
                    attempt,
                    max_retries,
                    type(exc).__name__,
                )

        # All retries exhausted — return type-safe fallback or raise (T-01-03, D-06)
        # T-01-02: never include api_key in log messages
        logger.warning("LLM call failed after %d retries", max_retries)
        logger.debug("LLM semaphore released (all retries exhausted, no latency recorded)")
        if fallback is not None:
            return fallback
        if response_model is AgentAction:
            return FALLBACK_AGENT_ACTION  # type: ignore[return-value]
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("complete_structured: no result and no exception")
