---
phase: 11-town-map-design-backend-sync
plan: "01"
subsystem: scripts
tags: [sync, tiled, map, tooling, tests]
dependency_graph:
  requires: []
  provides:
    - scripts/sync_map.py (TMJ -> town.json/buildings.json/spawn_points.json converter)
    - tests/test_sync_map.py (15 unit tests)
    - docs/tiled-authoring-guide.md (user map authoring guide)
  affects:
    - backend/data/map/town.json (written by sync_map.py main())
    - backend/data/map/buildings.json (written by sync_map.py main())
    - backend/data/map/spawn_points.json (written by sync_map.py main())
    - frontend/src/data/town.json (written by sync_map.py main())
    - backend/data/agents/*.json (coord field updated on spawn point match)
tech_stack:
  added: []
  patterns:
    - scripts/ utility module pattern (following copy_assets.py)
    - TDD: RED (failing import) -> GREEN (all 15 pass)
    - Sparse tile dict keyed by (x,y) tuple, sorted for deterministic JSON output
    - Collision-first processing to prevent address overwriting (Pitfall 8)
key_files:
  created:
    - scripts/sync_map.py
    - scripts/__init__.py
    - tests/test_sync_map.py
    - docs/tiled-authoring-guide.md
  modified:
    - tests/conftest.py (added minimal_tmj fixture)
decisions:
  - "Collision processed first: tiles marked collision=True cannot be overwritten by sector/arena addresses"
  - "Size field is [height, width] matching Maze.__init__ expectation (Pitfall 3)"
  - "int() before // on all Tiled pixel coords to handle float exports (Pitfall 2)"
  - "scripts/__init__.py added so tests can import via 'from scripts.sync_map import'"
  - "14 sectors in authoring guide (6 commercial + 8 homes); home-isabel and home-james excluded (no agent JSON files)"
metrics:
  duration: "~25 minutes"
  completed: "2026-04-12T19:24:42Z"
  tasks_completed: 2
  files_created: 4
  files_modified: 1
  tests_added: 15
  tests_passing: 15
---

# Phase 11 Plan 01: Sync Map Script and Authoring Guide Summary

**One-liner:** TMJ-to-JSON sync script with collision-first processing and 15 unit tests, plus a 357-line Tiled authoring guide covering all 14 sectors, 30+ arenas, and 8 spawn points.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create test_sync_map.py with minimal TMJ fixture and sync_map.py | 5f90b72 | scripts/sync_map.py, scripts/__init__.py, tests/test_sync_map.py, tests/conftest.py |
| 2 | Write Tiled authoring guide for the user | 320ac09 | docs/tiled-authoring-guide.md |

## What Was Built

### scripts/sync_map.py

Converts a Tiled TMJ export into three backend JSON files and one frontend JSON file:

- `extract_map(tmj)`: Produces town.json. Processing order: (1) collision rectangles marked as `{collision: True}`, (2) sector addresses assigned to non-collision tiles, (3) arena addresses assigned (sector:arena colon format validated). Size field is `[height, width]` matching `Maze.__init__`. World name hardcoded to `"agent-town"`.
- `extract_buildings(sector_objects)`: Produces buildings.json from Tiled custom properties (`display_name`, `opens`, `closes`, `purpose`). Defaults: opens=0, closes=24, purpose="general".
- `extract_spawn_points(spawn_objects)`: Converts pixel coordinates to tile coordinates (divide by TILE_SIZE=32). Handles float Tiled exports via `int()` before `//`.
- `main()`: CLI entry point. Reads TMJ, calls all extract functions, writes four JSON files, updates agent coord fields. Supports `--dry-run` for validation-only mode.

Security mitigations implemented per threat model:
- **T-11-01**: `json.load()` wrapped in try/except with clear error message
- **T-11-02**: Metadata layer type validated as "objectgroup"; ValueError raised if wrong type

### tests/test_sync_map.py (15 tests)

| Test | What It Validates |
|------|------------------|
| test_extract_map_size_is_height_width | size=[height, width] ordering |
| test_extract_map_world_name | world="agent-town" |
| test_extract_map_tile_address_keys | tile_address_keys=['world','sector','arena'] |
| test_extract_map_collision_tiles_marked | Top border row y=0 all marked collision=True |
| test_extract_map_sector_address_assigned | Non-collision tile inside sector has address=[sector] |
| test_extract_map_arena_address_assigned | Tile inside arena has address=[sector, arena] |
| test_extract_map_collision_not_overwritten_by_arena | Collision tiles retain collision, no address |
| test_extract_buildings_extracts_properties | All custom properties extracted correctly |
| test_extract_buildings_defaults_when_properties_missing | opens=0, closes=24, purpose="general" defaults |
| test_extract_spawn_points_pixel_to_tile | pixel(96,96) -> tile(3,3) |
| test_extract_spawn_points_float_coords | float pixel coords converted correctly |
| test_extract_map_raises_on_missing_required_layer | ValueError with layer name on missing layer |
| test_extract_map_raises_on_wrong_layer_type | ValueError with "objectgroup" on wrong type |
| test_extract_map_raises_on_arena_name_without_colon | ValueError with "colon" on missing separator |
| test_extract_map_float_coords_handled | Float coords don't crash; collision tiles correct |

### tests/conftest.py — minimal_tmj fixture

A 10x10 TMJ dict with all 14 layers (10 visual tilelayers + 4 objectgroup metadata layers):
- Sector "test-cafe" at pixel (64,64) size (128,96) -> tiles x:[2,5) y:[2,5)
- Arena "test-cafe:seating" at pixel (64,64) size (64,64) -> tiles x:[2,4) y:[2,4)
- Collision strip at pixel (0,0) size (320,32) -> top row y=0, x=0..9
- Spawn point "alice" at pixel (96,96) -> tile (3,3)

### docs/tiled-authoring-guide.md (357 lines)

9-section guide covering:
1. Project setup (140x100 tiles, 32px tile size, orthogonal)
2. All 16 CuteRPG tileset PNGs with embed-in-map instruction
3. Exact 14-layer order and naming (case-sensitive)
4. All 14 sectors with display_name/opens/closes/purpose reference table
5. All required arena pairs compiled from 8 agent JSON files (30+ arenas)
6. Collision rectangles including border sizing (4480x3200px map)
7. All 8 spawn point names and home sectors
8. Export steps (CSV format, embed tilesets)
9. Verify commands with sync_map.py and validate_map.py

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing] Added scripts/__init__.py**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** tests imported `from scripts.sync_map import ...` but `scripts/` had no `__init__.py`, causing `ModuleNotFoundError`
- **Fix:** Created `scripts/__init__.py` with one-line comment
- **Files modified:** scripts/__init__.py
- **Commit:** 5f90b72

## Known Stubs

None. The sync script is fully implemented with all documented functions. The authoring guide is complete with all required data compiled from actual agent JSON files.

## Threat Flags

None. sync_map.py only reads/writes within the project directory and has no network access (T-11-03 accepted per threat model).

## Self-Check: PASSED

| Item | Status |
|------|--------|
| scripts/sync_map.py | FOUND |
| tests/test_sync_map.py | FOUND |
| docs/tiled-authoring-guide.md | FOUND |
| commit 5f90b72 (Task 1) | FOUND |
| commit 320ac09 (Task 2) | FOUND |
