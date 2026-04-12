# Phase 11: Town Map Design & Backend Sync - Research

**Researched:** 2026-04-12
**Domain:** Tiled map authoring, Python TMJ sync script, BFS reachability validation, backend map data regeneration
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Expand map from 100x100 to 140x100 tiles (4480x3200px). Requires updating MAP_SIZE_PX in MapCanvas.tsx and related viewport logic.
- **D-02:** Central road layout style — main road through center, commercial buildings (stock exchange, wedding hall, cafe, office, shop) along it, park in a corner or center, homes on outskirts.
- **D-03:** Claude's discretion on number of homes — at least 8 (one per active agent), up to 10 if space allows.
- **D-04:** Reference-level detail for all building interiors — every room has furniture, decorations, floor patterns.
- **D-05:** Source new tileset assets for specialized buildings (stock exchange, wedding hall) where CuteRPG tiles are too generic. User will source these when gaps are flagged.
- **D-06:** Use Tiled object layers (not tile properties) for sector/arena metadata. Rectangles with name properties for each zone.
- **D-07:** Match reference visual layer count (10 visual layers): Bottom Ground, Exterior Ground, Exterior Decoration L1/L2, Interior Ground, Wall, Interior Furniture L1/L2, Foreground L1/L2.
- **D-08:** Add metadata object layers: Sectors, Arenas, Collision, Spawn Points.
- **D-09:** Agent spawn points encoded as point objects in a Tiled "Spawn Points" object layer, named per agent (alice, bob, etc.).
- **D-10:** Python sync script in `scripts/` extracts: tile grid + sector assignments, building metadata, spawn points, collision data. Regenerates both backend and frontend map data.
- **D-11:** All building metadata (operating hours, purpose tags) moves INTO Tiled as custom object properties. Tiled becomes single source of truth. buildings.json is generated, not hand-maintained.
- **D-12:** Separate `scripts/validate_map.py` runs BFS reachability checks from each spawn point to every sector.
- **D-13:** User designs the map manually in the Tiled desktop app. Claude provides layer template, tileset configuration, sector naming conventions, and object layer setup instructions. This is a human dependency that blocks downstream work.

### Claude's Discretion

- Number of homes (D-03, at least 8)
- Specific building placement within the central-road layout
- Path/terrain details (grass, dirt paths, trees, fences)
- Agent-to-spawn-point assignment (which agent starts where)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TOWN-01 | User sees an Agent Town-specific map designed in Tiled with thematic buildings (stock exchange, wedding hall, cafe, park, homes, office, shop) | Tiled layer structure, object layer format, tileset asset list |
| TOWN-02 | Backend town.json is regenerated from the Tiled map export preserving sector/arena coordinate structure | sync_map.py design, existing Maze/town.json schema, object-layer extraction algorithm |
| TOWN-03 | Agent collision detection uses the Tiled collision layer instead of hardcoded collision data | Collision object layer extraction, Maze.collision field, BFS pathfinding unchanged |
| TOWN-04 | Every agent home, workplace, and routine destination maps to a reachable walkable tile after Tiled map export — no agent spawns in walls or has unreachable schedule destinations | validate_map.py BFS design, agent JSON spatial trees, all 8 agent home/workplace sectors |

</phase_requirements>

---

## Summary

Phase 11 is a multi-deliverable phase with a hard human-dependency blocker at its center: the user must author the Tiled map manually. Claude's job is to (a) produce everything the user needs to author the map correctly (layer template, naming conventions, object layer guide), (b) write `scripts/sync_map.py` that regenerates `backend/data/map/town.json`, `backend/data/map/buildings.json`, and `frontend/src/data/town.json` from the Tiled export, and (c) write `scripts/validate_map.py` that proves every agent spawn point reaches every required sector destination.

The existing codebase defines the schemas this phase must produce. `backend/simulation/world.py`'s `Maze` class loads `town.json` directly — the sync script must produce valid input for that class. The `buildings.json` schema is a flat array of `{name, sector, opens, closes, purpose}` objects — the sync script extracts this from Tiled custom object properties. The `frontend/src/data/town.json` file is a static import in `TileMap.tsx` and must maintain the same schema until Phase 12 replaces the renderer.

The reference Tiled map (`GenerativeAgentsCN/tilemap.json`) is 140x100 tiles with exactly 10 visual tile layers + 7 metadata layers. D-07 matches the reference visual layer count. D-08 departs from the reference's metadata approach: the reference uses colored tile blocks (blocks_1/2/3.png) to encode sector/arena zones via GIDs, while Agent Town uses named rectangle objects in object layers — this is simpler to author and parse. The sync script does NOT need GID-based block parsing for sector/arena data; it reads object bounds instead.

**Primary recommendation:** Deliver in three sequential waves — (Wave 0) the Tiled authoring guide and layer template for the user, (Wave 1) `scripts/sync_map.py` tested against a minimal test TMJ, (Wave 2) `scripts/validate_map.py` + frontend/backend integration of the generated files after the user delivers the real map.

