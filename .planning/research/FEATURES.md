# Feature Research

**Domain:** Pixel-art RPG town simulation UI — v1.2 milestone (visual upgrade from colored rectangles to tileset-based rendering with animated agent sprites)
**Researched:** 2026-04-11
**Confidence:** HIGH for tileset/sprite rendering patterns (reference implementation in repo, direct file inspection). HIGH for PixiJS AnimatedSprite API (official docs + Context7). MEDIUM for UI polish decisions (community conventions, no single authoritative source).

---

## Scope of This Document

This is a **milestone-scoped** feature research update for v1.2. The v1.1 foundation (OOP agent architecture, building walls via Graphics API, readable text labels, 3-level LLM decision, collision) is already shipped. This document focuses exclusively on:

1. **Tileset-based tile map rendering** — replace Graphics rectangles with CuteRPG tile textures via Tiled JSON + pixi-tiledmap
2. **Animated agent sprites** — replace colored circles with 4-direction walk-cycle sprite sheets
3. **Agent overhead UI** — name labels, activity text, speech-bubble style display above sprites
4. **Layer depth ordering** — agents behind foreground tiles (trees, building fronts), above ground
5. **Pixel-art UI shell** — sidebar, controls, typography styled to match RPG aesthetic

**What is NOT in scope for v1.2:**
- Any agent behavior changes (that is v1.3)
- New town layout (map redesign is in scope as a sub-task, but no new locations)
- Sound or audio
- Camera follow on agent click (deferred; see anti-features)

---

## Feature Landscape

### Table Stakes (Users Expect These — for v1.2 pixel-art milestone)

Features that, once "pixel-art RPG visual upgrade" is promised, users expect to see. Missing any makes the upgrade feel incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Tile-textured map ground (grass, paths, dirt) | Core promise: "replace colored rectangles with CuteRPG tilesets." Without real tiles, it still looks like a prototype | HIGH | Requires pixi-tiledmap v2, Tiled map redesign in Tiled editor, 9+ tileset PNGs loaded as assets |
| Building walls and roofs rendered with tilesets | Buildings must look like buildings, not colored boxes. Table stakes for "RPG town" | HIGH | Tiled Room_Builder_32x32 tileset handles walls/roofs; requires Wall layer in Tiled map |
| Interior details (furniture, floor tiles) | Without interiors, buildings are hollow. Reference has 5 interior tilesets with furniture | HIGH | Interior Ground + Furniture L1/L2 layers in Tiled; significant authoring work in Tiled editor |
| Animated agent sprites replacing colored circles | Core promise: "replace colored circles with animated agent sprites." Without this, the milestone is not shipped | HIGH | Requires CuteRPG-style character sprite sheets (32x32 frames), PixiJS AnimatedSprite, shared sprite.json atlas, 4-direction walk cycles |
| Walk direction tracking — sprite faces correct direction | Players expect sprites to face left when moving left, etc. Facing a fixed direction while moving looks broken | MEDIUM | Backend must send movement direction with each position update, or frontend infers from delta |
| Name label above each agent sprite | Users need to identify agents. Without names, the simulation is unreadable | LOW | Already exists as PixiJS Text; requires repositioning above sprite head not below circle |
| Activity text above agent (truncated, legible) | Core UX — users watch what agents are doing. This exists on current circles; must survive migration | LOW | Already exists; needs repositioning for new sprite height (~64px tall at default zoom) |
| Layer ordering: agents above ground, below foreground | Agents must walk behind trees and under building roofs, not float on top of everything | MEDIUM | Requires explicit PixiJS zIndex — agents at z=1, foreground tiles at z=2, labels at z=3 |
| Map pan and zoom preserved | Navigation already works; must not regress during refactor | LOW | MapCanvas.tsx pan/zoom logic is independent of tile rendering layer; regression risk is real |

### Differentiators (Competitive Advantage — v1.2 additions)

