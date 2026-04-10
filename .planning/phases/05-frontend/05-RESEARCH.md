# Phase 5: Frontend - Research

**Researched:** 2026-04-09
**Domain:** React/PixiJS browser rendering — tile map, agent sprites, activity feed, inspector panel
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Colored rectangles with text labels for tiles. Green for park, brown for buildings, gray for roads. Location names rendered as text overlays. No pixel art in v1.
- **D-02:** 32px tile size, 100x100 grid = 3200x3200px canvas.
- **D-03:** Click-drag to pan the map, mouse wheel to zoom in/out. Camera centers on town initially.
- **D-04:** Colored circles with first initial letter inside. Each agent gets a unique color. Name label below the circle.
- **D-05:** Smooth lerp interpolation between tile positions. PixiJS ticker interpolates position each frame over the tick interval. Agents slide rather than snap.
- **D-06:** Name label and current activity text displayed above/below each agent sprite at all times.
- **D-07:** Auto-scrolling log with latest entries at the bottom. Auto-scroll pauses when user scrolls up; resumes when scrolled back to bottom.
- **D-08:** Each feed entry shows agent name (colored to match their circle), action description, and timestamp.
- **D-09:** Full profile panel: name, occupation, personality traits (innate), current activity, current location, last 5 memory entries.
- **D-10:** Inspector opens in sidebar, replacing activity feed. Closing inspector restores feed.
- **D-11:** Click an agent circle to open inspector. Close button or click another agent to switch.
- **D-12:** Clean minimal style with soft/pastel colors. Light map background, dark sidebar. Sans-serif fonts.
- **D-13:** Map-dominant layout. PixiJS canvas takes most of the screen. Collapsible right sidebar. Bottom bar for controls.

### Claude's Discretion
- Exact color palette (tile colors, agent colors, sidebar theme)
- Font family choice (Inter, system fonts, etc.)
- Zoom min/max levels
- Activity feed entry density (how many visible without scrolling)
- Whether to show a minimap for the 3200x3200 canvas
- PixiJS vs CSS for label rendering (performance tradeoff)

### Deferred Ideas (OUT OF SCOPE)
- Pixel art tileset and agent sprites — v2
- Minimap — Claude's discretion for v1, explicitly deferred if complex
- Conversation speech bubbles on the map (DSP-04) — v2
- Memory timeline visualization (DSP-05) — v2
- Relationship graph between agents (DSP-06) — v2
- Dark mode toggle — v2
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MAP-01 | 2D tile-map town rendered in browser with top-down view | PixiJS Graphics API draws colored rectangles per tile zone; town.json provides tile data with sector addresses |
| MAP-02 | Agent sprites visible on map, moving between tiles in real-time | PixiJS Graphics circles with useTick lerp; agent positions from Zustand store updated via WebSocket agent_update messages |
| MAP-05 | User can click agent on map to inspect current activity, personality, recent memories | Click handler on agent Graphics object; sidebar panel reads AgentState from store; backend needs /api/agents/{name}/memories endpoint |
| DSP-01 | Activity feed showing real-time agent actions and conversations as scrolling log | Existing ActivityFeed.tsx placeholder; needs to parse agent_update and conversation WSMessage types properly |
| DSP-02 | Agent labels on map showing name and current activity above each sprite | PixiJS Text objects parented to agent Container; updates every tick from Zustand store |
</phase_requirements>

---

## Summary

Phase 5 builds on a fully scaffolded React/PixiJS frontend from Phase 1 and a complete WebSocket backend from Phase 4. The codebase already has `MapCanvas.tsx` (grass placeholder), `ActivityFeed.tsx` (raw JSON dump), `Layout.tsx` (sidebar/canvas split), and a Zustand store with agent state types. The WebSocket hook connects, parses messages, and appends to feed — but it currently dumps raw WSMessage objects rather than routing by type.

The core challenge in this phase is threefold: (1) building the actual PixiJS scene — colored tile zones, agent circles, text labels, and interactivity with pan/zoom; (2) upgrading the Zustand store to properly dispatch `snapshot` and `agent_update` messages into structured agent state; and (3) building the inspector panel, which requires a new backend REST endpoint for recent memories (the memory store is ChromaDB-backed but not yet exposed to the browser).

The `town.json` map is 100x100 tiles with 4,845 explicit tile records (of 10,000 total). Un-recorded tiles are walkable ground (roads/paths between sectors). The sectors are: park, cafe, shop, office, stock-exchange, wedding-hall, and 10 homes (alice, bob, carla, henry, isabel, david, emma, frank, grace, james). The address hierarchy is `[sector, arena]` — there is no world-level prefix in tile addresses.

