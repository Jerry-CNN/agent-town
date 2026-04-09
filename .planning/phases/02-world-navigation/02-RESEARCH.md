# Phase 2: World & Navigation - Research

**Researched:** 2026-04-09
**Domain:** Tile-map data modeling, BFS pathfinding, agent data structures
**Confidence:** HIGH — all critical findings verified directly from codebase and reference implementation

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Large map (100x100+ tiles). The reference maze.json uses 100x140. 100x100 minimum.
- **D-02:** Thematic locations: stock exchange, wedding hall, park, homes (multiple), shops, cafe, office. No additions for v1.
- **D-03:** Neighborhood cluster arrangement — residential, commercial, civic, green space.
- **D-04:** 32px tile size. 100x100 grid = 3200x3200px canvas.
- **D-05:** Tiled JSON format. Map stored as Tiled-compatible JSON, parsed at runtime by the backend.
- **D-06:** Dedicated collision layer in the Tiled JSON marks walkable vs obstacle tiles. Pathfinding reads this layer only.
- **D-07:** Claude generates the Tiled JSON programmatically during this phase. User reviews output.
- **D-08:** 8-10 pre-defined agents with diverse occupations (trader, baker, florist, office worker, barista, etc.).
- **D-09:** Agent personality data stored in JSON config files — one per agent. Contains name, traits, occupation, home location, daily routine template.
- **D-10:** Hybrid daily routines — config provides rough template; LLM fills in details in Phase 3.
- **D-11:** Agents spawn at a mixture of home and workplace locations when simulation starts.
- **D-12:** Pure BFS shortest path. All walkable tiles have equal cost. No alternatives.
- **D-13:** Destination resolution: agent resolves a location name (e.g., "cafe") to any walkable tile within that zone.
- **D-14:** Minimal metadata per location — name and associated tile coordinates only. LLM infers activity types from name.

### Claude's Discretion

- Interior room depth: whether locations have sub-areas (hierarchical addressing like the reference) or are flat named zones.
- Agent movement speed per simulation step.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MAP-03 | Custom town with thematic locations (stock exchange, wedding hall, park, homes, shops, cafe, office) | Tile layout design, location zone coordinates, address hierarchy in maze.json format |
| MAP-04 | BFS pathfinding so agents navigate around obstacles to reach destinations | Reference BFS implementation in maze.py directly usable; collision layer from Tiled JSON |
| AGT-01 | Each agent has a distinct personality (name, traits, occupation, daily routine) | Reference agent.json format provides exact schema pattern; 8-10 agent cast defined |
</phase_requirements>

---

## Summary

Phase 2 delivers the pure-Python data layer for world and agents — no rendering, no LLM calls, no network. Every component is a data structure with a unit-testable interface. The reference implementation (`GenerativeAgentsCN`) provides verified, directly portable patterns for all three deliverables: tile-map data model, BFS pathfinding, and agent config schema.

