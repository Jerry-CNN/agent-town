"""Tests for the memory stream: storage, retrieval, agent isolation, composite scoring.

TDD RED phase: these tests are written before implementation and should fail initially.
"""
import asyncio
import time
import pytest

# These will fail until implementation exists
from backend.agents.memory.store import (
    MemoryStore,
    add_memory,
    get_collection,
    score_importance,
    reset_simulation,
)
from backend.agents.memory.retrieval import retrieve_memories
from backend.schemas import Memory, ImportanceScore


# ---------------------------------------------------------------------------
# Task 1 Tests: Storage and metadata
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_memory_and_query_roundtrip():
    """Store a memory then query for it -- content must match."""
    sim_id = "test_roundtrip"
    await reset_simulation(sim_id)

    await add_memory(
        simulation_id=sim_id,
        agent_id="alice",
        content="Alice baked bread at the town bakery",
        memory_type="observation",
        importance=7,
    )

    col = get_collection(sim_id)
    results = col.query(
        query_texts=["baked bread"],
        n_results=1,
        where={"agent_id": "alice"},
    )
    assert len(results["documents"][0]) == 1
    assert "bread" in results["documents"][0][0].lower()


@pytest.mark.asyncio
async def test_add_memory_uses_asyncio_to_thread():
    """Verify add_memory does not block the event loop (implementation must use asyncio.to_thread)."""
    # This test verifies the semantic behaviour: two concurrent add_memory calls
    # both complete without deadlock, confirming async-safe wrapping.
    sim_id = "test_async"
    await reset_simulation(sim_id)

    await asyncio.gather(
        add_memory(sim_id, "alice", "Alice visited the park", "observation", 3),
        add_memory(sim_id, "bob", "Bob went to the market", "observation", 4),
    )

    col = get_collection(sim_id)
    total = col.count()
    assert total == 2


@pytest.mark.asyncio
async def test_agent_isolation_in_storage():
    """Memories stored by agent 'alice' are NOT returned when querying for agent 'bob'."""
    sim_id = "test_isolation"
    await reset_simulation(sim_id)

    await add_memory(sim_id, "alice", "Alice secret: she loves cats", "observation", 5)
    await add_memory(sim_id, "bob", "Bob is at the coffee shop", "observation", 5)

    col = get_collection(sim_id)
    alice_results = col.query(
        query_texts=["cats"],
        n_results=5,
        where={"agent_id": "alice"},
    )
    bob_results = col.query(
        query_texts=["cats"],
        n_results=5,
        where={"agent_id": "bob"},
    )

    # Alice's memory should contain the cat secret
    alice_docs = alice_results["documents"][0]
    assert any("cats" in doc.lower() for doc in alice_docs)

    # Bob's results should NOT contain the cat secret
    bob_docs = bob_results["documents"][0]
    assert not any("cats" in doc.lower() for doc in bob_docs)


@pytest.mark.asyncio
async def test_importance_metadata_stored():
    """Importance is stored as integer metadata (1-10 range)."""
    sim_id = "test_importance_meta"
    await reset_simulation(sim_id)

    await add_memory(sim_id, "alice", "Alice watched the sunset", "observation", 8)

    col = get_collection(sim_id)
    results = col.get(where={"agent_id": "alice"}, include=["metadatas"])
    assert len(results["metadatas"]) == 1
    meta = results["metadatas"][0]
    assert meta["importance"] == 8
    assert isinstance(meta["importance"], int)


@pytest.mark.asyncio
async def test_memory_type_metadata_stored():
    """memory_type metadata accepts only valid literal values."""
    sim_id = "test_type_meta"
    await reset_simulation(sim_id)

    for mtype in ["observation", "conversation", "action", "event"]:
        await add_memory(
            sim_id, "alice", f"Alice did something ({mtype})", mtype, 5
        )

    col = get_collection(sim_id)
    results = col.get(where={"agent_id": "alice"}, include=["metadatas"])
    types = {m["memory_type"] for m in results["metadatas"]}
    assert types == {"observation", "conversation", "action", "event"}


@pytest.mark.asyncio
async def test_collection_uses_cosine_distance():
    """Collection metadata specifies cosine distance space."""
    sim_id = "test_cosine"
    col = get_collection(sim_id)
    assert col.metadata.get("hnsw:space") == "cosine"


@pytest.mark.asyncio
async def test_metadata_timestamps_present():
    """created_at and last_access are stored as float timestamps."""
    sim_id = "test_timestamps"
    await reset_simulation(sim_id)

    before = time.time()
    await add_memory(sim_id, "alice", "Alice arrived in town", "event", 6)
    after = time.time()

    col = get_collection(sim_id)
    results = col.get(where={"agent_id": "alice"}, include=["metadatas"])
    meta = results["metadatas"][0]

    assert "created_at" in meta
    assert "last_access" in meta
    assert before <= meta["created_at"] <= after
    assert before <= meta["last_access"] <= after


@pytest.mark.asyncio
async def test_score_importance_idle_events_no_llm():
    """Idle/waiting events get importance=1 without making an LLM call."""
    # If this calls an LLM, it will fail (no provider configured in tests).
    # The hardcode=1 path must be taken for idle events.
    score = await score_importance(
        agent_name="alice",
        agent_scratch="warm, creative",
        memory_text="idle",
    )
    assert score == 1