---

## Standard Stack

### Core — No New Dependencies

This phase is predominantly Python scripting and Tiled map authoring. All required tools are already installed. [VERIFIED: codebase inspection]

| Tool / Library | Version | Purpose | Source |
|---------------|---------|---------|--------|
| Python 3.11+ | Already installed (`.venv` present) | sync_map.py, validate_map.py | project pyproject.toml |
| Tiled Map Editor | Desktop app, user-installed | Author 140x100 Tiled map | External tool, user dependency |
| `backend/simulation/world.py` Maze | Already in codebase | BFS pathfinding, unchanged | Direct codebase read |
| `json` (stdlib) | — | Parse .tmj, write .json | stdlib |
| `pathlib` (stdlib) | — | File path handling | stdlib |
| `collections.deque` (stdlib) | — | BFS frontier (already in Maze) | already in world.py |

### Tiled Export Format

Tiled exports `.tmj` (Tiled Map JSON) — same format as `.json`, different extension since Tiled 1.8+. The sync script should accept both extensions. [ASSUMED — based on Tiled documentation knowledge; direct version verification not performed]

**Installation:** None required — no new packages.

---

## Architecture Patterns

### Existing Schemas (MUST PRESERVE)

**town.json schema** (read directly from `backend/data/map/town.json`): [VERIFIED: direct file read]

```json
{
  "world": "agent-town",
  "tile_size": 32,
  "size": [100, 140],
  "tile_address_keys": ["world", "sector", "arena"],
  "tiles": [
    {"coord": [5, 5], "address": ["park", "garden"]},
    {"coord": [0, 0], "collision": true}
  ]
}
```

Key detail: `"size"` is `[height, width]` — the Maze class does `self.height, self.width = config["size"]`. For the 140x100 map: `"size": [100, 140]`. [VERIFIED: world.py line 184]

Tile entries omit `address` when anonymous walkable. Omit `collision` when False (not present = walkable). Tiles with both `address` AND `collision: true` exist (door tiles marked as entrance address but passable — collision False).

**buildings.json schema** (read directly from `backend/data/map/buildings.json`): [VERIFIED: direct file read]

```json
[
  {"name": "Town Cafe", "sector": "cafe", "opens": 7, "closes": 22, "purpose": "food"},
  {"name": "Alice's Home", "sector": "home-alice", "opens": 0, "closes": 24, "purpose": "residential"}
]
```

The `Building` class in `world.py` uses `Building(**b)` to instantiate — the dict keys must exactly match the dataclass field names: `name`, `sector`, `opens`, `closes`, `purpose`. [VERIFIED: world.py lines 150-161]

**Required sector names** (all 16 must exist in generated files): [VERIFIED: direct file read of town.json + buildings.json]

```
cafe, stock-exchange, wedding-hall, park, office, shop
home-alice, home-bob, home-carla, home-david, home-emma,
home-frank, home-grace, home-henry, home-isabel, home-james
```

Note: `home-isabel` and `home-james` are in the current town.json but there are only 8 active agent JSON files (alice through henry). The sync script should generate sectors for all agents in `backend/data/agents/*.json`.

**Agent JSON spatial tree** (determines what arenas must be reachable): [VERIFIED: alice.json, bob.json, henry.json read]

```json
{
  "coord": [12, 40],
  "spatial": {
    "address": {
      "living_area": ["agent-town", "home-alice", "bedroom"],
      "workplace": ["agent-town", "cafe", "counter"]
    },
    "tree": {
      "agent-town": {
        "home-alice": {"bedroom": [], "living-room": [], "kitchen": []},
        "cafe": {"seating": [], "counter": [], "kitchen": []},
        "park": {"bench-area": []}
      }
    }
  }
}
```

The `coord` field is the agent's spawn tile `[x, y]`. The spatial `tree` keys define every sector+arena the agent might navigate to — all must be reachable from the spawn coord.

### Agent Spawn Coordinates

All 8 active agents with their current spawn coords (to be superseded by Tiled spawn points after sync): [VERIFIED: direct agent JSON reads]

| Agent | Current coord [x,y] | Home sector | Workplace sector |
|-------|---------------------|-------------|-----------------|
| alice | [12, 40] | home-alice | cafe |
| bob | [82, 42] | home-bob | stock-exchange |
| carla | [65, 22] | home-carla | shop |
| david | [58, 42] | home-david | office |
| emma | [35, 45] | home-emma | shop |
| frank | [15, 12] | home-frank | park |
| grace | [20, 68] | home-grace | wedding-hall |
| henry | [77, 23] | home-henry | (no workplace — retired) |

### Tiled Layer Structure (D-07 + D-08)

The reference map has exactly this layer order (17 layers total). The new map MUST match the visual layer names for pixi-tiledmap to split background/foreground correctly in Phase 12. [VERIFIED: reference tilemap.json layer dump]

