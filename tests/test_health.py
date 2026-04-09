"""Tests for GET /health endpoint."""
import pytest
from httpx import AsyncClient


async def test_health_returns_200_with_correct_keys(async_client: AsyncClient):
    """GET /health returns 200 with status and provider_status fields."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "provider_status" in body
    assert "ollama" in body["provider_status"]
    assert "openrouter" in body["provider_status"]


async def test_health_returns_200_when_ollama_unavailable(
    async_client: AsyncClient,
    monkeypatch,
):
    """GET /health returns 200 even when Ollama is not running (non-blocking, D-06)."""
    import backend.config as cfg
    monkeypatch.setattr(cfg.state, "ollama_available", False)
    response = await async_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["provider_status"]["ollama"] is False