Features that make Agent Town's visual quality stand out from other Generative Agents reimplementations.

| Feature | Value Proposition | Complexity | Notes |
|---------|------------------|------------|-------|
| Agent portrait in inspector panel | Reference implementation shows per-agent portrait images (portrait.png per agent). Clicking an agent shows their face. Creates character attachment | LOW-MEDIUM | Reference has portrait.png per agent folder. Requires frontend inspector update, asset serving. Significant value for minimal cost |
| Emoji pronunciation above agent during conversation | Stanford reference uses emoji translations of agent actions above sprite head (yellow background pill). Gives instant semantic read of what agent is doing without reading text | MEDIUM | Requires LLM to produce a 1-2 emoji summary per action alongside the text activity. Surfaced as PixiJS Text with emoji font |
| Distinct visual styles per building type | Park = green grass tiles, Stock Exchange = fancy floor tiles, Wedding Hall = ornate. Visual differentiation makes the map readable at a glance without labels | HIGH | Requires careful tileset selection per sector in Tiled editor. Authoring-heavy, rendering is free once tiles exist |
| Smooth walk animation tied to movement (not looping when idle) | Walking animation plays when moving, idle frame shown when standing. The reference does this: `anims.stop()` + set idle frame when agent reaches destination | MEDIUM | Requires frontend to detect when agent reaches target position. Stop animation and hold facing direction frame. PixiJS AnimatedSprite.stop() |
| Pixel-art styled sidebar (border frame, RPG-font) | Sidebar with pixel border, `Press Start 2P` or similar pixel font for headers makes the whole UI feel cohesive. Currently the sidebar is a plain dark panel | LOW-MEDIUM | CSS-only for sidebar: pixel-art border image, monospace/pixel font for headers. Activity feed stays system-ui for legibility. Zero rendering cost |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Camera auto-follow on agent click | Users want to track a specific agent as they walk around | Breaks the "watch the whole town at once" experience. Single-agent follow makes it hard to see emergent interactions. High implementation cost (smooth camera interpolation, edge constraints) | Keep click-to-select for inspector; add a "center on agent" button that does a one-shot pan, no tracking |
| Unique sprite art per agent | Each agent having a visually distinct sprite (different clothes, hair) makes them feel individual | 8-25 unique sprite sheets is an enormous art asset burden. The reference uses the same sprite.json animation frames but per-agent texture.png with different palette/colors — a compromise | Use per-agent tinted sprites: same sprite sheet geometry, hue-shifted per agent colorIndex. PixiJS `sprite.tint` property handles this at zero cost |
| Health bars / stat overlays above agents | Some users expect RPG-style HUD elements | This is a simulation viewer, not a game. Stat overlays add visual noise that obscures the emergent behavior, which is the product's core value | Show all agent stats in the inspector panel on click. Keep the map view clean |
| Isometric (2.5D) tile rendering | "It would look so much better in isometric!" | Requires depth-sorted sprites, z-buffer tricks per Y position, split sprites for wall peek-over. Phaser, the reference renderer, doesn't use isometric. Adding this costs 3-4 weeks and conflicts with existing pathfinding on an orthogonal grid | Stay orthogonal. Wall + foreground layers give sufficient depth illusion |
| Real-time streaming thought bubble | Show LLM "thinking" as text appears above agents during decision | 8 agents simultaneously streaming at varying latencies creates visual chaos. Overlapping text bubbles at different update rates are unreadable and cause PixiJS text object churn | Store completed thoughts; surface in inspector. Show a subtle "thinking..." indicator in the activity pill if the agent's last LLM call is in-flight |
| Tile animation (water rippling, torch flames) | Animated environment tiles make the world feel alive | pixi-tiledmap v2 supports animated tiles natively, but CuteRPG tilesets used in the reference do not include animated variants. Authoring animated tiles requires separate asset work | Static tiles for v1.2. If animated tiles are desired, add as a v1.3 polish task with explicit asset sourcing |
| Per-agent conversation speech bubbles (chat log over map) | Show dialogue visually in the game world, RPG-style | Speech bubbles large enough to read require significant map space. With 8+ agents potentially all talking, the map fills with overlapping bubbles. Performance: PixiJS Text objects are expensive; many updating simultaneously cause frame drops | Show active conversation in the activity feed sidebar (already implemented). On the map, show a small conversation indicator icon above agents who are talking |

