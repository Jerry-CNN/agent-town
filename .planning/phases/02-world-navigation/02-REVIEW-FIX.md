---
phase: 02-world-navigation
fixed_at: 2026-04-09T00:00:00Z
review_path: .planning/phases/02-world-navigation/02-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 02: Code Review Fix Report

**Fixed at:** 2026-04-09
**Source review:** .planning/phases/02-world-navigation/02-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5
- Fixed: 5
- Skipped: 0

## Fixed Issues

### WR-01: Henry spawns inside home-bob, not home-henry

**Files modified:** `backend/data/agents/henry.json`
**Commit:** cefacdb
**Applied fix:** Changed `coord` from `[82, 12]` (inside home-bob bounds) to `[77, 23]` (walkable interior of home-henry, x=73–82, y=18–28). This aligns the spawn position with Henry's `spatial.address.living_area` of `["agent-town", "home-henry", "bedroom"]`.

---

### WR-02: Carla spawns inside the office building, not home-carla

**Files modified:** `backend/data/agents/carla.json`
**Commit:** 7d15e61
**Applied fix:** Changed `coord` from `[65, 38]` (inside office building, commercial band y=35-52) to `[65, 22]` (walkable interior of home-carla, x=60–71, y=18–28). This aligns the spawn with Carla's `currently` field ("at home watering her indoor plants") and her `spatial.address.living_area`.

---

### WR-03: `tile_at()` has no bounds checking

**Files modified:** `backend/simulation/world.py`
**Commit:** 5f6ed0e
**Applied fix:** Added an explicit bounds guard in `tile_at()` before the `self.tiles[y][x]` access. Raises `IndexError` with a descriptive message (including the bad coordinate and grid dimensions) for both out-of-range positive coordinates and negative coordinates, eliminating the silent Python list wrap-around behaviour.

---

### WR-04: `Tile.get_address()` and `Tile.has_address()` raise bare `ValueError` for invalid level

**Files modified:** `backend/simulation/world.py`
**Commit:** bed5940
**Applied fix:** Added a module-level `_validate_level(level: str) -> None` helper that raises a descriptive `ValueError` (naming the invalid level and listing valid choices) when `level` is not in `ADDRESS_KEYS`. Called at the top of `get_address()` (guarded by `if level is not None`) and at the top of `has_address()`, before any `ADDRESS_KEYS.index(level)` call.

---

### WR-05: Arena boundary gaps create silently unlabeled tiles (`main` arena)

**Files modified:** `backend/simulation/map_generator.py`
**Commit:** 7fe54b0
**Applied fix:** Changed the arena interior fill loop in `_add_building()` from `range(ay1+1, ay2-1)` / `range(ax1+1, ax2-1)` (exclusive upper bound, creating gap rows) to `range(ay1+1, ay2)` / `range(ax1+1, ax2)` (inclusive upper boundary). The existing `continue` guard skips collision tiles so perimeter walls are not overwritten. This eliminates the gap row at shared arena boundaries (e.g., bedroom/living-room boundary) that was causing tiles to fall back to the `"main"` arena label.

---

_Fixed: 2026-04-09_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
