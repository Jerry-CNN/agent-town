# Phase 5: Frontend - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Phase Boundary

The browser renders the tile map with moving agent sprites, labels, and an activity feed; users can click any agent to inspect their state. This phase builds the React/PixiJS frontend that consumes the WebSocket stream from Phase 4. No event injection UI (Phase 6).

</domain>

<decisions>
## Implementation Decisions

### Map Rendering
- **D-01:** Colored rectangles with text labels for tiles. Green for park, brown for buildings, gray for roads. Location names rendered as text overlays. Simple, clear visual distinction. Pixel art can come in v2.
- **D-02:** 32px tile size, 100x100 grid = 3200x3200px canvas (carried from Phase 2, D-04).
- **D-03:** Click-drag to pan the map, mouse wheel to zoom in/out. Camera centers on the town initially. Standard map interaction.

### Agent Sprites & Movement
- **D-04:** Colored circles with first initial letter inside. Each agent gets a unique color. Name label below the circle. Simple, distinctive, scales with 8 agents.
- **D-05:** Smooth lerp interpolation between tile positions. PixiJS ticker interpolates position each frame over the tick interval. Agents slide naturally rather than snapping.
- **D-06:** Name label and current activity text displayed above/below each agent sprite at all times (DSP-02).

### Activity Feed
- **D-07:** Auto-scrolling log with latest entries at the bottom. New entries appear and auto-scroll. When user scrolls up to read history, auto-scroll pauses; resumes when scrolled to bottom.
- **D-08:** Each feed entry shows: agent name (colored to match their circle), action description, and timestamp.

### Agent Inspector
- **D-09:** Full profile panel: name, occupation, personality traits (innate), current activity, current location, and last 5 memory entries. Satisfies MAP-05.
- **D-10:** Inspector opens in the sidebar, replacing the activity feed (carried from Phase 1, D-05). Closing inspector restores the feed.
- **D-11:** Click an agent circle on the map to open their inspector. Click the close button or click another agent to switch.

### Visual Style
- **D-12:** Clean and minimal with soft/pastel colors. Light background for the map, dark sidebar for contrast. Sans-serif fonts. Professional simulation tool aesthetic, not game-like.

### Layout
- **D-13:** Map-dominant layout (carried from Phase 1, D-04). PixiJS canvas takes most of the screen. Collapsible right sidebar for feed/inspector. Bottom bar for controls (pause/resume, future event input).

### Claude's Discretion
- Exact color palette (tile colors, agent colors, sidebar theme)
- Font family choice (Inter, system fonts, etc.)
- Zoom min/max levels
- Activity feed entry density (how many visible without scrolling)
- Whether to show a minimap for the 3200x3200 canvas
- PixiJS vs CSS for label rendering (performance tradeoff)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Frontend stack (from CLAUDE.md)
- React 19+ with TypeScript 5.4+
- PixiJS 8.17+ with @pixi/react 8+ for React-PixiJS bridge
- Vite 5+ for build tooling
- Zustand 4.5+ for global state
- Biome for linting/formatting
- pixi-tiledmap for potential Tiled JSON loading (may not be needed with colored rectangles)

### Existing codebase
- `frontend/` — React app scaffolded in Phase 1 (Vite + React + TS)
- `frontend/src/App.tsx` — App shell with map-dominant layout placeholder
- `frontend/src/store/` — Zustand store (if exists from Phase 1)
- `backend/routers/ws.py` — WebSocket endpoint the frontend connects to
- `backend/schemas.py` — WSMessage schema defining the push protocol
- `backend/simulation/connection_manager.py` — Snapshot-on-connect behavior

### Prior phase context
- `.planning/phases/01-foundation/01-CONTEXT.md` — App shell layout decisions (D-04, D-05)
- `.planning/phases/02-world-navigation/02-CONTEXT.md` — Tile size (D-04), map dimensions
- `.planning/phases/04-simulation-engine-transport/04-CONTEXT.md` — WebSocket protocol, snapshot format

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 1 frontend scaffold: Vite + React + TS app shell with map-dominant layout
- WebSocket hook (if created in Phase 1) or Zustand store for WS state
- WSMessage type definitions can be mirrored from backend schemas

### Established Patterns
- Zustand for high-frequency WebSocket state updates (from CLAUDE.md stack decisions)
- @pixi/react for declarative PixiJS rendering in React components

### Integration Points
- WebSocket at ws://localhost:8000/ws — connects on mount, receives snapshot then deltas
- Zustand store ingests WebSocket messages and updates agent positions/activities
- PixiJS canvas reads from Zustand store each frame for rendering

</code_context>

<specifics>
## Specific Ideas

- The PixiJS canvas should feel like a living map you're observing, not a game you're playing
- Agent circles with initials are recognizable at any zoom level
- The activity feed should feel like watching a news ticker of the town's life
- Clicking an agent should feel instant — no loading state needed since data is in memory

</specifics>

<deferred>
## Deferred Ideas

- Pixel art tileset and agent sprites — v2 visual upgrade
- Minimap — Claude's discretion for v1, explicitly deferred if complex
- Conversation speech bubbles on the map (DSP-04) — v2
- Memory timeline visualization (DSP-05) — v2
- Relationship graph between agents (DSP-06) — v2
- Dark mode toggle — v2

</deferred>

---

*Phase: 05-frontend*
*Context gathered: 2026-04-10*
