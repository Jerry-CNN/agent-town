---
phase: 08-visual-building-behavior
plan: 02
subsystem: backend
tags: [building-hours, sim-time, agent-ejection, operating-hours, bld-03]
dependency_graph:
  requires: []
  provides: [building-hours-enforcement, sim-time-clock, open-locations-filter]
  affects: [backend/simulation/engine.py, backend/simulation/world.py, backend/agents/cognition/decide.py]
tech_stack:
  added: []
  patterns: [sim-time-tracking, building-hours-filter, ejection-guard-pitfall5]
key_files:
  created:
    - tests/test_building_hours.py
  modified:
    - backend/simulation/world.py
    - backend/agents/cognition/decide.py
    - backend/simulation/engine.py
decisions:
  - "Building.is_open() uses closes==24 as the always-open sentinel (parks, homes)"
  - "open_locations param added as optional (None = full spatial tree fallback) for backward compatibility"
  - "_last_ejection_hour=-1 at init so first tick always triggers the ejection check at hour 7"
  - "Ejection catches IndexError from tile_at to safely handle agents at boundary coords"
metrics:
  duration: ~25 minutes
  completed: 2026-04-11T18:53:39Z
  tasks: 2
  files: 4
---

# Phase 8 Plan 02: Building Operating Hours Enforcement Summary

Simulation time clock + building hours filter + agent ejection. Agents no longer navigate to closed buildings and are immediately interrupted when a building closes while they are inside.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for building hours | bb04cc0 | tests/test_building_hours.py |
| 1 (GREEN) | Building.is_open(), sim time, open-locations filter | 9c3786f | world.py, decide.py, engine.py, tests/test_building_hours.py |
| 2 | Agent ejection from closed buildings (D-09) | 2bba709 | backend/simulation/engine.py |

## What Was Built

### Building.is_open() — backend/simulation/world.py

Method added to the `Building` dataclass handling three cases:
- `closes=24`: always returns True (parks, homes — never close)
- `opens < closes`: standard range, e.g. `9 <= hour < 17`
- `opens >= closes`: midnight wrap-around, e.g. `hour >= 22 or hour < 4`

### Sim Time Clock — backend/simulation/engine.py

`SimulationEngine.__init__` now initializes:
- `_sim_hour = 7` — simulation starts at 7am
- `_sim_minute = 0` — within-hour minute counter
- `_last_ejection_hour = -1` — Pitfall 5 guard
- `_buildings = load_buildings()` — loaded once, never per tick

`_tick_loop` advances `_sim_minute` by 10 after each tick batch; rolls to next hour when `_sim_minute >= 60`.

### Open-Locations Filter — backend/simulation/engine.py + decide.py

`_agent_step` extracts `all_locations` from the agent's spatial tree, filters through `_is_location_open()`, and passes `open_locs` to `decide_action` as the `open_locations` parameter. The LLM prompt now only lists currently-open destinations.

`decide_action` gained an `open_locations: list[str] | None = None` parameter — when provided, used directly; when None, falls back to `_extract_known_locations(agent_spatial.tree)` (backward-compatible).

### Agent Ejection — backend/simulation/engine.py

`_eject_agents_from_closed_buildings()` iterates all agents and checks:
1. `self.maze` is set (guard against test environments with no maze)
2. `tile.address` has length >= 2 (skips road tiles with no sector component)
3. The sector's Building (if any) returns False from `is_open(self._sim_hour)`

On match: `agent.path = []`, `agent.current_activity = "leaving (building closed)"`, `_emit_agent_update` broadcast.

Wired into `_tick_loop` with Pitfall 5 guard:
```python
if self._sim_hour != self._last_ejection_hour:
    self._last_ejection_hour = self._sim_hour
    await self._eject_agents_from_closed_buildings()
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] AgentScratch constructor calls used non-existent fields**
- **Found during:** Task 1 GREEN — `TestDecideActionOpenLocations` tests failed with ValidationError
- **Issue:** Test used `name`, `currently`, `living_area` fields that belong to `AgentConfig`, not `AgentScratch`. `AgentScratch` only has `age`, `innate`, `learned`, `lifestyle`, `daily_plan`.
- **Fix:** Updated test constructors to use actual schema fields. `AgentSpatial` also doesn't have a `name` field — removed.
- **Files modified:** tests/test_building_hours.py
- **Commit:** 9c3786f (included in Task 1 GREEN commit)

### Pre-existing Failures (Out of Scope)

The following 6 tests were already failing before this plan and are unrelated to building hours:
- `test_health.py::test_health_returns_200_with_correct_keys`
- `test_health.py::test_health_returns_200_when_ollama_unavailable`
- `test_integration.py::test_health_check_returns_200`
- `test_integration.py::test_config_ollama_returns_configured`
- `test_integration.py::test_config_openrouter_returns_configured`
- `test_simulation.py::test_movement_one_tile_per_tick`

These are logged to deferred-items and not touched by this plan.

## Test Results

```
35 passed in test_building_hours.py
247 passed total (including all pre-existing passing tests)
6 failed (same pre-existing failures, zero regressions)
```

## Known Stubs

None. All building hours logic is fully wired: `is_open()` reads real `opens`/`closes` fields, `load_buildings()` reads actual `buildings.json`, and `_is_location_open()` calls `is_open()` with the live `_sim_hour`.

## Threat Flags

No new threat surface introduced. Mitigations from plan's threat register applied:
- T-08-03 (DoS via ejection every tick): mitigated by `_last_ejection_hour` Pitfall 5 guard
- T-08-04 (Tampering open_locations): `open_locations` computed server-side, users cannot influence
- T-08-05 (Info disclosure sim_hour in logs): accepted — no PII, info-level only

## Self-Check: PASSED

All created/modified files exist:
- FOUND: backend/simulation/world.py
- FOUND: backend/simulation/engine.py
- FOUND: backend/agents/cognition/decide.py
- FOUND: tests/test_building_hours.py
- FOUND: .planning/phases/08-visual-building-behavior/08-02-SUMMARY.md

All commits exist:
- bb04cc0: test(08-02): TDD RED — failing tests
- 9c3786f: feat(08-02): Building.is_open(), sim time, open-locations filter
- 2bba709: feat(08-02): agent ejection from closed buildings