---

## Feature Dependencies

```
Tiled map authoring (in Tiled editor — one-time authoring task)
    └──produces──> tilemap.json (17 layers, 18 tilesets)
    └──produces──> tileset PNGs (CuteRPG_Field_B, CuteRPG_Village_B, Room_Builder_32x32, interiors_pt1-5, etc.)
    └──required-by──> Tileset-based map rendering

Tileset-based map rendering (pixi-tiledmap v2)
    └──replaces──> TileMap.tsx (Graphics API rectangles)
    └──required-by──> Layer depth ordering (must know which layers are foreground vs ground)
    └──required-by──> Interior detail rendering (Interior Furniture layers)
    └──required-by──> Building walls via Wall layer (not Graphics stroke)

Layer depth ordering
    └──requires──> Tileset-based map rendering (layers must exist to order them)
    └──requires──> Agent sprites have explicit zIndex (1, between ground=0 and foreground=2)
    └──enhances──> Visual coherence (agents appear to walk inside buildings)

Animated agent sprites
    └──requires──> CuteRPG character sprite sheets (texture.png per agent + shared sprite.json atlas)
    └──requires──> PixiJS AnimatedSprite + Assets.load (replaces PixiJS Graphics circle)
    └──requires──> Walk direction tracking (backend sends direction OR frontend infers from position delta)
    └──replaces──> AgentSprite.tsx colored circle + first-initial rendering
    └──required-by──> Idle frame (stop animation, hold facing direction)

Walk direction tracking
    └──requires──> Either: backend AgentState.direction field + WebSocket update
                   Or:     frontend infers direction from (prev_pos → new_pos) delta
    └──required-by──> Animated sprite direction selection (down/up/left/right animation key)
    └──required-by──> Idle facing (hold correct direction idle frame on arrival)

Agent overhead UI (name + activity labels)
    └──requires──> Animated agent sprites (must know sprite height to position labels above)
    └──soft-depends-on──> Emoji activity summary (if implemented, replace text with emoji pill)
    └──already-exists-as──> PixiJS Text nodes in AgentSprite.tsx; requires Y-offset adjustment

Agent portrait in inspector
    └──requires──> Portrait images served as static assets (portrait.png per agent from reference)
    └──soft-depends-on──> Animated sprites (visual consistency — portraits should match sprite style)
    └──modifies──> AgentInspector.tsx (add img element)

Pixel-art UI shell
    └──no-dependency-on──> Tileset rendering (pure CSS/font changes)
    └──no-dependency-on──> Sprite animation
    └──enhances──> Perceived polish; can be done independently in any order
```

### Dependency Notes

- **Tiled map authoring must come before tileset rendering:** pixi-tiledmap.load() takes a Tiled JSON file. No JSON, no rendering. This is the critical path.
- **Animated sprites and tileset rendering are independent:** Sprite animation does not depend on tilesets. Can be developed in parallel or sequenced — tileset rendering first is recommended so the map exists before placing sprites on it.
- **Walk direction tracking can be solved in the frontend:** Infer direction from `(prev_position → new_position)` delta in the useTick lerp loop. No backend changes needed. Backend direction field is a nice-to-have for accuracy at the instant a path starts.
- **Agent overhead UI repositioning is LOW risk:** The PixiJS Text nodes already exist. The only change is the Y-offset constant: from `y = -24` (above circle radius 18) to `y = -(SPRITE_HEIGHT / 2 + 8)` (above sprite top edge). No architecture change.

---

## MVP Definition

