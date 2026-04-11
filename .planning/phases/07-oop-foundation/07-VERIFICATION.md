---
phase: 07-oop-foundation
verified: 2026-04-10T12:45:00Z
status: gaps_found
score: 4/6 must-haves verified
overrides_applied: 0
gaps:
  - truth: "SimulationEngine holds a single dict[str, Agent] — no separate configs or states dicts remain"
    status: failed
    reason: "engine.py still contains the AgentState dataclass and _agent_states dict. The Plan 02 commits (c786ba8, 6023938, 4338608) exist as git objects but were made in an executor worktree that was never merged into main (unlike Plan 01's worktree which was merged via 8352e66). The HEAD commit tree does not include backend/agents/agent.py, the _agents rename, or the AgentState removal."
    artifacts:
      - path: "backend/simulation/engine.py"
        issue: "Still contains 'class AgentState:' at line 46 and 'self._agent_states: dict[str, AgentState] = {}' at line 116. import Agent and self._agents dict are absent."
      - path: "backend/agents/agent.py"
        issue: "File does not exist in the working tree — the commit 6023938 that created it was never merged to main."
    missing:
      - "Merge the Plan 02 executor worktree commits into main (c786ba8 -> 6023938 -> 4338608)"
      - "Alternatively: recreate backend/agents/agent.py from commit 6023938, update backend/simulation/engine.py from commit 4338608, update tests/test_simulation.py and tests/test_event_injection.py from commit 4338608"

  - truth: "Calling agent.perceive(), agent.decide(), and agent.converse() delegates correctly to existing function implementations"
    status: failed
    reason: "backend/agents/agent.py does not exist in the working tree. The Agent class with perceive(), decide(), converse() wrappers is only in an unmerged git commit (6023938). No callable agent.perceive() / agent.decide() / agent.converse() exist at HEAD."
    artifacts:
      - path: "backend/agents/agent.py"
        issue: "MISSING — file not in working tree, only in unmerged commit 6023938"
    missing:
      - "Same fix as truth 1 — merge Plan 02 worktree commits"

  - truth: "WebSocket snapshot and agent_update payloads are byte-identical before and after the refactor — a contract test compares serialized output"
    status: failed
    reason: "tests/test_ws_contract.py does not exist in the working tree. The file was created in commit 4338608 which was never merged to main. get_snapshot() and _emit_agent_update() in engine.py still reference _agent_states (old pattern) rather than _agents (new Agent dict), so the contract test cannot exercise the refactored code path even if the file were restored."
    artifacts:
      - path: "tests/test_ws_contract.py"
        issue: "MISSING — file not in working tree, only in unmerged commit 4338608"
      - path: "tests/test_agent_class.py"
        issue: "MISSING — file not in working tree, only in unmerged commit c786ba8"
    missing:
      - "Merge Plan 02 commits to get test_ws_contract.py and test_agent_class.py"
      - "Once agent.py exists and engine.py uses _agents, contract test can verify structural identity of snapshot and agent_update payloads"
---

# Phase 7: OOP Foundation Verification Report

**Phase Goal:** The backend has an Agent class (unifying config + state + cognition), a Building class, and an Event class; SimulationEngine operates on Agent objects instead of separate dicts; schemas.py is split into domain-grouped files — with no behavior change, all existing tests passing, and WebSocket payloads unchanged.
**Verified:** 2026-04-10T12:45:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Root Cause Summary

Phase 7 was executed in two plans using separate git worktrees. Plan 01's worktree was merged into main (commit `8352e66`), delivering the schema split, Event model, and Building class. Plan 02's worktree was **never merged** — its commits (`c786ba8`, `6023938`, `4338608`) exist as unreachable git objects but are absent from the working tree and any branch. The 07-02-SUMMARY.md was committed to main but the code changes it documents were not.

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC-1 | SimulationEngine holds a single `dict[str, Agent]` — no separate configs or states dicts remain | FAILED | `engine.py` line 46: `class AgentState:` still present. Line 116: `self._agent_states: dict[str, AgentState] = {}`. `backend/agents/agent.py` does not exist in working tree. |
| SC-2 | Calling `agent.perceive()`, `agent.decide()`, and `agent.converse()` delegates correctly | FAILED | `backend/agents/agent.py` is missing from the working tree. No callable Agent class exists at HEAD. |
| SC-3 | Each Building object carries name, operating hours, and purpose tag; town loads without KeyError | VERIFIED | `Building` dataclass in `world.py` (lines 108-126) has `name, sector, opens, closes, purpose`. `load_buildings()` returns 16 sector-indexed buildings. All building tests pass (10/10). |
| SC-4 | Each injected/perceived event has a `status` field from: created, active, spreading, expired | VERIFIED | `Event` class in `backend/schemas/events.py` (line 47): `status: Literal["created", "active", "spreading", "expired"] = "created"`. `tick()` transitions verified by spot-check and 17/17 event tests. |
| SC-5 | Schemas previously in `schemas.py` are importable from new domain-grouped paths with no import errors | VERIFIED | `backend/schemas/` package exists with 4 domain files + `__init__.py`. All 13 existing `from backend.schemas import X` call sites verified working. Domain-path imports (`from backend.schemas.agent import AgentConfig`) also work. All regression tests pass (117/117 for cognition/memory/loader/world). |
| SC-6 | WebSocket snapshot and agent_update payloads are byte-identical — a contract test compares serialized output | FAILED | `tests/test_ws_contract.py` does not exist. `get_snapshot()` still uses `_agent_states` (line 515). No contract test in any test file. |

