# Phase 10: Asset Pipeline - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Port all pixel-art source assets (tilesets, agent sprites, atlas metadata) from the reference repo (GenerativeAgentsCN) into the Agent Town frontend, convert the Phaser sprite atlas to PixiJS format, and configure PixiJS to render pixel art crisply. This phase is pure infrastructure — no rendering changes, no map redesign, no new UI.

</domain>

<decisions>
## Implementation Decisions

### Agent Sprite Selection
- **D-01:** Port ALL 25 agent sprite sheets from the reference repo (texture.png + portrait.png per agent). Assign 8 to current Agent Town agents (Alice, Bob, Carla, David, Emma, Frank, Grace, Henry) based on visual variety. Remaining sprites stay available for future agent additions.

### Tileset Scope
- **D-02:** Port ALL 16 tileset PNGs from the reference — 9 CuteRPG terrain, 5 interiors, Room_Builder_32x32, blocks_1. Maximum flexibility for map design in Phase 11.

### Atlas Conversion
- **D-03:** Use a one-time Python conversion script to transform the Phaser-format `sprite.json` (array-based frames) into PixiJS spritesheet format (dictionary frames + animations section + meta.image). Converted output committed to repo. Script retained in `scripts/` for reuse if sprites change.

### Asset Organization
- **D-04:** Claude's Discretion — organize `frontend/public/assets/` in whatever structure best suits PixiJS asset loading. Simplified flat structure preferred over deep nesting.

### Claude's Discretion
- Asset directory structure under `frontend/public/assets/` (D-04)
- Agent-to-sprite mapping (which of the 25 reference sprites maps to which of the 8 Agent Town agents) — pick for visual variety

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Reference Implementation Assets
- `~/projects/GenerativeAgentsCN/generative_agents/frontend/static/assets/village/tilemap/` — All 16 tileset PNGs and tilemap.json
- `~/projects/GenerativeAgentsCN/generative_agents/frontend/static/assets/village/agents/sprite.json` — Phaser-format sprite atlas (source for conversion)
- `~/projects/GenerativeAgentsCN/generative_agents/frontend/static/assets/village/agents/*/texture.png` — 25 agent sprite sheets (96x128px)
- `~/projects/GenerativeAgentsCN/generative_agents/frontend/static/assets/village/agents/*/portrait.png` — 25 agent portraits (32x32px)

### Current Frontend
- `frontend/src/components/MapCanvas.tsx` — PixiJS Application wrapper; scaleMode config goes here (before Assets.load)
- `frontend/src/components/AgentSprite.tsx` — Current agent rendering (colored circles); Phase 13 will replace this
- `frontend/src/components/TileMap.tsx` — Current tile rendering (Graphics primitives); Phase 12 will replace this

### Research
- `.planning/research/STACK.md` — pixi-tiledmap 2.2.0, AnimatedSprite/Assets API details
- `.planning/research/PITFALLS.md` — Phaser atlas incompatibility (Pitfall 1), scaleMode timing (Pitfall 5)
- `.planning/research/ARCHITECTURE.md` — Component integration plan, build order

### Agent Config
- `backend/data/agents/*.json` — 8 agent configs (alice, bob, carla, david, emma, frank, grace, henry)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — no image assets exist in the frontend. This phase creates the asset foundation from scratch.

### Established Patterns
- `extend({ Container, Graphics, Text })` in MapCanvas.tsx — new PixiJS types (Sprite, AnimatedSprite) will need to be registered here in later phases
- Vite serves `frontend/public/` as static assets at the root URL path

### Integration Points
- `frontend/public/assets/` — new directory, served by Vite dev server
- MapCanvas.tsx — scaleMode configuration must be set before any Assets.load() call
- `frontend/package.json` — no new npm dependencies needed for this phase (PixiJS Assets API is built-in)

</code_context>

<specifics>
## Specific Ideas

- User wants the UI to look "at least like the original Agent Town" — the reference repo screenshot is the visual target
- Pixel art style is essential — scaleMode nearest is non-negotiable
- All 25 reference sprites ported to allow future agent expansion without re-running the pipeline

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 10-asset-pipeline*
*Context gathered: 2026-04-11*
