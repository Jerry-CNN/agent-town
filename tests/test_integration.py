"""End-to-end integration tests for Agent Town backend.

Tests the full stack: health check, provider config, WebSocket ping-pong,
and concurrency suite verification. Requires no real LLM — mocks where needed.
"""
import json
import subprocess
import sys
import os

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Test 1: Health check
# ---------------------------------------------------------------------------

async def test_health_check_returns_200(async_client: AsyncClient):
    """GET /health returns 200 with status and provider_status keys."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "provider_status" in data
    assert "ollama" in data["provider_status"]
    assert "openrouter" in data["provider_status"]


# ---------------------------------------------------------------------------
# Test 2: Config — Ollama
# ---------------------------------------------------------------------------

async def test_config_ollama_returns_configured(async_client: AsyncClient):
    """POST /api/config with ollama provider returns configured status."""
    response = await async_client.post(
        "/api/config",
        json={"provider": "ollama"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "configured"
    assert data["provider"] == "ollama"

    # Subsequent GET /health should reflect ollama state
    health_resp = await async_client.get("/health")
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    # openrouter should be false since we configured ollama (no api_key)
    assert health_data["provider_status"]["openrouter"] is False


# ---------------------------------------------------------------------------
# Test 3: Config — OpenRouter
# ---------------------------------------------------------------------------

async def test_config_openrouter_returns_configured(async_client: AsyncClient):
    """POST /api/config with openrouter+api_key returns configured; health shows openrouter=true."""
    response = await async_client.post(
        "/api/config",
        json={"provider": "openrouter", "api_key": "sk-or-test-123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "configured"
    assert data["provider"] == "openrouter"

    # Subsequent GET /health should show openrouter=true
    health_resp = await async_client.get("/health")
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert health_data["provider_status"]["openrouter"] is True


# ---------------------------------------------------------------------------
# Test 4: Config — OpenRouter missing key returns 422
# ---------------------------------------------------------------------------

async def test_config_openrouter_missing_key_returns_422(async_client: AsyncClient):
    """POST /api/config with openrouter but no api_key returns 422 (schema validation)."""
    response = await async_client.post(
        "/api/config",
        json={"provider": "openrouter"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Test 5: WebSocket ping-pong (synchronous Starlette TestClient)
# ---------------------------------------------------------------------------

def test_ws_ping_pong():
    """Open WS connection, send ping, receive pong."""
    from starlette.testclient import TestClient
    from backend.main import app

    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.send_text(json.dumps({"type": "ping", "payload": {}, "timestamp": 1.0}))
        response = ws.receive_text()
        data = json.loads(response)
        assert data["type"] == "pong"


# ---------------------------------------------------------------------------
# Test 6: Concurrency integration — run test_concurrency.py as subprocess
# ---------------------------------------------------------------------------

def test_concurrency_suite_passes():
    """
    Run tests/test_concurrency.py via subprocess to verify concurrent
    execution proof is still green in integration context.
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = subprocess.run(
        ["uv", "run", "pytest", "tests/test_concurrency.py", "-q"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    assert result.returncode == 0, (
        f"test_concurrency.py failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
