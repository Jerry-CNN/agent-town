---
phase: 09-llm-optimization
reviewed: 2026-04-11T00:00:00Z
depth: standard
files_reviewed: 21
files_reviewed_list:
  - backend/agents/agent.py
  - backend/agents/cognition/converse.py
  - backend/agents/cognition/decide.py
  - backend/config.py
  - backend/gateway.py
  - backend/prompts/arena_decide.py
  - backend/routers/llm.py
  - backend/schemas/__init__.py
  - backend/schemas/agent.py
  - backend/schemas/ws.py
  - backend/simulation/engine.py
  - frontend/src/App.tsx
  - frontend/src/components/BottomBar.tsx
  - frontend/src/components/Layout.tsx
  - frontend/src/components/ProviderSetup.tsx
  - frontend/src/hooks/useWebSocket.ts
  - frontend/src/store/simulationStore.ts
  - frontend/src/types/index.ts
  - tests/test_agent_class.py
  - tests/test_converse_repetition.py
  - tests/test_decide_cascade.py
  - tests/test_engine_adaptive.py
  - tests/test_gateway_semaphore.py
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 09: Code Review Report

**Reviewed:** 2026-04-11
**Depth:** standard
**Files Reviewed:** 21
**Status:** issues_found

## Summary

Phase 09 introduces adaptive tick intervals, per-sector LLM gating (D-08), the 2-level sector/arena cascade (D-09), conversation repetition detection (D-10), and the arena-level decision prompt. The overall architecture is sound and security mitigations are correctly applied. The four warning-level findings are correctness issues in the test suite and in the gateway log contract — none crash production, but two will cause test failures and one silently breaks an observable behavior.

---

## Warnings

### WR-01: Test 7 in `test_gateway_semaphore.py` asserts log messages that `gateway.py` never emits

**File:** `tests/test_gateway_semaphore.py:196-201`

**Issue:** The test `test_debug_log_messages_on_acquire_and_release` asserts that the strings `"LLM semaphore acquired"` and `"LLM semaphore released"` appear in debug logs. Searching `gateway.py` reveals that **neither string is ever logged**. The only semaphore-related debug log that exists (line 141) reads `"LLM semaphore released (all retries exhausted, no latency recorded)"` and is only emitted on the failure path. The success path emits no semaphore-level debug messages at all. This test will fail on every run.

**Fix:** Either add the expected debug log statements to `gateway.py`:
```python
async with _llm_semaphore:
    logger.debug("LLM semaphore acquired: type=%s", call_type)
    ...
    logger.debug("LLM semaphore released: type=%s latency=%.2fs", call_type, elapsed)
    return result
```
or update the test to assert messages that `gateway.py` actually logs (`"LLM call:"` and `"LLM done:"`).

---

### WR-02: `engine.py` — dynamic attribute `_last_schedule_block` set with `type: ignore` is not declared on `Agent`

**File:** `backend/simulation/engine.py:407`

**Issue:** The engine writes `agent._last_schedule_block = current_schedule_block` with a `# type: ignore[attr-defined]` comment. This attribute is not declared on the `Agent` dataclass (`backend/agents/agent.py`), so it relies on Python's ability to set arbitrary attributes on dataclass instances. While this works at runtime, it has two concrete risks:
1. If `Agent` is ever changed to use `__slots__` (common optimization for high-count dataclasses), all existing simulations will crash with `AttributeError` at this line.
2. The `getattr(agent, '_last_schedule_block', None)` guard on line 406 is the only protection — if the guard is removed or the attribute name is changed in one place but not the other, the gating logic silently breaks.

**Fix:** Declare the field on `Agent`:
```python
# In backend/agents/agent.py, add to the dataclass:
_last_schedule_block: str | None = field(default=None, repr=False)
```
Then remove the `type: ignore` comment and the `getattr` fallback in `engine.py`.

---

### WR-03: `run_conversation` records the cooldown before schedule revision completes — early failure leaves pair permanently throttled

**File:** `backend/agents/cognition/converse.py:301`

**Issue:** `_record_conversation(agent_a_name, agent_b_name)` is called on line 301 — immediately after the turn loop ends and **before** the `score_importance`, `add_memory`, and `ScheduleRevision` LLM calls (lines 313–383). If any of those subsequent awaits raise an exception (LLM failure not caught by instructor, ChromaDB write failure, etc.), the cooldown is already recorded. The calling code in `engine._agent_step_safe` catches all exceptions (T-04-01), so the exception is swallowed. The effect is that the agent pair is cooldown-blocked for 60 seconds despite the conversation effectively not completing (no memories stored, no schedule revised).