```
VISUAL LAYERS (tilelayer, all visible: true):
1. Bottom Ground          ← base terrain (grass, ground)
2. Exterior Ground        ← paths, roads, exterior floors
3. Exterior Decoration L1 ← trees, bushes, fences (first pass)
4. Exterior Decoration L2 ← trees, bushes (second pass, overlay)
5. Interior Ground        ← interior floor tiles
6. Wall                   ← building walls and exterior borders
7. Interior Furniture L1  ← furniture, counters, first layer
8. Interior Furniture L2  ← furniture, decorations, second layer
9. Foreground L1          ← tree tops, roof overhangs (render above agents)
10. Foreground L2         ← foreground overhangs, second pass

METADATA LAYERS (objectgroup, visible: false — D-08):
11. Sectors               ← rectangle objects per sector (name = sector key)
12. Arenas                ← rectangle objects per arena (name = "sector:arena")
13. Collision             ← rectangle objects marking non-walkable zones
14. Spawn Points          ← point objects per agent (name = agent name)
```

**Critical:** Phase 12's `TiledMapRenderer.tsx` splits by layer name checking `child.label === 'Foreground L1' || 'Foreground L2'`. The visual layer names must match exactly. [VERIFIED: ARCHITECTURE.md]

### Tiled Object Layer Formats (D-06, D-08, D-09)

**Sector object** (rectangle, `name` = sector key from buildings.json): [VERIFIED: Tiled JSON spec knowledge + analysis]

```json
{
  "id": 1,
  "name": "cafe",
  "type": "",
  "x": 160, "y": 1120,
  "width": 640, "height": 544,
  "properties": [
    {"name": "display_name", "type": "string", "value": "Town Cafe"},
    {"name": "opens", "type": "int", "value": 7},
    {"name": "closes", "type": "int", "value": 22},
    {"name": "purpose", "type": "string", "value": "food"}
  ]
}
```

Tile coordinates extracted by: `x1 = obj["x"] // 32`, `y1 = obj["y"] // 32`, `x2 = (obj["x"] + obj["width"]) // 32`, `y2 = (obj["y"] + obj["height"]) // 32`.

**Arena object** (rectangle, `name` = `"sector:arena"` composite key):

```json
{
  "id": 2,
  "name": "cafe:seating",
  "type": "",
  "x": 160, "y": 1120, "width": 320, "height": 288,
  "properties": []
}
```

**Collision object** (rectangle, marks non-walkable zones):

```json
{
  "id": 3,
  "name": "wall",
  "type": "",
  "x": 160, "y": 1120, "width": 32, "height": 544,
  "properties": []
}
```

**Spawn point object** (point, `name` = agent name):

```json
{
  "id": 4,
  "name": "alice",
  "type": "",
  "x": 384, "y": 1280,
  "point": true
}
```

Tile coordinate: `tile_x = obj["x"] // 32`, `tile_y = obj["y"] // 32`.

### sync_map.py Algorithm

The sync script reads one `.tmj` / `.json` file and writes three output files: [ASSUMED — design derived from D-10, D-11 decisions + existing schema knowledge]

```python
def extract_map(tmj_path: Path) -> tuple[dict, list[dict], dict[str, list[int]]]:
    """Returns (town_json, buildings_json, spawn_points)."""
    tmj = json.loads(tmj_path.read_text())
    width = tmj["width"]   # 140
    height = tmj["height"] # 100

    # 1. Extract object layers by name
    layers_by_name = {l["name"]: l for l in tmj["layers"]}
    sectors_layer = layers_by_name.get("Sectors", {}).get("objects", [])
    arenas_layer = layers_by_name.get("Arenas", {}).get("objects", [])
    collision_layer = layers_by_name.get("Collision", {}).get("objects", [])
    spawns_layer = layers_by_name.get("Spawn Points", {}).get("objects", [])

    # 2. Build tile grid (width x height), default walkable
    tiles = {}  # (x,y) -> dict

    # 3. Mark collision tiles from Collision rectangles
    for obj in collision_layer:
        x1, y1 = obj["x"] // 32, obj["y"] // 32
        x2 = (obj["x"] + obj["width"]) // 32
        y2 = (obj["y"] + obj["height"]) // 32
        for y in range(y1, y2):
            for x in range(x1, x2):
                tiles[(x, y)] = {"coord": [x, y], "collision": True}

    # 4. Assign sector addresses from Sectors rectangles
    # (collision takes precedence — skip if already collision)

    # 5. Assign arena addresses from Arenas rectangles
    # (name is "sector:arena", split on ":" to get [sector, arena])

    # 6. Build buildings.json from sector custom properties (D-11)

    # 7. Extract spawn points
    spawns = {}
    for obj in spawns_layer:
        name = obj["name"]
        spawns[name] = [obj["x"] // 32, obj["y"] // 32]

    # 8. Serialize town_json with size=[height, width]
```

**Border wall handling:** The Maze class's `get_walkable_neighbors` uses `0 < c[0] < width-1` and `0 < c[1] < height-1` — border tiles are excluded from pathfinding regardless of collision flag. The sync script should still mark border tiles as collision to match the existing schema convention. The Collision object layer should include border rectangles, or the sync script adds them programmatically.

