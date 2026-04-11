---
phase: 09-llm-optimization
plan: 02
subsystem: backend-cognition
tags: [llm-optimization, cascade, gating, repetition-detection, tdd]
requirements: [LLM-01, LLM-03]
dependency_graph:
  requires: [09-01]
  provides: [2-level-cascade, per-sector-gating, arena-validation, repetition-detection]
  affects: [backend/simulation/engine.py, backend/agents/cognition/decide.py, backend/agents/cognition/converse.py]
tech_stack:
  added: [difflib.SequenceMatcher]
  patterns: [2-level-cascade, gating-returns-none, arena-validation-fallback, terminated_reason-field]
key_files:
  created:
    - backend/prompts/arena_decide.py
    - tests/test_decide_cascade.py
    - tests/test_converse_repetition.py
  modified:
    - backend/agents/cognition/decide.py
    - backend/agents/cognition/converse.py
    - backend/agents/agent.py
    - backend/schemas/agent.py
    - backend/schemas/__init__.py
    - tests/test_agent_class.py
decisions:
  - Per-sector gating checks all three conditions (last_sector + new_perceptions + schedule_changed) not just last_sector alone — Codex P1-2/P1-6 fix
  - Arena validation rejects unknown LLM-returned arena names with arenas[0] fallback — Codex P1-5 fix
  - _sector_has_arenas returns [] for single-arena sectors, skipping the arena LLM call entirely (D-09)
  - Repetition detection skips turn 0 to avoid premature termination of opening greetings
  - MAX_TURNS raised from 4 to 6 to allow natural conversation exchange before hard cap
metrics:
  duration: "~10 minutes (excluding 8-minute integration test run)"
  completed: "2026-04-11"
  tasks_completed: 2
  files_modified: 9
  commits: 3
---

# Phase 09 Plan 02: 2-Level Decision Cascade and Conversation Repetition Detection Summary

**One-liner:** 2-level LLM cascade (sector → arena) with per-sector gating returning None, arena name validation with arenas[0] fallback, and difflib-based conversation repetition detection terminating stagnant exchanges early.

## What Was Built

### Task 1: 2-Level Decision Cascade with Per-Sector Gating (commits 5728c78, d674ac3)

**decide.py** received three major additions:

1. `_sector_has_arenas(sector_name, spatial_tree) -> list[str]` — returns arena names for multi-arena sectors (>1 key), empty list for single-arena or missing sectors. Drives the cascade decision.

2. **Gating parameters** added to `decide_action()`:
   - `last_sector: str | None = None` — None on first tick, sector name on subsequent ticks
   - `new_perceptions: bool = True` — True if nearby agents/events/injected memories present
   - `schedule_changed: bool = False` — True if schedule block advanced since last tick
   - Returns `AgentAction | None` — None skips all LLM calls for the tick

3. **2-level cascade**: After sector selection LLM call, if `_sector_has_arenas()` returns a non-empty list, a second `arena_decide_prompt()` LLM call fires. The arena name is validated against the known list — unknown names fall back to `arenas[0]` with a WARNING log. Final destination format: `"sector:arena"` (e.g. `"cafe:seating"`).

**backend/prompts/arena_decide.py** — new prompt template for arena-level LLM call.

**backend/schemas/agent.py** — new `ArenaAction(BaseModel)` with `arena: str` and `reasoning: str` fields.

**backend/agents/agent.py** — `Agent.decide()` updated: return type is now `AgentAction | None`, `**kwargs` forwarded to `decide_action()` so callers can pass `last_sector`, `new_perceptions`, `schedule_changed`.

**tests/test_decide_cascade.py** — 11 tests covering `_sector_has_arenas` (3), gating logic (4), LLM call count (2), arena validation (2).

**tests/test_agent_class.py** — added `test_agent_decide_passes_through_none` (Test 12 / Codex P2-7).

### Task 2: Conversation Repetition Detection (commit 5726e84)

**converse.py** received:

1. `import difflib` at top.

2. `MAX_TURNS = 6` (raised from 4 per D-12 to allow more natural exchange).

3. `_is_repetition(text_a, text_b, threshold=0.6) -> bool` — uses `difflib.SequenceMatcher(None, text_a.lower(), text_b.lower()).ratio() > threshold`. Case-insensitive to avoid false negatives from capitalization.

4. **Repetition detection in turn loop** — checked after `turn >= 1` (skips opening exchange), comparing last utterance from each speaker. On repetition: logs `"conversation ended (repetition): {A} <-> {B} (ratio > 0.6)"` at INFO, sets `terminated_by_repetition = True`, breaks.

5. **`terminated_reason` field** added to return dict: `"repetition"` | `"agent_choice"` | `"max_turns"`.

**tests/test_converse_repetition.py** — 8 tests: 4 unit tests for `_is_repetition`, 1 for `MAX_TURNS`, 3 integration tests for `run_conversation` termination behavior.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Duplicate ArenaAction import in decide.py**
- **Found during:** Post-Task 1 verification
- **Issue:** `decide.py` had `ArenaAction` imported twice — once from `backend.schemas` and once from `backend.schemas.agent` with `# noqa: F811`. The second import was a leftover from initial draft.
- **Fix:** Removed the duplicate `from backend.schemas.agent import ArenaAction` line, keeping the single import via `backend.schemas`.
- **Files modified:** `backend/agents/cognition/decide.py`
- **Commit:** d674ac3

**2. [Rule 1 - Bug] Wrong field name in test helper `_make_schedule_entry`**
- **Found during:** Task 2 RED→GREEN transition
- **Issue:** Test helper used `duration=60` but `ScheduleEntry` schema uses `duration_minutes`. Pydantic raised `ValidationError: duration_minutes — Field required`.
- **Fix:** Changed to `duration_minutes=60` in the test fixture.
- **Files modified:** `tests/test_converse_repetition.py`
- **Commit:** included in 5726e84

## Known Stubs

None — all new functionality is fully wired. `decide_action()` returns `AgentAction | None` but the engine still calls `decide_action()` directly (not via `Agent.decide()`). The `None` return path is handled by tests but the engine's `_agent_step` does not yet pass `last_sector`/`new_perceptions`/`schedule_changed` — those wiring calls are scope for a follow-on plan (the engine currently calls `decide_action` directly, not through `Agent.decide()`).

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes at trust boundaries. The `ArenaAction` schema is internal to the LLM call cycle and validated against the known arenas list before use — threat T-09-04 mitigated as planned.

## Self-Check

Files created/modified exist on disk:
- `backend/prompts/arena_decide.py` — created
- `backend/agents/cognition/decide.py` — modified (contains `_sector_has_arenas`, `last_sector`, `schedule_changed`, `return None`, `ArenaAction`)
- `backend/agents/cognition/converse.py` — modified (contains `MAX_TURNS = 6`, `_is_repetition`, `terminated_reason`)
- `backend/schemas/agent.py` — modified (contains `class ArenaAction`)
- `backend/schemas/__init__.py` — modified (exports `ArenaAction`)
- `backend/agents/agent.py` — modified (return type `AgentAction | None`, `**kwargs` forwarded)
- `tests/test_decide_cascade.py` — created (11 tests)
- `tests/test_converse_repetition.py` — created (8 tests)
- `tests/test_agent_class.py` — modified (test_agent_decide_passes_through_none added)

Commits in this plan:
- 5728c78: feat(09-02): 2-level decision cascade with per-sector gating and arena validation
- 5726e84: feat(09-02): conversation repetition detection with difflib, MAX_TURNS=6
- d674ac3: fix(09-02): remove duplicate ArenaAction import in decide.py

## Self-Check: PASSED
