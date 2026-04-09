---
phase: 02-world-navigation
plan: "01"
subsystem: world-navigation
tags: [tile-map, bfs, pathfinding, world-model, data-model, tdd]
dependency_graph:
  requires: []
  provides:
    - backend/simulation/world.py (Tile, Maze, ADDRESS_KEYS)
    - backend/simulation/map_generator.py (generate_town_map)
    - backend/data/map/town.json (generated 100x100 town map)
    - tests/test_world.py (49 unit tests)
  affects:
    - Phase 3 (agent cognition uses Maze.resolve_destination and Maze.tile_at)
    - Phase 4 (simulation loop calls Maze.find_path every tick)
    - Phase 5 (town.json needs a converter for pixi-tiledmap rendering)
tech_stack:
  added: []
  patterns:
    - Sparse tile list with dict-keyed dedup to prevent coordinate collisions
    - 3-level address hierarchy (world:sector:arena) for spatial indexing
    - BFS with strict boundary guard (0 < c < dim-1) matching reference impl
    - deque-based BFS frontier for O(1) popleft
    - Post-generation validation asserting all required sectors have walkable tiles
key_files:
  created:
    - backend/simulation/__init__.py
    - backend/simulation/world.py
    - backend/simulation/map_generator.py
    - backend/data/map/town.json
    - tests/test_world.py
  modified: []
decisions:
  - "3-level address hierarchy (world:sector:arena) chosen over reference's 4-level (adds game_object in Phase 3 dynamically)"
  - "town.json uses custom backend format (sparse tile list), not standard Tiled export — Phase 5 will need a converter"
  - "Park implemented as open area (no perimeter walls) while commercial/civic/residential use walled buildings with door openings"
  - "BFS boundary guard uses strict inequality (0 < c < dim-1) matching reference; border tiles are always collision"
metrics:
  duration_minutes: 25
  completed_date: "2026-04-09"
  tasks_completed: 2
  tasks_total: 2
  files_created: 5
  files_modified: 0
  tests_added: 49
  tests_passed: 49
---

# Phase 02 Plan 01: World Data Model and BFS Pathfinding Summary

**One-liner:** 100x100 tile-map town with 3-level address hierarchy, BFS pathfinding, and programmatic JSON generation covering 7+ thematic locations across 16 named sectors.

## What Was Built

The spatial foundation for the entire Agent Town simulation:

1. **`backend/simulation/world.py`** — `Tile` dataclass with 3-level address hierarchy (`world:sector:arena`), `Maze` class with BFS pathfinding (`find_path`), reverse address index (`address_tiles`), and destination resolution (`resolve_destination`).

2. **`backend/simulation/map_generator.py`** — `generate_town_map()` generates a 100x100 town with 4 neighbourhood clusters: NW=Park, NE=Residential-1 (5 homes), middle=Commercial band (cafe/shop/office/stock-exchange), SW=Civic (wedding-hall), SE=Residential-2 (5 homes). Each building has perimeter walls with door openings.

3. **`backend/data/map/town.json`** — Generated output: 4,845 tile entries, all 16 sectors indexed, all sectors mutually reachable via BFS.

4. **`tests/test_world.py`** — 49 unit tests covering: Tile defaults and address slicing, Maze loading, border collision, address indexing, resolve_destination valid/invalid, BFS (same-src-dst, disconnected graph, path adjacency, no collision in path), and full-town cross-sector connectivity.

## Deviations from Plan

### Auto-fixed Issues

None.

### Design Choices Made During Execution

**1. Tests written as one comprehensive file (both tasks together)**

Tasks 1 and 2 were both TDD tasks. Since Task 2 only added BFS-focused tests and the Task 1 implementation was immediately available, both test classes were written together in the RED phase before any implementation. This is valid TDD — tests preceded code.

**2. Park implemented as open area (no perimeter walls)**

The plan specified "mark outer perimeter tiles of the bounding rect as collision." For the park, open boundary tiles would block access from road tiles. The park was implemented as a flat open area (walkable, addressed tiles only) accessible from all sides — more natural for a green space and required for BFS connectivity.

**3. Door openings added as arena="entrance" or arena="foyer" tiles**

Door tiles needed an address to avoid being bare walkable tiles without context. Each building door is addressed as `[sector, "entrance"]` (or `"foyer"` for the wedding hall). This ensures agents stepping through a door still have spatial context.

## Known Stubs

None — all sectors are wired to real generated data, resolve_destination returns walkable tiles for all 16 sectors.

## Threat Flags

None — this plan creates no network endpoints, auth paths, file upload mechanisms, or trust boundary crossings. The town.json is authored by code and committed to git (T-02-01 accepted per threat model).

## Phase 5 Note

`town.json` uses the custom backend format (sparse tile list with address hierarchy), NOT the standard Tiled editor export format. The `pixi-tiledmap` library (Phase 5 rendering) parses the standard Tiled format with `layers`, `tilesets`, `tilewidth`, etc. Phase 5 will need either: (a) a separate Tiled-format file for rendering, or (b) a converter from this format to Tiled JSON. Tracked as a deferred open question.

## Self-Check: PASSED

All created files verified to exist:
- `backend/simulation/__init__.py` — FOUND
- `backend/simulation/world.py` — FOUND
- `backend/simulation/map_generator.py` — FOUND
- `backend/data/map/town.json` — FOUND
- `tests/test_world.py` — FOUND

Commits verified:
- `359ce2a` — FOUND (feat(02-01): tile data model, BFS pathfinding, and town map generator)

Tests: 49/49 passed. Full suite: 64/64 passed.