**Primary recommendation:** Implement in four sequential tasks — (1) WebSocket message dispatch and Zustand agent state, (2) PixiJS tile map rendering, (3) PixiJS agent sprites with lerp and labels, (4) activity feed upgrade and inspector panel including the new memories endpoint.

---

## Standard Stack

### Core (Already Installed — Verified)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 19.2.5 | UI framework | Already installed [VERIFIED: package.json] |
| PixiJS | 8.17.1 | 2D WebGL canvas rendering | Already installed; Graphics/Container/Text APIs confirmed available [VERIFIED: node_modules] |
| @pixi/react | 8.0.5 | React-PixiJS bridge | Already installed; exports: Application, extend, useApplication, useTick [VERIFIED: node_modules] |
| Zustand | 5.0.12 | Global state for WS messages | Already installed [VERIFIED: package.json] |
| TypeScript | 6.0.2 | Type safety | Already installed [VERIFIED: node_modules] |
| Vite | 8.0.8 | Build tool with HMR | Already installed [VERIFIED: package.json] |
| Vitest | 4.1.4 | Frontend unit testing | Already installed and passing (11 tests green) [VERIFIED: npm run test] |

### Supporting (Already Installed)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @testing-library/react | 16.0.0 | Component testing | Already used in providerSetup.test.tsx |
| jsdom | 25.0.0 | DOM environment for Vitest | Already configured in vitest.config.ts |
| Biome | 2.4.11 | Lint + format | Already configured in biome.json |

**No new npm dependencies needed for this phase.**

**Version verification:** All versions confirmed against installed `node_modules` — not training data. [VERIFIED: node_modules inspection, 2026-04-09]

---

## Architecture Patterns

### Recommended Project Structure

```
frontend/src/
├── components/
│   ├── Layout.tsx           # existing — map-dominant shell
│   ├── MapCanvas.tsx        # existing placeholder — REPLACE with full impl
│   ├── ActivityFeed.tsx     # existing placeholder — UPGRADE message rendering
│   ├── BottomBar.tsx        # existing — wire pause/resume WebSocket send
│   ├── AgentSprite.tsx      # NEW — PixiJS container: circle + label + click
│   ├── TileMap.tsx          # NEW — PixiJS Graphics for sector zones
│   └── AgentInspector.tsx   # NEW — React sidebar panel (pure CSS, not PixiJS)
├── hooks/
│   └── useWebSocket.ts      # existing — needs message routing by type
├── store/
│   └── simulationStore.ts   # existing — needs agent state dispatch logic
└── types/
    └── index.ts             # existing — WSMessageType needs full backend enum
```

### Pattern 1: @pixi/react v8 Component Structure

**What:** Every PixiJS class used in JSX must be registered via `extend()`. JSX elements use camelCase prefixed with `pixi` (e.g., `<pixiContainer>`, `<pixiGraphics>`, `<pixiText>`). Children of `<Application>` render into the PixiJS stage.

**When to use:** Any PixiJS object rendered as a React element.

```typescript
// Source: existing MapCanvas.tsx (confirmed working)
import { Application, extend } from "@pixi/react";
import { Container, Graphics, Text, TextStyle } from "pixi.js";

// Register ALL PixiJS classes you plan to use in JSX
extend({ Container, Graphics, Text });

// Inside JSX (children of <Application>):
<pixiContainer x={agentX} y={agentY} interactive onpointertap={handleClick}>
  <pixiGraphics draw={drawCircle} />
  <pixiText text={agentName} style={labelStyle} />
</pixiContainer>
```

**Critical:** `extend()` must be called once before any JSX that uses those elements. Missing a class causes a runtime error: "Could not find matching PixiJS class for [ClassName]". [VERIFIED: node_modules/@pixi/react/lib/helpers/extend.js]

### Pattern 2: useTick for Lerp Animation

**What:** `useTick` fires a callback on every PixiJS animation frame (via app.ticker). Use it to advance lerp interpolation each frame, reading from Zustand store and updating PixiJS object positions.

**When to use:** Any per-frame visual update — agent movement, animations.

