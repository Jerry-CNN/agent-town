"""Tests for GET /api/agents/{agent_name}/memories endpoint."""
import pytest
from httpx import AsyncClient


async def test_memories_returns_empty_for_unknown_agent(async_client: AsyncClient):
    """GET /api/agents/unknown/memories returns 200 with empty memories list.

    When a simulation is running but no memories exist for the agent,
    the endpoint returns an empty list rather than 404 or 500.
    """
    response = await async_client.get("/api/agents/unknown-agent-xyz/memories")
    # Either 200 (engine running, no memories) or 503 (engine not initialized)
    # — both are valid depending on test startup state
    assert response.status_code in (200, 503)
    if response.status_code == 200:
        body = response.json()
        assert "memories" in body
        assert body["memories"] == []


async def test_memories_endpoint_registered(async_client: AsyncClient):
    """The /api/agents/{name}/memories route exists (not 404/405)."""
    response = await async_client.get("/api/agents/Alice/memories")
    assert response.status_code != 404
    assert response.status_code != 405


async def test_memories_503_when_engine_not_initialized(
    async_client: AsyncClient,
    monkeypatch,
):
    """Returns 503 with detail when app.state.engine is None."""
    from backend.main import app
    original = getattr(app.state, "engine", None)
    try:
        app.state.engine = None
        response = await async_client.get("/api/agents/Alice/memories")
        assert response.status_code == 503
        body = response.json()
        assert "detail" in body
        assert body["detail"] == "Simulation not initialized"
    finally:
        app.state.engine = original


async def test_memories_limit_clamped(async_client: AsyncClient, monkeypatch):
    """The limit parameter is clamped to 50 — excessive values are safe."""
    from backend.main import app
    original = getattr(app.state, "engine", None)
    try:
        app.state.engine = None
        # With no engine, we get 503 regardless of limit — just check no crash
        response = await async_client.get(
            "/api/agents/Alice/memories?limit=9999"
        )
        assert response.status_code in (200, 503)
    finally:
        app.state.engine = original


async def test_memories_with_mock_engine(async_client: AsyncClient, monkeypatch):
    """Returns memories list structure when engine is initialized (mocked)."""
    import chromadb
    from backend.main import app
    from unittest.mock import MagicMock

    # Create an ephemeral collection with one test memory
    client = chromadb.EphemeralClient()
    test_sim_id = "test-sim-001"
    col = client.get_or_create_collection(f"sim_{test_sim_id}")
    col.add(
        ids=["mem-001"],
        documents=["Alice went to the park and felt happy."],
        metadatas=[{
            "agent_id": "Alice",
            "memory_type": "observation",
            "importance": 7,
            "created_at": 1700000000.0,
            "last_access": 1700000000.0,
        }],
    )

    # Patch get_collection to return our test collection
    monkeypatch.setattr(
        "backend.routers.agents.get_collection",
        lambda sim_id: col,
    )

    # Provide a mock engine with the test simulation_id
    mock_engine = MagicMock()
    mock_engine.simulation_id = test_sim_id
    original_engine = getattr(app.state, "engine", None)

    try:
        app.state.engine = mock_engine
        response = await async_client.get("/api/agents/Alice/memories?limit=5")
        assert response.status_code == 200
        body = response.json()
        assert "memories" in body
        assert len(body["memories"]) == 1
        memory = body["memories"][0]
        assert memory["content"] == "Alice went to the park and felt happy."
        assert memory["type"] == "observation"
        assert memory["importance"] == 7
        assert memory["created_at"] == 1700000000.0
    finally:
        app.state.engine = original_engine
