---
phase: 09-llm-optimization
plan: "01"
subsystem: backend/llm-gateway
tags: [concurrency, adaptive-timing, semaphore, tdd]
dependency_graph:
  requires: []
  provides:
    - asyncio.Semaphore(8) bounding concurrent LLM calls in gateway.py
    - get_adaptive_tick_interval() computing max(10, avg_latency * 1.5)
    - _latency_window deque recording successful LLM call durations
    - SimulationEngine.tick_interval adaptive property replacing TICK_INTERVAL constant
    - Agent.last_sector and Agent.had_new_perceptions gating fields
  affects:
    - backend/gateway.py
    - backend/simulation/engine.py
    - backend/agents/agent.py
tech_stack:
  added: []
  patterns:
    - asyncio.Semaphore for I/O-bound LLM concurrency control
    - Rolling deque(maxlen=10) for latency tracking without unbounded memory
    - @property for computed engine state derived from gateway module
    - TDD (RED/GREEN) for both tasks
key_files:
  created:
    - tests/test_gateway_semaphore.py
    - tests/test_engine_adaptive.py
  modified:
    - backend/gateway.py
    - backend/simulation/engine.py
    - backend/agents/agent.py
decisions:
  - Placed tick_interval as a @property on SimulationEngine (not a field) so it always reads the current latency window without caching
  - _latency_window records only successful call durations to avoid retry-overhead inflation (Pitfall 6)
  - 120s cold-start floor in _agent_step_safe prevents agents from timing out before any latency data is recorded
  - asyncio.Semaphore(8) wraps entire complete_structured() body including retry loop, not just the create() call
metrics:
  duration: "322s (~5 min)"
  completed_date: "2026-04-11"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 5
---

# Phase 09 Plan 01: LLM Concurrency Control and Adaptive Tick Timing Summary

One-liner: asyncio.Semaphore(8) bounds concurrent LLM calls while adaptive tick interval auto-adjusts to actual provider latency via rolling window.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add asyncio.Semaphore(8) and latency tracking to gateway.py | dd2595a | backend/gateway.py, tests/test_gateway_semaphore.py |
| 2 | Convert TICK_INTERVAL to adaptive property on SimulationEngine and add gating fields to Agent | f236bff | backend/simulation/engine.py, backend/agents/agent.py, tests/test_engine_adaptive.py |

## What Was Built

### Task 1 — gateway.py concurrency and latency tracking

Added to `backend/gateway.py`:

- `_llm_semaphore = asyncio.Semaphore(8)` — module-level semaphore bounding concurrent LLM calls (T-09-01, LLM-04)
- `_latency_window: deque[float] = deque(maxlen=10)` — rolling window of successful call latencies
- `get_adaptive_tick_interval(min_interval=10.0)` — returns `max(min_interval, avg * 1.5)`
- Wrapped `complete_structured()` body in `async with _llm_semaphore:`
- Measures latency via `time.perf_counter()` around ONLY the successful `_client.chat.completions.create()` call (not retry overhead)
- D-14 debug logging: "LLM semaphore acquired (model=...)" on entry and "LLM semaphore released (latency=...)" on successful return

7 tests in `tests/test_gateway_semaphore.py` cover: concurrency limit proof, latency recording on success, no latency on failure, get_adaptive_tick_interval edge cases (empty/fast/slow windows), and debug log messages.

### Task 2 — engine.py adaptive tick + agent gating fields

Modified `backend/simulation/engine.py`:

- Removed `TICK_INTERVAL: int = 30` constant (no longer referenced as assignment)
- Added `from backend.gateway import get_adaptive_tick_interval`
- Added `tick_interval` property: `get_adaptive_tick_interval(min_interval=10.0)`
- `_tick_loop()` now runs `asyncio.TaskGroup` of `_agent_step_safe` calls per tick (D-02), then sleeps `self.tick_interval` seconds with debug log
- `_agent_step_safe()` timeout changed from `max(TICK_INTERVAL * 4, 120)` to `max(self.tick_interval * 2, 120)` — the 120s floor prevents cold-start agent timeouts (Codex P1-3 fix)
- `get_snapshot()` includes `"tick_interval": self.tick_interval`