```typescript
// Source: @pixi/react v8 useTick [VERIFIED: node_modules/@pixi/react/lib/hooks/useTick.js]
import { useTick } from "@pixi/react";
import { useRef } from "react";
import { useSimulationStore } from "../store/simulationStore";

function AgentSprite({ agentId }: { agentId: string }) {
  const targetPos = useSimulationStore(s => s.agents[agentId]?.position);
  const currentPos = useRef({ x: targetPos.x, y: targetPos.y });
  const containerRef = useRef<Container>(null);

  useTick(() => {
    if (!containerRef.current || !targetPos) return;
    // Lerp: move 10% of remaining distance per frame
    const LERP = 0.1;
    currentPos.current.x += (targetPos.x - currentPos.current.x) * LERP;
    currentPos.current.y += (targetPos.y - currentPos.current.y) * LERP;
    containerRef.current.x = currentPos.current.x;
    containerRef.current.y = currentPos.current.y;
  });

  return <pixiContainer ref={containerRef}>...</pixiContainer>;
}
```

**TICK_INTERVAL is 5 seconds** (confirmed in engine.py). The lerp coefficient should converge within ~1.5s of receiving a new target — coefficient ~0.06 per frame at 60fps (1 - 0.06^(60*1.5) ≈ 0). [ASSUMED: lerp coefficient value; confirmed TICK_INTERVAL=5s from engine.py]

### Pattern 3: PixiJS Graphics v8 Drawing API

**What:** PixiJS v8 changed the drawing API from v7. The `draw` prop pattern on `<pixiGraphics>` takes a callback receiving a `Graphics` instance.

```typescript
// Source: existing MapCanvas.tsx (confirmed working in codebase)
import { useCallback } from "react";

const drawZone = useCallback((g: Graphics) => {
  g.clear();
  // PixiJS v8 fill style API
  g.setFillStyle({ color: 0x4a7c59 }); // green for park
  g.rect(zoneX, zoneY, zoneWidth, zoneHeight);
  g.fill();
}, [zoneX, zoneY]); // deps for useCallback

<pixiGraphics draw={drawZone} />
```

**IMPORTANT:** In PixiJS v8, `setFillStyle({ color: 0xRRGGBB })` replaces v7's `beginFill(color)`. The `fill()` call is required after `rect()` (formerly `endFill()`). `FillStyle` class is NOT exported from pixi.js v8 — use the object literal form. [VERIFIED: `FillStyle` absent from pixi.js exports; setFillStyle confirmed in MapCanvas.tsx]

### Pattern 4: Pan and Zoom with PixiJS Container

**What:** Wrap all scene content in a single `<pixiContainer>` (the "viewport"). Pan by tracking pointerdown + pointermove delta and updating container x/y. Zoom by listening to wheel event on the canvas element (not PixiJS) and scaling the container.

```typescript
// Source: PixiJS pan/zoom pattern [ASSUMED — standard PixiJS technique]
const viewportRef = useRef<Container>(null);
const dragState = useRef<{ active: boolean; startX: number; startY: number } | null>(null);

// On the <Application> canvas wrapper div:
// onMouseDown -> dragState.active = true, record startX/Y + container position
// onMouseMove -> if dragging, update viewport.x/y
// onWheel -> scale = clamp(scale * (1 - delta*0.001), MIN_ZOOM, MAX_ZOOM)
//            adjust viewport position to zoom toward cursor

<pixiContainer ref={viewportRef} x={panX} y={panY} scale={zoom}>
  <TileMap />
  {agentIds.map(id => <AgentSprite key={id} agentId={id} />)}
</pixiContainer>
```