### validate_map.py Algorithm

```python
def validate(town_json_path, agents_dir, buildings_path):
    maze = Maze(json.loads(town_json_path.read_text()))
    agents = [json.loads(f.read_text()) for f in agents_dir.glob("*.json")]
    buildings = json.loads(buildings_path.read_text())

    errors = []

    # Check 1: every sector has at least one walkable tile
    for bld in buildings:
        sector = bld["sector"]
        coords = maze.address_tiles.get(f"{maze.world}:{sector}", set())
        walkable = [c for c in coords if not maze.tile_at(c).collision]
        if not walkable:
            errors.append(f"Sector '{sector}' has no walkable tiles")

    # Check 2: every spawn point tile is walkable
    for agent in agents:
        name = agent["name"]
        x, y = agent["coord"]
        if maze.tile_at((x, y)).collision:
            errors.append(f"Agent {name} spawns on collision tile ({x},{y})")

    # Check 3: every arena in agent's spatial tree is BFS-reachable from spawn
    for agent in agents:
        spawn = tuple(agent["coord"])
        tree = agent["spatial"]["tree"].get(maze.world, {})
        for sector, arenas in tree.items():
            sector_coord = maze.resolve_destination(sector)
            if sector_coord is None:
                errors.append(f"Agent {agent['name']}: sector '{sector}' not found")
                continue
            path = maze.find_path(spawn, sector_coord)
            if not path:
                errors.append(f"Agent {agent['name']}: unreachable sector '{sector}' from {spawn}")

    return errors
```

Exits with code 0 on success, 1 on any error. Prints all errors before exiting.

### Map Dimension Change Impact (D-01)

The map expands from 100x100 to 140x100 tiles. All dimension-sensitive code: [VERIFIED: direct code reads]

| File | Current | Required Change |
|------|---------|----------------|
| `backend/data/map/town.json` | `"size": [100, 100]` | `"size": [100, 140]` (height, width) |
| `frontend/src/components/MapCanvas.tsx` | `const MAP_SIZE_PX = 3200` | `const MAP_WIDTH_PX = 4480; const MAP_HEIGHT_PX = 3200` |
| `frontend/src/components/TileMap.tsx` | `const MAP_SIZE = 100; const CANVAS_SIZE = MAP_SIZE * TILE_SIZE` | `MAP_WIDTH = 140; MAP_HEIGHT = 100; CANVAS_W = 4480; CANVAS_H = 3200` |
| `frontend/src/components/MapCanvas.tsx` | Viewport centering uses `MAP_SIZE_PX * FIXED_SCALE` for both axes | Use `MAP_WIDTH_PX * FIXED_SCALE` for X, `MAP_HEIGHT_PX * FIXED_SCALE` for Y |
| `tests/test_world.py` | `town_maze.width == 100` assertion | `town_maze.width == 140` |

The `Maze` class itself needs no changes — it reads width/height from the config dict. The pathfinding constraint `0 < c[0] < self.width - 1` automatically adapts to width=140. [VERIFIED: world.py line 250-254]

### Project Structure for New Files

```
scripts/
├── copy_assets.py              ← existing (Phase 10)
├── convert_sprite_atlas.py     ← existing (Phase 10)
├── sync_map.py                 ← NEW: TMJ -> town.json + buildings.json
└── validate_map.py             ← NEW: BFS reachability checker

frontend/public/assets/tilemap/
├── *.png                       ← existing CuteRPG tilesets (Phase 10)
└── town.tmj                    ← NEW: Tiled export (user delivers, D-13)

backend/data/map/
├── town.json                   ← REGENERATED by sync_map.py
└── buildings.json              ← REGENERATED by sync_map.py

frontend/src/data/
└── town.json                   ← REGENERATED by sync_map.py (static import in TileMap.tsx)

frontend/src/components/
├── MapCanvas.tsx               ← MODIFIED: MAP_SIZE_PX split to width/height
└── TileMap.tsx                 ← MODIFIED: MAP_SIZE split to width/height
```

### Tiled Authoring Guide Deliverable

Claude must produce a written guide for the user covering: [ASSUMED — scope derived from D-13]

