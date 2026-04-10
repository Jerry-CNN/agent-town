---
phase: 03-agent-cognition
plan: 02
subsystem: cognition
tags: [perception, schedule-generation, tile-grid, tdd, pydantic, llm, pure-python]
dependency_graph:
  requires: [03-01-memory-stream, phase-02-world-navigation]
  provides: [perception-module, schedule-generation, prompt-templates]
  affects: [03-03-conversation-decisions]
tech_stack:
  added: []
  patterns: [tile-grid-euclidean-scan, two-level-schedule-tdd-red-green, pydantic-wrapper-for-list-response]
key_files:
  created:
    - backend/agents/cognition/__init__.py
    - backend/agents/cognition/perceive.py
    - backend/agents/cognition/plan.py
    - backend/prompts/schedule_init.py
    - backend/prompts/schedule_decompose.py
    - tests/test_cognition.py
  modified: []
decisions:
  - "perceive() is synchronous (not async) -- perception is a pure Python tile-grid read with zero LLM calls (Anti-Pattern 1 prevention)"
  - "_SubTaskList wrapper model: instructor requires Pydantic model at top level for decompose_hour, so list[SubTask] is wrapped in _SubTaskList(subtasks=...)"
  - "Square bounding box + Euclidean distance filter: iterate over (x-r, y-r)→(x+r, y+r) then filter by math.sqrt(dx^2+dy^2) <= radius; avoids Manhattan approximation"
  - "Events capped at 10 (att_bandwidth limit from reference GenerativeAgentsCN perceive.py)"
  - "decompose_hour handles both mock (list) and real (_SubTaskList) return types for test compatibility"
metrics:
  duration_seconds: 269
  completed_date: "2026-04-10"
  tasks_completed: 2
  tasks_total: 2
  files_created: 6
  files_modified: 0
  tests_added: 21
  tests_total_after: 123
---

# Phase 03 Plan 02: Perception and Schedule Planning Summary

**One-liner:** Synchronous tile-grid perception scan (zero LLM calls) and two-level daily schedule generation (DailySchedule LLM call → hourly ScheduleEntry list, then _SubTaskList LLM call → SubTask decomposition).

## What Was Built

### Perception Module (`backend/agents/cognition/perceive.py`)

Pure Python perception with zero LLM calls (Anti-Pattern 1 prevention). `perceive()` scans a square bounding box `(x±radius, y±radius)` and filters by Euclidean distance `math.sqrt(dx² + dy²) <= radius`. For each in-radius tile, it reads `tile._events` for events and checks `all_agents` entries for nearby agents.

Key behaviors:
- Self-exclusion via `agent_name` comparison
- `try/except IndexError` around `maze.tile_at()` for edge-of-map safety
- Events capped at 10 (`_MAX_EVENTS`) per the reference att_bandwidth limit
- Both events and agents sorted by distance ascending (closest first)
- Location string from `maze.tile_at(agent_coord).get_address(as_list=False)`

The `all_agents` parameter uses a plain dict (`name -> {"coord": ..., "current_activity": ...}`) decoupling perception from any specific `AgentState` class not yet defined.

### Two-Level Schedule Generation (`backend/agents/cognition/plan.py`)

**LLM Call 1 — `generate_daily_schedule()`:** Calls `complete_structured()` with `schedule_init_prompt()` and `DailySchedule` response model. Converts the returned activity list into `ScheduleEntry` objects distributed across hours starting at `wake_hour`. Each entry gets `start_minute = (wake_hour + i) * 60`, `duration_minutes = 60`.

**LLM Call 2 — `decompose_hour()`:** Calls `complete_structured()` with `schedule_decompose_prompt()` and `_SubTaskList` response model (a Pydantic wrapper around `list[SubTask]`). Attaches the result to `entry.decompose` and returns the list.

`_SubTaskList` wrapper exists because instructor requires a Pydantic model at the top level — it cannot directly return `list[SubTask]`. The decompose_hour implementation handles both real `_SubTaskList` instances and raw list mocks for test compatibility.

### Prompt Templates

