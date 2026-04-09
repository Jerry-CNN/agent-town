---
phase: "02-world-navigation"
plan: "02"
subsystem: "agent-config"
tags: ["agents", "pydantic", "data-models", "json-config", "tdd"]
dependency_graph:
  requires: []
  provides: ["AgentConfig schema", "AgentScratch schema", "AgentSpatial schema", "load_all_agents()", "8 agent JSON configs"]
  affects: ["Phase 3 cognition (consumes AgentConfig)", "Phase 4 simulation (spawn positions)", "Phase 5 frontend (agent labels)"]
tech_stack:
  added: []
  patterns: ["Pydantic v2 model_validate()", "JSON config files per agent", "Path.glob for config discovery", "TDD (RED/GREEN)"]
key_files:
  created:
    - backend/agents/__init__.py
    - backend/agents/loader.py
    - backend/data/agents/alice.json
    - backend/data/agents/bob.json
    - backend/data/agents/carla.json
    - backend/data/agents/david.json
    - backend/data/agents/emma.json
    - backend/data/agents/frank.json
    - backend/data/agents/grace.json
    - backend/data/agents/henry.json
    - tests/test_agent_loader.py
  modified:
    - backend/schemas.py
decisions:
  - "Three-level spatial hierarchy (world:location:zone) used per research recommendation -- simpler than reference four-level but sufficient for Phase 3 spatial memory"
  - "Agents sorted alphabetically by filename for deterministic load order"
  - "AGENTS_DIR uses Path(__file__) for relocatability -- avoids CWD coupling"
  - "Spawn coords: 6 agents at workplace, 2 at home (Alice/Bob/David/Emma/Frank/Grace at work; Carla/Henry at home)"
metrics:
  duration: "~15 minutes"
  completed_date: "2026-04-09"
  tasks_completed: 1
  tasks_total: 1
  files_created: 11
  files_modified: 1
---

# Phase 02 Plan 02: Agent Configs and Loader Summary

## One-liner

Pydantic v2 agent schema (AgentScratch/AgentSpatial/AgentConfig) with 8 pre-defined agent JSON configs and a glob-based loader — barista, stockbroker, florist, office worker, baker, park keeper, wedding planner, and retiree each with distinct personality, spatial knowledge tree, and mixed spawn coordinates.

## What Was Built

### Pydantic v2 Models (backend/schemas.py extension)

Three new models appended to the existing schemas without modifying any existing models:

- `AgentScratch` — personality and background: age, innate traits, learned background, lifestyle, daily_plan template
- `AgentSpatial` — spatial knowledge: hierarchical address dict and location tree dict
- `AgentConfig` — complete agent config: name, coord (tuple[int,int]), currently, scratch, spatial

### Agent Loader (backend/agents/loader.py)

`load_all_agents()` uses `sorted(AGENTS_DIR.glob("*.json"))` for deterministic ordering. Each file is validated through `AgentConfig.model_validate(raw)`. Raises `FileNotFoundError` if the agents directory is missing, `ValidationError` if any file is malformed.

### 8 Agent JSON Configs

| Agent | Occupation | Spawn | Location |
|-------|-----------|-------|----------|
| Alice Chen, 28 | Barista at cafe | (12, 40) | Cafe |
| Bob Martinez, 45 | Stockbroker | (82, 42) | Stock exchange |
| Carla Rossi, 34 | Florist | (65, 38) | Home |
| David Park, 31 | Office accountant | (58, 42) | Office |
| Emma Johansson, 52 | Baker | (35, 45) | Shop |
| Frank Okafor, 62 | Park keeper | (15, 12) | Park |
| Grace Nakamura, 38 | Wedding planner | (20, 68) | Wedding hall |
| Henry Walsh, 71 | Retired teacher | (82, 12) | Home |

Mix: 6 agents spawn at workplace, 2 at home (D-11 satisfied).

Each agent has a three-level spatial tree (`agent-town > location > zone`) covering home and key visited locations.

### Tests (tests/test_agent_loader.py)

15 tests covering: minimum count, distinct names, innate traits, daily_plan, coord type/validity, mixed spawn locations, spatial living_area key, spatial tree non-empty, Pydantic ValidationError on incomplete data, occupation keyword diversity, age, learned background, lifestyle, currently, and world key in spatial tree.

All 15 tests pass. Full worktree suite: 30 passed.

## Commits

| Hash | Type | Description |
|------|------|-------------|
| f5d7f23 | feat | Agent Pydantic schemas, 8 JSON configs, and loader module |

## Deviations from Plan

None — plan executed exactly as written.

The spatial hierarchy uses three levels (world:location:zone) as recommended by the research rather than the reference implementation's four levels — this was explicitly called out as Claude's discretion in CONTEXT.md and confirmed by RESEARCH.md recommendation.

## Known Stubs

None. All 8 agent configs have complete non-stub data for all required fields.

## Threat Flags

No new security-relevant surface introduced. All data is fictional agent personalities loaded from committed JSON files (T-02-04, T-02-05, T-02-06 accept dispositions apply as planned).

## Self-Check: PASSED

Files verified to exist:
- backend/agents/__init__.py: FOUND
- backend/agents/loader.py: FOUND
- backend/data/agents/alice.json: FOUND (+ 7 other agents)
- tests/test_agent_loader.py: FOUND
- backend/schemas.py (extended): FOUND

Commit f5d7f23 exists in git log.
All 15 agent loader tests pass.