The key architectural decision (Claude's discretion) is **interior room depth**: whether locations use the reference's four-level address hierarchy (`world:sector:arena:game_object`) or a simpler two-level scheme (`sector:arena`). Research shows the four-level scheme is required to correctly support Phase 3 agent cognition (spatial memory, action targeting). The flat scheme saves implementation time but creates Phase 3 retrofit debt. Recommendation: use a three-level hierarchy (`world:location:zone`) — simpler than the reference but preserving the structure Phase 3 needs.

The BFS in the reference has a known edge-boundary quirk: it excludes the outermost row/column of the grid (`0 < c[0] < width-1`). This must be preserved exactly or adapted with explicit boundary collision tiles — otherwise agents can theoretically walk off the map edge.

**Primary recommendation:** Port the reference `Maze` and `Tile` classes directly into `backend/simulation/world.py`, adapt agent JSON config format to English and project locations, and generate the town map programmatically as a Tiled-compatible JSON.

---

## Standard Stack

### Core (all verified from existing pyproject.toml and codebase)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.11+ (3.14.2 on host) | Runtime | Already established in Phase 1 |
| Pydantic | 2.12+ | Agent and map data models | Already installed; Phase 1 established v2 patterns |
| pytest | 9.0.3 | Unit tests including BFS tests | Already installed with asyncio_mode=auto |
| pytest-asyncio | 1.3.0 | Async test support | Already installed |

[VERIFIED: /Users/sainobekou/projects/agent-town/pyproject.toml]

### No New Dependencies Required

Phase 2 is pure Python data structures. No new packages needed. The map JSON is generated by code and loaded at startup. BFS is a hand-written algorithm (deliberately, per D-12). Pydantic v2 models cover agent configs.

**Do not add:** pathfinding libraries (python-pathfinding, pyastar2d) — D-12 mandates pure BFS. Do not add map parsing libraries — the Tiled JSON is parsed directly with `json.load()`.

---

## Architecture Patterns

### Recommended File Layout (extending Phase 1 structure)

[VERIFIED: /Users/sainobekou/projects/agent-town/backend/ — existing structure]
[CITED: /Users/sainobekou/projects/agent-town/.planning/research/ARCHITECTURE.md — layer 0 spec]

```
backend/
├── simulation/
│   ├── __init__.py
│   ├── world.py          # Tile, Maze classes — BFS lives here
│   └── pathfinding.py    # find_path() extracted as standalone function (testability)
├── agents/
│   ├── __init__.py
│   └── loader.py         # Load agent JSON configs → AgentConfig Pydantic models
├── schemas.py            # EXTEND with AgentConfig, TileAddress, LocationMeta
└── data/
    ├── map/
    │   └── town.json     # Generated Tiled-compatible JSON (programmatic output of Wave 1)
    └── agents/
        ├── alice.json    # One file per agent
        ├── bob.json
        └── ...           # 8-10 total
```

**Note on `data/` location:** The architecture doc places assets under a top-level `data/` dir. For Phase 2 (backend-only, no frontend), placing data under `backend/data/` keeps it importable via relative paths. Confirmed: `backend/` is the Python package root. [VERIFIED: /Users/sainobekou/projects/agent-town/backend/__init__.py exists]

### Pattern 1: Tile Data Model (port from reference)

[VERIFIED: /Users/sainobekou/projects/GenerativeAgentsCN/generative_agents/modules/maze.py]

The reference `Tile` class carries:
- `coord: tuple[int, int]` — (x, y) grid position
- `address: list[str]` — hierarchical path, e.g. `["agent-town", "cafe", "seating"]`
- `address_keys: list[str]` — labels for each level, e.g. `["world", "sector", "arena"]`
- `collision: bool` — walkability flag
- `_events: dict` — runtime event store (Phase 3 concern; initialize empty)

**Claude's discretion resolved — use 3-level hierarchy:** `world:sector:arena`
- Level 0 `world`: "agent-town" (single string, always present)
- Level 1 `sector`: location name ("cafe", "stock-exchange", "park", "home-alice", ...)
- Level 2 `arena`: zone within location ("seating", "counter", "garden", "bedroom", ...)

This drops the reference's 4th level (`game_object`) because: (1) Phase 3 cognition needs sector and arena for spatial memory and action description; (2) game_object level is for interactive object events, which Phase 3 adds dynamically — no need to pre-define all objects in the map. Simpler upfront, no Phase 3 refactor needed.

```python
# backend/simulation/world.py
# Source: adapted from GenerativeAgentsCN/generative_agents/modules/maze.py

from dataclasses import dataclass, field

ADDRESS_KEYS = ["world", "sector", "arena"]

@dataclass
class Tile:
    coord: tuple[int, int]
    address: list[str] = field(default_factory=list)  # ["agent-town", "cafe", "seating"]
    collision: bool = False
    _events: dict = field(default_factory=dict, repr=False)

    def get_address(self, level: str | None = None, as_list: bool = True) -> list[str] | str:
        """Return address up to specified level (inclusive)."""
        if level is None or level == ADDRESS_KEYS[-1]:
            addr = self.address
        else:
            pos = ADDRESS_KEYS.index(level) + 1
            addr = self.address[:pos]
        return addr if as_list else ":".join(addr)

    def get_addresses(self) -> list[str]:
        """Return all ancestor address strings (for address_tiles index)."""
        return [":".join(self.address[:i]) for i in range(2, len(self.address) + 1)]

    def has_address(self, level: str) -> bool:
        key_idx = ADDRESS_KEYS.index(level)
        return len(self.address) > key_idx

    @property
    def is_walkable(self) -> bool:
        return not self.collision
```

### Pattern 2: Maze Class with BFS

[VERIFIED: /Users/sainobekou/projects/GenerativeAgentsCN/generative_agents/modules/maze.py lines 109-210]

**Critical implementation note — BFS boundary guard:**
The reference `find_path` uses `0 < c[0] < maze_width - 1` (strict inequality), which excludes the outermost border row/column from pathfinding. This is intentional: the reference map marks border tiles as collision. Our map must either:
1. Mark all border tiles as collision in the JSON (recommended — matches reference approach), OR
2. Change the BFS bounds check to `0 <= c[0] <= maze_width - 1` (non-strict) if border tiles are walkable.

Recommendation: mark all perimeter tiles collision in map generation. This preserves reference behavior and ensures BFS never produces out-of-bounds coordinates.

```python
# backend/simulation/world.py (continued)

import random
from collections import deque

class Maze:
    def __init__(self, config: dict) -> None:
        self.world = config["world"]           # "agent-town"
        self.height, self.width = config["size"]   # [rows, cols]
        self.tile_size = config["tile_size"]   # 32

        # Initialize all tiles as empty walkable tiles
        self.tiles: list[list[Tile]] = [
            [Tile(coord=(x, y)) for x in range(self.width)]
            for y in range(self.height)
        ]

        # Apply tile definitions from config
        for tile_def in config.get("tiles", []):
            x, y = tile_def["coord"]
            self.tiles[y][x] = Tile(
                coord=(x, y),
                address=[self.world] + tile_def.get("address", []),
                collision=tile_def.get("collision", False),
            )

        # Build reverse index: address string → set of (x,y) coords
        self.address_tiles: dict[str, set[tuple[int, int]]] = {}
        for row in self.tiles:
            for tile in row:
                for addr in tile.get_addresses():
                    self.address_tiles.setdefault(addr, set()).add(tile.coord)

    def tile_at(self, coord: tuple[int, int]) -> Tile:
        x, y = coord
        return self.tiles[y][x]

    def get_walkable_neighbors(self, coord: tuple[int, int]) -> list[tuple[int, int]]:
        """4-directional neighbors that are in-bounds and not collision."""
        x, y = coord
        candidates = [(x-1, y), (x+1, y), (x, y-1), (x, y+1)]
        return [
            c for c in candidates
            if 0 < c[0] < self.width - 1      # strict: border tiles are collision
            and 0 < c[1] < self.height - 1
            and not self.tiles[c[1]][c[0]].collision
        ]

    def find_path(self, src: tuple[int, int], dst: tuple[int, int]) -> list[tuple[int, int]]:
        """BFS shortest path from src to dst. Returns [] if unreachable."""
        if src == dst:
            return [src]

        # Distance map: 0 = unvisited
        dist: list[list[int]] = [[0] * self.width for _ in range(self.height)]
        dist[src[1]][src[0]] = 1

        frontier = deque([src])
        while frontier:
            curr = frontier.popleft()
            if curr == dst:
                break
            for neighbor in self.get_walkable_neighbors(curr):
                if dist[neighbor[1]][neighbor[0]] == 0:
                    dist[neighbor[1]][neighbor[0]] = dist[curr[1]][curr[0]] + 1
                    frontier.append(neighbor)

        if dist[dst[1]][dst[0]] == 0:
            return []  # dst unreachable

        # Reconstruct path backwards
        path = [dst]
        step = dist[dst[1]][dst[0]]
        while step > 1:
            for c in self.get_walkable_neighbors(path[-1]):
                if dist[c[1]][c[0]] == step - 1:
                    path.append(c)
                    break
            step -= 1
        return path[::-1]

    def get_address_tiles(self, address: list[str]) -> set[tuple[int, int]]:
        """Return all tile coordinates for a given address."""
        key = ":".join(address)
        return self.address_tiles.get(key, set())

    def resolve_destination(self, sector: str) -> tuple[int, int] | None:
        """Pick a random walkable tile in a named sector."""
        # Build the full address key including world prefix
        key = f"{self.world}:{sector}"
        tiles = self.address_tiles.get(key, set())
        walkable = [t for t in tiles if not self.tile_at(t).collision]
        return random.choice(walkable) if walkable else None
```

**BFS improvement over reference:** Using `collections.deque` instead of a list-based frontier. The reference uses a plain list with `new_frontier = []` per level, which is O(n) for each append-and-iterate cycle. `deque` with `popleft()` is O(1) per operation — negligible difference at 100x100 scale but cleaner. [ASSUMED — standard Python CS, not verified via benchmarks at this scale]

### Pattern 3: Town Map JSON Format

[VERIFIED: /Users/sainobekou/projects/GenerativeAgentsCN/generative_agents/frontend/static/assets/village/maze.json]

The reference maze.json is a custom format (NOT a standard Tiled export). Key structure:

```json
{
  "world": "agent-town",
  "tile_size": 32,
  "size": [100, 100],
  "tile_address_keys": ["world", "sector", "arena"],
  "tiles": [
    {"coord": [0, 0], "collision": true},
    {"coord": [15, 10], "address": ["cafe", "seating"]},
    {"coord": [16, 10], "address": ["cafe", "seating"]},
    {"coord": [17, 10], "address": ["cafe", "counter"], "collision": true}
  ]
}
```

**Important:** `tiles` is a sparse list — only tiles that differ from the default (empty, walkable) are listed. The reference maze.json has ~thousands of tile entries because the full map is defined tile-by-tile. For Phase 2, the plan generates this JSON programmatically using rectangular zone definitions and a flood-fill approach: define each location as a bounding rect, mark its tiles, then mark collision borders and interior obstacles.

**Tiled JSON compatibility (D-05):** The decision says "Tiled-compatible JSON format." The reference uses a custom format that is NOT a standard Tiled export. The pixi-tiledmap library (used in Phase 5 for rendering) parses the standard Tiled export format (with `layers`, `tilesets`, `tilewidth`, etc.). **Resolution:** Phase 2 uses the custom format (reference-compatible) for backend pathfinding. Phase 5 will need either: (a) a separate Tiled-format file for rendering, or (b) a converter. This should be flagged as an open question for Phase 5 planning — Phase 2 is backend-only and has no renderer dependency.

### Pattern 4: Agent Config JSON Schema

[VERIFIED: /Users/sainobekou/projects/GenerativeAgentsCN/generative_agents/frontend/static/assets/village/agents/山姆/agent.json]

The reference agent.json structure (translated to English context):

```json
{
  "name": "Alice Chen",
  "coord": [36, 65],
  "currently": "Alice is a barista at the town cafe who loves jazz and is planning...",
  "scratch": {
    "age": 28,
    "innate": "warm, creative, curious",
    "learned": "Alice grew up in the city and moved to this town after...",
    "lifestyle": "Alice goes to bed around 10pm and wakes at 6:30am...",
    "daily_plan": "Alice likes to open the cafe in the morning and visit the park in the evening."
  },
  "spatial": {
    "address": {
      "living_area": ["agent-town", "alice-home", "bedroom"]
    },
    "tree": {
      "agent-town": {
        "alice-home": {"bedroom": ["bed", "closet"], "bathroom": ["sink", "shower"]},
        "cafe": {"seating": ["window-seat", "bar-stool"], "counter": ["coffee-machine"]}
      }
    }
  }
}
```

The Pydantic model for loading this:

```python
# backend/schemas.py — extend existing file
from pydantic import BaseModel

class AgentScratch(BaseModel):
    age: int
    innate: str          # personality traits, comma-separated
    learned: str         # background paragraph
    lifestyle: str       # sleep/wake patterns
    daily_plan: str      # routine template for LLM to fill in Phase 3

class AgentSpatial(BaseModel):
    address: dict[str, list[str]]   # named addresses, e.g. {"living_area": ["agent-town", "alice-home", "bedroom"]}
    tree: dict                       # spatial knowledge tree (nested dict, any depth)

class AgentConfig(BaseModel):
    name: str
    coord: tuple[int, int]           # spawn position (x, y)
    currently: str                   # current situation summary (seed for Phase 3)
    scratch: AgentScratch
    spatial: AgentSpatial
```

### Pattern 5: Agent Loader

```python
# backend/agents/loader.py
import json
from pathlib import Path
from backend.schemas import AgentConfig

AGENTS_DIR = Path(__file__).parent.parent / "data" / "agents"

def load_all_agents() -> list[AgentConfig]:
    configs = []
    for f in sorted(AGENTS_DIR.glob("*.json")):
        raw = json.loads(f.read_text())
        configs.append(AgentConfig.model_validate(raw))
    return configs
```

### Town Layout Design (Claude's discretion — movement speed)

**Movement speed:** 1 tile per simulation tick. At a 5-second tick interval (Phase 4 default), this equals 0.2 tiles/second — slow enough to see agents walking, fast enough to cross the map in ~500 seconds (~8 minutes), which feels natural for a town-scale simulation. [ASSUMED — judgment call; not benchmarked]

**Proposed layout (100x100 grid):**

```
y=0  ████████████████████████████████████████████  (collision border)
     ██  PARK (green space)           ██  HOMES  ██
     ██  [park tiles y=5-30, x=5-35] ██  AREA   ██
y=30 ██████████████  roads  ████████████████████████
     ██  CAFE   ██  SHOPS  ██  OFFICE  ██  STOCK ██
y=50 ██  (commercial area, y=35-55, x=5-75)      ██
y=55 ██████████████  roads  ████████████████████████
     ██  WEDDING HALL  ██  MORE HOMES              ██
     ██  (civic, y=60-85, x=5-45)                  ██
y=85 ████████████████████████████████████████████████
     ██  additional homes (y=87-98, x=5-95)        ██
y=99 ████████████████████████████████████████████████
```

Specific zone bounding boxes (approximate, subject to map generator tuning):

| Location | Sector ID | Approx bounds (x1,y1)→(x2,y2) | Zones |
|----------|-----------|-------------------------------|-------|
| Park | `park` | (5,5)→(35,28) | garden, bench-area, pond |
| Home Alice | `home-alice` | (60,5)→(75,28) | bedroom, living-room, kitchen |
| Home Bob | `home-bob` | (77,5)→(92,28) | bedroom, living-room |
| Home Carla | `home-carla` | (60,30)→(75,50)... | ... |
| Cafe | `cafe` | (5,35)→(25,52) | seating, counter, kitchen |
| Shop | `shop` | (28,35)→(48,52) | floor, counter, stockroom |
| Office | `office` | (51,35)→(71,52) | open-plan, meeting-room |
| Stock Exchange | `stock-exchange` | (74,35)→(95,52) | trading-floor, clerk-desk |
| Wedding Hall | `wedding-hall` | (5,60)→(45,82) | hall, dressing-room, foyer |

Homes for remaining agents fill rows y=55-95 in the residential cluster.

### Pattern 6: Map Generator (programmatic Tiled JSON creation)

```python
# backend/simulation/map_generator.py
# Generates town.json from zone definitions

def generate_town_map() -> dict:
    size = [100, 100]  # [height, width]
    tiles = []

    # 1. Mark all border tiles as collision
    for x in range(100):
        tiles.append({"coord": [x, 0], "collision": True})
        tiles.append({"coord": [x, 99], "collision": True})
    for y in range(1, 99):
        tiles.append({"coord": [0, y], "collision": True})
        tiles.append({"coord": [99, y], "collision": True})

    # 2. Add zone tiles (addressable walkable interior tiles)
    zones = [
        ("park", [(5,5,35,28)], [("garden", (5,5,35,18)), ("bench-area", (5,18,35,28))]),
        ("cafe", [(5,35,25,52)], [("seating", (5,35,20,44)), ("counter", (20,35,25,52))]),
        # ... etc for each location
    ]

    for sector, outer_bounds, arenas in zones:
        for x1, y1, x2, y2 in outer_bounds:
            # Building walls (collision)
            for x in range(x1, x2):
                tiles.append({"coord": [x, y1], "collision": True})
                tiles.append({"coord": [x, y2-1], "collision": True})
            for y in range(y1, y2):
                tiles.append({"coord": [x1, y], "collision": True})
                tiles.append({"coord": [x2-1, y], "collision": True})

        for arena_name, (ax1, ay1, ax2, ay2) in arenas:
            for y in range(ay1+1, ay2-1):
                for x in range(ax1+1, ax2-1):
                    tiles.append({
                        "coord": [x, y],
                        "address": [sector, arena_name]
                    })

    return {
        "world": "agent-town",
        "tile_size": 32,
        "size": size,
        "tile_address_keys": ["world", "sector", "arena"],
        "tiles": tiles
    }
```

### Anti-Patterns to Avoid

- **Storing the full tiles grid in memory:** The reference builds a full NxM Tile object grid. At 100x100 = 10,000 tiles this is fine (Python object overhead ~200 bytes each = ~2MB). Do not attempt lazy/sparse tile loading — BFS needs random access by coordinate. [ASSUMED — memory estimate not benchmarked]
- **Using pathfinding libraries:** D-12 mandates pure BFS. Libraries like `python-pathfinding` use A* with heuristics — different algorithm, different edge behavior.
- **Parsing Tiled's actual export format in Phase 2:** The standard Tiled export uses `data` arrays with global tile IDs, requiring tileset resolution. The reference custom format avoids this entirely. Phase 5 deals with rendering format; Phase 2 only needs the pathfinding/address data.
- **Initializing ChromaDB or memory in Phase 2:** Agent data models defined here are plain Pydantic objects. Memory stores (ChromaDB) are Phase 3's concern. Do not mix.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON schema validation | Manual dict parsing with try/except | Pydantic v2 `model_validate()` | Already in stack; catches missing fields, wrong types, extra fields automatically |
| File loading patterns | Hardcoded paths in each file | `Path(__file__).parent / "..."` relative paths | Survives working directory changes; already used in Phase 1 patterns |
| BFS algorithm | A*, Dijkstra, or anything else | Pure BFS as specified in D-12 | Equal-cost tiles, no diagonal movement needed; BFS is O(V+E) optimal for this |

---

## Common Pitfalls

### Pitfall 1: BFS Infinite Loop on Disconnected Graph

**What goes wrong:** If `src` and `dst` are in disconnected regions of the map (separated by collision tiles with no walkable path), the reference BFS loops until `new_frontier` is empty — which it handles correctly by returning `[]`. But if the BFS is refactored without this termination check, it loops forever.

**Why it happens:** Developers testing BFS with "obviously reachable" pairs skip the disconnected case and don't test it.

**How to avoid:** The success criterion explicitly requires a unit test for the disconnected case. Write it first. Confirm `find_path(src, dst)` returns `[]` when a wall of collision tiles separates them.

**Warning signs:** Test suite has no test for unreachable pair; BFS hangs on certain map configs.

### Pitfall 2: Tiled JSON Format Confusion

**What goes wrong:** "Tiled JSON" means two different things: (1) the reference's custom format loaded by the backend; (2) the Tiled editor's standard export format consumed by `pixi-tiledmap` in Phase 5. Building one when you need the other wastes a full plan cycle.

**Why it happens:** The CONTEXT.md decision (D-05) says "Tiled-compatible JSON" without specifying which interpretation.

**How to avoid:** Phase 2 generates the custom backend format (reference-compatible, sparse tile list). Phase 5 generates or converts to standard Tiled export. Document this explicitly in the plan so Phase 5 planner knows they need a conversion step or a separate tilemap asset.

**Warning signs:** Trying to import `pixi-tiledmap` in backend Python code — wrong layer.

### Pitfall 3: Sparse Tile List Coordinate Collisions

**What goes wrong:** The map generator produces multiple tile definitions for the same coordinate (e.g., a border-collision entry AND an address entry for the same tile). When the `Maze` constructor iterates the list, the later entry silently overwrites the earlier one. A building wall tile gains an address, becoming walkable.

**Why it happens:** Zone generators and border generators are independent and don't check for overlap.

**How to avoid:** Deduplicate the tile list by coordinate before serializing to JSON. Use a `dict` keyed by `(x, y)` during generation, last-write-wins with explicit priority (border collision > zone address).

**Warning signs:** Agents can walk through walls in specific locations; pathfinding unit test shows unexpected paths.

### Pitfall 4: Resolve-Destination Returns None for Empty Sectors

**What goes wrong:** `resolve_destination("stock-exchange")` returns `None` if no walkable tiles are indexed under that sector. Agents attempting to navigate to an empty sector either crash or silently stay in place.

**Why it happens:** Map generation bug where building walls consume all tiles in a zone, leaving no walkable interior.

**How to avoid:** Add a post-generation validation step: for each required sector, assert `len(address_tiles[sector]) > 0`. Run this validation in a test — not just at runtime.

**Warning signs:** `resolve_destination` returns `None` for any named location during tests.

### Pitfall 5: BFS Path Reconstruction Gets Stuck

**What goes wrong:** The backward reconstruction phase (`while step > 1`) calls `get_walkable_neighbors` on intermediate path tiles. If a path tile is a collision tile (shouldn't happen, but edge cases exist around destination tiles that are "in" a building), the reconstruction finds no valid step-1 neighbor and loops or returns a truncated path.

**Why it happens:** Destination tile is marked collision in the map but is still indexed as an address tile. An agent targeting `cafe:counter` lands on a collision tile.

**How to avoid:** `resolve_destination` must filter to walkable-only tiles before returning a target. Assert in tests that all address tiles returned by `resolve_destination` are walkable (`tile.collision == False`).

### Pitfall 6: Agent spawn coord outside map or on collision tile

**What goes wrong:** Agent JSON specifies a `coord` that is outside the 100x100 grid or on a collision tile. `Maze.tile_at(coord)` raises an IndexError, crashing startup.

**Why it happens:** Agent JSON is hand-authored; map may change during generation.

**How to avoid:** `load_all_agents()` validates each agent's `coord` against the loaded maze. If invalid, raise a clear startup error naming the offending agent file.

---

## Code Examples

### BFS Unit Test (success criterion test)

```python
# tests/test_world.py
import pytest
from backend.simulation.world import Maze

SMALL_MAP = {
    "world": "test-world",
    "tile_size": 32,
    "size": [10, 10],
    "tile_address_keys": ["world", "sector", "arena"],
    "tiles": [
        # Border walls
        *[{"coord": [x, 0], "collision": True} for x in range(10)],
        *[{"coord": [x, 9], "collision": True} for x in range(10)],
        *[{"coord": [0, y], "collision": True} for y in range(1, 9)],
        *[{"coord": [9, y], "collision": True} for y in range(1, 9)],
        # Vertical wall blocking left side from right side
        *[{"coord": [5, y], "collision": True} for y in range(0, 10)],
    ]
}

def test_bfs_finds_path():
    maze = Maze(SMALL_MAP)
    path = maze.find_path((1, 1), (4, 8))
    assert len(path) > 0
    assert path[0] == (1, 1)
    assert path[-1] == (4, 8)

def test_bfs_returns_empty_when_disconnected():
    maze = Maze(SMALL_MAP)
    # Left side (x=1-4) and right side (x=6-8) are disconnected
    path = maze.find_path((1, 5), (7, 5))
    assert path == []

def test_bfs_same_start_and_goal():
    maze = Maze(SMALL_MAP)
    path = maze.find_path((2, 2), (2, 2))
    assert path == [(2, 2)]
```

### Agent Config Loading + Validation

```python
# tests/test_agent_loader.py
from backend.agents.loader import load_all_agents

def test_loads_minimum_agent_count():
    agents = load_all_agents()
    assert len(agents) >= 5  # success criterion: minimum 5 agents

def test_agents_have_distinct_names():
    agents = load_all_agents()
    names = [a.name for a in agents]
    assert len(names) == len(set(names))

def test_agents_have_required_fields():
    agents = load_all_agents()
    for agent in agents:
        assert agent.name
        assert agent.scratch.innate      # personality traits
        assert agent.scratch.daily_plan  # routine template
        assert agent.coord               # spawn position
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tiled Map Editor for map design | Programmatic JSON generation (D-07) | Phase 2 decision | No GUI tooling needed; map is code, version-controlled, reproducible |
| A* pathfinding (heuristic) | BFS (equal-cost tiles, D-12) | Reference paper choice | Simpler, no heuristic tuning, correct for grid with uniform movement cost |
| LlamaIndex for spatial memory | Custom Pydantic spatial tree | Reference CN adaptation | LlamaIndex has high RAM overhead (see PITFALLS.md); custom tree is 10x lighter |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 3-level hierarchy (`world:sector:arena`) is sufficient for Phase 3 cognition without needing the 4th `game_object` level upfront | Architecture Patterns / Pattern 1 | Phase 3 may need to refactor Tile class to add game_object level; medium retrofit cost |
| A2 | `deque` BFS improvement has negligible performance difference vs. reference list-based BFS at 100x100 scale | Pattern 2 | None — at 10,000 tiles the difference is microseconds |
| A3 | Movement speed of 1 tile/tick feels natural for Phase 4's 5-second tick interval | Town Layout Design | May need tuning in Phase 4; easily configurable |
| A4 | Placing `data/` under `backend/data/` (rather than project root) works with the existing import structure | Architecture Patterns | Minor path adjustment; low risk |

---

## Open Questions

1. **Standard Tiled format vs. custom format for Phase 5**
   - What we know: D-05 says "Tiled-compatible JSON." The backend uses the custom format. `pixi-tiledmap` (Phase 5) expects standard Tiled export.
   - What's unclear: Does Phase 5 need a second, rendering-specific map file, or does pixi-tiledmap accept the custom format?
   - Recommendation: Phase 5 planner should resolve this. Phase 2 generates the backend format without visual tile IDs. A converter or a second visual map file (authored separately with Tiled app) is the likely resolution.

2. **Agent cast final names and occupations**
   - What we know: 8-10 agents needed (D-08); diverse occupations listed conceptually.
   - What's unclear: Exact names, personality text, spawn coordinates within the designed map.
   - Recommendation: Plan wave that generates agent JSON files should finalize the cast. Suggest: Alice (barista, cafe), Bob (stockbroker, stock-exchange), Carla (florist, shop), David (office worker, office), Emma (baker, shop), Frank (park keeper, park), Grace (wedding planner, wedding-hall), Henry (retired, home), Isabel (home), James (home).

3. **Road tiles between zones**
   - What we know: Agents commute between clusters (D-03). Roads must be walkable and addressable-or-anonymous.
   - What's unclear: Do road tiles need addresses (e.g., `streets:main-street`) or are they anonymous walkable tiles?
   - Recommendation: Anonymous walkable tiles (no address entry in JSON). BFS will route through them naturally. Only named zones need addresses. Phase 3 cognition uses location names from zones, not roads.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python 3.11+ | Backend runtime | Yes | 3.14.2 | — |
| uv | Package management | Yes | 0.9.26 | pip (slower) |
| pytest | Unit tests | Yes (pyproject.toml) | 9.0.3 | — |
| pytest-asyncio | Async test support | Yes (pyproject.toml) | 1.3.0 | — |
| Pydantic v2 | Data models | Yes (pyproject.toml) | 2.12+ | — |

[VERIFIED: /Users/sainobekou/projects/agent-town/pyproject.toml, bash environment checks]

**Missing dependencies with no fallback:** None. Phase 2 requires only what Phase 1 already installed.

**Step 2.6: No additional external dependencies identified.**

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-asyncio 1.3.0 |
| Config file | `/Users/sainobekou/projects/agent-town/pyproject.toml` (asyncio_mode = "auto") |
| Quick run command | `cd /Users/sainobekou/projects/agent-town && uv run pytest tests/test_world.py tests/test_agent_loader.py -x -q` |
| Full suite command | `cd /Users/sainobekou/projects/agent-town && uv run pytest -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MAP-03 | Town loads all required locations (all 7 location types indexed in address_tiles) | unit | `uv run pytest tests/test_world.py::test_all_required_locations_exist -x` | No — Wave 0 |
| MAP-04 | `find_path(src, dst)` returns valid BFS path avoiding collision tiles | unit | `uv run pytest tests/test_world.py::test_bfs_finds_path -x` | No — Wave 0 |
| MAP-04 | `find_path` returns `[]` when disconnected | unit | `uv run pytest tests/test_world.py::test_bfs_returns_empty_when_disconnected -x` | No — Wave 0 |
| AGT-01 | Minimum 5 agents load with distinct names, personality, occupation, routine | unit | `uv run pytest tests/test_agent_loader.py -x` | No — Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_world.py tests/test_agent_loader.py -x -q`
- **Per wave merge:** `uv run pytest -x -q` (full suite)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_world.py` — covers MAP-03, MAP-04 (BFS tests)
- [ ] `tests/test_agent_loader.py` — covers AGT-01

*(Existing `tests/conftest.py` has the `async_client` fixture; no new fixtures needed for Phase 2 — pathfinding and agent loading are sync operations.)*

---

## Security Domain

Phase 2 is a pure data-layer phase (no HTTP endpoints, no user input, no LLM calls, no external network). The only security-relevant consideration:

**Input validation on agent JSON:** Agent JSON files are authored by Claude and committed to the repo — not user-supplied at runtime. No injection risk. Pydantic validation provides schema safety.

**ASVS categories:** V5 (Input Validation) applies only to the agent/map JSON loading. Pydantic v2 `model_validate()` with strict typing handles this. No other ASVS categories apply to this phase. [VERIFIED: phase has no auth, sessions, crypto, or user-facing access control]

---

## Sources

### Primary (HIGH confidence)

- `/Users/sainobekou/projects/GenerativeAgentsCN/generative_agents/modules/maze.py` — Tile class, Maze class, BFS implementation, address indexing. Verified line-by-line.
- `/Users/sainobekou/projects/GenerativeAgentsCN/generative_agents/frontend/static/assets/village/maze.json` — Tiled JSON format, tile structure, address hierarchy, collision layer.
- `/Users/sainobekou/projects/GenerativeAgentsCN/generative_agents/frontend/static/assets/village/agents/山姆/agent.json` — Agent config schema (name, coord, currently, scratch, spatial).
- `/Users/sainobekou/projects/agent-town/backend/schemas.py` — Existing Pydantic patterns (v2, model_validator).
- `/Users/sainobekou/projects/agent-town/pyproject.toml` — Verified installed packages and pytest config.
- `/Users/sainobekou/projects/agent-town/.planning/research/ARCHITECTURE.md` — Layer 0 build order, world.py and pathfinding.py file placement.

### Secondary (MEDIUM confidence)

- `/Users/sainobekou/projects/agent-town/.planning/research/STACK.md` — Stack decisions confirmed matching current pyproject.toml.
- `/Users/sainobekou/projects/agent-town/.planning/research/PITFALLS.md` — Pathfinding and agent loop pitfalls.

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — all verified from pyproject.toml; no new packages needed
- Architecture: HIGH — reference implementation verified line-by-line; patterns are direct ports
- BFS algorithm: HIGH — read actual code; identified boundary guard quirk
- Map JSON format: HIGH — verified from reference maze.json structure
- Agent config format: HIGH — verified from reference agent.json
- Town layout coordinates: MEDIUM — zone sizing is judgment-based; needs map generator validation
- Agent cast names/personalities: MEDIUM — occupations specified in D-08; exact text is Claude's authoring choice

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (stable domain — no external libraries involved)
