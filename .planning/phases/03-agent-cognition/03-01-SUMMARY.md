---
phase: 03-agent-cognition
plan: 01
subsystem: memory
tags: [chromadb, memory-stream, pydantic, async, retrieval, tdd]
dependency_graph:
  requires: [phase-01-foundation, phase-02-world-navigation]
  provides: [memory-stream, cognition-schemas]
  affects: [03-02-perception-planning, 03-03-conversation]
tech_stack:
  added: [chromadb==1.5.7, sentence-transformers==5.4.0]
  patterns: [asyncio.to_thread-for-sync-libs, composite-retrieval-scoring, tdd-red-green]
key_files:
  created:
    - backend/agents/memory/__init__.py
    - backend/agents/memory/store.py
    - backend/agents/memory/retrieval.py
    - backend/prompts/__init__.py
    - backend/prompts/importance_score.py
    - tests/test_memory.py
  modified:
    - backend/schemas.py
    - pyproject.toml
decisions:
  - "One ChromaDB collection per simulation (D-01): agent isolation via metadata filter not separate collections"
  - "asyncio.to_thread wraps all synchronous ChromaDB calls to avoid blocking FastAPI event loop"
  - "Idle/waiting events hardcoded to importance=1 without LLM call (reference pattern, T-03-03)"
  - "ImportanceScore fallback=5 on LLM failure — neutral score never crashes the pipeline"
  - "Over-fetch strategy: min(50, top_k*5) candidates before composite re-ranking"
metrics:
  duration_seconds: 287
  completed_date: "2026-04-10"
  tasks_completed: 2
  tasks_total: 2
  files_created: 6
  files_modified: 2
  tests_added: 16
  tests_total_after: 102
---

# Phase 03 Plan 01: Memory Stream and Cognition Schemas Summary

**One-liner:** ChromaDB-backed async memory stream with composite retrieval scoring (recency×0.5 + relevance×3 + importance×2) and all Phase 3 Pydantic v2 cognition schemas.

## What Was Built

### Memory Store (`backend/agents/memory/store.py`)

The core memory persistence layer. `add_memory()` wraps ChromaDB's synchronous `.add()` with `asyncio.to_thread()` so it never blocks the FastAPI event loop. Each memory document carries metadata: `agent_id`, `memory_type`, `importance`, `created_at`, `last_access`. The collection uses cosine distance space (`hnsw:space: cosine`).

`score_importance()` assigns 1-10 ratings at storage time via an LLM call (D-03). Idle/waiting events receive hardcoded importance=1 without any LLM call, saving cost on routine no-ops (reference `agent.py:631-656` pattern). On LLM failure, returns 5 as a neutral failsafe.

`reset_simulation()` deletes and recreates the simulation collection for fresh starts (INF-01).

Agent isolation is enforced structurally: `add_memory()` always stores `agent_id` in metadata, and every query in `retrieve_memories()` passes `where={"agent_id": agent_id}` (T-03-02).

### Retrieval Engine (`backend/agents/memory/retrieval.py`)

Implements the reference paper's composite scoring formula (D-02):

```
score = recency * 0.5 + relevance * 3.0 + importance * 2.0
```

Where:
- `recency = 0.995 ^ hours_since_last_access` (exponential decay)
- `relevance = 1.0 - cosine_distance` (ChromaDB distance → similarity)
- `importance = metadata["importance"] / 10.0` (normalized [0,1])

Over-fetches `min(50, top_k * 5)` candidates from ChromaDB before re-ranking, ensuring the scoring has enough diversity to differentiate results. Updates `last_access` timestamps on retrieved memories via write-back.

### Phase 3 Cognition Schemas (`backend/schemas.py`)

Extended with 9 new Pydantic v2 models shared across all Phase 3 plans:

| Model | Purpose |
|-------|---------|
| `Memory` | Memory stream entry with importance, type, timestamps |
| `ImportanceScore` | LLM-assigned 1-10 score with Field(ge=1, le=10) bounds |
| `SubTask` | 5-60 minute sub-task for schedule decomposition |
| `ScheduleEntry` | Hourly block with optional sub-task list |
| `DailySchedule` | Full daily schedule (min 3 activities, wake_hour 4-11) |
| `ConversationDecision` | LLM decision on whether agents should talk |
| `ConversationTurn` | Single conversation turn with end signal |
| `ScheduleRevision` | Post-conversation schedule update |
| `PerceptionResult` | Tile-grid perception sweep output |

### Importance Scoring Prompt (`backend/prompts/importance_score.py`)

`importance_score_prompt()` returns a messages list for the LLM importance call. Provides agent persona context (traits, lifestyle) and asks for a 1-10 rating with anchored examples (1=mundane routine, 10=life-changing). Designed to work with cheap models (GPT-4o-mini, Haiku).

### Test Suite (`tests/test_memory.py`)

16 tests covering:
- Storage roundtrip, async concurrency, agent isolation, metadata correctness
- Cosine space configuration, timestamp tracking, idle event hardcoding
- Composite score ordering, top_k limiting, empty agent handling
- Memory schema validation, last_access write-back

## Test Results

```
uv run pytest tests/test_memory.py -x -q  →  16 passed
uv run pytest -x -q                       →  102 passed (no regressions)
```

## Commits

| Hash | Message |
|------|---------|
| `811a437` | test(03-01): add failing tests for memory storage and retrieval (TDD RED) |
| `deaed25` | feat(03-01): memory store, cognition schemas, importance scoring prompt |
| `ba3b9c7` | feat(03-01): composite-scored memory retrieval with recency/relevance/importance |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Stub retrieval.py needed for import compatibility**
- **Found during:** Task 1 GREEN phase
- **Issue:** `tests/test_memory.py` imports `retrieve_memories` at module level. Running Task 1 tests failed with `ModuleNotFoundError: No module named 'backend.agents.memory.retrieval'`.
- **Fix:** Created a minimal `retrieval.py` stub raising `NotImplementedError` so Task 1 tests could be collected and run without Task 2's implementation.
- **Files modified:** `backend/agents/memory/retrieval.py` (stub, later replaced by full implementation)
- **Commit:** Included in `deaed25`

**2. [Rule 2 - Missing] ChromaDB count guard in retrieve_memories**
- **Found during:** Task 2 implementation
- **Issue:** ChromaDB raises an error if `n_results` exceeds the number of documents in the collection. A fresh simulation with no memories would crash the first retrieval call.
- **Fix:** Added `col.count()` check before querying. Returns `[]` immediately if collection is empty. Also caps `effective_n = min(n_results, total)`.
- **Files modified:** `backend/agents/memory/retrieval.py`
- **Commit:** `ba3b9c7`

## Known Stubs

None. All functionality is fully implemented and tested.

## Threat Flags

No new security surface beyond what was declared in the plan's threat model. The T-03-01 through T-03-04 mitigations are all implemented:
- T-03-01: `ImportanceScore` with `Field(ge=1, le=10)` + fallback=5
- T-03-02: `where={"agent_id": agent_id}` enforced on every query
- T-03-03: Idle-event hardcode + max_retries=3 + fallback=5
- T-03-04: `f"sim_{simulation_id}"` collection naming accepted (server-generated)

## Self-Check: PASSED

| Item | Status |
|------|--------|
| backend/agents/memory/__init__.py | FOUND |
| backend/agents/memory/store.py | FOUND |
| backend/agents/memory/retrieval.py | FOUND |
| backend/prompts/__init__.py | FOUND |
| backend/prompts/importance_score.py | FOUND |
| tests/test_memory.py | FOUND |
| 03-01-SUMMARY.md | FOUND |
| Commit 811a437 (test RED) | FOUND |
| Commit deaed25 (feat store) | FOUND |
| Commit ba3b9c7 (feat retrieval) | FOUND |
| 16 memory tests pass | PASS |
| 102 total tests pass | PASS |
