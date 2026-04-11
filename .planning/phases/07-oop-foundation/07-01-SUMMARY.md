---
phase: 07-oop-foundation
plan: "01"
subsystem: backend-schemas
tags: [schema-split, event-model, building-model, pydantic, tdd]
dependency_graph:
  requires: []
  provides:
    - backend.schemas package (4 domain files + backward-compat __init__)
    - Event model with lifecycle tracking (EVTS-01, EVTS-02, EVTS-03)
    - Building dataclass + load_buildings() (BLD-01)
    - buildings.json data for all 16 town sectors
  affects:
    - backend/agents/loader.py (imports AgentConfig)
    - backend/simulation/engine.py (imports AgentConfig, ScheduleEntry)
    - backend/agents/cognition/converse.py (imports 5 cognition models)
    - backend/main.py (imports WSMessage)
    - backend/agents/cognition/perceive.py (imports PerceptionResult)
    - backend/agents/cognition/decide.py (imports AgentAction, AgentScratch, AgentSpatial, PerceptionResult)
    - backend/gateway.py (imports AgentAction, ProviderConfig)
    - backend/agents/cognition/plan.py (imports DailySchedule, ScheduleEntry, SubTask, AgentScratch)
    - backend/routers/ws.py (imports WSMessage)
    - backend/agents/memory/retrieval.py (imports Memory)
    - backend/agents/memory/store.py (imports ImportanceScore)
    - backend/routers/llm.py (imports ProviderConfig, LLMTestResponse)
tech_stack:
  added: []
  patterns:
    - Pydantic v2 domain-grouped package split
    - Backward-compatible __all__ re-exports in __init__.py
    - Dataclass + JSON loader pattern for static config data
    - TDD red-green cycle per task
key_files:
  created:
    - backend/schemas/__init__.py
    - backend/schemas/agent.py
    - backend/schemas/cognition.py
    - backend/schemas/events.py
    - backend/schemas/ws.py
    - backend/data/map/buildings.json
    - tests/test_events.py
    - tests/test_building.py
  modified:
    - backend/simulation/world.py
  deleted:
    - backend/schemas.py
decisions:
  - "Event.tick() transitions created->active on first call, then active->spreading (whisper only), then expired when tick count reached"
  - "buildings.json covers all 16 sectors from town.json (6 public + 10 homes) for complete cross-validation"
  - "No intra-package imports in domain files — all 4 domain files import only from pydantic/typing/stdlib"
metrics:
  duration: "~25 minutes"
  completed: "2026-04-11T11:05:28Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 8
  files_modified: 1
  files_deleted: 1
  tests_added: 27
  tests_passed: 144
---

# Phase 7 Plan 1: Schema Split + Event/Building Models Summary

**One-liner:** Monolithic `schemas.py` split into 4 domain-grouped Pydantic files with a backward-compatible `__init__.py`, plus a new `Event` model with tick-based lifecycle state machine and a `Building` dataclass loaded from `buildings.json`.

## What Was Built

### Task 1: Schema package split + Event model

Split `backend/schemas.py` (182 lines, 14 models) into a domain-grouped `backend/schemas/` package:

- `backend/schemas/agent.py` — AgentAction, AgentScratch, AgentSpatial, AgentConfig
- `backend/schemas/cognition.py` — SubTask, ScheduleEntry, DailySchedule, ConversationDecision, ConversationTurn, ScheduleRevision, PerceptionResult
- `backend/schemas/events.py` — ImportanceScore, Memory, **Event** (new), EVENT_EXPIRY_TICKS
- `backend/schemas/ws.py` — WSMessage, ProviderConfig, LLMTestResponse
- `backend/schemas/__init__.py` — backward-compatible re-exports of all 18 symbols with `__all__`

The new `Event` model implements:
- **EVTS-01** lifecycle state machine: `created -> active -> [spreading] -> expired`
  - `tick(current_tick)` advances state; broadcast skips `spreading`
- **EVTS-02** propagation tracking: `heard_by: list[str]` accumulates for whisper; broadcast stays empty
- **EVTS-03** tick-based expiry: `is_expired(current_tick)` returns `True` when `current_tick - created_tick >= expires_after_ticks`
- **T-07-01** input validation: `text: str = Field(max_length=500)` prevents oversized injected events

All 13 existing `from backend.schemas import X` call sites continue to work unchanged.

### Task 2: Building class + buildings.json data file

Added to `backend/simulation/world.py` (above `Maze` class):

- `Building` dataclass with `name, sector, opens, closes, purpose` fields (BLD-01)
- `load_buildings() -> dict[str, Building]` — reads `buildings.json`, returns sector-indexed dict, returns `{}` gracefully if file missing
- `BUILDINGS_PATH` constant resolving to `backend/data/map/buildings.json`

Created `backend/data/map/buildings.json` with metadata for all 16 sectors from `town.json`:
- 6 public buildings: cafe (7-22, food), stock-exchange (9-17, finance), wedding-hall (10-23, social), park (0-24, leisure), office (8-18, work), shop (8-20, retail)
- 10 residential homes (all 0-24, residential)

All sector keys in `buildings.json` cross-validate against `maze.address_tiles` in the existing tests.

## Test Results

| Test Suite | Tests | Result |
|------------|-------|--------|
| tests/test_events.py | 17 | PASS |
| tests/test_building.py | 10 | PASS |
| tests/test_cognition.py | 27 | PASS (regression) |
| tests/test_memory.py | 22 | PASS (regression) |
| tests/test_agent_loader.py | 27 | PASS (regression) |
| tests/test_world.py | 41 | PASS (regression) |
| **Total** | **144** | **PASS** |

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 28101d2 | test | Failing tests for Event model and schema backward compat (RED) |
| 2537ec6 | feat | Split schemas.py into domain package with Event model (GREEN) |
| 2c5a306 | test | Failing tests for Building class and load_buildings() (RED) |
| 851dbd9 | feat | Building dataclass + buildings.json data (GREEN) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Event.tick() missing created -> active transition**
- **Found during:** Task 1 GREEN phase (test_broadcast_lifecycle failed)
- **Issue:** The plan's `tick()` spec only showed `active -> spreading` and `expired` transitions; did not explicitly show `created -> active` as a state machine step
- **Fix:** Added `elif self.status == "created": self.status = "active"` branch before the whisper spreading check
- **Files modified:** `backend/schemas/events.py`
- **Commit:** 2537ec6 (included in the GREEN commit)

## Known Stubs

None. All data is wired: `load_buildings()` reads `buildings.json`, `Event` is a fully implemented model, `__init__.py` re-exports all symbols.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries beyond those modeled in the plan's threat register.

- T-07-01 (mitigate): `Event.text = Field(max_length=500)` — implemented
- T-07-02 (accept): `buildings.json` — static file, no web endpoint writes to it
- T-07-03 (accept): `schemas/__init__.py` re-exports — no new visibility boundary

## Self-Check: PASSED

- All 8 created files: FOUND
- schemas.py deleted: CONFIRMED
- All 4 commits: FOUND (28101d2, 2537ec6, 2c5a306, 851dbd9)
- 144 tests pass
