"""Composite-scored memory retrieval for Agent Town's memory stream.

Architecture decisions implemented here:
- D-02: Composite scoring formula: recency x 0.5 + relevance x 3 + importance x 2
  Follows the reference paper's AssociateRetriever._normalize() pattern.
- T-03-02: agent_id filter enforced on EVERY ChromaDB query — impossible to call
  retrieve_memories without specifying an agent_id. Cross-agent contamination prevented.
- Pitfall 1: ChromaDB .query() is synchronous — wrapped with asyncio.to_thread().
- D-05: Returns top 5-10 memories per decision query; top_k parameter is explicit.
- Over-fetch strategy: query min(50, top_k * 5) candidates before re-ranking to ensure
  enough diversity for composite scoring to differentiate results.
"""
import asyncio
import logging
import time

from backend.schemas import Memory
from backend.agents.memory.store import get_collection

logger = logging.getLogger(__name__)


async def retrieve_memories(
    simulation_id: str,
    agent_id: str,
    query: str,
    top_k: int = 10,
    recency_decay: float = 0.995,
    recency_weight: float = 0.5,
    relevance_weight: float = 3.0,
    importance_weight: float = 2.0,
) -> list[Memory]:
    """Retrieve and rank an agent's memories by composite score.

    Composite score = recency * recency_weight + relevance * relevance_weight
                    + importance * importance_weight

    Where:
    - recency   = recency_decay ** hours_since_last_access  (exponential decay)
    - relevance = 1.0 - cosine_distance                     (ChromaDB cosine: 0=same, 1=orthogonal)
    - importance = metadata["importance"] / 10.0            (normalized to [0, 1])

    Agent isolation is ALWAYS enforced via where={"agent_id": agent_id} (T-03-02).
    ChromaDB calls are wrapped in asyncio.to_thread() to avoid blocking the event loop.

    Args:
        simulation_id:     The simulation collection to query.
        agent_id:          Agent whose memories to retrieve. Mandatory filter.
        query:             Natural language query for semantic similarity search.
        top_k:             Maximum number of memories to return after re-ranking.
        recency_decay:     Exponential decay base (0.995 = default from paper).
        recency_weight:    Multiplier for recency score (0.5 = default from paper).
        relevance_weight:  Multiplier for relevance score (3.0 = default from paper).
        importance_weight: Multiplier for importance score (2.0 = default from paper).

    Returns:
        List of Memory models sorted by composite score descending, length <= top_k.
        Returns [] if no memories exist for this agent.
    """
    now = time.time()
    # Over-fetch to ensure re-ranking has enough candidates
    n_results = min(50, max(top_k * 5, top_k + 5))

    def _query() -> dict | None:
        col = get_collection(simulation_id)

        # Agent-scoped existence check: col.count() counts ALL agents in the collection,
        # so use a filtered get() with limit=1 to test whether this specific agent has
        # any memories. This prevents querying with n_results > agent's actual document
        # count, which causes ChromaDB to error or return empty unexpectedly (WR-04 fix).
        agent_docs = col.get(where={"agent_id": agent_id})
        agent_count = len(agent_docs["ids"]) if agent_docs["ids"] else 0
        if agent_count == 0:
            return None

        # Clamp n_results to agent's actual document count to avoid ChromaDB errors
        clamped = min(n_results, agent_count)

        try:
            results = col.query(
                query_texts=[query],
                n_results=clamped,
                where={"agent_id": agent_id},
                include=["documents", "metadatas", "distances"],
            )
            return results
        except Exception as exc:
            # Catch "no embeddings", "n_results > count", or "no results" gracefully.
            logger.debug("ChromaDB query returned no results: %s", exc)
            return None

    raw = await asyncio.to_thread(_query)

    if raw is None:
        return []

    docs = raw["documents"][0]
    metas = raw["metadatas"][0]
    dists = raw["distances"][0]
    # ChromaDB returns ids at the top level when include=["ids"] is requested.
    # The query result shape is: {"ids": [[id1, id2, ...]], "documents": [[...]], ...}
    raw_ids: list[str] = raw.get("ids", [[]])[0]

    if not docs:
        return []

    # Compute composite scores — track doc ID alongside score for correct write-back
    scored: list[tuple[float, str, str, dict]] = []
    for doc_id, doc, meta, dist in zip(raw_ids, docs, metas, dists):
        hours_since_access = (now - meta["last_access"]) / 3600.0
        recency = recency_decay ** hours_since_access

        # ChromaDB cosine distance: 0 = identical, 1 = orthogonal, 2 = opposite.
        # Convert to similarity: 1.0 - dist gives [0, 1] for [orthogonal, identical].
        relevance = max(0.0, 1.0 - dist)

        importance = meta["importance"] / 10.0

        score = (
            recency * recency_weight
            + relevance * relevance_weight
            + importance * importance_weight
        )
        scored.append((score, doc_id, doc, meta))

    # Sort by composite score descending
    scored.sort(key=lambda x: x[0], reverse=True)
    top_results = scored[:top_k]

    # Extract the IDs of the semantically top-k results for correct write-back.
    # These are the memories that were actually accessed — NOT insertion-order IDs.
    retrieved_ids: list[str] = [doc_id for _score, doc_id, _doc, _meta in top_results]
    memories: list[Memory] = []

    for _score, _doc_id, doc, meta in top_results:
        memories.append(
            Memory(
                content=doc,
                agent_id=meta["agent_id"],
                memory_type=meta["memory_type"],
                importance=meta["importance"],
                created_at=meta["created_at"],
                last_access=now,
            )
        )

    # Write-back last_access using the exact IDs returned by the semantic query (WR-02 fix).
    if retrieved_ids:
        await _update_last_access_by_ids(simulation_id, retrieved_ids, now)

    return memories


async def _update_last_access_by_ids(
    simulation_id: str,
    doc_ids: list[str],
    now: float,
) -> None:
    """Write back updated last_access timestamps for the exact document IDs retrieved.

    Uses the IDs returned directly from the semantic query so that recency scoring
    is updated for the memories that were actually accessed, not insertion-order ones.
    """

    def _do_update() -> None:
        col = get_collection(simulation_id)
        try:
            # Fetch current metadata for the specific retrieved documents
            results = col.get(
                ids=doc_ids,
                include=["metadatas"],
            )
            if not results["ids"]:
                return

            updated_metas = []
            for meta in results["metadatas"]:
                updated = dict(meta)
                updated["last_access"] = now
                updated_metas.append(updated)

            col.update(
                ids=results["ids"],
                metadatas=updated_metas,
            )
        except Exception as exc:
            logger.debug("last_access write-back failed (non-critical): %s", exc)

    await asyncio.to_thread(_do_update)
