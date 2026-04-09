---
phase: 02-world-navigation
reviewed: 2026-04-09T00:00:00Z
depth: standard
files_reviewed: 17
files_reviewed_list:
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
  - backend/data/map/town.json
  - backend/schemas.py
  - backend/simulation/__init__.py
  - backend/simulation/map_generator.py
  - backend/simulation/world.py
  - tests/test_agent_loader.py
  - tests/test_cross_validation.py
  - tests/test_world.py
findings:
  critical: 0
  warning: 5
  info: 6
  total: 11
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-04-09
**Depth:** standard
**Files Reviewed:** 17
**Status:** issues_found

## Summary

Phase 02 delivers the world data model (`Maze`, `Tile`), BFS pathfinding, the programmatic town map generator, agent JSON configs for 8 characters, and a Pydantic v2 schema layer. The architecture is sound and the test coverage is thorough. Two agent data files contain incorrect spawn coordinates that place agents in the wrong buildings. The `tile_at()` method lacks bounds checking, producing undefined behaviour (IndexError or silent wrong-tile return) when called with coordinates outside the grid. Several arena boundary gaps in the map generator silently create a large number of unlabeled `main`-arena tiles. No critical (security/crash/data-loss) issues were found.

## Warnings

### WR-01: Henry spawns inside home-bob, not home-henry

**File:** `backend/data/agents/henry.json:4`
**Issue:** `henry.json` sets `coord` to `[82, 12]`. That coordinate falls inside the `home-bob` building (generator bounds x=77–92, y=5–16), not `home-henry` (x=73–82, y=18–28). The cross-validation soft-check (`test_agent_spawn_coords_match_intended_sector`) will log a warning but not fail. Henry's `spatial.address.living_area` correctly points to `home-henry`, creating an immediate mismatch between where he spawns and where the system believes he lives.

**Fix:** Change Henry's coord to any walkable tile inside `home-henry`. Valid interior tiles are approximately x=74–80, y=19–26:
```json
"coord": [77, 23]
```

---

### WR-02: Carla spawns inside the office building, not home-carla

**File:** `backend/data/agents/carla.json:4`
**Issue:** `carla.json` sets `coord` to `[65, 38]`. That coordinate is inside the `office` building (`office/main` arena, y=38 is in the commercial band y=35–52), not `home-carla` (x=60–71, y=18–28). Carla's `currently` field says she is "at home watering her indoor plants," directly contradicting the spawn location. The cross-validation soft-check will log a warning (tile sector `office` is not in her valid set `{home-carla, shop}`).

**Fix:** Change Carla's coord to a walkable tile inside `home-carla` (interior approximately x=61–69, y=19–26):
```json
"coord": [65, 22]
```

---

### WR-03: `tile_at()` has no bounds checking — raises IndexError or silently returns wrong tile

**File:** `backend/simulation/world.py:145-148`
**Issue:** `tile_at(coord)` performs `self.tiles[y][x]` with no range validation. Two failure modes:
- `x >= self.width` or `y >= self.height`: raises an unhandled `IndexError` that propagates to callers with no useful error context.
- Negative coordinates: Python list indexing wraps silently (e.g., `tile_at((-1, 5))` returns the tile at `(width-1, 5)`, which is the right-border collision tile). This produces a wrong result with no error.

Any future caller that derives coordinates from agent movement or LLM output without pre-validating can trigger either failure mode.

**Fix:**
```python
def tile_at(self, coord: tuple[int, int]) -> Tile:
    """Return the Tile at (x, y) coordinate."""
    x, y = coord
    if not (0 <= x < self.width and 0 <= y < self.height):
        raise IndexError(
            f"Coordinate {coord} is out of bounds "
            f"(width={self.width}, height={self.height})"
        )
    return self.tiles[y][x]
```

---

### WR-04: `Tile.get_address()` and `Tile.has_address()` raise bare `ValueError` for invalid level

**File:** `backend/simulation/world.py:62-80`
**Issue:** Both `get_address(level=...)` and `has_address(level)` call `ADDRESS_KEYS.index(level)` without guarding against an unknown `level` value. An invalid level (e.g., `"zone"` or a typo) raises `ValueError: list.index(x): x not in list` — a bare exception with no indication of which level was invalid or what values are valid. This will surface as an opaque error in Phase 3 when cognition code navigates the address hierarchy.

**Fix:**
```python
def _validate_level(level: str) -> None:
    if level not in ADDRESS_KEYS:
        raise ValueError(
            f"Invalid address level {level!r}. Must be one of: {ADDRESS_KEYS}"
        )
```
Call this at the top of `get_address()` and `has_address()` before `ADDRESS_KEYS.index(level)`.

---

### WR-05: Arena boundary gaps create 789 silently unlabeled tiles (`main` arena)

**File:** `backend/simulation/map_generator.py:142-158`
**Issue:** In `_add_building()`, tiles whose coordinates fall between adjacent arena definitions get the fallback label `"main"` (line 154: `arena_name = arena_map.get(coord, "main")`). The arena interior range is computed as `range(ay1+1, ay2-1)` — exclusive on both ends — which means the row at `y=ay2-1` and `y=ay1` are excluded. When two arenas share a boundary (e.g., bedroom `ay2=mid_y` and living-room `ay1=mid_y`), neither arena claims the row at `y=mid_y`, producing a gap row labeled `main`.

