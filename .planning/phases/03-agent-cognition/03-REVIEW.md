---
phase: 03-agent-cognition
reviewed: 2026-04-09T00:00:00Z
depth: standard
files_reviewed: 20
files_reviewed_list:
  - backend/agents/cognition/__init__.py
  - backend/agents/cognition/converse.py
  - backend/agents/cognition/decide.py
  - backend/agents/cognition/perceive.py
  - backend/agents/cognition/plan.py
  - backend/agents/memory/__init__.py
  - backend/agents/memory/retrieval.py
  - backend/agents/memory/store.py
  - backend/prompts/__init__.py
  - backend/prompts/action_decide.py
  - backend/prompts/conversation_start.py
  - backend/prompts/conversation_turn.py
  - backend/prompts/importance_score.py
  - backend/prompts/schedule_decompose.py
  - backend/prompts/schedule_init.py
  - backend/prompts/schedule_revise.py
  - backend/schemas.py
  - pyproject.toml
  - tests/test_cognition.py
  - tests/test_memory.py
findings:
  critical: 1
  warning: 4
  info: 3
  total: 8
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-04-09
**Depth:** standard
**Files Reviewed:** 20
**Status:** issues_found

## Summary

Phase 3 delivers a well-structured cognition and memory system. The architecture
decisions — ChromaDB-per-simulation isolation, asyncio.to_thread wrapping,
importance failsafes, and bounded conversation turn loops — are sound and the
security threat mitigations (T-03-01 through T-03-14) are correctly implemented.

The critical issue is a gateway contract violation: `complete_structured()` documents
"never raises" but silently re-raises for all non-AgentAction response models when
retries are exhausted. Every cognition call site (conversation, planning, schedule
revision) is unprotected and will surface uncaught exceptions to callers in
production under LLM failure.

Three warnings surface logic correctness issues: importance scoring silently drops
lifestyle context (double-uses the innate traits string), the last_access write-back
updates the wrong memory IDs, and a raw-dict branch in the schedule formatter can
pass unsanitized objects into prompt templates.

---

## Critical Issues

### CR-01: `complete_structured()` raises for non-`AgentAction` models — "never raises" contract violated

**File:** `backend/gateway.py:91-98`

**Issue:** The gateway docstring and inline comments (D-06) promise the function
"never raises." This is only true for `AgentAction`. For every other response
model (`DailySchedule`, `ConversationDecision`, `ConversationTurn`, `ScheduleRevision`,
`_SubTaskList`, `ImportanceScore`), when all retries are exhausted the function
re-raises `last_exc`. None of the call sites in `plan.py`, `decide.py`, or
`converse.py` have try/except guards. A transient LLM failure during schedule
generation or a conversation turn will propagate as an unhandled exception into
the simulation loop.

The only protected call site is `score_importance()` in `store.py` (lines 122-145),
which correctly wraps in try/except and returns the failsafe score of 5. All other
call sites assume the never-raises guarantee that does not exist.

**Fix:** Either extend the fallback to all response types, or change the contract to
explicitly document that non-`AgentAction` calls can raise and add try/except at
each call site. The cleanest approach is to accept a `fallback` parameter:

```python
async def complete_structured(
    messages: list[dict],
    response_model: Type[T],
    provider_config: ProviderConfig | None = None,
    max_retries: int = 3,
    fallback: T | None = None,  # <-- add this
) -> T:
    ...
    # All retries exhausted
    logger.warning("LLM call failed after %d retries", max_retries)
    if fallback is not None:
        return fallback
    if response_model is AgentAction:
        return FALLBACK_AGENT_ACTION  # type: ignore[return-value]
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("complete_structured: no result and no exception")
```

Then callers can opt in to a safe fallback:
```python
# In plan.py generate_daily_schedule():
daily_schedule: DailySchedule = await complete_structured(
    messages=messages,
    response_model=DailySchedule,
    fallback=DailySchedule(activities=["rest at home"], wake_hour=7),
)
```

---

## Warnings

### WR-01: `score_importance()` passes `innate` string as both `agent_traits` and `agent_lifestyle` — lifestyle context silently lost

**File:** `backend/agents/memory/store.py:126-130`

**Issue:** `score_importance()` takes `agent_scratch: str` and passes it to
`importance_score_prompt()` for both `agent_traits` and `agent_lifestyle`:

```python
messages = importance_score_prompt(
    agent_name=agent_name,
    agent_traits=agent_scratch,      # <-- correct: this is the innate string
    agent_lifestyle=agent_scratch,   # <-- BUG: should be a separate lifestyle string
    memory_text=memory_text,
)
```

The callers in `converse.py` (lines 265, 271) pass `agent_a_scratch.innate` —
only the personality traits string — because `score_importance` has no parameter
for lifestyle. The LLM receives the same string for both fields, so lifestyle
context (sleep patterns, daily habits) never informs importance scoring. A memory
about "waking at 5am" would score identically for a night owl and an early riser.

**Fix:** Update the signature to accept the full `AgentScratch` or add a separate
`agent_lifestyle` parameter:

```python
async def score_importance(
    agent_name: str,
    agent_scratch: str,          # innate traits
    memory_text: str,
    agent_lifestyle: str = "",   # <-- add this
) -> int:
    ...
    messages = importance_score_prompt(
        agent_name=agent_name,
        agent_traits=agent_scratch,
        agent_lifestyle=agent_lifestyle or agent_scratch,
        memory_text=memory_text,
    )
```

And update callers in `converse.py`:
```python
importance_a = await score_importance(
    agent_name=agent_a_name,
    agent_scratch=agent_a_scratch.innate,
    memory_text=summary_a,
    agent_lifestyle=agent_a_scratch.lifestyle,
)
```

---

### WR-02: `_update_last_access()` updates the wrong memory IDs — recency scoring corrupted

**File:** `backend/agents/memory/retrieval.py:157-186`

**Issue:** `_update_last_access()` calls `col.get(where={"agent_id": agent_id})` which
returns documents in insertion order, then updates the first `top_k` of those. This
is not the same set of documents that was actually retrieved in the semantic
query — the semantically top-k results by composite score may be any subset of the
agent's memories. The write-back will update insertion-order-first memories instead
of the ones that were actually accessed.

Over time this corrupts recency scoring: frequently-accessed memories (by semantic
query) never have their `last_access` updated, while the oldest inserted memories
always get updated. The composite score formula will eventually rank old-but-early-
inserted memories higher than recently accessed ones.

The comment in the code acknowledges this: "simplified: update all for this agent."
This should be flagged as a correctness issue, not just a simplification.

**Fix:** Track document IDs in the main query path and pass them to `_update_last_access`:

```python
# In retrieve_memories(), after building `top_results`:
retrieved_ids: list[str] = []
for _score, doc, meta in top_results:
    # Extract ID from raw results — ChromaDB returns ids in raw dict
    ...

# Pass IDs to the write-back
if retrieved_ids:
    await _update_last_access_by_ids(simulation_id, retrieved_ids, now)
```

Or include `"ids"` in the initial `col.query()` call (ChromaDB supports this via
`include=["documents", "metadatas", "distances", "ids"]` if available) and
pass those IDs directly.

At minimum, add `include=["ids"]` to the over-fetch query to capture which
specific documents were returned, then use those IDs in `col.update()`.

---

### WR-03: Schedule formatting in `run_conversation()` passes raw dicts verbatim — type inconsistency

**File:** `backend/agents/cognition/converse.py:291-298`

**Issue:** The schedule formatting loop:

```python
schedule_a_dicts = [
    {"describe": e.describe} if hasattr(e, "describe") else e
    for e in remaining_schedule_a
]
```

When `e` is a plain dict without a `describe` key (e.g., `{"start_minute": 720,
"duration_minutes": 60}`), the `else e` branch passes the raw dict object through.
The `schedule_revise_prompt` then calls `s.get('describe', str(s))` — for these
malformed entries, `str(s)` renders as something like
`"{'start_minute': 720, 'duration_minutes': 60}"` which the LLM receives as a
schedule item. This is not a crash, but it produces prompt pollution and
potentially garbled schedule revision output.

The same pattern appears at `decide.py:93-98` but is handled correctly there
because only `ScheduleEntry` objects or well-formed dicts are expected from
`current_schedule`.

**Fix:** Be explicit about the fallback:

```python
schedule_a_dicts = []
for e in remaining_schedule_a:
    if hasattr(e, "describe"):
        schedule_a_dicts.append({"describe": e.describe})
    elif isinstance(e, dict) and "describe" in e:
        schedule_a_dicts.append({"describe": e["describe"]})
    # else: silently skip malformed entries
```

