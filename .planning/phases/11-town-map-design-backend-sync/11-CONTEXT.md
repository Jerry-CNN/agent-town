# Phase 11: Town Map Design & Backend Sync - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Design a new Agent Town map in the Tiled editor (140x100, 32px tiles) with 7 thematic buildings and full interiors, export it as TMJ, and build a Python sync script that regenerates backend town.json, buildings.json, spawn points, and frontend map data from the Tiled export. Includes a separate reachability validation script.

</domain>

<decisions>
## Implementation Decisions

### Map Dimensions & Layout
- **D-01:** Expand map from 100x100 to 140x100 tiles (4480x3200px). Requires updating MAP_SIZE_PX in MapCanvas.tsx and related viewport logic.
- **D-02:** Central road layout style — main road through center, commercial buildings (stock exchange, wedding hall, cafe, office, shop) along it, park in a corner or center, homes on outskirts.
- **D-03:** Claude's discretion on number of homes — at least 8 (one per active agent), up to 10 if space allows.

### Building Interiors
- **D-04:** Reference-level detail for all building interiors — every room has furniture, decorations, floor patterns. Each building is a mini-scene.
- **D-05:** Source new tileset assets for specialized buildings (stock exchange, wedding hall) where CuteRPG tiles are too generic. User will source these when gaps are flagged. Phase may pause for asset sourcing.

### Tiled Layer Structure
- **D-06:** Use Tiled object layers (not tile properties) for sector/arena metadata. Rectangles with name properties for each zone. Easier to author and extract.
- **D-07:** Match reference visual layer count (10 visual layers): Bottom Ground, Exterior Ground, Exterior Decoration L1/L2, Interior Ground, Wall, Interior Furniture L1/L2, Foreground L1/L2.
- **D-08:** Add metadata object layers: Sectors, Arenas, Collision, Spawn Points.
- **D-09:** Agent spawn points encoded as point objects in a Tiled "Spawn Points" object layer, named per agent (alice, bob, etc.).

### Backend Sync Script
- **D-10:** Python sync script in `scripts/` extracts: tile grid + sector assignments, building metadata (names, operating hours, purpose tags), spawn points, collision data. Regenerates both backend and frontend map data.
- **D-11:** All building metadata (operating hours, purpose tags) moves INTO Tiled as custom object properties. Tiled becomes single source of truth for everything building-related. buildings.json is generated, not hand-maintained.
- **D-12:** Separate `scripts/validate_map.py` runs BFS reachability checks from each spawn point to every sector. Can be run independently after sync.

### Map Authoring Workflow
- **D-13:** User designs the map manually in the Tiled desktop app. Claude provides layer template, tileset configuration, sector naming conventions, and object layer setup instructions. This is a human dependency that blocks downstream work.

### Claude's Discretion
- Number of homes (D-03, at least 8)
- Specific building placement within the central-road layout
- Path/terrain details (grass, dirt paths, trees, fences)
- Agent-to-spawn-point assignment (which agent starts where)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Current Map Data
- `backend/data/map/town.json` — Current 100x100 tile grid data (to be replaced)
- `backend/data/map/buildings.json` — Current building metadata with operating hours (to be replaced by Tiled extraction)
- `frontend/src/data/town.json` — Current frontend map copy (to be replaced)

### Agent Configuration
- `backend/data/agents/*.json` — 8 agent configs with home/workplace references

### Reference Implementation
- `~/projects/GenerativeAgentsCN/generative_agents/frontend/static/assets/village/tilemap/tilemap.json` — Reference Tiled map (3.7MB, 140x100, 17 layers)
- `~/projects/GenerativeAgentsCN/generative_agents/frontend/static/assets/village/maze.json` — Reference spatial/navigation data

### Phase 10 Assets
- `frontend/public/assets/tilemap/` — 16 CuteRPG tileset PNGs (ported in Phase 10)
- `frontend/public/assets/agents/` — 25 agent sprite directories (ported in Phase 10)

### Research
- `.planning/research/ARCHITECTURE.md` — Integration architecture, build order
- `.planning/research/PITFALLS.md` — GID flip flags, layer visibility, map dimension changes

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/copy_assets.py` and `scripts/convert_sprite_atlas.py` — Established pattern for Python scripts in `scripts/` directory
- `backend/data/map/` — Existing map data directory structure

### Established Patterns
- Backend reads town.json at startup for pathfinding (BFS on tile grid)
- Buildings loaded from buildings.json with sector/arena mapping
- Frontend reads town.json for TileMap rendering (sector colors, collision flags)
- MAP_SIZE_PX = 3200 in MapCanvas.tsx — must become MAP_WIDTH_PX = 4480, MAP_HEIGHT_PX = 3200

### Integration Points
- `backend/engine.py` — Reads town.json for agent pathfinding, building lookup
- `frontend/src/components/TileMap.tsx` — Reads town.json for tile rendering (will be replaced in Phase 12)
- `frontend/src/components/MapCanvas.tsx` — MAP_SIZE_PX constant, viewport calculations

</code_context>

<specifics>
## Specific Ideas

- User wants it to "look at least like the original Agent Town" — the reference screenshot is the visual target
- Central road with commercial buildings along it, park area, homes on outskirts
- Reference-level interior detail — every room should feel like a mini-scene
- New tileset assets will be sourced for stock exchange and wedding hall if CuteRPG tiles are insufficient
- Tiled is the single source of truth — buildings.json, town.json, spawn points all generated from it

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 11-town-map-design-backend-sync*
*Context gathered: 2026-04-12*