**Score: 3/6 truths verified** (SC-3, SC-4, SC-5)

Note: SC-1 and SC-2 fail from the same root cause (Plan 02 worktree not merged). SC-6 compounds SC-1 failure.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/schemas/__init__.py` | Backward-compatible re-exports of all models | VERIFIED | 18 symbols in `__all__`, all 4 domain files re-exported. |
| `backend/schemas/agent.py` | AgentConfig, AgentScratch, AgentSpatial, AgentAction | VERIFIED | All 4 classes present, no intra-package imports. |
| `backend/schemas/cognition.py` | DailySchedule, ScheduleEntry, SubTask, ScheduleRevision, PerceptionResult, ConversationDecision, ConversationTurn | VERIFIED | All 7 classes present. |
| `backend/schemas/events.py` | Event, Memory, ImportanceScore, EVENT_EXPIRY_TICKS | VERIFIED | All present. Event has lifecycle state machine, `is_expired()`, `tick()`, max_length=500. |
| `backend/schemas/ws.py` | WSMessage, ProviderConfig, LLMTestResponse | VERIFIED | All 3 classes present. |
| `backend/simulation/world.py` | Building dataclass and load_buildings() | VERIFIED | `Building` at line 108, `load_buildings()` at line 129, `BUILDINGS_PATH` at line 22. |
| `backend/data/map/buildings.json` | Building metadata for all town sectors | VERIFIED | 16 entries, each with `name, sector, opens, closes, purpose`. |
| `tests/test_building.py` | Building class and loading tests | VERIFIED | 10 test functions, all pass. |
| `tests/test_events.py` | Event lifecycle, propagation, and expiry tests | VERIFIED | 17 test functions, all pass. |
| `backend/agents/agent.py` | Unified Agent class (AgentConfig + AgentState) | MISSING | Not in working tree. Only in unmerged commit `6023938`. |
| `backend/simulation/engine.py` | SimulationEngine using Agent objects | FAILED | Still contains `AgentState` (line 46) and `_agent_states` (line 116). No `from backend.agents.agent import Agent`. |
| `tests/test_agent_class.py` | Agent class unit tests | MISSING | Not in working tree. Only in unmerged commit `c786ba8`. |
| `tests/test_ws_contract.py` | WebSocket payload contract test | MISSING | Not in working tree. Only in unmerged commit `4338608`. |

### Key Link Verification (07-01: Plan 1)

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/schemas/__init__.py` | `backend/schemas/agent.py`, `cognition.py`, `events.py`, `ws.py` | explicit re-exports | VERIFIED | Lines 10-35: all 4 domain files re-exported via `from backend.schemas.X import ...` |
| `backend/simulation/world.py` | `backend/data/map/buildings.json` | `load_buildings()` reads JSON | VERIFIED | Line 139: `json.loads(BUILDINGS_PATH.read_text(...))` |

