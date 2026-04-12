# Roadmap: Agent Town

**Created:** 2026-04-08
**Updated:** 2026-04-11 (v1.2 Pixel Art UI roadmap added)
**Granularity:** Standard

---

## Milestones

- v1.0 Core - Phases 1-6 (shipped 2026-04-10)
- v1.1 Architecture & Polish - Phases 7-9.2 (shipped 2026-04-12)
- v1.2 Pixel Art UI - Phases 10-14 (active)
- v1.3 Agent Behavior - Phases 15+ (planned)

---

## Phases

<details>
<summary>v1.0 Core (Phases 1-6) - SHIPPED 2026-04-10</summary>

- [x] **Phase 1: Foundation** - Project scaffold, async infrastructure, LLM gateway, structured output, and configuration UI
- [x] **Phase 2: World & Navigation** - Tile map data model, BFS pathfinding, agent data structures, and thematic town layout
- [x] **Phase 3: Agent Cognition** - Memory stream, daily planning, perception, LLM decisions, and agent-to-agent conversations
- [x] **Phase 4: Simulation Engine & Transport** - Real-time async simulation loop, WebSocket push, and pause/resume control
- [x] **Phase 5: Frontend** - React/PixiJS map rendering, agent sprites, activity feed, agent inspection panel
- [x] **Phase 6: Event Injection** - Event UI, broadcast mode, whisper mode, and organic gossip spreading

Full details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>v1.1 Architecture & Polish (Phases 7-9.2) - SHIPPED 2026-04-12</summary>

- [x] **Phase 7: OOP Foundation** - Agent/Building/Event classes, schema split, SimulationEngine migration (2/2 plans)
- [x] **Phase 8: Visual & Building Behavior** - Wall outlines, operating hours, readable text (2/2 plans)
- [x] **Phase 9: LLM Optimization** - 2-level cascade, adaptive tick, repetition detection, semaphore (3/3 plans)
- [x] **Phase 9.1: Backend Runtime Wiring** - Event lifecycle + Agent wrappers wired into runtime (1/1 plan, gap closure)
- [x] **Phase 9.2: Visual Text Restoration** - Activity text restored, WCAG AA contrast (1/1 plan, gap closure)

Full details: `.planning/milestones/v1.1-ROADMAP.md`

</details>

---

### v1.2 Pixel Art UI (Active)

**Milestone Goal:** Transform the prototype-looking UI into a pixel-art RPG town — CuteRPG tilesets, Tiled-authored map, animated directional agent sprites, and UI harmonized with the pixel-art aesthetic.

- [x] **Phase 10: Asset Pipeline** - Port CuteRPG tilesets and sprite sheets from reference repo; convert Phaser atlas to PixiJS format; configure scaleMode nearest (completed 2026-04-12)
- [ ] **Phase 11: Town Map Design & Backend Sync** - Author Agent Town-specific map in Tiled with thematic buildings; regenerate town.json; wire collision layer to backend pathfinding
- [ ] **Phase 12: Tile Map Rendering** - Integrate pixi-tiledmap; render full building interiors and furniture from Tiled layers; depth ordering for foreground objects; loading screen
- [ ] **Phase 13: Animated Agent Sprites** - Replace colored circles with AnimatedSprite walk cycles; directional facing; idle pose; portraits in inspector; pixel-art activity bubbles
- [ ] **Phase 14: UI Polish** - Harmonize sidebar and controls with pixel-art aesthetic; pixel-art typography; loading overlay with progress bar

---

### v1.3 Agent Behavior (Planned)

**Milestone Goal:** Add reflection, relationship tracking, task state machines, and perception diffing to create deeper agent behavior.

- [ ] **Phase 15: Task & Perception Systems** - Task state machine with interrupt/resume; perception diff so agents react to changes not static scenes
- [ ] **Phase 16: Reflection System** - Poignancy accumulation, threshold-triggered insight generation as background asyncio tasks
- [ ] **Phase 17: Relationship Tracking** - Agent-to-agent relationship state (familiarity, sentiment, last interaction) visible in inspector

---

## Phase Details

