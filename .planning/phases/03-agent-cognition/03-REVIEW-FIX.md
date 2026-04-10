---
phase: 03-agent-cognition
fixed_at: 2026-04-09T00:00:00Z
review_path: .planning/phases/03-agent-cognition/03-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 03: Code Review Fix Report

**Fixed at:** 2026-04-09
**Source review:** .planning/phases/03-agent-cognition/03-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (1 Critical, 4 Warning)
- Fixed: 5
- Skipped: 0

## Fixed Issues

### CR-01: `complete_structured()` raises for non-`AgentAction` models — "never raises" contract violated

**Files modified:** `backend/gateway.py`, `backend/agents/cognition/plan.py`, `backend/agents/cognition/converse.py`
**Commit:** bd1c898
**Applied fix:** Added optional `fallback: T | None = None` parameter to `complete_structured()`. When all retries are exhausted, the fallback is returned first (if provided), then the `AgentAction` hardcoded fallback, then re-raise. Updated the docstring to accurately describe the new contract. Added caller-supplied fallbacks at all unprotected call sites: `DailySchedule` and `_SubTaskList` in `plan.py`; `ConversationDecision`, `ConversationTurn` (both A and B), and `ScheduleRevision` (both A and B) in `converse.py`. `AgentAction` in `decide.py` already had the hardcoded fallback and needed no change.

---

### WR-01: `score_importance()` passes `innate` string as both `agent_traits` and `agent_lifestyle` — lifestyle context silently lost

**Files modified:** `backend/agents/memory/store.py`, `backend/agents/cognition/converse.py`
**Commit:** 47ab280
**Applied fix:** Added `agent_lifestyle: str = ""` parameter to `score_importance()`. Updated the `importance_score_prompt()` call inside to use `agent_lifestyle or agent_scratch` so lifestyle context informs importance scoring when provided. Updated both callers in `converse.py` to pass `agent_a_scratch.lifestyle` and `agent_b_scratch.lifestyle` respectively. The default empty string keeps all other callers backward-compatible.

---

### WR-02: `_update_last_access()` updates the wrong memory IDs — recency scoring corrupted

**Files modified:** `backend/agents/memory/retrieval.py`
**Commit:** c234b2e
**Applied fix:** Added `"ids"` to the `include` list in `col.query()`. Threaded the returned IDs through the composite scoring loop alongside each document, so the top-k results carry their exact ChromaDB document IDs. Replaced the old `_update_last_access()` (which re-fetched by insertion order) with `_update_last_access_by_ids()` that calls `col.get(ids=doc_ids)` to fetch and update only the memories that were actually semantically retrieved. The write-back now correctly updates recency for accessed memories.

---

### WR-03: Schedule formatting in `run_conversation()` passes raw dicts verbatim — type inconsistency

**Files modified:** `backend/agents/cognition/converse.py`
**Commit:** 4b28923
**Applied fix:** Replaced the list comprehension with an explicit loop for both `schedule_a_dicts` and `schedule_b_dicts`. The loop checks `hasattr(e, "describe")` for `ScheduleEntry` objects, then `isinstance(e, dict) and "describe" in e` for well-formed dicts, and silently skips any other entries (malformed dicts without a `describe` key). This prevents raw dict reprs like `"{'start_minute': 720, 'duration_minutes': 60}"` from reaching the LLM prompt.

---

### WR-04: `col.count()` in `retrieve_memories()` is not agent-scoped — empty-agent check can fail

**Files modified:** `backend/agents/memory/retrieval.py`
**Commit:** 9bfd720
**Applied fix:** Replaced the unscoped `col.count()` guard (which counted all agents' documents) with an agent-scoped `col.get(where={"agent_id": agent_id}, limit=1)` existence check. If the agent has no memories the function returns `None` immediately. Removed the `effective_n = min(n_results, total)` cap since it was based on the wrong total; the existing `except` block in `col.query()` already handles the case where `n_results` exceeds the actual agent document count.

---

_Fixed: 2026-04-09_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