### Key Link Verification (07-02: Plan 2)

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/simulation/engine.py` | `backend/agents/agent.py` | `import Agent; self._agents dict` | NOT_WIRED | `agent.py` does not exist; engine has no `from backend.agents.agent import Agent` import. |
| `backend/agents/agent.py` | `backend/agents/cognition/perceive.py` | `Agent.perceive()` delegates | NOT_WIRED | `agent.py` does not exist. |
| `backend/agents/agent.py` | `backend/agents/cognition/decide.py` | `Agent.decide()` delegates | NOT_WIRED | `agent.py` does not exist. |
| `backend/agents/agent.py` | `backend/agents/cognition/converse.py` | `Agent.converse()` delegates | NOT_WIRED | `agent.py` does not exist. |

### Data-Flow Trace (Level 4)

Not applicable for Phase 7 artifacts. Schema models and dataclasses are data definitions, not dynamic data renderers. The `load_buildings()` function reads from a static JSON file (not a DB query) and is correct for this use case.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Event lifecycle transitions (broadcast) | `Event(text='t', mode='broadcast').tick(0)` → status | `active` | PASS |
| Event lifecycle transitions (whisper) | Whisper event tick sequence: `created → active → spreading` | Correct | PASS |
| Event expiry | `Event(..., expires_after_ticks=1).tick(1)` → `expired` | Correct | PASS |
| Building load | `load_buildings()` returns 16 entries with correct fields | 16 buildings, all have name/sector/opens/closes/purpose | PASS |
| Backward-compat imports | All 13 call-site patterns tested with `python -c "from backend.schemas import ..."` | All succeed | PASS |
| Agent class exists | `from backend.agents.agent import Agent` | ImportError — file does not exist | FAIL |
| SimulationEngine uses Agent | `grep _agents engine.py` | Only `_agent_states` found | FAIL |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| ARCH-01 | 07-02-PLAN.md | Agent class unifies AgentConfig + AgentState into a single object with identity, runtime state, and cognition methods | BLOCKED | `backend/agents/agent.py` is missing from working tree. Plan 02 commits not merged. |
| ARCH-02 | 07-02-PLAN.md | Agent class has cognition methods (perceive, decide, converse, reflect) that delegate to existing functions | BLOCKED | Same root cause — `agent.py` not in working tree. |
| ARCH-03 | 07-02-PLAN.md | SimulationEngine uses Agent objects instead of separate config/state dicts | BLOCKED | `engine.py` still uses `AgentState` and `_agent_states`. Plan 02 engine changes not merged. |
| BLD-01 | 07-01-PLAN.md | Building class with properties (name, operating hours, purpose tag) | SATISFIED | `Building` dataclass in `world.py` lines 108-126. `load_buildings()` returns sector-indexed dict. 10/10 building tests pass. |
| EVTS-01 | 07-01-PLAN.md | Event class tracks lifecycle (created, active, spreading, expired) | SATISFIED | `Event.status: Literal["created", "active", "spreading", "expired"]`. `tick()` advances state. 17/17 tests pass. |
| EVTS-02 | 07-01-PLAN.md | Events track propagation — which agents heard the event | SATISFIED | `Event.heard_by: list[str]`. Whisper events accumulate agent names. Broadcast stays empty. |
| EVTS-03 | 07-01-PLAN.md | Events expire after a configurable duration | SATISFIED | `is_expired(current_tick)`, `expires_after_ticks` field, `EVENT_EXPIRY_TICKS = 10` constant. |

All 7 Phase 7 requirements appear in plan frontmatter (no orphaned requirements). ARCH-01, ARCH-02, ARCH-03 are blocked by the unmerged Plan 02 worktree.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `backend/simulation/engine.py` | 46 | `class AgentState:` — should have been removed by Plan 02 | Blocker | Engine still manages dual-dict state (config + AgentState), blocking ARCH-01 and ARCH-03 |
| `tests/test_simulation.py` | 86, 121, 184, 217, 291, ... | `from backend.simulation.engine import AgentState` — 21 occurrences | Blocker | Tests still construct `AgentState` objects — the migration to `Agent` was never applied |
| `tests/test_event_injection.py` | 133, 144, 189, 224, ... | `AgentState` — 12 occurrences | Blocker | Same as above — no migration applied |

The `test_movement_one_tile_per_tick` failure (1 of 197 tests) is pre-existing per both the 07-02-SUMMARY.md and the 07-01-SUMMARY.md regression table. It is not introduced by Phase 7.

### Human Verification Required

None. All required checks are programmatic.

### Gaps Summary

**Plan 01 (Schema split + Event + Building): COMPLETE.** All 4 domain schema files exist, old `schemas.py` deleted, `__init__.py` has backward-compatible re-exports with `__all__` (18 symbols), Event model fully implements lifecycle/propagation/expiry, Building dataclass loaded from `buildings.json` (16 sectors), all tests pass.

**Plan 02 (Agent class + Engine migration): NOT MERGED.** The executor created three commits (`c786ba8` agent_class TDD RED, `6023938` Agent class GREEN, `4338608` engine migration + WS contract test) in a separate worktree that was never merged into main, unlike Plan 01 which was merged via `8352e66`. The SUMMARY documents these commits and claims a self-check PASSED — but the self-check ran inside the worktree, not on the main branch. The working tree on main is missing:
- `backend/agents/agent.py`
- Updated `backend/simulation/engine.py` (AgentState removed, _agents dict)
- Updated `tests/test_simulation.py` (21 AgentState references)
- Updated `tests/test_event_injection.py` (12 AgentState references)
- `tests/test_agent_class.py`
- `tests/test_ws_contract.py`

**Fix:** Cherry-pick or recreate the three Plan 02 commits onto main. The commits exist in git history as reachable objects and contain the correct implementation — they simply were not included in the merge that brought Plan 01 artifacts into main.

---

_Verified: 2026-04-10T12:45:00Z_
_Verifier: Claude (gsd-verifier)_
