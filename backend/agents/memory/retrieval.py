"""Composite-scored memory retrieval — stub (to be fully implemented in Task 2)."""
from backend.schemas import Memory


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
    """Stub — full implementation coming in Task 2."""
    raise NotImplementedError("retrieve_memories not yet implemented")