### Launch With (v1.2)

Minimum set to call the pixel-art milestone "shipped":

- [ ] Tiled-authored map loaded and rendered via pixi-tiledmap (ground, walls, foreground layers) — without this, the milestone promise is not met
- [ ] CuteRPG tilesets visible — grass paths, building walls, exterior decoration
- [ ] Agent sprites replacing colored circles — animated walk cycle, 4 directions
- [ ] Walk direction correct (sprite faces the direction of movement)
- [ ] Name and activity labels repositioned above sprite heads
- [ ] Agents render at correct layer depth (above ground tiles, below foreground tiles)
- [ ] Map pan and zoom not regressed

### Add After Core Is Working (v1.2 polish)

- [ ] Idle frame on arrival — agent stops animation and holds facing direction frame when they reach destination
- [ ] Per-agent sprite tinting — use PixiJS `sprite.tint` with existing colorIndex palette so agents remain visually distinct without unique art
- [ ] Agent portrait in inspector — static portrait.png from reference repo shown in AgentInspector when agent is selected
- [ ] Pixel-art CSS shell — pixel font headers in sidebar, pixel border on inspector panel

### Future Consideration (v1.3+)

- [ ] Emoji activity summary above agent head — requires LLM prompt change; a v1.3 behavior concern
- [ ] Animated environment tiles — requires animated tileset assets not currently available
- [ ] Camera center-on-agent button — useful but not blocking core UX
- [ ] Unique per-agent character sprite art — art asset burden; tinting is sufficient for v1.2

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Tileset-based map rendering (ground + walls) | HIGH — core promise | HIGH (Tiled authoring + pixi-tiledmap integration) | P1 |
| Animated agent sprites | HIGH — core promise | HIGH (sprite sheets + AnimatedSprite) | P1 |
| Walk direction tracking (frontend delta inference) | HIGH — immersion | LOW (infer from lerp delta) | P1 |
| Layer depth ordering (agents below foreground) | HIGH — visual coherence | MEDIUM (explicit zIndex per layer) | P1 |
| Name + activity label repositioning | MEDIUM — regression risk if skipped | LOW (Y-offset constant change) | P1 |
| Idle facing frame on arrival | MEDIUM — polish | LOW (AnimatedSprite.stop() + setTexture) | P2 |
| Per-agent sprite tinting | MEDIUM — agent distinctiveness | LOW (sprite.tint = colorIndex color) | P2 |
| Agent portrait in inspector | LOW-MEDIUM — character attachment | LOW (static img, existing asset) | P2 |
| Pixel-art CSS shell (font, border) | LOW — cohesion | LOW (CSS + Google Fonts) | P2 |
| Interior detail (furniture layers) | MEDIUM — depth of world | HIGH (Tiled authoring — most time-consuming part) | P2 |

**Priority key:** P1 = must have for v1.2 milestone to be considered shipped. P2 = ship if time allows, high return per hour.

---

## Reference Implementation Analysis

The reference (GenerativeAgentsCN) does these things well that we should replicate:

### What the Reference Does Well

**Shared sprite.json atlas:** All 26 agents use the same sprite.json frame definitions (`down-walk.000` through `down-walk.003`, `left-walk.000-003`, etc.) but each agent has their own `texture.png`. This means one JSON parse, N texture loads. In PixiJS v8 terms: load sprite.json once as the atlas metadata, load each agent's texture.png as the atlas image via `Assets.add(agentName, textureUrl)` + `Assets.load`. The AnimatedSprite frames reference the shared JSON but render from per-agent textures.

**4-frame walk cycle per direction:** `down-walk.000`, `down-walk.001`, `down-walk.002`, `down-walk.003` — frame 001 is the midstride, frame 003 is a repeat of 001 (pendulum pattern). This is the standard minimal walk cycle. At frameRate=4 (reference), one full walk cycle = 1 second. At frameRate=8 (fast movement), 0.5 seconds.