Modified `backend/agents/agent.py`:

- Added `last_sector: str | None = None` (D-08 per-sector gating, Phase 9)
- Added `had_new_perceptions: bool = True` (D-08 per-sector gating, Phase 9)

7 tests in `tests/test_engine_adaptive.py` cover: tick_interval property (empty/slow window), _agent_step_safe timeout formula, cold-start 120s floor, slow-provider above-floor case, Agent field defaults.

## Verification Results

```
tests/test_gateway_semaphore.py: 7 passed
tests/test_engine_adaptive.py: 7 passed
tests/test_structured_output.py: 5 passed (no regression)
tests/test_building_hours.py: all passed (no regression)
tests/test_agent_class.py: all passed (no regression)
Total: 14 new tests + all pre-existing relevant tests green
```

Acceptance criteria grep checks:
- `backend/gateway.py` contains `_llm_semaphore = asyncio.Semaphore(8)` ✓
- `backend/gateway.py` contains `_latency_window: deque[float] = deque(maxlen=10)` ✓
- `backend/gateway.py` contains `def get_adaptive_tick_interval(` ✓
- `backend/gateway.py` contains `async with _llm_semaphore:` ✓
- `backend/simulation/engine.py` does NOT contain `TICK_INTERVAL: int = 30` or assignment ✓
- `backend/simulation/engine.py` contains `def tick_interval(self) -> float:` ✓
- `backend/simulation/engine.py` contains `max(self.tick_interval * 2, 120)` ✓
- `backend/agents/agent.py` contains `last_sector: str | None = None` ✓
- `backend/agents/agent.py` contains `had_new_perceptions: bool = True` ✓

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] tick_interval property placed inside __init__ body causing instance attributes to be unreachable**

- **Found during:** Task 2 GREEN verification
- **Issue:** The `@property` was inserted at a point that placed `_sim_hour`, `_sim_minute`, `_last_ejection_hour`, and `_buildings` as unreachable code inside the property body (after `return`). `TestSimTimeTracking::test_sim_hour_starts_at_7` caught this.
- **Fix:** Moved all instance attribute assignments back into `__init__` before `return`, and placed the `@property` method after `__init__` closes.
- **Files modified:** backend/simulation/engine.py
- **Commit:** f236bff

**2. [Rule 1 - Bug] Test helper _minimal_agent_config used wrong AgentScratch fields**

- **Found during:** Task 2 RED run
- **Issue:** Test file used `name`, `occupation`, and `currently` fields that don't exist on `AgentScratch`. Also `AgentSpatial` requires `address` field.
- **Fix:** Updated `_minimal_agent_config()` to use the correct schema fields: `age`, `innate`, `learned`, `lifestyle`, `daily_plan` for scratch; `address` + `tree` for spatial; `coord` + `currently` at the AgentConfig level.
- **Files modified:** tests/test_engine_adaptive.py
- **Commit:** f236bff (included in same commit)

### Pre-existing Failures (Out of Scope)

The following test failures existed before this plan's changes (verified via git stash):

- `tests/test_health.py` — health endpoint returns 404 (route not registered)
- `tests/test_integration.py` — health + config endpoint failures (same root cause)
- `tests/test_simulation.py::test_movement_one_tile_per_tick` — movement test expects coord (6,5) but agent step doesn't advance tiles (movement is in `_movement_loop`, not `_agent_step`)

These are logged to deferred-items.md per scope boundary rules. Not caused by this plan.

## Known Stubs

None — all implemented functionality is wired to real logic. The `Agent.last_sector` and `Agent.had_new_perceptions` fields are intentional placeholders for Phase 9 Plan 02 (per-sector gating), which will wire them into the decision flow.

## Threat Flags

No new threat surface introduced beyond what was already declared in the plan's threat model (T-09-01, T-09-02, T-09-03 all addressed).

## Self-Check: PASSED

Files exist:
- backend/gateway.py — FOUND
- backend/simulation/engine.py — FOUND
- backend/agents/agent.py — FOUND
- tests/test_gateway_semaphore.py — FOUND
- tests/test_engine_adaptive.py — FOUND

Commits exist:
- dd2595a (Task 1) — FOUND
- f236bff (Task 2) — FOUND