1. **Tiled project setup**: Create new map, 140 wide × 100 tall, 32px tiles. Save `.tmx` inside `frontend/public/assets/tilemap/`.
2. **Tileset configuration**: Add all 16 PNGs from `frontend/public/assets/tilemap/` as tilesets with correct relative paths (e.g., `./CuteRPG_Field_B.png`). This prevents Pitfall 2 (broken image paths).
3. **Layer creation in exact order**: Create all 10 visual tile layers + 4 metadata object layers with the exact names listed in D-07/D-08.
4. **Metadata layer visibility**: Set Sectors, Arenas, Collision, and Spawn Points layers to `visible: false` in Tiled before exporting. Prevents Pitfall 8 (colored blocks rendering over the map in Phase 12).
5. **Object naming conventions**: Sectors named by sector key (e.g., `cafe`), Arenas named `sector:arena` (e.g., `cafe:seating`), Spawn Points named by agent name (e.g., `alice`).
6. **Custom properties for sectors (D-11)**: Each sector rectangle needs `display_name` (string), `opens` (int), `closes` (int), `purpose` (string).
7. **Export settings**: File > Export As > `town.tmj`. Enable "Embed tilesets" to keep all tileset data in one file.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| BFS pathfinding in validate_map.py | Custom BFS | `Maze.find_path()` from `backend/simulation/world.py` | Already tested, handles border exclusion, returns empty on unreachable |
| Building metadata schema | Custom parser | The existing `Building` dataclass + `load_buildings()` | Exact schema is already defined; sync script must match it |
| Collision grid | New data structure | Set collision on tile entries in the sparse list | `Maze.__init__` already builds a full grid from the sparse list; just emit the right JSON |
| Tiled JSON parsing | Custom recursive parser | Flat dict comprehension on `tmj["layers"]` | The TMJ format is flat at the layers level; no recursion needed for this use case |

---

## Common Pitfalls

### Pitfall 1: Tiled Pixel Coordinates vs Tile Coordinates

**What goes wrong:** Tiled stores object positions in pixel coordinates (`x`, `y`, `width`, `height` in pixels). Dividing by 32 gives tile coordinates. If the division is applied inconsistently (e.g., only to `x`/`y` but not to `x + width`), sector rectangles get incorrect tile bounds.

**How to avoid:** Always compute all four tile bounds before filling the grid:
```python
x1, y1 = obj["x"] // 32, obj["y"] // 32
x2, y2 = (obj["x"] + obj["width"]) // 32, (obj["y"] + obj["height"]) // 32
for ty in range(y1, y2):
    for tx in range(x1, x2):
        ...
```

**Warning signs:** Sectors in town.json that are shifted 1 tile from what the visual map shows.

### Pitfall 2: Tiled Object Coordinates Are Float in Some Exports

**What goes wrong:** Some Tiled versions export object `x`, `y`, `width`, `height` as floats (e.g., `160.0` instead of `160`). Integer division `160.0 // 32` returns `5.0` (a float), which fails as a dict key or list index.

**How to avoid:** Always convert to int before division:
```python
x1 = int(obj["x"]) // 32
```

**Warning signs:** `TypeError: list indices must be integers or slices, not float` in sync_map.py.

### Pitfall 3: town.json size Field Is [height, width], Not [width, height]

**What goes wrong:** Maze reads `self.height, self.width = config["size"]` — height is first. If the sync script writes `"size": [width, height]` = `[140, 100]`, Maze sees width=100 and height=140, causing all coordinates > 100 in the X axis to be out of bounds.

**How to avoid:** Always write `"size": [height, width]` = `[100, 140]` in sync_map.py output. [VERIFIED: world.py line 184]

**Warning signs:** `IndexError: Coordinate (x, y) is out of bounds (width=100, height=140)` at startup.

### Pitfall 4: Object Layer vs Tile Layer — Metadata Layer Type Check

**What goes wrong:** The sync script iterates `tmj["layers"]` and assumes all named layers are object layers (`type: "objectgroup"`). If the user accidentally creates a metadata layer as a tile layer (`type: "tilelayer"`), `.get("objects", [])` returns an empty list silently — all sectors are missing from town.json with no error.

**How to avoid:** Add an assertion in sync_map.py:
```python
for required in ["Sectors", "Arenas", "Collision", "Spawn Points"]:
    layer = layers_by_name.get(required)
    if layer is None:
        raise ValueError(f"Missing required layer: '{required}'")
    if layer["type"] != "objectgroup":
        raise ValueError(f"Layer '{required}' must be objectgroup, got {layer['type']}")
```

**Warning signs:** `validate_map.py` reports all sectors unreachable, but sync_map.py exits with 0.

### Pitfall 5: Arena Name Convention Must Use Colon Separator

**What goes wrong:** Arena object names in Tiled are `"cafe:seating"`. The sync script splits on `":"` to get `[sector, arena]`. If the user names an arena `"cafe-seating"` (dash) or `"cafe/seating"` (slash), the split produces one element and the arena is stored under the sector level incorrectly.

**How to avoid:** sync_map.py validates arena names contain exactly one `":"`. Document the convention clearly in the authoring guide.

### Pitfall 6: Non-Visual Metadata Layers Must Have visible: false Before Tiled Export

**What goes wrong:** If the user forgets to set Sectors/Arenas/Collision/Spawn Points to `visible: false` in Tiled, pixi-tiledmap in Phase 12 will attempt to render them. These layers have no tiles (they are object layers), so the renderer produces nothing visible — but this may confuse debugging. More critically, if the user accidentally makes a visual layer invisible, it disappears from the rendered map.

**How to avoid:** The authoring guide must include this step explicitly. The sync_map.py script can check and warn but cannot fix it.

### Pitfall 7: Homes Without Workplaces (Henry) Break Spatial Tree Validation

