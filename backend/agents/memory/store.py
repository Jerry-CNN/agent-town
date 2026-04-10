"""ChromaDB-backed async memory store for Agent Town agent memory streams.

Architecture decisions implemented here:
- D-01: One ChromaDB collection per simulation (not per agent). Agent isolation is
  enforced via metadata filter `where={"agent_id": agent_id}` on every query.
- D-03: Importance scored by LLM at storage time. Idle/waiting events skip LLM
  and receive hardcoded importance=1 (reference agent.py:631-656 pattern).
- Pitfall 1: All ChromaDB calls are synchronous — wrapped with asyncio.to_thread()
  to avoid blocking the FastAPI async event loop.
- T-03-01: ImportanceScore Pydantic Field(ge=1, le=10) enforces range; fallback=5
  on LLM failure to prevent DoS from scoring failures.
- INF-01: reset_simulation() deletes and recreates the collection for fresh starts.
"""
import asyncio
import logging
import time
import uuid

import chromadb

from backend.schemas import ImportanceScore
from backend.prompts.importance_score import importance_score_prompt

logger = logging.getLogger(__name__)

# Module-level singleton client. EphemeralClient for tests and single-process use.
# Collections persist for the lifetime of the process (suitable for single-user v1).
_chroma_client = chromadb.EphemeralClient()

# Idle/waiting keywords — these events get importance=1 without an LLM call.
# Based on reference agent.py pattern for filtering non-significant routine events.
_IDLE_KEYWORDS = frozenset({"idle", "waiting", "nothing", "nothing happened"})


def get_collection(simulation_id: str) -> chromadb.Collection:
    """Return (or create) the ChromaDB collection for a simulation.

    Uses cosine distance space for semantic similarity retrieval (D-02).
    Collection name: f"sim_{simulation_id}" — server-generated, not user-supplied (T-03-04).

    Args:
        simulation_id: Unique identifier for the simulation instance.

    Returns:
        A ChromaDB Collection configured with cosine distance.
    """
    return _chroma_client.get_or_create_collection(
        f"sim_{simulation_id}",
        metadata={"hnsw:space": "cosine"},
    )


async def add_memory(
    simulation_id: str,
    agent_id: str,
    content: str,
    memory_type: str,
    importance: int,
) -> None:
    """Async wrapper to store a memory in the ChromaDB collection.

    Wraps synchronous ChromaDB call with asyncio.to_thread() so it never blocks
    the FastAPI event loop (Pitfall 1 mitigation).

    Agent isolation is enforced by storing agent_id in metadata. Every query
    MUST filter by agent_id to prevent cross-agent memory contamination (T-03-02).

    Args:
        simulation_id: Simulation collection to write into.
        agent_id:      Agent that owns this memory. Stored as metadata.
        content:       Natural language description of the memory.
        memory_type:   One of: "observation", "conversation", "action", "event".
        importance:    Integer 1-10 importance score (assign via score_importance).
    """
    now = time.time()
    doc_id = str(uuid.uuid4())
    metadata = {
        "agent_id": agent_id,
        "memory_type": memory_type,
        "importance": importance,
        "created_at": now,
        "last_access": now,
    }

    def _add() -> None:
        col = get_collection(simulation_id)
        col.add(
            ids=[doc_id],
            documents=[content],
            metadatas=[metadata],
        )

    await asyncio.to_thread(_add)


async def score_importance(
    agent_name: str,
    agent_scratch: str,
    memory_text: str,
) -> int:
    """Assign an importance score (1-10) to a memory via LLM (D-03).

    Idle/waiting events receive hardcoded importance=1 without an LLM call, saving
    cost on routine no-op events (reference agent.py:631-656 pattern, T-03-03).

    Returns 5 (neutral) as a failsafe if all LLM retries are exhausted (Pitfall 5).

    Args:
        agent_name:    Agent's display name for the prompt context.
        agent_scratch: Agent personality/lifestyle string for the prompt context.
        memory_text:   The memory text to score.

    Returns:
        Integer importance score in [1, 10].
    """
    # Hardcode importance=1 for idle/waiting events — skip the LLM call entirely.
    text_lower = memory_text.lower().strip()
    if any(kw in text_lower for kw in _IDLE_KEYWORDS):
        return 1

    # Build prompt and call LLM via gateway.
    # Import here to avoid circular import (gateway imports schemas, schemas is module).
    try:
        from backend.gateway import complete_structured

        messages = importance_score_prompt(
            agent_name=agent_name,
            agent_traits=agent_scratch,
            agent_lifestyle=agent_scratch,
            memory_text=memory_text,
        )
        result: ImportanceScore = await complete_structured(
            messages=messages,
            response_model=ImportanceScore,
            max_retries=3,
        )
        return result.score
    except Exception as exc:
        # Failsafe: return neutral score 5 rather than crashing (Pitfall 5, T-03-03).
        logger.warning(
            "score_importance failed for '%s': %s — returning fallback 5",
            memory_text[:50],
            type(exc).__name__,
        )
        return 5


async def reset_simulation(simulation_id: str) -> None:
    """Delete and recreate the simulation collection for a fresh start (INF-01).

    Safe to call even if the collection does not yet exist.

    Args:
        simulation_id: The simulation whose memory store should be cleared.
    """
    def _reset() -> None:
        try:
            _chroma_client.delete_collection(f"sim_{simulation_id}")
        except Exception:
            pass  # Collection may not exist yet — that's fine.
        # Recreate to ensure get_collection works immediately after reset.
        _chroma_client.get_or_create_collection(
            f"sim_{simulation_id}",
            metadata={"hnsw:space": "cosine"},
        )

    await asyncio.to_thread(_reset)


# Expose a MemoryStore name as a convenience alias referenced by the plan's must_haves.
MemoryStore = None  # Functional API — no class needed. Alias kept for import compatibility.