**Idle frame is the mid-stride frame:** When stopped, the reference sets the idle texture to `down`, `left`, `right`, or `up` — which maps to frame 001 (mid-stride, foot slightly forward). This is the standard RPG idle stance convention — not the extreme frame, not frame 0.

**Pronunciatio (activity label) with yellow background:** The reference uses `backgroundColor: "#ffffcc"` (light yellow) for activity text above agents. This is highly readable against both dark ground tiles and bright grass tiles. More visible than the current dark pill with white text at small sizes.

**26 distinct character sprites:** Even though the reference is Chinese-localized, the sprite sheets are pixel-art characters with distinct silhouettes. For Agent Town, using the same sprite sheets (8-10 characters for typical agent count) is immediately available from the reference repo.

**Foreground layers at depth 2:** The reference sets `foregroundL1Layer.setDepth(2)` and `foregroundL2Layer.setDepth(2)`. Agents are at depth 1 (their sprites are between ground and foreground). This is the correct z-ordering pattern to port to PixiJS zIndex.

**17 layers with clear semantic grouping:**
- Ground layers: `Bottom Ground`, `Exterior Ground`, `Interior Ground` (depth 0)
- Decoration: `Exterior Decoration L1/L2`, `Interior Furniture L1/L2` (depth 0-1)
- Walls: `Wall` layer (depth 0, but visually above ground)
- Foreground (overhangs): `Foreground L1`, `Foreground L2` (depth 2, above agents)
- Logic-only layers (invisible at runtime): `Collisions`, `Arena Blocks`, `Sector Blocks`, `World Blocks`, `Spawning Blocks`

For Agent Town's Tiled map, the same layer structure should be used. Logic-only layers carry address/collision data consumed by the backend (already using town.json); they do not need to render.

### What the Reference Does That We Adapt Differently

**Phaser vs PixiJS:** The reference uses Phaser 3's built-in `make.tilemap()` + `createLayer()`. In PixiJS v8, the equivalent is `pixi-tiledmap` v2's `TiledMap.from(url)` async loader which returns a Container with sub-containers per layer. We do not use Phaser's physics or scene system — pixi-tiledmap is a pure rendering integration.

**Camera via physics sprite:** The reference follows a ghost physics sprite with arrow keys for camera navigation. We already have click-drag pan implemented in MapCanvas.tsx. No change needed; our implementation is better for a browser tool (mouse-native, no arrow key dependency).

**Collision via `setCollisionByProperty`:** The reference uses Phaser's built-in tile collision system for camera bounds. Our collision is handled by the Python backend BFS pathfinder — the Collisions layer in the Tiled map only needs to exist for the backend to read from town.json. It does not need runtime collision in the browser. This simplifies our PixiJS integration significantly.

**Chinese character names on sprites:** The reference shows the agent's Chinese name in the pronunciatio label. Our implementation already has English names — no change needed.

---

## Asset Inventory (What We Have vs What We Need)

### Available in Reference Repo (can copy)

| Asset | Path in Reference | Notes |
|-------|-------------------|-------|
| CuteRPG_Field_B.png | `generative_agents/frontend/static/assets/village/tilemap/` | Exterior ground tileset |
| CuteRPG_Field_C.png | same | Exterior ground variant |
| CuteRPG_Village_B.png | same | Village buildings |
| CuteRPG_Forest_B.png, C.png | same | Trees, forest tiles |
| CuteRPG_Desert_B.png, C.png | same | Desert/path tiles |
| CuteRPG_Mountains_B.png | same | Mountain/rock tiles |
| CuteRPG_Harbor_C.png | same | Water/harbor tiles |
| Room_Builder_32x32.png | same | Interior walls, floors, roofs |
| interiors_pt1-5.png | same | Furniture, decorations |
| blocks_1.png | same | Collision marker tiles (invisible) |
| sprite.json | `agents/` | Shared animation frame definitions (all 4-direction walk cycles) |
| texture.png (x26 agents) | `agents/<name>/` | Per-agent character sprite sheets |
| portrait.png (x26 agents) | `agents/<name>/` | Per-agent portrait images for inspector |