@pytest.mark.asyncio
async def test_score_importance_idle_variants():
    """Various idle/waiting events also get hardcoded importance=1."""
    for text in ["waiting", "idle", "Nothing happened", "alice is idle"]:
        score = await score_importance("alice", "warm", text)
        assert score == 1, f"Expected 1 for '{text}', got {score}"


@pytest.mark.asyncio
async def test_reset_simulation_clears_collection():
    """reset_simulation removes all memories from the simulation collection."""
    sim_id = "test_reset"
    await reset_simulation(sim_id)

    await add_memory(sim_id, "alice", "Alice has a secret", "observation", 5)
    col = get_collection(sim_id)
    assert col.count() > 0

    await reset_simulation(sim_id)
    col = get_collection(sim_id)
    assert col.count() == 0


# ---------------------------------------------------------------------------
# Task 2 Tests: Composite-scored retrieval
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retrieve_memories_returns_sorted_by_score():
    """High-importance memories rank above low-importance when recency/relevance equal."""
    sim_id = "test_retrieval_sort"
    await reset_simulation(sim_id)

    # Store memories with very different importance scores
    # Use the same content to equalize relevance
    await add_memory(sim_id, "alice", "Alice went for a walk in the park", "observation", 1)
    await add_memory(sim_id, "alice", "Alice went for a walk in the park", "observation", 10)
    await add_memory(sim_id, "alice", "Alice went for a walk in the park", "observation", 5)

    memories = await retrieve_memories(
        simulation_id=sim_id,
        agent_id="alice",
        query="walk in the park",
        top_k=3,
    )

    assert len(memories) == 3
    # The highest importance memory should rank first or second
    importances = [m.importance for m in memories]
    assert importances[0] >= importances[-1]  # sorted descending


@pytest.mark.asyncio
async def test_retrieve_memories_agent_isolation():
    """Querying for 'alice' never returns 'bob' memories."""
    sim_id = "test_retrieval_isolation"
    await reset_simulation(sim_id)

    await add_memory(sim_id, "alice", "Alice visited the bookstore", "observation", 5)
    await add_memory(sim_id, "bob", "Bob's secret mission to the vault", "observation", 5)

    alice_memories = await retrieve_memories(sim_id, "alice", "bookstore", top_k=10)
    bob_memories = await retrieve_memories(sim_id, "bob", "bookstore", top_k=10)

    # Alice's memories should NOT contain bob's
    alice_contents = [m.content for m in alice_memories]
    assert not any("vault" in c.lower() for c in alice_contents)

    # Bob's memories should NOT contain alice's
    bob_contents = [m.content for m in bob_memories]
    assert not any("bookstore" in c.lower() for c in bob_contents)


@pytest.mark.asyncio
async def test_retrieve_memories_top_k_limit():
    """top_k parameter limits the number of returned results."""
    sim_id = "test_retrieval_topk"
    await reset_simulation(sim_id)

    for i in range(5):
        await add_memory(sim_id, "alice", f"Alice memory number {i}", "observation", 5)

    memories = await retrieve_memories(sim_id, "alice", "Alice memory", top_k=2)
    assert len(memories) == 2


@pytest.mark.asyncio
async def test_retrieve_memories_empty_agent():
    """Returns empty list when no memories exist for the agent."""
    sim_id = "test_retrieval_empty"
    await reset_simulation(sim_id)

    memories = await retrieve_memories(sim_id, "nobody", "any query", top_k=5)
    assert memories == []


@pytest.mark.asyncio
async def test_retrieve_memories_returns_memory_models():
    """Retrieved memories are Memory Pydantic models with correct fields."""
    sim_id = "test_retrieval_schema"
    await reset_simulation(sim_id)

    await add_memory(sim_id, "alice", "Alice loves gardening", "observation", 7)

    memories = await retrieve_memories(sim_id, "alice", "gardening", top_k=1)
    assert len(memories) == 1
    m = memories[0]
    assert isinstance(m, Memory)
    assert m.agent_id == "alice"
    assert m.memory_type == "observation"
    assert m.importance == 7
    assert "garden" in m.content.lower()


@pytest.mark.asyncio
async def test_retrieve_memories_updates_last_access():
    """Retrieved memories have their last_access timestamp updated."""
    sim_id = "test_retrieval_access"
    await reset_simulation(sim_id)

    await add_memory(sim_id, "alice", "Alice found a rare book", "observation", 6)

    col = get_collection(sim_id)
    before_results = col.get(where={"agent_id": "alice"}, include=["metadatas"])
    original_access = before_results["metadatas"][0]["last_access"]

    # Wait briefly then retrieve
    await asyncio.sleep(0.01)
    before_retrieve = time.time()

    await retrieve_memories(sim_id, "alice", "rare book", top_k=1)

    after_results = col.get(where={"agent_id": "alice"}, include=["metadatas"])
    new_access = after_results["metadatas"][0]["last_access"]

    # last_access should be updated to >= before_retrieve time
    assert new_access >= before_retrieve
