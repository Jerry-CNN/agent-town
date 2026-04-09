"""Shared pytest fixtures for Agent Town backend tests."""
import pytest
import httpx
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def async_client():
    """AsyncClient fixture using ASGI transport (httpx >= 0.28)."""
    from backend.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
def mock_ollama_available(monkeypatch):
    """Monkeypatches state.ollama_available = True for tests that need it."""
    import backend.config as cfg
    monkeypatch.setattr(cfg.state, "ollama_available", True)
    return cfg.state