### Needs Creation

| Asset | Description | Effort |
|-------|-------------|--------|
| tilemap.json (Agent Town version) | Tiled-authored map with Agent Town locations (stock exchange, wedding hall, park, café, etc.) using the above tilesets. Must match existing town.json sector structure for backend compatibility | HIGH — main authoring task; 1-3 days in Tiled editor |

### License Note

CuteRPG tilesets by PixyMoon are paid assets (~$4.99/pack) that allow commercial use and modification but cannot be resold. The reference repo ships them as part of the academic research code. Agent Town should verify whether using them in a public/deployed context requires a separate license purchase. For development and private use, the assets from the reference repo are immediately available. MEDIUM confidence on exact license terms — verify at https://pixymoon.itch.io before public deployment.

---

## Sources

- [GenerativeAgentsCN frontend JS](file:///Users/sainobekou/projects/GenerativeAgentsCN/generative_agents/frontend/templates/main_script.html) — HIGH confidence; direct read of reference renderer. Phaser 3 layer setup, animation creation, sprite depth ordering, pronunciatio pattern
- [GenerativeAgentsCN tilemap.json](file:///Users/sainobekou/projects/GenerativeAgentsCN/generative_agents/frontend/static/assets/village/tilemap/tilemap.json) — HIGH confidence; direct read. 17 layers, 18 tilesets, 140x100 grid confirmed
- [GenerativeAgentsCN sprite.json](file:///Users/sainobekou/projects/GenerativeAgentsCN/generative_agents/frontend/static/assets/village/agents/sprite.json) — HIGH confidence; direct read. 4-direction walk cycle frame definitions, 32x32 frames, anchor (0.5, 0.5)
- [pixi-tiledmap v2 (riebel/pixi-tiledmap)](https://github.com/riebel/pixi-tiledmap) — HIGH confidence; WebFetch confirmed v2.2.0 supports PixiJS v8, full layer support, Tiled JSON parser, animated tiles. No zstd compression (gzip/deflate only — Tiled editor default export is fine)
- [PixiJS AnimatedSprite API](https://pixijs.download/dev/docs/scene.AnimatedSprite.html) — HIGH confidence; official docs. `new AnimatedSprite(sheet.animations['key'])`, `.play()`, `.stop()`, `.animationSpeed`, `.onComplete`
- [PixiJS Spritesheet/Assets.load](https://pixijs.download/dev/docs/assets.Spritesheet.html) — HIGH confidence; official docs. `Assets.load(atlasUrl)` returns Spritesheet; `.animations` for AnimatedSprite; `Assets.add(alias, url)` for per-agent textures
- [PixiJS BitmapText](https://pixijs.download/dev/docs/scene.BitmapText.html) — MEDIUM confidence; BitmapText is higher performance than Text for frequently-updating labels; relevant for agent name/activity if 25 agents
- [Generative Agents paper (Park et al.)](https://ar5iv.labs.arxiv.org/html/2304.03442) — HIGH confidence; emoji pronunciatio pattern, overhead action label design
- [Tiled layer documentation](https://doc.mapeditor.org/en/stable/manual/layers/) — HIGH confidence; layer ordering, foreground/background layer conventions for RPG top-down
- [a16z ai-town](https://github.com/a16z-infra/ai-town) — MEDIUM confidence; confirms PixiJS + Tiled JSON "bgtiles"/"objmap" pattern is the community standard for browser-based agent town simulations
- [CuteRPG license (PixyMoon itch.io)](https://pixymoon.itch.io/cuterpg-caves) — MEDIUM confidence; commercial use allowed, resale prohibited; verify before public deployment

---

*Feature research for: Agent Town v1.2 — pixel-art RPG visual upgrade*
*Researched: 2026-04-11*