In practice this is a minor UX issue, but it can cause agents who experience repeated LLM failures to become permanently non-conversational (the cooldown keeps resetting on each failed attempt before they recover).

**Fix:** Move `_record_conversation` to after the schedule revision is complete, or wrap the post-loop work in a try/finally that records the cooldown only on clean completion:
```python
try:
    # ... score_importance, add_memory, schedule revision ...
finally:
    _record_conversation(agent_a_name, agent_b_name)
```

---

### WR-04: `appendFeed` in `simulationStore.ts` grows unbounded — no size cap

**File:** `frontend/src/store/simulationStore.ts:61`

**Issue:** `appendFeed` spreads the existing feed array and appends unconditionally:
```typescript
set((state) => ({ feed: [...state.feed, msg] })),
```
Every `conversation` and `event` message is appended for the lifetime of the browser session. In a long-running simulation with 10+ agents, conversations fire every tick. With a 10-second tick interval and 5 agent pairs, the feed accumulates ~1,800 entries per hour. Over a multi-hour session this causes progressive memory growth and re-render cost, because every `appendFeed` call creates a new array reference and triggers a full re-render of any subscriber that depends on `feed`.

**Fix:** Cap the feed at a reasonable limit (e.g., 200 entries):
```typescript
appendFeed: (msg: WSMessage) =>
  set((state) => {
    const next = [...state.feed, msg];
    return { feed: next.length > 200 ? next.slice(-200) : next };
  }),
```

---

## Info

### IN-01: `engine.py` `get_snapshot` uses `hasattr` guard for `occupation` field that does not exist on `AgentScratch`

**File:** `backend/simulation/engine.py:665`

**Issue:** The snapshot builder uses `hasattr(agent.config.scratch, "occupation")` as a safety guard before reading it, but `AgentScratch` (defined in `backend/schemas/agent.py`) has no `occupation` field at all. The `hasattr` guard always returns `False`, so `occupation` is always emitted as `""` in every snapshot. This is dead/unreachable code that silently returns the wrong data. Clients that display occupation (the `AgentInspector` component references `agent.occupation` from the snapshot) will always show an empty string.

**Fix:** Either add `occupation: str = ""` to `AgentScratch` and populate it in agent config JSON files, or remove the `occupation` key from the snapshot entirely and update the frontend `SnapshotAgent` type accordingly.

---

### IN-02: `ProviderSetup.tsx` — API key stored in `localStorage` without documentation in security comment

**File:** `frontend/src/components/ProviderSetup.tsx:54,64`

**Issue:** The comment on line 54 reads `"T-03-01: API key stored in localStorage as known tradeoff"` but there is no explanation of the risk or a reference to a mitigations document. The API key is a user-supplied OpenRouter credential. Storing it in `localStorage` exposes it to any JavaScript running in the same origin (XSS attack surface). This is the standard pattern for SPAs but it should be explicitly called out in the risk register. The existing comment is correct that it is a known tradeoff — this is an info item to ensure it is tracked.

No code change required; suggest adding a brief inline note or a reference to the threat model document where T-03-01 is recorded.

---

### IN-03: `test_engine_adaptive.py` — tests 3, 4, and 5 are not decorated with `@pytest.mark.asyncio` and will not be collected as async tests

**File:** `tests/test_engine_adaptive.py:85,122,157`

**Issue:** `test_agent_step_safe_timeout_formula`, `test_agent_step_safe_cold_start_floor_120`, and `test_agent_step_safe_slow_provider_above_floor` are all `async def` functions but lack the `@pytest.mark.asyncio` decorator. With `pytest-asyncio` in `auto` mode these will run correctly; in `strict` mode (the more reliable configuration for CI) they will be collected but not awaited — pytest will emit a warning and the test body will never execute, making the tests silently pass vacuously. Similarly, `test_semaphore_limits_concurrent_inflight` (line 15), `test_successful_call_records_latency` (line 59), `test_failed_call_does_not_record_latency` (line 95), and `test_debug_log_messages_on_acquire_and_release` (line 172) in `test_gateway_semaphore.py` share the same issue.

**Fix:** Add `@pytest.mark.asyncio` to all `async def` test functions in both files, or add `asyncio_mode = "auto"` to `pyproject.toml`/`pytest.ini` to make the entire test suite use auto mode consistently.

---

_Reviewed: 2026-04-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