**What goes wrong:** `henry.json` has no `workplace` key in `spatial.address`. `validate_map.py` must not assume all agents have a `workplace` key. [VERIFIED: henry.json read]

**How to avoid:**
```python
living_area = agent["spatial"]["address"].get("living_area")
workplace = agent["spatial"]["address"].get("workplace")  # May be None
```

### Pitfall 8: Collision Priority — Arena Addresses Must Not Overwrite Collision Tiles

**What goes wrong:** The sync script processes Sectors, then Arenas, then marks collisions. If collision objects are processed LAST, they correctly overwrite address-only tiles. But if arenas are processed after collisions, arena interior tiles that overlap with wall rectangles get incorrectly converted to walkable arena tiles.

**How to avoid:** Process in this order: (1) mark all collision rectangles, (2) assign sector addresses (skip if already collision), (3) assign arena addresses (skip if already collision). This matches the reference `map_generator.py` pattern which uses `if coord in tiles and tiles[coord].get("collision"): continue`. [VERIFIED: map_generator.py]

### Pitfall 9: Frontend TileMap.tsx Uses CANVAS_SIZE for Both Axes

**What goes wrong:** `TileMap.tsx` defines `const CANVAS_SIZE = MAP_SIZE * TILE_SIZE` and uses it for both X and Y bounds. With 140x100, `CANVAS_SIZE = 100 * 32 = 3200` — the right 40 tiles (x=100 to x=139) are never rendered. The map visually cuts off.

**How to avoid:**
```typescript
const MAP_WIDTH = 140;
const MAP_HEIGHT = 100;
const CANVAS_W = MAP_WIDTH * TILE_SIZE;  // 4480
const CANVAS_H = MAP_HEIGHT * TILE_SIZE; // 3200
```
Use `CANVAS_W` for all X-axis computations and `CANVAS_H` for Y-axis. [VERIFIED: TileMap.tsx lines 30, 134]

---

## Code Examples

### sync_map.py: Object Layer Extraction Pattern

```python
# Source: direct codebase + Tiled JSON spec analysis
TILE_SIZE = 32
FLIP_MASK = ~(0x80000000 | 0x40000000 | 0x20000000) & 0xFFFFFFFF

def _obj_to_tile_bounds(obj: dict) -> tuple[int, int, int, int]:
    """Convert Tiled pixel-space object to tile-space bounding box."""
    x1 = int(obj["x"]) // TILE_SIZE
    y1 = int(obj["y"]) // TILE_SIZE
    x2 = (int(obj["x"]) + int(obj["width"])) // TILE_SIZE
    y2 = (int(obj["y"]) + int(obj["height"])) // TILE_SIZE
    return x1, y1, x2, y2

def _get_property(obj: dict, name: str, default=None):
    """Get a named custom property from a Tiled object."""
    for prop in obj.get("properties", []):
        if prop["name"] == name:
            return prop["value"]
    return default
```

### sync_map.py: buildings.json Generation (D-11)

```python
# Source: buildings.json schema verified from direct file read
def extract_buildings(sector_objects: list) -> list[dict]:
    buildings = []
    for obj in sector_objects:
        buildings.append({
            "name": _get_property(obj, "display_name", obj["name"]),
            "sector": obj["name"],
            "opens": _get_property(obj, "opens", 0),
            "closes": _get_property(obj, "closes", 24),
            "purpose": _get_property(obj, "purpose", "general"),
        })
    return buildings
```

### MapCanvas.tsx: Rectangular Map Dimensions

```typescript
// Source: MapCanvas.tsx direct read + dimension analysis
// Replace:
// const MAP_SIZE_PX = 3200;
// With:
const MAP_WIDTH_PX = 4480;  // 140 tiles * 32px
const MAP_HEIGHT_PX = 3200; // 100 tiles * 32px

// In centerMap():
setOffsetX((el.clientWidth - MAP_WIDTH_PX * FIXED_SCALE) / 2);
setOffsetY((el.clientHeight - MAP_HEIGHT_PX * FIXED_SCALE) / 2);
```

### TileMap.tsx: Non-Square Canvas Constants

```typescript
// Source: TileMap.tsx direct read
const TILE_SIZE = 32;
const MAP_WIDTH = 140;
const MAP_HEIGHT = 100;
const CANVAS_W = MAP_WIDTH * TILE_SIZE;  // 4480px
const CANVAS_H = MAP_HEIGHT * TILE_SIZE; // 3200px
// Use CANVAS_W for x-axis rect bounds, CANVAS_H for y-axis
```

### validate_map.py: BFS Reachability Check