### Phase 10: Asset Pipeline
**Goal**: All pixel-art source assets from the reference repo are available in the frontend asset directory in PixiJS-compatible formats, and the renderer is configured to preserve pixel crispness before any assets load.
**Depends on**: Phase 9.2
**Requirements**: PIPE-01, PIPE-02, PIPE-03
**Success Criteria** (what must be TRUE):
  1. CuteRPG tileset images and agent sprite sheets are present under `frontend/public/assets/` and loadable via a browser request without 404.
  2. The sprite atlas JSON that ships from the reference repo (Phaser format) has been converted to PixiJS spritesheet format and validated against the PixiJS Assets API.
  3. PixiJS initializes with `scaleMode: 'nearest'` set before any `Assets.load()` call — confirmed by loading a single tile and observing crisp (non-blurred) pixel edges in the browser at 2x zoom.
**Plans**: 2 plans
Plans:
- [x] 10-01-PLAN.md — Port tileset and agent sprite assets + convert Phaser atlas to PixiJS format
- [x] 10-02-PLAN.md — Configure scaleMode nearest, CSS pixelated, roundPixels
**UI hint**: yes

---

### Phase 11: Town Map Design & Backend Sync
**Goal**: Agent Town has a purpose-built Tiled map with all thematic buildings, and the backend town.json is regenerated from the Tiled export so sector/arena coordinates and collision data come from the map, not hardcoded data.
**Depends on**: Phase 10
**Requirements**: TOWN-01, TOWN-02, TOWN-03, TOWN-04
**Success Criteria** (what must be TRUE):
  1. The Tiled map contains all seven thematic buildings (stock exchange, wedding hall, cafe, park, homes, office, shop) with labeled layers distinguishing ground, walls, furniture, and collision.
  2. The backend `town.json` is regenerated from the Tiled export — sector names and arena coordinate boundaries match the map visually (an agent assigned to "Stock Exchange" navigates to the tile region where that building visually sits).
  3. Agent pathfinding uses the collision layer exported from Tiled rather than hardcoded obstacle data — blocking walls in Tiled halt agent movement; removing a wall in Tiled and re-exporting makes that tile walkable without any backend code change.
  4. Every agent home, workplace, and routine destination maps to a reachable walkable tile — no agent spawns in walls or has unreachable schedule destinations after the map export.
**Plans**: TBD

---

### Phase 12: Tile Map Rendering
**Goal**: The browser renders the full Tiled map with proper layering — ground tiles, building interiors with furniture, and foreground objects that visually occlude agents standing behind them — with a loading screen shown while assets initialize.
**Depends on**: Phase 11
**Requirements**: TILE-01, TILE-02, TILE-03, TILE-04, PERF-01, PERF-02
**Success Criteria** (what must be TRUE):
  1. The town map displays CuteRPG pixel-art tiles instead of colored rectangles — ground tiles, walls, and floor patterns are all visible.
  2. Building interiors are rendered with furniture and room layouts matching the Tiled design — tables, counters, and decor are visible inside buildings when the camera covers them.
  3. An agent standing behind a tree or under a roof is visually occluded by the foreground tile — the agent sprite renders below the foreground layer, not on top of it.
  4. A loading screen is displayed from app startup until all tile map assets have finished loading — the map does not flash with raw tile indices or blank tiles during load.
  5. Tile map with 17 layers and animated agent sprites renders at 30+ FPS with 10 agents on a standard laptop.
  6. Initial asset loading (tilesets + sprite sheets) completes within 5 seconds on a broadband connection.
**Plans**: TBD
**UI hint**: yes

---

### Phase 13: Animated Agent Sprites
**Goal**: Agents are represented by animated pixel-art sprites that face their direction of movement, stop in an idle pose when stationary, and have visual indicators (portrait in inspector, activity bubble above sprite) that match the pixel-art style.
**Depends on**: Phase 12
**Requirements**: SPRT-01, SPRT-02, SPRT-03, SPRT-04, SPRT-05
**Success Criteria** (what must be TRUE):
  1. Colored circles are replaced by animated sprite characters — the walk animation plays (at least 2 visible frames cycling) while an agent is moving between tiles.
  2. An agent moving right displays frames from the right-facing walk cycle; moving up shows the up-facing cycle; moving left shows left-facing; moving down shows down-facing.
  3. When an agent reaches its destination and stops moving, the sprite displays a static idle frame rather than continuing to animate.
  4. The agent inspector sidebar shows a 32x32 portrait thumbnail for the selected agent, not a colored circle or placeholder.
  5. A pixel-art styled speech or activity bubble appears above each agent showing their current activity — the bubble uses pixel-art border styling (not a plain CSS div with rounded corners).
