# Phase 8: Visual & Building Behavior - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the map visually clear (wall outlines, readable text) and behaviorally correct (buildings close, agents respect hours). This is a programmatic improvement phase — the full pixel-art tileset overhaul is deferred to a separate milestone (v1.3).

</domain>

<decisions>
## Implementation Decisions

### Wall Rendering
- **D-01:** Building walls rendered as 3-4px dark stroke outlines around each sector's bounding box using PixiJS v8 `g.stroke()` after `g.fill()`. Uses existing TileMap.tsx draw pattern.
- **D-02:** Claude decides the exact stroke color and width for best contrast against sector fill colors.

### Map Collision Data
- **D-03:** `map_generator.py` auto-generates wall collision tiles as the outer perimeter ring of each sector bounding box. Each building gets 1-2 designated doorway gaps (non-collision tiles on the perimeter) for entry/exit.
- **D-04:** Doorway placement is automatic — one gap per sector placed at the tile closest to the nearest road/path tile.

### Text Readability
- **D-05:** Agent labels get semi-transparent dark background pills (rounded rect) behind white text. Always readable regardless of underlying map color.
- **D-06:** Font sizes increased: agent name 20px, activity text 16px, initial letter 16px. Sector labels increased to 28px.
- **D-07:** Activity text truncated with ellipsis if longer than ~25 characters on the map label. Full text visible in inspector panel.

### Operating Hours Behavior
- **D-08:** When an agent's LLM decide call fires, the list of available destinations in the prompt context excludes closed buildings. The agent never sees closed buildings as options.
- **D-09:** If an agent is inside a building when it closes, the agent immediately interrupts its current activity and triggers a new decide call to pick an open destination.
- **D-10:** Simulation time is tracked (hour of day) and compared against each Building's `opens`/`closes` fields to determine open/closed status.

### Pixel-Art Overhaul (DEFERRED)
- **D-11:** Full Stardew Valley / pixel-art tileset rendering is deferred to milestone v1.3. Phase 8 uses the existing programmatic approach with visual improvements only.

### Claude's Discretion
- Exact stroke colors per sector (darker shade of fill color recommended)
- Doorway gap width (1 or 2 tiles)
- Background pill opacity and corner radius
- Whether sector labels also get background pills
- Simulation time advancement rate (e.g., 1 tick = 10 sim-minutes)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Frontend (files being modified)
- `frontend/src/components/TileMap.tsx` — Current sector rendering (fill only, no stroke), collision tile drawing, sector label style
- `frontend/src/components/AgentSprite.tsx` — Current agent label rendering (9-12px font sizes)
- `frontend/src/components/MapCanvas.tsx` — Map auto-scale logic

### Backend (files being modified)
- `backend/simulation/world.py` — Building class (Phase 7), Maze class, Tile collision flag
- `backend/simulation/map_generator.py` — Town layout generation (needs wall tile generation)
- `backend/data/map/buildings.json` — Building properties (hours, purpose)
- `backend/data/map/town.json` — Tile grid with collision flags (needs wall tiles added)
- `backend/simulation/engine.py` — Agent step logic (needs operating hours check before decide)
- `backend/agents/cognition/decide.py` — decide_action() prompt (needs closed-building filtering)

### Research
- `.planning/research/FEATURES.md` — Wall rendering technique (PixiJS v8 stroke after fill)
- `.planning/research/PITFALLS.md` — Wall tile walkability risk, map-spawn cross-validation

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `TileMap.tsx` `computeSectorBounds()` — already computes bounding boxes for all sectors
- `TileMap.tsx` collision tile rendering — already draws dark gray rects for collision tiles
- `buildings.json` — 16 sectors with opens/closes/purpose already defined from Phase 7
- `Building` dataclass in `world.py` — name, sector, opens, closes, purpose fields ready
- `load_buildings()` in `world.py` — loads and indexes buildings by sector name

### Established Patterns
- PixiJS v8: `g.setFillStyle()` → `g.rect()` → `g.fill()` (add `g.stroke()` for walls)
- Map drawn once via `useCallback` with empty deps `[]` — static drawing, no per-frame redraws
- Agent sprites use PixiJS `Text` component with `TextStyle` for labels

### Integration Points
- `engine.py` `_agent_step()` — add operating hours check before calling `decide_action()`
- `decide.py` prompt context — inject "open buildings: [list]" or filter closed ones out
- `map_generator.py` — needs to mark perimeter tiles as collision when generating town.json
- Frontend receives town.json at build time (static import) — if town.json changes, frontend auto-picks it up

</code_context>

<specifics>
## Specific Ideas

- User wants the map to eventually look like Stardew Valley / original Generative Agents pixel art — that's v1.3, not this phase
- For Phase 8, the goal is: buildings clearly bounded, text readable, hours enforced. Functional polish, not art direction.
- When a building closes with an agent inside, agent leaves immediately (not "finish current task")

</specifics>

<deferred>
## Deferred Ideas

- **Full pixel-art tileset rendering** — Stardew Valley style via pixi-tiledmap + Tiled editor. Separate milestone (v1.3) after v1.1 completes. Codex and user agreed on this scoping.
- **Dynamic text scaling** — font size adjusts with zoom level. Nice-to-have but not Phase 8 scope.

</deferred>

---

*Phase: 08-visual-building-behavior*
*Context gathered: 2026-04-11*