```python
# Source: world.py Maze class + agent JSON schema analysis
import sys
import json
from pathlib import Path
from backend.simulation.world import Maze

def run_validation(town_json: Path, agents_dir: Path, buildings: Path) -> list[str]:
    maze = Maze(json.loads(town_json.read_text()))
    errors = []

    for agent_path in agents_dir.glob("*.json"):
        agent = json.loads(agent_path.read_text())
        spawn = tuple(agent["coord"])

        # Spawn tile must be walkable
        if maze.tile_at(spawn).collision:
            errors.append(f"{agent['name']}: spawn tile {spawn} is collision")
            continue

        # Every sector in spatial tree must be BFS-reachable from spawn
        tree = agent["spatial"]["tree"].get(maze.world, {})
        for sector in tree:
            dest = maze.resolve_destination(sector)
            if dest is None:
                errors.append(f"{agent['name']}: sector '{sector}' not in map")
                continue
            path = maze.find_path(spawn, dest)
            if not path:
                errors.append(f"{agent['name']}: '{sector}' unreachable from {spawn}")

    return errors

if __name__ == "__main__":
    errors = run_validation(...)
    for e in errors:
        print(f"ERROR: {e}")
    sys.exit(1 if errors else 0)
```

---

## Runtime State Inventory

This phase replaces `backend/data/map/town.json` and `backend/data/map/buildings.json`. These are files read at startup by the backend — no persistent runtime state beyond filesystem files.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | `backend/data/map/town.json` — 4845 tile entries, 100x100 | Regenerated by sync_map.py; old file replaced |
| Stored data | `backend/data/map/buildings.json` — 16 building entries | Regenerated by sync_map.py from Tiled custom properties |
| Stored data | `frontend/src/data/town.json` — static copy for TileMap.tsx | Regenerated by sync_map.py |
| Live service config | None — backend reads files at startup, no cached DB state | No action |
| OS-registered state | None | None |
| Secrets/env vars | None | None |
| Build artifacts | `backend/simulation/map_generator.py` — now obsolete after sync_map.py | Keep file but mark as deprecated; do not delete (tests reference `generate_town_map()`) |

**Critical note on map_generator.py:** `tests/test_world.py` imports `from backend.simulation.map_generator import generate_town_map` and tests `TestTownJsonStructure.test_generate_town_map_structure`. This test will need updating after Phase 11 — the test should eventually validate `sync_map.py` output instead. For Phase 11, the test can be updated to test against the new generated `town.json` dimensions (140x100). [VERIFIED: test_world.py direct read]

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (existing) |
| Config file | `pyproject.toml` (project root) |
| Quick run command | `pytest tests/test_world.py -x -q` |
| Full suite command | `pytest tests/ -x -q` |
| Frontend tests | `npm run test --prefix frontend` (vitest) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TOWN-01 | Town TMJ has all 10 visual layers + 4 metadata object layers | unit (sync_map.py) | `pytest tests/test_sync_map.py -x -q` | ❌ Wave 0 |
| TOWN-02 | Generated town.json has size=[100,140], all 16 sectors, correct arena structure | unit (sync_map.py) | `pytest tests/test_sync_map.py -x -q` | ❌ Wave 0 |
| TOWN-03 | Collision tiles from Tiled object layer match walls in generated town.json | unit (sync_map.py) | `pytest tests/test_sync_map.py -x -q` | ❌ Wave 0 |
| TOWN-04 | All agent spawns walkable; all sectors in spatial tree BFS-reachable | unit (validate_map.py) | `python scripts/validate_map.py` | ❌ Wave 0 |
| TOWN-02 (existing) | town.json loads cleanly into Maze, width=140, height=100 | unit (existing) | `pytest tests/test_world.py -x -q` | ✅ exists (needs update) |

### Sampling Rate