**Plans**: TBD
**UI hint**: yes

---

### Phase 14: UI Polish
**Goal**: The sidebar, controls, and key UI elements use colors and typography that are visually consistent with the pixel-art map, so the interface feels like one cohesive product rather than a pixel-art canvas embedded in a generic web UI.
**Depends on**: Phase 12
**Requirements**: UIPOL-01, UIPOL-02, UIPOL-03
**Success Criteria** (what must be TRUE):
  1. The sidebar background, button colors, and activity feed styling use a color palette that harmonizes with the CuteRPG tile palette — no mismatched modern gradient or flat Material-style colors dominating the layout.
  2. Map labels (agent names, building names) and at least one key UI element (e.g., the "Inject Event" button or panel header) use a pixel-art or retro-style font, not the default system sans-serif.
  3. The loading overlay shown at startup includes a visible progress indicator (bar, percentage, or step label) — the user can see the load is progressing rather than staring at a blank or static screen.
**Plans**: TBD
**UI hint**: yes

---

## Phase Summary

### v1.2 Pixel Art UI (active)

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|-----------------|
| 10 | Asset Pipeline | 2/2 | Complete    | 2026-04-12 |
| 11 | Town Map Design & Backend Sync | Tiled map authored, town.json regenerated, collision from Tiled, reachability validated | TOWN-01, TOWN-02, TOWN-03, TOWN-04 | 4 |
| 12 | Tile Map Rendering | pixi-tiledmap integration, depth ordering, loading screen, performance targets | TILE-01, TILE-02, TILE-03, TILE-04, PERF-01, PERF-02 | 6 |
| 13 | Animated Agent Sprites | Walk cycles, directional facing, idle, portrait, bubbles | SPRT-01, SPRT-02, SPRT-03, SPRT-04, SPRT-05 | 5 |
| 14 | UI Polish | Color palette, pixel font, loading progress bar | UIPOL-01, UIPOL-02, UIPOL-03 | 3 |

### v1.3 Agent Behavior (planned)

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|-----------------|
| 15 | Task & Perception Systems | Task state machine, interrupt/resume, perception diff | TSK-01, TSK-02, TSK-03, PCPT-01, PCPT-02 | 4 |
| 16 | Reflection System | Poignancy accumulation, threshold-triggered thought memories, background task | RFL-01, RFL-02, RFL-03 | 4 |
| 17 | Relationship Tracking | Per-pair relationship state, initiation weighting, inspector display | REL-01, REL-02, REL-03 | 3 |

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 3/3 | Complete | 2026-04-10 |
| 2. World & Navigation | v1.0 | 3/3 | Complete | 2026-04-10 |
| 3. Agent Cognition | v1.0 | 3/3 | Complete | 2026-04-10 |
| 4. Simulation Engine & Transport | v1.0 | 2/2 | Complete | 2026-04-10 |
| 5. Frontend | v1.0 | 4/4 | Complete | 2026-04-10 |
| 6. Event Injection | v1.0 | 2/2 | Complete | 2026-04-10 |
| 7. OOP Foundation | v1.1 | 2/2 | Complete | 2026-04-11 |
| 8. Visual & Building Behavior | v1.1 | 2/2 | Complete | 2026-04-11 |
| 9. LLM Optimization | v1.1 | 3/3 | Complete | 2026-04-11 |
| 9.1 Backend Runtime Wiring | v1.1 | 1/1 | Complete | 2026-04-12 |
| 9.2 Visual Text Restoration | v1.1 | 1/1 | Complete | 2026-04-12 |
| 10. Asset Pipeline | v1.2 | 0/2 | Planned | - |
| 11. Town Map Design & Backend Sync | v1.2 | 0/? | Not started | - |
| 12. Tile Map Rendering | v1.2 | 0/? | Not started | - |
| 13. Animated Agent Sprites | v1.2 | 0/? | Not started | - |
| 14. UI Polish | v1.2 | 0/? | Not started | - |
| 15. Task & Perception Systems | v1.3 | 0/? | Not started | - |
| 16. Reflection System | v1.3 | 0/? | Not started | - |
| 17. Relationship Tracking | v1.3 | 0/? | Not started | - |
