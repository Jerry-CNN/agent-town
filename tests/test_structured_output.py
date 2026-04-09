"""Tests for instructor retry and fallback behavior in LLM gateway."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.schemas import AgentAction


async def test_complete_structured_retries_and_succeeds(monkeypatch):
    """
    INF-03: Mock litellm to fail on first call, succeed on second.
    complete_structured should return a valid AgentAction without raising.
    """
    from backend import gateway
    from backend.schemas import ProviderConfig

    valid_action = AgentAction(
        destination="park", activity="walking", reasoning="test"
    )

    call_count = 0

    async def mock_create(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("Malformed JSON on first attempt")
        return valid_action

    monkeypatch.setattr(
        gateway._client.chat.completions, "create", mock_create
    )

    provider_config = ProviderConfig(provider="ollama")
    result = await gateway.complete_structured(
        messages=[{"role": "user", "content": "test"}],
        response_model=AgentAction,
        provider_config=provider_config,
        max_retries=3,
    )

    assert isinstance(result, AgentAction)
    assert result.destination == "park"


async def test_complete_structured_returns_fallback_on_all_failures(monkeypatch):
    """
    INF-03: Mock litellm to always fail.
    complete_structured returns FALLBACK_AGENT_ACTION, does NOT raise.
    """
    from backend import gateway
    from backend.schemas import ProviderConfig

    async def mock_create_always_fail(*args, **kwargs):
        raise Exception("Always malformed JSON")

    monkeypatch.setattr(
        gateway._client.chat.completions, "create", mock_create_always_fail
    )

    provider_config = ProviderConfig(provider="ollama")
    result = await gateway.complete_structured(
        messages=[{"role": "user", "content": "test"}],
        response_model=AgentAction,
        provider_config=provider_config,
        max_retries=3,
    )

    assert isinstance(result, AgentAction)
    assert result.destination == "idle"
    assert result.activity == "waiting"
    assert result.reasoning == "LLM parse failed"


async def test_llm_test_endpoint_422_on_missing_openrouter_key(async_client):
    """
    POST /api/llm/test with openrouter provider but no api_key returns 422.
    Pydantic validation rejects this at the schema level (D-03/CFG-02).
    """
    response = await async_client.post(
        "/api/llm/test",
        json={"provider": "openrouter", "api_key": None},
    )
    assert response.status_code == 422


async def test_config_endpoint_422_on_missing_openrouter_key(async_client):
    """
    POST /api/config with openrouter provider but no api_key returns 422.
    """
    response = await async_client.post(
        "/api/config",
        json={"provider": "openrouter"},
    )
    assert response.status_code == 422