This affects all homes (1-row gap between bedroom/living-room, and between living-room/kitchen in `has_kitchen` homes) and the wedding-hall (gap row at y=68 between foyer and hall). The current generated map contains **789 tiles** with `"main"` as the arena label — 16% of all defined tiles. This makes spatial reasoning in Phase 3 less precise: agents reasoning about location will land on an unnamed sub-zone and receive `["home-alice", "main"]` rather than `["home-alice", "bedroom"]`.

**Fix:** Change the arena interior fill range from exclusive-both-ends to inclusive-on-upper to close the gaps:
```python
# Current (creates gap at ay2-1):
for y in range(ay1 + 1, ay2 - 1):
    for x in range(ax1 + 1, ax2 - 1):

# Fix — include the boundary row on the lower-arena side:
for y in range(ay1 + 1, ay2):          # include ay2-1
    for x in range(ax1 + 1, ax2):      # include ax2-1
```
This requires that the `_add_building` perimeter loop (which runs first) marks walls before interior fill, so the `continue` guard on line 152 (`if tiles[coord].get("collision")`) prevents overwriting walls. The interior fill already skips collision tiles, so widening the range is safe.

---

## Info

### IN-01: `Maze` size field documentation — latent ambiguity for non-square maps

**File:** `backend/simulation/world.py:110-113`
**Issue:** `Maze.__init__` unpacks `config["size"]` as `self.height, self.width = config["size"]` (height-first). The docstring says `"size" -- [height, width] (rows x cols)`. The generator returns `[100, 100]`. For the current square map this is unambiguous, but if a future map is non-square, a developer may naturally write `[width, height]` and get silently transposed dimensions. No validator or assertion guards against this.

**Fix:** Add an assertion after unpacking to document the invariant and catch transposition early:
```python
self.height, self.width = config["size"]
assert self.height == len(self.tiles) if ... # or add to _REQUIRED_SECTORS check
```
Or validate in `generate_town_map()` with an explicit comment: `"size": [HEIGHT, WIDTH]  # rows first (height, width)`.

---

### IN-02: `ProviderConfig` accepts whitespace-only `api_key` for openrouter

**File:** `backend/schemas.py:30`
**Issue:** The `validate_openrouter_api_key` validator checks `not self.api_key`, which is falsy for empty string but truthy for `"   "` (whitespace-only). A whitespace-only key would pass validation and only fail at actual LLM call time with a confusing authentication error.

**Fix:**
```python
if self.provider == "openrouter" and not (self.api_key or "").strip():
    raise ValueError("api_key is required when provider is 'openrouter'")
```

---

### IN-03: `loader.py` docstring omits `json.JSONDecodeError` from `Raises`

**File:** `backend/agents/loader.py:17-25`
**Issue:** The `load_all_agents()` docstring lists `FileNotFoundError` and `pydantic.ValidationError` in its `Raises` section, but `json.loads()` can raise `json.JSONDecodeError` if a file contains malformed JSON (not a Pydantic issue). Callers who catch only the documented exceptions will receive an unexpected uncaught error.

**Fix:** Add to the Raises section:
```
json.JSONDecodeError: If any agent JSON file is not valid JSON.
```

---

### IN-04: `AgentConfig.coord` has no range validation at schema level

**File:** `backend/schemas.py:78`
**Issue:** `coord: tuple[int, int]` accepts any integers, including negative values or coordinates beyond map bounds (e.g., `[200, 500]`). The cross-validation tests catch this at test time, but nothing prevents a malformed config from passing schema validation and reaching runtime code.

**Fix:** Add a field validator or use `Annotated` constraints:
```python
from typing import Annotated
from pydantic import Field

Coord = Annotated[int, Field(ge=0, lt=100)]
coord: tuple[Coord, Coord]
```
Or use a `@field_validator("coord")` to enforce bounds.

---

### IN-05: `AgentSpatial.tree` is an untyped `dict` with no structural validation

**File:** `backend/schemas.py:67`
**Issue:** `tree: dict` accepts any value, including `{}` or a deeply malformed structure. Phase 3 cognition will iterate this tree to build the agent's knowledge of the world. A missing or malformed `tree` will surface as a `KeyError` or `AttributeError` deep inside cognition logic rather than at load time.

**Fix:** Consider a typed structure or at minimum a `@model_validator` that asserts `"agent-town"` is a key in the tree (the test `test_spatial_tree_has_world_key` already checks this, but only after loading):
```python
@model_validator(mode="after")
def validate_tree_has_world(self) -> "AgentSpatial":
    if "agent-town" not in self.tree:
        raise ValueError("spatial.tree must contain 'agent-town' as the world key")
    return self
```

---

### IN-06: `test_cross_validation.py` test 7 always passes unconditionally

**File:** `tests/test_cross_validation.py:280`
**Issue:** `test_agent_spawn_coords_match_intended_sector` ends with `assert True, "..."` — it always passes regardless of how many mismatches were found. The mismatches are logged as warnings, which is intentional per the comment, but the test function's trailing assertion is misleading: it looks like a test assertion but provides no enforcement. If CI runs in a mode that suppresses logging, the mismatches are invisible.

**Fix:** The current design (soft-warn) is intentional and correct per the comment. Consider renaming or documenting the function to make its always-passing nature explicit:
```python
def test_agent_spawn_coords_soft_sector_check(agents, maze):
    """Soft check: logs sector mismatches but does not fail. See tests 1-3 for hard constraints."""
```
Or emit the warning count as a metric rather than using `assert True`.

---

_Reviewed: 2026-04-09_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
