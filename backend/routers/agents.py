"""Agents REST API router for Agent Town backend.

Provides endpoints for querying per-agent data (memories, state).
"""
import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.agents.memory.store import get_collection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# T-05-06: Clamp limit to prevent unbounded ChromaDB fetch (DoS mitigation)
_MAX_MEMORIES = 50


@router.get("/agents/{agent_name}/memories")
async def get_agent_memories(
    agent_name: str,
    request: Request,
    limit: int = 5,
) -> JSONResponse:
    """Return the last N memories for an agent, sorted by created_at descending.

    Args:
        agent_name: URL path parameter — the agent's name (e.g. "Alice").
                    Used as ChromaDB metadata filter (string equality — no SQL injection risk,
                    T-05-04). Single-user localhost application.
        request:    FastAPI request for accessing app.state.engine.
        limit:      Number of memories to return (1-50). Defaults to 5.

    Returns:
        JSON object with "memories" list. Each entry has:
            content, type, importance, created_at

    Status codes:
        200: Success (including when agent has no memories — returns empty list)
        503: Simulation not yet initialized
    """
    # T-05-06: Clamp limit to prevent unbounded fetch
    limit = max(1, min(limit, _MAX_MEMORIES))

    engine = getattr(request.app.state, "engine", None)
    if engine is None:
        return JSONResponse(
            status_code=503,
            content={"detail": "Simulation not initialized"},
        )

    simulation_id: str = engine.simulation_id

    def _fetch() -> dict[str, Any]:
        """Synchronous ChromaDB fetch — run in thread to avoid blocking event loop.

        Pitfall 1 from store.py: all ChromaDB calls are synchronous — must wrap
        with asyncio.to_thread().
        """
        col = get_collection(simulation_id)
        result = col.get(
            where={"agent_id": agent_name},
            include=["documents", "metadatas"],
        )
        return result

    result = await asyncio.to_thread(_fetch)

    ids = result.get("ids") or []
    documents = result.get("documents") or []
    metadatas = result.get("metadatas") or []

    if not ids:
        return JSONResponse(content={"memories": []})

    # Sort by created_at descending (ChromaDB has no ORDER BY)
    entries = list(zip(documents, metadatas))
    entries.sort(key=lambda x: x[1].get("created_at", 0.0), reverse=True)

    # Slice to limit
    entries = entries[:limit]

    memories = [
        {
            "content": doc,
            "type": meta.get("memory_type", "observation"),
            "importance": meta.get("importance", 5),
            "created_at": meta.get("created_at", 0.0),
        }
        for doc, meta in entries
    ]

    return JSONResponse(content={"memories": memories})