- **Per task commit:** `pytest tests/test_world.py tests/test_sync_map.py -x -q`
- **Per wave merge:** `pytest tests/ -x -q`
- **Phase gate:** Full suite green + `python scripts/validate_map.py` exits 0 before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_sync_map.py` — covers TOWN-01, TOWN-02, TOWN-03 with a minimal fixture TMJ
- [ ] `tests/test_world.py` — update `test_town_json_size` to assert `width == 140, height == 100`
- [ ] `tests/conftest.py` — add `minimal_tmj` fixture (a small 10x10 TMJ with all 4 object layers)

---

## Security Domain

This phase is file I/O and data transformation — no network exposure, no user input beyond local file reads. `security_enforcement` is not explicitly set to false in config.json (key absent), so the section is included.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | — |
| V3 Session Management | No | — |
| V4 Access Control | No | — |
| V5 Input Validation | Yes (TMJ file parsing) | Validate required layer names and types; fail loudly on missing/malformed layers |
| V6 Cryptography | No | — |

### Known Threat Patterns for File Parsing

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed TMJ crashes sync script | Denial of service (local) | Wrap json.loads() in try/except; validate required keys before processing |
| Path traversal in tileset image refs | Tampering | sync_map.py does not copy files; image paths remain in TMJ for pixi-tiledmap to resolve |
| Oversized TMJ (e.g., 140x100 with data arrays) | DoS | 140x100 = 14,000 tiles × 17 layers = reasonable; no streaming needed |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | sync_map.py, validate_map.py | ✓ | `.venv` present | — |
| Tiled Map Editor | D-13: user authors map | UNKNOWN (user machine) | User installs | No fallback — human dependency |
| CuteRPG tilesets | Tiled authoring, pixi-tiledmap | ✓ | 16 PNGs in `frontend/public/assets/tilemap/` | — |
| `pytest` | test_sync_map.py | ✓ | Present in `.venv` | — |

**Missing dependencies with no fallback:**
- Tiled Map Editor on user's machine — without this, the map cannot be authored (D-13). Phase 11 has a hard pause at the map delivery gate.

**Missing dependencies with fallback:**
- None.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | TMJ format (`type: "objectgroup"` for object layers, `objects` array with `x/y/width/height` fields) matches standard Tiled 1.8+ export | Architecture Patterns | sync_map.py fails to parse object layers; need to inspect actual TMJ |
| A2 | Tiled exports `point: true` for point objects (spawn points) with no `width/height` fields | Architecture Patterns | Spawn point parsing logic breaks |
| A3 | `home-isabel` and `home-james` sectors in current town.json are legacy (no agent JSON files) and can be dropped in the new map | Architecture Patterns | If kept, they need to appear in Tiled sectors layer and have buildings.json entries |
| A4 | `sync_map.py` writes `frontend/src/data/town.json` in addition to `backend/data/map/town.json` for backward compatibility with Phase 12 | Architecture Patterns | TileMap.tsx static import breaks during Phase 12 transition |

---

## Open Questions

1. **Should home-isabel and home-james exist in the new map?**
   - What we know: They exist in current town.json and buildings.json but have no corresponding agent JSON files. Only 8 agents are active (alice through henry).
   - What's unclear: Are they reserved for future agents, or legacy from the programmatic generator?
   - Recommendation: Include them in the new map if space allows (D-03 says "up to 10 homes"). Exclude from validate_map.py BFS checks since no agent JSON files reference them.

2. **Does the Collision object layer replace the Wall tile layer for collision purposes, or does the sync script also parse the Wall tile layer GIDs?**
   - What we know: D-08 specifies a Collision object layer. The Wall tile layer (D-07) is visual.
   - What's unclear: In the reference, collision comes from a dedicated collision tile layer (blocks GIDs). For Agent Town with object layers, the Collision rectangles encode walkability.
   - Recommendation: Collision object layer is the authoritative source for the sync script. The Wall visual layer is for rendering only. Document this clearly in the authoring guide — walls painted on the Wall layer must ALSO have matching Collision rectangles to block pathfinding.

3. **Does sync_map.py need to also update agent `coord` fields from the Tiled Spawn Points layer?**
   - What we know: D-09 defines spawn points in Tiled. D-10 says sync script extracts spawn points.
   - What's unclear: Should the script update `backend/data/agents/{name}.json` coord fields automatically, or just verify them?
   - Recommendation: Write spawn points to a separate `backend/data/map/spawn_points.json` file AND update each agent's `coord` field in-place. This keeps agent JSON files consistent with the Tiled map.

---

## Sources

### Primary (HIGH confidence)
- `backend/simulation/world.py` — Maze class, size field ordering, BFS logic [VERIFIED: direct read]
- `backend/data/map/town.json` — existing schema, sector/arena naming conventions [VERIFIED: direct read]
- `backend/data/map/buildings.json` — existing buildings schema [VERIFIED: direct read]
- `backend/data/agents/*.json` — all 8 agent files, spatial tree structure, coord field [VERIFIED: direct reads]
- `backend/simulation/map_generator.py` — tile priority pattern (collision > address) [VERIFIED: direct read]
- `frontend/src/components/TileMap.tsx` — MAP_SIZE constant, static JSON import [VERIFIED: direct read]
- `frontend/src/components/MapCanvas.tsx` — MAP_SIZE_PX = 3200 constant [VERIFIED: direct read]
- `tests/test_world.py` — existing test patterns, test assertions against Maze [VERIFIED: direct read]
- `GenerativeAgentsCN/tilemap.json` — layer names, count, type, visibility [VERIFIED: python parse]
- `.planning/research/ARCHITECTURE.md` — layer split by label convention, pixi-tiledmap behavior [VERIFIED: direct read]
- `.planning/research/PITFALLS.md` — GID flip mask, non-visual layer rendering, scaleMode order [VERIFIED: direct read]

### Secondary (MEDIUM confidence)
- Tiled JSON object layer format (x, y, width, height, properties array) — derived from Tiled 1.x documentation and standard JSON export behavior

### Tertiary (LOW confidence)
- TMJ extension vs JSON for Tiled 1.8+ [ASSUMED: based on Tiled documentation knowledge]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all tools verified present
- Architecture: HIGH — schemas verified by direct file reads; sync algorithm derived from verified schemas
- Pitfalls: HIGH — drawn from direct code inspection and reference map analysis
- Tiled object layer format: MEDIUM — derived from Tiled spec knowledge, not live-verified against an actual export

**Research date:** 2026-04-12
**Valid until:** 2026-06-01 (stable tooling; Tiled format changes rarely)