---

### WR-04: `col.count()` in `retrieve_memories()` is not agent-scoped — empty-agent check can fail

**File:** `backend/agents/memory/retrieval.py:68-75`

**Issue:** The guard that prevents ChromaDB from being queried with `n_results`
exceeding document count uses `col.count()` — which counts ALL documents in the
collection across all agents. If agent "alice" has 0 memories but agent "bob" has
50, then `total = 50 > 0`, `effective_n = min(50, 50) = 50`, and ChromaDB
executes a query with `n_results=50` and `where={"agent_id": "alice"}`. ChromaDB
will attempt to retrieve 50 results for an agent with 0 matching documents.

Depending on the ChromaDB version, this either returns an empty result set
(harmless but wasting a query) or raises an exception (caught by the outer
try/except, returning `None` — which then returns `[]`). The `[]` case is
correct but only because the exception is swallowed, not because the logic is
sound.

**Fix:** Use a filtered count or rely solely on the exception handler:

```python
# Option A: remove the pre-check and rely on the exception handler
# (the existing except block already returns None -> [])

# Option B: count per-agent (ChromaDB Collection.count() doesn't support filters
# natively, but you can use col.get() with where filter and check len):
def _query() -> dict | None:
    col = get_collection(simulation_id)
    # Quick check: does this agent have any memories?
    agent_check = col.get(where={"agent_id": agent_id}, limit=1)
    if not agent_check["ids"]:
        return None
    ...
```

---

## Info

### IN-01: `isinstance(result, list)` branch in `decompose_hour()` is test-accommodation in production code

**File:** `backend/agents/cognition/plan.py:109-113`

**Issue:** The comment "Handle both the case where result is already a list (mock)"
reveals this branch exists to accommodate tests that return a raw list instead of
a `_SubTaskList`. In production, `complete_structured()` with `response_model=_SubTaskList`
always returns a `_SubTaskList` instance. The `isinstance(result, list)` check
is dead code in production and adds misleading complexity.

**Fix:** Remove the branch or move it into a test helper. If tests need to mock
this, they should return a `_SubTaskList` instance:
```python
# In test: return _SubTaskList(subtasks=[...]) instead of a raw list
# In plan.py:
subtasks = result.subtasks  # always safe if complete_structured is called correctly
```

---

### IN-02: `MemoryStore = None` is a misleading exported name

**File:** `backend/agents/memory/store.py:171`

**Issue:** `MemoryStore = None` is exported from the module with the comment
"Alias kept for import compatibility." Any consumer that imports `MemoryStore`
and attempts to use it as a class will get a `TypeError: 'NoneType' object is
not callable` with no helpful diagnostic. There is no functional API that matches
the name `MemoryStore` — the module uses standalone functions.

**Fix:** Remove the alias entirely. If it exists for import compatibility, document
which import it was replacing. If nothing imports it, delete it:
```python
# Remove this line:
MemoryStore = None  # Functional API — no class needed. Alias kept for import compatibility.
```

---

### IN-03: Module-level `_conversation_cooldowns` dict grows unbounded — no TTL pruning

**File:** `backend/agents/cognition/converse.py:50`

**Issue:** `_conversation_cooldowns: dict[frozenset, float] = {}` accumulates an
entry for every unique agent pair that ever converses. In a long-running simulation
with many agents, this dict grows indefinitely. Since entries are only written
(never pruned), a simulation running for hours with 20 agents (190 unique pairs)
creates 190 entries that are never removed even after they expire.

This is a minor memory concern at current scale (20 agents) but is worth noting
as a maintainability issue for future scaling.

**Fix:** Prune expired entries lazily inside `check_cooldown()`:
```python
def check_cooldown(agent_a: str, agent_b: str) -> bool:
    now = time.time()
    # Lazy prune: remove entries that have expired
    expired = [k for k, t in _conversation_cooldowns.items()
               if (now - t) >= COOLDOWN_SECONDS * 2]
    for k in expired:
        del _conversation_cooldowns[k]
    key = _pair_key(agent_a, agent_b)
    last_time = _conversation_cooldowns.get(key, 0)
    return (now - last_time) >= COOLDOWN_SECONDS
```

---

_Reviewed: 2026-04-09_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
