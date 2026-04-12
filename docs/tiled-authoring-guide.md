# Tiled Authoring Guide — Agent Town Map

This guide walks you through creating the Agent Town map in the Tiled Map Editor,
exporting it, and syncing it into the backend and frontend.

---

## 1. Project Setup

1. Download and install [Tiled Map Editor](https://www.mapeditor.org/) (free, open source).
2. Open Tiled and choose **File > New > New Map**.
3. Set these map properties:
   - **Orientation:** Orthogonal
   - **Tile layer format:** CSV
   - **Tile render order:** Right Down
   - **Map size:** Fixed — **140 tiles wide x 100 tiles tall**
   - **Tile size:** 32 x 32 pixels
4. Click **OK**.
5. Save the working file as:
   ```
   frontend/public/assets/tilemap/town.tmx
   ```
   (The `.tmx` is the editable source file. You will export `.tmj` separately in step 8.)

---

## 2. Add Tilesets

For each of the 16 CuteRPG PNG files below, add a tileset via **Map > New Tileset**.

**Important: Check "Embed in map"** when adding each tileset. This keeps all tileset
data inside the exported `.tmj` file, avoiding broken tileset path references if the
file is moved.

Tile size for all tilesets: **32 x 32 pixels**.

| Tileset Filename              | Purpose                        |
|-------------------------------|--------------------------------|
| `CuteRPG_Desert_B.png`        | Desert terrain                 |
| `CuteRPG_Desert_C.png`        | Desert decoration              |
| `CuteRPG_Field_B.png`         | Field terrain                  |
| `CuteRPG_Field_C.png`         | Field decoration               |
| `CuteRPG_Forest_B.png`        | Forest terrain                 |
| `CuteRPG_Forest_C.png`        | Forest decoration              |
| `CuteRPG_Harbor_C.png`        | Harbor / waterfront            |
| `CuteRPG_Mountains_B.png`     | Mountain terrain               |
| `CuteRPG_Village_B.png`       | Village buildings / paths      |
| `Room_Builder_32x32.png`      | Interior room builder          |
| `blocks_1.png`                | Block tiles                    |
| `interiors_pt1.png`           | Interior furniture part 1      |
| `interiors_pt2.png`           | Interior furniture part 2      |
| `interiors_pt3.png`           | Interior furniture part 3      |
| `interiors_pt4.png`           | Interior furniture part 4      |
| `interiors_pt5.png`           | Interior furniture part 5      |

All 16 PNG files are already in `frontend/public/assets/tilemap/`.

---

## 3. Create Layers (EXACT ORDER REQUIRED)

Create all 14 layers in Tiled's Layers panel. The **order and names must match exactly**
(case-sensitive) for the pixi-tiledmap renderer to work correctly in Phase 12.

### Visual Tile Layers (type: Tile Layer)

Create these 10 layers in order (bottom to top in Tiled's layer stack):

| # | Layer Name                | Type       | Purpose                              |
|---|---------------------------|------------|--------------------------------------|
| 1 | Bottom Ground             | Tile Layer | Base ground texture (grass, dirt)    |
| 2 | Exterior Ground           | Tile Layer | Paths, roads, plazas                 |
| 3 | Exterior Decoration L1    | Tile Layer | Exterior decor: bushes, benches      |
| 4 | Exterior Decoration L2    | Tile Layer | Exterior decor: trees, signs         |
| 5 | Interior Ground           | Tile Layer | Indoor floor tiles                   |
| 6 | Wall                      | Tile Layer | Building walls (visual only)         |
| 7 | Interior Furniture L1     | Tile Layer | Furniture below agent height         |
| 8 | Interior Furniture L2     | Tile Layer | Furniture at/above agent height      |
| 9 | Foreground L1             | Tile Layer | Foreground elements (tree canopy)    |
| 10 | Foreground L2            | Tile Layer | Upper foreground (rooftop details)   |

### Metadata Object Layers (type: Object Layer)

Create these 4 layers **above** the visual layers. Set **visible: false** for each.

> **Why visible: false?** The pixi-tiledmap renderer displays ALL Tiled layers,
> including metadata layers. Setting them invisible prevents colored blocks from
> rendering over the visual map in the browser.

| # | Layer Name   | Type         | visible |
|---|--------------|--------------|---------|
| 11 | Sectors     | Object Layer | false   |
| 12 | Arenas      | Object Layer | false   |
| 13 | Collision   | Object Layer | false   |
| 14 | Spawn Points | Object Layer | false  |

---

## 4. Sector Objects (in Sectors layer)

Sectors define the major zones of the town. Each sector is a **rectangle** in the
Sectors layer.

### Steps

1. Select the **Sectors** layer.
2. Choose the **Rectangle tool** (R key).
3. Draw a rectangle covering the full area of each building or zone.
4. In the object Properties panel, set:
   - **Name:** The sector key (exact value from the table below)
5. Click **Add Property** for each of the four custom properties:

| Property Name | Type   | Description                                 |
|---------------|--------|---------------------------------------------|
| `display_name`| string | Human-readable name shown in UI             |
| `opens`       | int    | Opening hour (0-24), e.g. `7`              |
| `closes`      | int    | Closing hour (0-24), e.g. `22`             |
| `purpose`     | string | One of: food, finance, social, leisure, work, retail, residential |

### Reference: All 14 Sectors

| Sector Key       | display_name       | opens | closes | purpose     |
|------------------|--------------------|-------|--------|-------------|
| `cafe`           | Town Cafe          | 7     | 22     | food        |
| `stock-exchange` | Stock Exchange     | 9     | 17     | finance     |
| `wedding-hall`   | Wedding Hall       | 10    | 23     | social      |
| `park`           | Central Park       | 0     | 24     | leisure     |
| `office`         | Town Office        | 8     | 18     | work        |
| `shop`           | General Shop       | 8     | 20     | retail      |
| `home-alice`     | Alice's Home       | 0     | 24     | residential |
| `home-bob`       | Bob's Home         | 0     | 24     | residential |
| `home-carla`     | Carla's Home       | 0     | 24     | residential |
| `home-david`     | David's Home       | 0     | 24     | residential |
| `home-emma`      | Emma's Home        | 0     | 24     | residential |
| `home-frank`     | Frank's Home       | 0     | 24     | residential |
| `home-grace`     | Grace's Home       | 0     | 24     | residential |
| `home-henry`     | Henry's Home       | 0     | 24     | residential |

**14 sectors total: 6 commercial + 8 homes (one per agent).**

> Do NOT add home-isabel or home-james. There are no agent config files for
> Isabel or James. Those were legacy sectors from an earlier map design.

---

## 5. Arena Objects (in Arenas layer)

Arenas are sub-zones within each sector (e.g., the seating area inside the cafe).
Each arena is a **rectangle** in the Arenas layer.

### Naming Format

Arena names **must use the colon separator format**: `sector:arena`

Example: `cafe:seating` (not `cafe-seating` or `cafe / seating`).

The `sync_map.py` script validates this — it will raise an error if any arena
name is missing the colon.

### All Required Arenas (from agent spatial trees)

Draw a rectangle for each of these arena names:

**cafe**
- `cafe:seating`
- `cafe:counter`
- `cafe:kitchen`

**stock-exchange**
- `stock-exchange:trading-floor`
- `stock-exchange:clerk-desk`

**wedding-hall**
- `wedding-hall:hall`
- `wedding-hall:dressing-room`
- `wedding-hall:foyer`

**park**
- `park:bench-area`
- `park:garden`
- `park:pond`

**office**
- `office:open-plan`
- `office:meeting-room`

**shop**
- `shop:floor`
- `shop:counter`
- `shop:stockroom`

**home-alice**
- `home-alice:bedroom`
- `home-alice:living-room`
- `home-alice:kitchen`

**home-bob**
- `home-bob:bedroom`
- `home-bob:living-room`

**home-carla**
- `home-carla:bedroom`
- `home-carla:living-room`

**home-david**
- `home-david:bedroom`
- `home-david:living-room`

**home-emma**
- `home-emma:bedroom`
- `home-emma:living-room`
- `home-emma:kitchen`

**home-frank**
- `home-frank:bedroom`
- `home-frank:living-room`

**home-grace**
- `home-grace:bedroom`
- `home-grace:living-room`

**home-henry**
- `home-henry:bedroom`
- `home-henry:living-room`
- `home-henry:kitchen`

> Arenas must be fully contained within their parent sector rectangle. Tiles
> get arena addresses only if they are inside an arena rectangle; tiles inside
> a sector rectangle but outside any arena rectangle receive only the sector
> address.

---

## 6. Collision Objects (in Collision layer)

Collision rectangles mark non-walkable areas. The BFS pathfinder uses this data —
painting walls on the **Wall** visual layer does NOT block pathfinding.

**Every non-walkable tile must have a matching Collision rectangle.**

### Steps

1. Select the **Collision** layer.
2. Draw rectangles over:
   - Building walls (the thick outer walls of each building)
   - Water, ponds, and impassable terrain
   - Dense trees and obstacles
   - Map border (see border rectangles below)
3. Use **View > Snap to Grid** (32px) for clean tile alignment.

### Required Border Rectangles

Draw these four rectangles to wall off the map edges:

| Name          | Pixel X | Pixel Y | Width (px) | Height (px) |
|---------------|---------|---------|------------|-------------|
| border-top    | 0       | 0       | 4480       | 32          |
| border-bottom | 0       | 3168    | 4480       | 32          |
| border-left   | 0       | 0       | 32         | 3200        |
| border-right  | 4448    | 0       | 32         | 3200        |

(Map is 140 tiles × 100 tiles × 32px/tile = 4480 × 3200 pixels total.)

---

## 7. Spawn Points (in Spawn Points layer)

Spawn points set each agent's starting position when the simulation begins.

### Steps

1. Select the **Spawn Points** layer.
2. Choose the **Point tool** (from the Insert menu or toolbar).
3. Place one point inside each agent's home sector, on a **walkable tile**
   (not inside a Collision rectangle).
4. Set the point **Name** to the agent's lowercase name.

### All 8 Agents

| Agent Name | Sector       |
|------------|-------------|
| `alice`    | home-alice  |
| `bob`      | home-bob    |
| `carla`    | home-carla  |
| `david`    | home-david  |
| `emma`     | home-emma   |
| `frank`    | home-frank  |
| `grace`    | home-grace  |
| `henry`    | home-henry  |

> Points must land on a walkable tile. Avoid placing them directly on a wall
> pixel — use the center of a room tile for safety.

---

## 8. Export

1. **File > Export As**
2. Set the filename to:
   ```
   frontend/public/assets/tilemap/town.tmj
   ```
3. In the export dialog:
   - **Tile Layer Format:** CSV
   - **Embed tilesets:** YES (tilesets should already be embedded from step 2 —
     this keeps all data in one file and avoids broken tileset path references)
4. Click **Export**.

> Keep `town.tmx` as your working file (re-edit and re-export as needed).
> The `.tmj` is the runtime file consumed by the sync script and the browser.

---

## 9. Verify

After exporting, run the sync script to convert the TMJ into backend JSON files:

```bash
python scripts/sync_map.py --tmj frontend/public/assets/tilemap/town.tmj
```

This writes:
- `backend/data/map/town.json`
- `backend/data/map/buildings.json`
- `backend/data/map/spawn_points.json`
- `frontend/src/data/town.json`

Then run the map validator:

```bash
python scripts/validate_map.py
```

Fix any errors reported by either script, re-export from Tiled, and run both
scripts again until they both exit cleanly.

### Dry-run mode (validate without writing)

```bash
python scripts/sync_map.py --tmj frontend/public/assets/tilemap/town.tmj --dry-run
```

This parses and validates the TMJ and prints a summary of sectors, buildings,
spawn points, and warnings without writing any output files.

---

## Common Mistakes

| Mistake | How to Avoid |
|---------|-------------|
| Arena name has no colon | Name must be `sector:arena`, e.g. `cafe:seating` |
| Collision rectangle not snapped to grid | Enable View > Snap to Grid at 32px |
| Spawn point on a collision tile | Place spawn points in room centers, away from walls |
| Metadata layers are visible | Set Sectors, Arenas, Collision, Spawn Points to visible: false before exporting |
| Tilesets not embedded | Check "Embed in map" when adding each tileset |
| Wrong map size | Map must be 140 wide x 100 tall, not 100x140 |