**Zoom min/max (Claude's discretion):** Recommended 0.3–2.0. At 0.3 zoom, 3200px canvas fits ~1067px viewport width. At 2.0 zoom, single tiles are very large (64px). [ASSUMED]

### Pattern 5: Zustand Message Dispatch (Critical Gap)

**What:** The existing `useWebSocket.ts` calls `appendFeed(msg)` for ALL messages, regardless of type. This must be replaced with proper dispatch: `snapshot` initializes all agent state, `agent_update` updates a single agent, `conversation` appends to feed, `simulation_status` updates `isPaused`.

**Current gap (verified):** `WSMessageType` in `types/index.ts` only covers `"agent_update" | "event" | "ping" | "pong" | "error"` — missing `"snapshot"`, `"conversation"`, `"simulation_status"`. The store has no `updateAgent(name, coord, activity)` action.

```typescript
// Needed in simulationStore.ts
updateAgentsFromSnapshot: (agents: SnapshotAgent[]) => set((state) => ({
  agents: Object.fromEntries(agents.map(a => [a.name, {
    id: a.name,
    name: a.name,
    position: { x: a.coord[0] * TILE_SIZE, y: a.coord[1] * TILE_SIZE },
    activity: a.activity,
    personality: [],  // populated from agent configs or separate request
  }]))
})),
updateAgentPosition: (name: string, coord: [number, number], activity: string) =>
  set((state) => ({
    agents: {
      ...state.agents,
      [name]: {
        ...state.agents[name],
        position: { x: coord[0] * TILE_SIZE, y: coord[1] * TILE_SIZE },
        activity,
      }
    }
  })),
```

**TILE_SIZE = 32** — confirmed from town.json `"tile_size": 32` and Phase 2 decision D-04. [VERIFIED: backend/data/map/town.json]

### Pattern 6: Tile Map Rendering Strategy

**What:** The town.json has 4,845 explicit tile records but 10,000 total tiles. Un-recorded tiles are walkable ground (implicit roads/paths). Rather than drawing 10,000 individual tiles, draw sector zones as filled rectangles — compute the bounding box of each sector's tiles and render one large rectangle per sector.

**Why not per-tile:** At 32px tiles, drawing 10,000 individual Graphics objects would create 10,000 PixiJS display objects — significant overhead. Zone-based rendering uses ~16 rectangles (one per sector) + road background. [ASSUMED — standard PixiJS optimization; per-tile approach confirmed impractical from tile count]

**Sector bounding boxes (derived from town.json):**
```
Zone bounding boxes must be computed at load time from town.json tiles.
Group tiles by address[0] (sector), compute min/max x and y, draw rect.
```

**Sector color palette (D-12 — Claude's discretion, soft/pastel):**
- park → `0xa8d5a2` (sage green)
- cafe → `0xd4a96a` (warm tan)
- shop → `0xc9b99a` (muted brown)
- office → `0x9bb5c8` (slate blue)
- stock-exchange → `0xc8b4e0` (soft purple)
- wedding-hall → `0xf0c8d4` (blush pink)
- home-* → `0xe8d5b7` (cream)
- roads (background) → `0xd0d0c8` (warm gray)
- collision/walls → `0x888880` (dark gray)

### Pattern 7: Auto-scroll Feed with User Override

**What:** The existing `ActivityFeed.tsx` scrolls by calling `bottomRef.current?.scrollIntoView()` on every feed update. This must be upgraded to detect user scroll-up and pause auto-scroll.

```typescript
// D-07: pause auto-scroll when user scrolls up
const containerRef = useRef<HTMLDivElement>(null);
const userScrolled = useRef(false);

const handleScroll = () => {
  const el = containerRef.current;
  if (!el) return;
  const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 10;
  userScrolled.current = !atBottom;
};

useEffect(() => {
  if (!userScrolled.current) {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }
}, [feed]); // [ASSUMED — standard pattern; no library needed]
```

### Pattern 8: Agent Inspector — Memory API

**What:** The inspector panel (D-09) needs last 5 memory entries per agent. This data lives in ChromaDB (backend), NOT in the WebSocket snapshot. A new REST endpoint is required: `GET /api/agents/{agent_name}/memories?limit=5`.

**Gap identified:** No such endpoint exists in the backend. The existing `store.py` in `backend/agents/memory/` has `get_collection(simulation_id)` but no REST-exposed retrieval function for the frontend. [VERIFIED: routers directory only has health.py, llm.py, ws.py]

**Required backend addition:**
```python
# backend/routers/agents.py (new file)
@router.get("/agents/{agent_name}/memories")
async def get_agent_memories(agent_name: str, limit: int = 5):
    """Return last N memories for an agent from ChromaDB."""
    engine = app.state.engine  # via Request injection
    collection = get_collection(engine.simulation_id)
    # ChromaDB .get() with where filter and limit
    results = collection.get(
        where={"agent_id": agent_name},
        limit=limit,
        include=["documents", "metadatas"],
    )
    return {"memories": [...]}
```

**Note:** ChromaDB's `.get()` does not support `ORDER BY` — the last 5 entries require fetching all and sorting by `created_at` metadata descending, then slicing. [VERIFIED: ChromaDB API from store.py patterns — `.get()` with where filter confirmed; ORDER BY limitation is [ASSUMED] based on ChromaDB 0.6.x API]

### Anti-Patterns to Avoid

- **PixiJS Text inside react state-triggered re-renders for every frame:** Don't create new `Text` objects on each render. Create once, mutate `.text` property via ref in `useTick`. [ASSUMED — standard PixiJS performance pattern]
- **useCallback with stale deps on draw functions:** PixiJS `draw` callback on `<pixiGraphics>` is only re-called when the callback reference changes. If deps include the full agents array, it will re-draw every tick. Pre-compute static map zones outside render.
- **Directly mutating PixiJS objects from React state updates:** PixiJS runs on its own ticker. State updates come from Zustand (triggered by WebSocket). Mutations to PixiJS objects should happen inside `useTick`, reading from Zustand store via `getState()` (not `useSimulationStore` hook — that would trigger React re-renders).
- **Drawing all 10,000 tiles as individual Graphics objects:** Creates 10,000 display objects. Use zone-based rectangle approach instead.
- **Using `appendFeed` for all WS messages:** The current hook does this. Snapshot and agent_update messages must be dispatched to agent state, not the feed array.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| WebGL 2D rendering | Custom Canvas API drawing loop | PixiJS 8 (already installed) | Batching, WebGPU fallback, sprite atlas, already tested |
| React-PixiJS integration | Manual stage management | @pixi/react v8 Application + useTick | Handles lifecycle, resize, renderer cleanup |
| Global state for WS messages | useState prop-drilling | Zustand simulationStore (already exists) | Already wired to WebSocket hook |
| Auto-scrolling log | Custom scroll detection logic | IntersectionObserver or scroll event on container | Simple scroll-position comparison suffices; no library |
| Lerp animation | Custom requestAnimationFrame loop | useTick from @pixi/react | Already on PixiJS ticker; no second RAF loop |
| REST fetch for memories | WebSocket channel | Standard fetch() to /api/agents/{name}/memories | Inspector is on-demand, not streaming; REST is correct pattern |

**Key insight:** Almost everything is already provided by installed libraries. The main work is wiring: correct message dispatch in the WebSocket hook, proper Zustand store actions, PixiJS scene construction, and one new backend endpoint.

---

## Common Pitfalls

### Pitfall 1: snapshot vs agent_update Message Dispatch

**What goes wrong:** `useWebSocket.ts` currently calls `appendFeed(msg)` for all messages. After this phase, `snapshot` must initialize all agents, `agent_update` must update one agent's position+activity, and only `conversation` and `event` messages belong in the feed.

**Why it happens:** Phase 1 built the hook before the message protocol was finalized in Phase 4. The current `WSMessageType` union is also missing `"snapshot"`, `"conversation"`, `"simulation_status"`.

**How to avoid:** Update `WSMessageType` in `types/index.ts` to match backend `WSMessage.type` Literal exactly. Add `updateAgentsFromSnapshot` and `updateAgentPosition` actions to `simulationStore.ts`. Add a `dispatchMessage()` function in `useWebSocket.ts` that routes by `msg.type`.

**Warning signs:** All agents appear at position (0,0) or don't appear at all; feed is polluted with snapshot/agent_update JSON blobs.

### Pitfall 2: PixiJS Text Objects Created on Every React Re-Render

**What goes wrong:** If agent label Text objects are created inside a React component that re-renders frequently (e.g., every Zustand tick), the PixiJS stage accumulates duplicate Text objects rather than updating existing ones.

**Why it happens:** PixiJS objects are imperative. React's reconciler doesn't know they need cleanup unless you use refs + cleanup effects.

**How to avoid:** Create each agent's Container, Graphics (circle), and Text objects once. Update `.text` property and `.x/.y` position via `useTick` using refs. Use `useEffect` with cleanup to remove from parent Container on unmount.

**Warning signs:** Growing memory usage over time, duplicate labels visible on screen.

### Pitfall 3: useCallback Dependencies Cause Static Map to Redraw Every Tick

**What goes wrong:** The tile zone Graphics `draw` callback is wrapped in `useCallback`. If agent positions or other rapidly-changing state is in its dependency array (even indirectly), it returns a new function reference every tick, forcing PixiJS to re-draw all map Graphics on every animation frame.

**Why it happens:** The draw callback calls Graphics methods, so it "needs" its deps to avoid stale closures. But if those deps change frequently, it re-renders constantly.

**How to avoid:** Keep static map drawing (tile zones) completely separate from dynamic agent rendering. Static zone data comes from a one-time parse of `town.json` — compute zone bounding boxes in a module-level constant. No dynamic deps in the draw callbacks.

**Warning signs:** CPU usage high even when agents are paused; Chrome DevTools shows repeated "draw" evaluations.

### Pitfall 4: Pan/Zoom Touch Events vs PixiJS Interactive Events Conflict

**What goes wrong:** PixiJS registers `pointerdown`/`pointermove` events for agent interactivity. If the pan/zoom drag is also on the PixiJS stage, clicks on agents may trigger both agent selection and pan drag.

**Why it happens:** Event propagation from PixiJS bubbles up to the canvas DOM element.

**How to avoid:** Track drag state with `hasDragged` flag. On `pointerup`, only fire agent selection if `hasDragged === false` (i.e., the user clicked without dragging). [ASSUMED — standard UI pattern]

**Warning signs:** Clicking an agent also pans the map; pan drag sometimes selects an agent.

### Pitfall 5: ChromaDB `.get()` Returns Unordered Results

**What goes wrong:** Calling ChromaDB `collection.get(where={"agent_id": name})` returns all memories in insertion order — but ChromaDB's EphemeralClient does not guarantee order. Fetching "last 5 memories" requires sorting by `created_at` metadata.

**Why it happens:** ChromaDB is a vector store, not a relational DB — no ORDER BY.

**How to avoid:** In the backend memories endpoint, fetch all documents for the agent, sort by `metadata.created_at` descending, slice to `limit`. [VERIFIED: ChromaDB .get() with where filter pattern from store.py; ordering limitation [ASSUMED]]

**Warning signs:** Inspector shows memories in arbitrary order, not chronological.

### Pitfall 6: Coordinate System — Tile Coords vs Pixel Coords

**What goes wrong:** Backend sends agent positions as tile coordinates `[x, y]` (e.g., `[12, 40]`). PixiJS needs pixel coordinates. Missing the multiplication by `TILE_SIZE` (32) produces agents rendered in the top-left 100x100px corner.

**Why it happens:** Two coordinate systems coexist: tile space (0–99) and pixel space (0–3200).

**How to avoid:** Define `TILE_SIZE = 32` as a module constant. Always convert: `pixelX = coord[0] * TILE_SIZE`, `pixelY = coord[1] * TILE_SIZE`. Town.json confirms `"tile_size": 32`. [VERIFIED: backend/data/map/town.json]

**Warning signs:** All agents clustered in top-left corner of the canvas.

---

## Code Examples

Verified patterns from codebase and official sources:

### Correct PixiJS v8 Fill API (from existing codebase)
```typescript
// Source: frontend/src/components/MapCanvas.tsx [VERIFIED: file exists, confirmed working]
const drawZone = useCallback((g: Graphics) => {
  g.clear();
  g.setFillStyle({ color: 0xa8d5a2 }); // NOT g.beginFill() — that's v7
  g.rect(x, y, width, height);
  g.fill();                             // NOT g.endFill() — that's v7
}, [x, y, width, height]);
```

### @pixi/react v8 extend API (from existing codebase)
```typescript
// Source: frontend/src/components/MapCanvas.tsx [VERIFIED: file exists, confirmed working]
import { Application, extend } from "@pixi/react";
import { Container, Graphics, Text } from "pixi.js";
extend({ Container, Graphics, Text }); // must call before JSX that uses these
```

### useTick signature (from installed @pixi/react)
```typescript
// Source: @pixi/react 8.0.5 useTick.js [VERIFIED: node_modules inspection]
// Option 1: pass callback directly
useTick((ticker) => { /* runs every frame */ });

// Option 2: pass options object
useTick({ callback: (ticker) => { /* ... */ }, isEnabled: true, priority: 0 });
```

### Zustand getState() for PixiJS tick callbacks
```typescript
// Source: Zustand 5.x pattern [VERIFIED: zustand 5.0.12 installed]
// Use getState() inside useTick — avoids re-renders, reads latest state
useTick(() => {
  const agents = useSimulationStore.getState().agents;
  // update PixiJS objects from agents...
});
```

### WebSocket message routing pattern (needed upgrade to existing hook)
```typescript
// Source: backend/schemas.py WSMessage type + frontend/src/hooks/useWebSocket.ts [VERIFIED]
// In onmessage handler, replace current appendFeed-for-all with:
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data) as WSMessage;
  const store = useSimulationStore.getState();
  switch (msg.type) {
    case "snapshot":
      store.updateAgentsFromSnapshot(msg.payload.agents);
      break;
    case "agent_update":
      store.updateAgentPosition(msg.payload.name, msg.payload.coord, msg.payload.activity);
      break;
    case "conversation":
      store.appendFeed(msg);
      break;
    case "simulation_status":
      store.setPaused(msg.payload.status === "paused");
      break;
    case "event":
      store.appendFeed(msg);
      break;
    // ping, pong, error: no-op or log
  }
};
```

### Pause/Resume WebSocket send (BottomBar wiring gap)
```typescript
// Source: backend/routers/ws.py + frontend/src/components/BottomBar.tsx [VERIFIED: both files]
// BottomBar.tsx currently calls setPaused(local) without sending to backend.
// Fix: the useWebSocket hook should expose a sendMessage() function
const handlePauseResume = () => {
  sendMessage({ type: isPaused ? "resume" : "pause", payload: {}, timestamp: Date.now() });
};
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PixiJS v7 `beginFill(color)` | `setFillStyle({ color })` + `fill()` | PixiJS v8 (2024) | Existing MapCanvas.tsx already uses v8 API correctly |
| @pixi/react v7 (react-pixi-fiber) | @pixi/react v8 with `extend()` | March 2025 | Already installed; `extend()` required before JSX use |
| Zustand v4 with `devtools` middleware | Zustand v5.0 (React hooks only) | 2024 | 5.0.12 installed; no middleware needed for this phase |

**Deprecated/outdated:**
- `beginFill()` / `endFill()`: v7 API, replaced by `setFillStyle()` + `fill()` in v8
- `react-pixi-fiber`: old community package, replaced by official `@pixi/react` v8
- `create-react-app`: deprecated 2023; Vite already in use

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Lerp coefficient ~0.06/frame converges in ~1.5s at 60fps for 5s tick interval | Architecture Patterns, Pattern 2 | Visual feel may be too slow/fast — easy to tune after testing |
| A2 | ChromaDB `.get()` does not support ORDER BY; requires sort-after-fetch for "last 5 memories" | Common Pitfalls, Pitfall 5 | If ChromaDB supports ordering, endpoint is simpler |
| A3 | Zoom range 0.3–2.0 appropriate for 3200x3200 canvas in typical viewport | Architecture Patterns, Pattern 4 | May need adjustment after testing on actual screen sizes |
| A4 | hasDragged flag pattern sufficient to distinguish click vs pan on agent sprites | Common Pitfalls, Pitfall 4 | Touch devices may need additional handling (pinch-zoom) |
| A5 | Zone-based bounding box rendering adequate for visual distinction without per-tile rendering | Architecture Patterns, Pattern 6 | May look blocky if sector shapes are irregular; verify against town.json bounds |

---

## Open Questions

1. **Pause/Resume WebSocket send from BottomBar**
   - What we know: BottomBar.tsx calls `setPaused(!isPaused)` (local state only). Backend expects `pause`/`resume` WSMessage. The WebSocket hook exposes no `sendMessage` method.
   - What's unclear: Should `useWebSocket` expose `sendMessage`, or should a separate hook/store action hold the WebSocket ref?
   - Recommendation: Add `sendMessage(msg: WSMessage) => void` return value to `useWebSocket`. Store it in Zustand as a ref (not state) so components can call it without re-render.

2. **Agent personality data in Zustand store**
   - What we know: `AgentState.personality` in `types/index.ts` is `string[]`, but the snapshot payload only contains `{name, coord, activity}`. Inspector (D-09) needs `innate`, `occupation`, `age` from `AgentConfig.scratch`.
   - What's unclear: Should personality data come via the snapshot (extend it), a separate REST endpoint, or be bundled into the inspector's memory endpoint response?
   - Recommendation: Extend the snapshot payload to include personality fields (innate, occupation from the `currently` field). The engine `get_snapshot()` already has access to `AgentConfig` — add scratch fields to each agent's snapshot entry.

3. **Sector address structure — world prefix**
   - What we know: Town.json tile addresses are `["park", "garden"]` not `["agent-town", "park", "garden"]`. The `tile_address_keys` are `["world", "sector", "arena"]` but actual tile records omit the world level.
   - What's unclear: This is inconsistent with the keys definition. The frontend must handle both formats or assume 2-element addresses.
   - Recommendation: When building zone bounding boxes, use `address[0]` as sector (confirmed: yields "park", "cafe", etc.). No world prefix in practice.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js / npm | Frontend build, test | Yes | (npm available — package.json exists) | — |
| Vitest | Frontend unit tests | Yes | 4.1.4 | — |
| @testing-library/react | Component tests | Yes | 16.0.0 | — |
| PixiJS | Canvas rendering | Yes | 8.17.1 | — |
| @pixi/react | React-PixiJS bridge | Yes | 8.0.5 | — |
| Backend (FastAPI) | Inspector memory endpoint | Running (assumed) | localhost:8000 | Tests mock fetch |

**All frontend dependencies verified as installed. No new installs required.** [VERIFIED: node_modules inspection]

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest 4.1.4 |
| Config file | frontend/vitest.config.ts |
| Quick run command | `cd frontend && npm run test` |
| Full suite command | `cd frontend && npm run test` |

Current baseline: 11 tests across 2 test files, all passing. [VERIFIED: npm run test output, 2026-04-09]

### Phase Requirements — Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MAP-01 | Tile map renders zone rectangles, not blank canvas | unit (store) | `cd frontend && npm run test` | Partial — store.test.ts exists; need map zone parsing test |
| MAP-02 | Agent positions update from WS agent_update messages | unit (store) | `cd frontend && npm run test` | No — need store dispatch test |
| MAP-05 | Clicking agent sets selectedAgentId in store | unit (store) | `cd frontend && npm run test` | No — need setSelectedAgent test for click flow |
| DSP-01 | Feed entries formatted with agent name + action + timestamp | unit (component) | `cd frontend && npm run test` | No — ActivityFeed needs upgrade + test |
| DSP-02 | Agent label text updates when activity changes in store | unit (store) | `cd frontend && npm run test` | No — need updateAgentPosition test |

**PixiJS components are NOT unit-testable with jsdom** (WebGL requires a real browser). Component tests for MapCanvas, AgentSprite, and TileMap should be smoke tests (import without crash) or skipped. Store logic and React-only components (AgentInspector, ActivityFeed) can be fully tested. [ASSUMED — WebGL in jsdom not supported]

### Sampling Rate
- **Per task commit:** `cd frontend && npm run test`
- **Per wave merge:** `cd frontend && npm run test`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `frontend/src/tests/dispatch.test.ts` — covers MAP-02, DSP-02: test `updateAgentsFromSnapshot`, `updateAgentPosition`, `setPaused` store actions
- [ ] `frontend/src/tests/activityFeed.test.tsx` — covers DSP-01: test formatted feed entries (agent name + action + timestamp format)
- [ ] `frontend/src/tests/inspector.test.tsx` — covers MAP-05: test inspector renders name/traits/activity; mock fetch for memories

---

## Security Domain

> `security_enforcement` not explicitly set to false in config.json — including this section.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Frontend has no auth (single-user, local) |
| V3 Session Management | No | No session — localStorage stores provider config only |
| V4 Access Control | No | No multi-user access control |
| V5 Input Validation | Yes | Agent name from WS payload used in DOM text — must sanitize before rendering |
| V6 Cryptography | No | No crypto operations |

### Known Threat Patterns for React + PixiJS

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS via agent name in Text labels | Tampering | PixiJS Text is canvas-rendered (not innerHTML) — no DOM injection risk; React JSX string interpolation in inspector uses textContent, not dangerouslySetInnerHTML |
| Memory endpoint exposes all agent memories | Information Disclosure | Endpoint is localhost-only (single-user, no auth needed for v1) |
| WebSocket message injection | Tampering | Backend validates WSMessage via Pydantic; frontend trusts messages from localhost:8000 only |

**No additional security controls needed beyond existing patterns.** Agent name is only rendered in PixiJS canvas (not DOM innerHTML) and React text nodes (which escape by default). [VERIFIED: PixiJS Text is WebGL canvas — no DOM injection; React text escaping is default behavior]

---

## Sources

### Primary (HIGH confidence)
- `frontend/package.json` — installed library versions
- `frontend/node_modules/@pixi/react/lib/` — useTick, useApplication, Application, extend APIs
- `frontend/node_modules/pixi.js/` — PixiJS v8 exports (Graphics, Container, Text, Ticker confirmed)
- `frontend/src/` — existing components, hooks, store, types (all read directly)
- `backend/data/map/town.json` — tile structure, sector addresses, tile_size=32, 100x100 grid
- `backend/schemas.py` — WSMessage type Literal, AgentConfig, AgentScratch schemas
- `backend/simulation/engine.py` — TICK_INTERVAL=5, get_snapshot() payload structure, AgentState fields
- `backend/routers/ws.py` — snapshot-on-connect flow, pause/resume protocol

### Secondary (MEDIUM confidence)
- `backend/agents/memory/store.py` — ChromaDB .get() API with where filter; basis for memories endpoint design

### Tertiary (LOW confidence)
- Lerp coefficient calculation (A1) — standard animation math, not verified against running simulation
- ChromaDB ordering limitation (A2) — inferred from absence of ORDER BY in store.py, not official docs
- Zoom range recommendation (A3) — calculated from canvas/viewport geometry, not user-tested
- hasDragged click/pan disambiguation (A4) — standard UI pattern, not verified in PixiJS context

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all installed versions confirmed from node_modules
- Architecture: HIGH — existing codebase confirms @pixi/react v8 patterns work; WSMessage protocol confirmed from backend
- Pitfalls: MEDIUM — most verified from codebase; coordinate pitfall and ChromaDB ordering have evidence but not full docs verification

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (stable stack — PixiJS v8 and @pixi/react v8 APIs unlikely to change)