**`backend/prompts/schedule_init.py`:** Returns `[system, user]` messages. The user message includes agent name, age, traits, lifestyle, and — critically — the `daily_plan_template` (Pitfall 4 prevention). Without this, the LLM generates generic schedules that ignore the agent's configured routine, breaking D-09.

**`backend/prompts/schedule_decompose.py`:** Returns `[system, user]` messages asking for 3-5 sub-tasks of 5-15 minutes each, covering the full hourly block duration.

### Test Suite (`tests/test_cognition.py`)

21 tests covering:

**Perception (11 tests):**
- Agent detection within radius (distance ~2.83 < 5)
- Agent exclusion outside radius (distance ~14.1 > 5)
- Self-exclusion (agent not in its own nearby_agents list)
- Event detection within radius
- Event exclusion outside radius
- Location field populated from tile address
- Activity field in nearby_agents
- Distance-sorted results
- Radius boundary (exactly at 5.0 included; at 6.0 excluded)
- Returns PerceptionResult type
- Empty agents case

**Schedule (10 tests):**
- schedule_init_prompt includes daily_plan_template content
- schedule_init_prompt includes agent name
- schedule_init_prompt includes personality traits
- schedule_init_prompt returns valid messages list structure
- schedule_decompose_prompt includes hourly activity description
- schedule_decompose_prompt returns valid messages list structure
- generate_daily_schedule returns list[ScheduleEntry] (mocked LLM)
- generate_daily_schedule uses wake_hour for start_minute calculation
- decompose_hour returns list[SubTask] (mocked LLM)
- SubTask durations within valid range (5-60 minutes)

## Test Results

```
uv run pytest tests/test_cognition.py -x -q  →  21 passed
uv run pytest -x -q                          →  123 passed (no regressions)
```

## Commits

| Hash | Message |
|------|---------|
| `effb964` | test(03-02): add failing tests for perception and schedule generation (TDD RED) |
| `08f8749` | feat(03-02): perception module -- tile-grid scan within radius |
| `718838f` | feat(03-02): two-level schedule generation via LLM |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing] _SubTaskList wrapper model for decompose_hour**
- **Found during:** Task 2 implementation
- **Issue:** `complete_structured()` uses instructor which requires a Pydantic model at the top level. The plan specified returning `list[SubTask]` directly, but instructor cannot parse raw lists — it needs a named model.
- **Fix:** Created `_SubTaskList(subtasks: list[SubTask])` as a private wrapper model. `decompose_hour()` extracts `result.subtasks` from the parsed model. Mock compatibility handled by `isinstance(result, list)` check.
- **Files modified:** `backend/agents/cognition/plan.py`
- **Commit:** `718838f`

## Known Stubs

None. All functionality is fully implemented and tested.

## Threat Flags

No new security surface beyond what was declared in the plan's threat model. The T-03-05 and T-03-06 mitigations are implemented:
- T-03-05: `DailySchedule` with `Field(ge=4, le=11)` on `wake_hour` and `Field(min_length=3)` on `activities`; instructor retries on validation failure via `complete_structured(max_retries=3)`
- T-03-06: `SubTask` with `Field(ge=0, lt=1440)` on `start_minute` and `Field(ge=5, le=60)` on `duration_minutes`; invalid LLM values rejected by Pydantic

## Self-Check: PASSED

| Item | Status |
|------|--------|
| backend/agents/cognition/__init__.py | FOUND |
| backend/agents/cognition/perceive.py | FOUND |
| backend/agents/cognition/plan.py | FOUND |
| backend/prompts/schedule_init.py | FOUND |
| backend/prompts/schedule_decompose.py | FOUND |
| tests/test_cognition.py | FOUND |
| 03-02-SUMMARY.md | FOUND |
| Commit effb964 (test RED) | FOUND |
| Commit 08f8749 (feat perceive) | FOUND |
| Commit 718838f (feat plan) | FOUND |
| 21 cognition tests pass | PASS |
| 123 total tests pass | PASS |
| perceive.py has no async | PASS |
| plan.py uses complete_structured | PASS |
| schedule_init.py contains daily_plan | PASS |
