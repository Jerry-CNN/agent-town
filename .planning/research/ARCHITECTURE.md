# Architecture Research

**Domain:** Pixel-art RPG rendering upgrade — PixiJS v8 tileset + animated sprite integration
**Researched:** 2026-04-11
**Confidence:** HIGH (existing code read directly; reference impl inspected; pixi-tiledmap v2 docs verified)

---

## What This Document Covers

This is a focused integration analysis — not a greenfield architecture. The question is: given the existing React 19 + PixiJS v8 + @pixi/react v8 pipeline, what changes are required to port CuteRPG tilesets, a new Tiled-authored map, and per-agent animated sprite sheets? Everything below is grounded in direct inspection of the running codebase and reference implementation.

---

## Current System Overview

```
┌──────────────────────────────────────────────────────────────┐
│  React Layer                                                  │
│  App.tsx → Layout.tsx → MapCanvas.tsx                         │
│  ├── <Application> (@pixi/react PixiJS wrapper)               │
│  │   ├── <pixiContainer x={pan} y={pan} scale={0.45}>         │
│  │   │   ├── <TileMap />          ← Graphics API draws rects  │
│  │   │   └── <AgentSprite /> ×N   ← Graphics circles + lerp  │
│  │   └── [pan/zoom via React pointer events on wrapper div]   │
│  └── Sidebar: ActivityFeed, AgentInspector, BottomBar         │
├──────────────────────────────────────────────────────────────┤
│  State Layer                                                   │
│  simulationStore.ts (Zustand)                                  │
│  ├── agents: Record<name, AgentState>                          │
│  │   └── position: {x, y}  ← pixel coords (tile * 32)         │
│  └── useWebSocket.ts → updateAgentPosition(coord)              │
├──────────────────────────────────────────────────────────────┤
│  Data (Static)                                                 │
│  frontend/src/data/town.json   ← 100×100 tile grid            │
│  backend/data/map/town.json    ← same data, backend canonical │
└──────────────────────────────────────────────────────────────┘
```

### What the Current Code Actually Does

**TileMap.tsx** — Pure PixiJS Graphics API. At module load, it pre-computes sector bounding boxes and collision tile coordinates from `town.json`. In `drawMap()`, it draws: (1) road background rectangle, (2) collision tiles as dark rects, (3) sector zones as colored rects with strokes, then renders pixiText labels per sector. The draw callback has empty deps — stable across all re-renders. No textures, no sprites.

**AgentSprite.tsx** — Each agent is a PixiJS Container with: a colored circle (Graphics), initial letter (Text), activity text with pill background (Text + Graphics), and a name label. Position updates happen imperatively in `useTick()` reading `getState()` directly — bypasses React re-render on every frame. Lerp coefficient 0.08, ~1.5s convergence at 60fps.

**Coordinate system** — Backend sends `[tile_x, tile_y]` as integers. `updateAgentPosition` in the store multiplies by `TILE_SIZE = 32` to get pixel coords. `AgentState.position` is `{ x: tileX * 32, y: tileY * 32 }` — top-left corner of tile, not center. No changes needed to this protocol.

---

## Target System Overview (Post-Upgrade)

```
┌──────────────────────────────────────────────────────────────┐
│  React Layer                                                  │
│  MapCanvas.tsx [MODIFIED: asset-loading gate]                 │
│  ├── <Application>                                            │
│  │   ├── <pixiContainer x={pan} y={pan} scale>                │
│  │   │   ├── <TiledMapBackground />  ← NEW: layers 0-9        │
│  │   │   ├── <AgentSprite /> ×N      ← MODIFIED: AnimatedSprite│
│  │   │   └── <TiledMapForeground />  ← NEW: Foreground L1+L2  │
│  │   └── [pan/zoom unchanged]                                 │
│  └── Sidebar [MODIFIED: pixel-art typography/colors]          │
├──────────────────────────────────────────────────────────────┤
│  Asset Loading Layer (NEW)                                     │
│  useAssets.ts hook                                             │
│  ├── pixi-tiledmap extension registered once at app init       │
│  ├── Assets.loadBundle('map') → town.tmj + all tileset PNGs   │
│  └── Assets.loadBundle('agents') → per-agent sprite.json      │
│      sheetCache: Map<agentName, Spritesheet> (module-level)   │
├──────────────────────────────────────────────────────────────┤
│  State Layer [UNCHANGED]                                       │
│  simulationStore.ts — position in pixel coords, unchanged      │
│  useWebSocket.ts — coord protocol unchanged                    │
├──────────────────────────────────────────────────────────────┤
│  Data (Static) [REPLACED]                                      │
│  frontend/public/assets/tilemap/town.tmj  ← new Tiled map     │
│  frontend/public/assets/tilemap/*.png     ← CuteRPG + rooms   │
│  frontend/public/assets/agents/sprite.json ← shared atlas     │
│  frontend/public/assets/agents/*/texture.png ← per-agent PNG  │
│  backend/data/map/town.json               ← regenerated from  │
│                                             new Tiled map      │
└──────────────────────────────────────────────────────────────┘
```

---

## Component Boundary Map: New vs Modified vs Unchanged

| Component | Status | Change Summary |
|-----------|--------|----------------|
| `MapCanvas.tsx` | MODIFIED | Add async asset gate; split TileMap into background/foreground wrappers |
| `TileMap.tsx` | REPLACED | Delete; new `TiledMapRenderer.tsx` uses pixi-tiledmap |
| `AgentSprite.tsx` | MODIFIED | Replace Graphics circle with `AnimatedSprite`; add direction state ref |
| `simulationStore.ts` | UNCHANGED | Position protocol identical |
| `useWebSocket.ts` | UNCHANGED | Backend message format unchanged |
| `types/index.ts` | MODIFIED (minor) | Add optional `facing` field to `AgentState` for future use |
| `useAssets.ts` | NEW | PixiJS Assets.loadBundle for tilemap + sprite atlases; module-level sheet cache |
| `TiledMapRenderer.tsx` | NEW | pixi-tiledmap container split into background/foreground props |
| Layout, ActivityFeed, BottomBar, AgentInspector | MODIFIED (minor) | CSS/font changes for pixel-art aesthetic |
| Backend `world.py` / `town.json` | REGENERATED | Re-export from new Tiled map; same JSON schema |

---

## Data Flow Changes

### Tilemap Rendering Flow

**Current:**
```
town.json (static import) → computeSectorBounds() at module load
                          → Graphics API draw callback (stable, empty deps)
                          → PixiJS renders colored rects + text labels
```

**Target:**
```
town.tmj (runtime fetch via Assets.loadBundle)
    → pixi-tiledmap loader resolves all tileset PNGs in parallel
    → returns { container } with one child per Tiled layer
    → split children by layer name:
         backgroundContainer: layers 0-9 (rendered below agents)
         foregroundContainer: Foreground L1, Foreground L2 (rendered above agents)
    → metadata/invisible layers (Collisions, Arena Blocks, etc.) are not rendered
      because Tiled marks them visible: false — pixi-tiledmap respects this flag
```

The key change: tilemap is now a runtime async asset load, not a synchronous static import. This requires a loading state in MapCanvas before any PixiJS scene tree renders.

### Agent Rendering Flow

**Current:**
```
AgentState.position {x, y}
  → useTick lerp → containerRef.x, containerRef.y
  → Graphics circle + Text labels (name, activity)
```

**Target:**
```
AgentState.position {x, y}
  → useTick lerp → containerRef.x, containerRef.y
  → derive facing direction from lerp delta (no backend change)
  → AnimatedSprite.textures = sheet.animations[`${facing}-walk`] when moving
  → AnimatedSprite.textures = [sheet.textures[facing]] when idle
  → AnimatedSprite.play() / .stop() per frame
  + Text labels for name/activity (unchanged position logic)
```

Direction is derived in `useTick` by comparing lerp current position to target. If `|target.x - current.x| >= |target.y - current.y|`, the dominant axis determines `left`/`right`; otherwise `up`/`down`. If delta magnitude < 0.5px, agent is idle.

### Position Protocol (Unchanged)

Backend → WebSocket `agent_update` → `{ name, coord: [tile_x, tile_y], activity }` → `updateAgentPosition(name, coord, activity)` → `position: { x: coord[0] * 32, y: coord[1] * 32 }`.

No backend changes required for the pixel-art upgrade.

---

## Integration Point 1: pixi-tiledmap

### What pixi-tiledmap v2 Does

pixi-tiledmap v2.2.0 (released April 2026) is a PixiJS v8 `Assets` extension with a built-in Tiled JSON + TMX XML parser. Register it once at app init:

```typescript
import { extensions } from 'pixi.js';
import { tiledMapLoader } from 'pixi-tiledmap';
extensions.add(tiledMapLoader);
```

Then load:

```typescript
const { container } = await Assets.load('assets/tilemap/town.tmj');
```

It returns a PixiJS `Container` with one child per visible Tiled layer. All tileset images referenced in the TMJ are resolved in parallel automatically — no manual tileset registration needed. Supports embedded tilesets (image paths relative in the JSON) and external `.tsj`/`.tsx` files. It respects the Tiled `visible: false` flag, so metadata layers (Collisions, Arena Blocks, Sector Blocks, etc.) are excluded from the container automatically.

### Layer Splitting for Agent Z-Depth

Agents must render between the base map layers and the foreground (trees, roofs, overhangs). Split the pixi-tiledmap container by layer name:

```typescript
const { container } = await Assets.load('assets/tilemap/town.tmj');
const bgContainer = new Container();
const fgContainer = new Container();

for (const child of container.children) {
  const name = child.label; // pixi-tiledmap sets label to the Tiled layer name
  if (name === 'Foreground L1' || name === 'Foreground L2') {
    fgContainer.addChild(child);
  } else {
    bgContainer.addChild(child);
  }
}
```

Store `bgContainer` and `fgContainer` at module scope (not in React state). `TiledMapRenderer` receives a `layer="background"|"foreground"` prop and renders the corresponding container via a `useEffect` that calls `pixiParentRef.current.addChild(...)`.

### Tileset Constraints

The reference tilemap has 18 embedded tilesets, some very large (interiors_pt1: 512×10016px, ~2MB GPU). WebGL guarantees minimum 8 texture units per draw call; most desktop browsers support 16-32. pixi-tiledmap uses `CompositeTilemap` internally to batch across texture unit limits. For the reference map this works on desktop hardware. A new Agent Town-specific map with fewer/smaller interior tilesets will have lower memory footprint.

**Size concern for the new map:** The reference `tilemap.json` is 3.5MB. For the new Agent Town map, export from Tiled with tilesets embedded (`Embed Tilesets` option). A 100×100 map with 8-10 tilesets will be roughly 0.5-1.5MB — acceptable as a runtime fetch with a loading overlay.

---

## Integration Point 2: Sprite Sheet Atlas

### Reference Format vs PixiJS Format

The reference `sprite.json` is generated by Atlas Packer Gamma (Phaser format). It uses a `frames` **array**. PixiJS Assets requires `frames` as a **dictionary** plus an `animations` dictionary. This is a one-time conversion, not a runtime concern.

**Reference format (Phaser atlas):**
```json
{
  "frames": [
    { "filename": "down-walk.000", "frame": { "w": 32, "h": 32, "x": 0, "y": 0 } }
  ]
}
```

**PixiJS Assets format (`ISpritesheetData`):**
```json
{
  "frames": {
    "down-walk.000": { "frame": { "x": 0, "y": 0, "w": 32, "h": 32 } },
    "down-walk.001": { "frame": { "x": 32, "y": 0, "w": 32, "h": 32 } },
    "down-walk.002": { "frame": { "x": 64, "y": 0, "w": 32, "h": 32 } },
    "down-walk.003": { "frame": { "x": 32, "y": 0, "w": 32, "h": 32 } },
    "down":          { "frame": { "x": 32, "y": 0, "w": 32, "h": 32 } }
  },
  "animations": {
    "down-walk":  ["down-walk.000", "down-walk.001", "down-walk.002", "down-walk.003"],
    "left-walk":  ["left-walk.000", "left-walk.001", "left-walk.002", "left-walk.003"],
    "right-walk": ["right-walk.000", "right-walk.001", "right-walk.002", "right-walk.003"],
    "up-walk":    ["up-walk.000",   "up-walk.001",   "up-walk.002",   "up-walk.003"],
    "down": ["down"], "left": ["left"], "right": ["right"], "up": ["up"]
  },
  "meta": { "image": "texture.png", "size": { "w": 96, "h": 128 }, "scale": 1 }
}
```

Write a Python conversion script, output the PixiJS-compatible `sprite.json` once, commit to `frontend/public/assets/agents/`. Frame coordinates come directly from the inspected reference (96×128px texture, 32×32 tiles, 3-column layout: columns = walk-000, idle, walk-002).

### Per-Agent Loading Pattern

All agents share identical frame layout — only the texture PNG differs. Load each agent's atlas separately using `data.imageFilename` override:

```typescript
// In useAssets.ts — run before PixiJS scene mounts
for (const agentName of AGENT_NAMES) {
  Assets.add({
    alias: `agent-${agentName}`,
    src: 'assets/agents/sprite.json',          // shared layout
    data: { imageFilename: `assets/agents/${agentName}/texture.png` }
  });
}
const sheets = await Assets.loadBundle('agents');
// sheets is Record<alias, Spritesheet>
```

After loading, cache sheets at module scope:

```typescript
const sheetCache = new Map<string, Spritesheet>();
for (const [alias, sheet] of Object.entries(sheets)) {
  const agentName = alias.replace('agent-', '');
  sheetCache.set(agentName, sheet);
}
```

### AnimatedSprite Direction Logic in AgentSprite.tsx

```typescript
const animSpriteRef = useRef<AnimatedSprite | null>(null);
const facingRef = useRef<'down' | 'left' | 'right' | 'up'>('down');

useTick(() => {
  const agent = useSimulationStore.getState().agents[agentId];
  if (!agent || !containerRef.current || !animSpriteRef.current) return;

  // Lerp (unchanged)
  const cur = currentPosRef.current;
  const target = agent.position;
  cur.x += (target.x - cur.x) * LERP;
  cur.y += (target.y - cur.y) * LERP;
  containerRef.current.x = cur.x;
  containerRef.current.y = cur.y;

  // Direction + animation
  const dx = target.x - cur.x;
  const dy = target.y - cur.y;
  const moving = Math.abs(dx) > 0.5 || Math.abs(dy) > 0.5;

  if (moving) {
    const newFacing = Math.abs(dx) >= Math.abs(dy)
      ? (dx > 0 ? 'right' : 'left')
      : (dy > 0 ? 'down' : 'up');

    if (newFacing !== facingRef.current) {
      facingRef.current = newFacing;
      const sheet = getAgentSheet(agentId);
      if (sheet) {
        animSpriteRef.current.textures = sheet.animations[`${newFacing}-walk`];
        animSpriteRef.current.play();
      }
    } else if (!animSpriteRef.current.playing) {
      animSpriteRef.current.play();
    }
  } else if (animSpriteRef.current.playing) {
    animSpriteRef.current.stop();
    const sheet = getAgentSheet(agentId);
    if (sheet) {
      animSpriteRef.current.textures = [sheet.textures[facingRef.current]];
    }
  }
});
```

`getAgentSheet` reads from the module-level `sheetCache` — synchronous, O(1), no async in the hot path.

---

## Integration Point 3: New Town Map in Tiled

### What Needs to Be Rebuilt

The reference map is "The Ville" — a Chinese university town (professors' offices, bar, dormitories). Agent Town needs different locations: stock exchange, wedding hall, park, homes for 8 named agents, cafe, office building. The reference map layout cannot be reused, but the tileset PNGs can be copied directly.

**Map authoring spec for Agent Town:**
- Grid: 100×100 tiles at 32px (matches existing town.json and coordinate system)
- Export format: Tiled JSON (`.tmj`), tilesets embedded
- Layer structure: match the reference 10 visible + metadata layers (backend expects Sector/Arena/Collision layer names for map parsing)
- Sector names: must match the existing `backend/data/map/buildings.json` keys

### Backend Map Regeneration

After designing the new map in Tiled, regenerate `backend/data/map/town.json` from the TMJ:
1. Parse the Sector Blocks and Arena Blocks layers (invisible metadata layers) to extract tile addresses
2. Parse the Collisions layer to extract collision flags
3. Output in the existing town.json schema: `{ tiles: [{ coord, address, collision }] }`

The existing backend `world.py` `Tile` and `Maze` classes work against town.json — they do not need to change. The regeneration is a one-time Python script task.

---

## Recommended File Structure Changes

```
frontend/
├── public/
│   └── assets/                        ← NEW: runtime-fetched assets (not bundled)
│       ├── tilemap/
│       │   ├── town.tmj                ← New Tiled JSON (Agent Town map)
│       │   ├── CuteRPG_Field_B.png
│       │   ├── CuteRPG_Field_C.png
│       │   ├── CuteRPG_Village_B.png
│       │   ├── CuteRPG_Harbor_C.png
│       │   ├── CuteRPG_Forest_B.png    (and other CuteRPG variants if used)
│       │   ├── Room_Builder_32x32.png
│       │   ├── interiors_pt1.png ... interiors_pt5.png
│       │   └── blocks_1.png
│       └── agents/
│           ├── sprite.json             ← PixiJS-format atlas (converted from reference)
│           ├── alice/texture.png
│           ├── bob/texture.png
│           ├── carla/texture.png
│           ├── david/texture.png
│           ├── emma/texture.png
│           └── [remaining agents]
├── src/
│   ├── components/
│   │   ├── MapCanvas.tsx               ← MODIFIED: add asset gate
│   │   ├── TiledMapRenderer.tsx        ← NEW: replaces TileMap.tsx
│   │   ├── AgentSprite.tsx             ← MODIFIED: AnimatedSprite
│   │   └── [others unchanged]
│   ├── hooks/
│   │   ├── useWebSocket.ts             ← UNCHANGED
│   │   └── useAssets.ts               ← NEW: loadBundle + sheetCache
│   ├── data/
│   │   └── town.json                   ← REGENERATED from new Tiled map
│   └── types/
│       └── index.ts                    ← MINOR: optional facing field
```

**Why `public/assets/` not `src/data/`:** Tileset PNGs total 10-30MB. Vite would reject or inline them into the JS bundle. `public/` is served as static files, referenced by URL at runtime. PixiJS Assets caches them in GPU memory after first load.

**Why `sprite.json` is shared:** All agent sprites use identical frame coordinates at identical pixel positions. Per-agent atlases reference the shared JSON but each supply their own PNG path via `data.imageFilename`.

---

## Architectural Patterns

### Pattern 1: Assets-First Gate in MapCanvas

**What:** MapCanvas renders a loading overlay until all assets resolve, then mounts the full PixiJS scene tree.

**When to use:** Required. @pixi/react children cannot render before their textures exist. Mounting `TiledMapRenderer` or `AgentSprite` before their assets are loaded throws in PixiJS v8.

**Implementation sketch:**

```typescript
function MapCanvas() {
  const [assetsReady, setAssetsReady] = useState(false);

  useEffect(() => {
    loadAllGameAssets().then(() => setAssetsReady(true));
  }, []);

  if (!assetsReady) {
    return <div style={{ ...mapStyles }}>Loading map...</div>;
  }

  return (
    <div ref={containerRef} style={...} onPointerDown={...} ...>
      <Application background={BG_COLOR} resizeTo={containerRef}>
        <pixiContainer x={offsetX} y={offsetY} scale={scale}>
          <TiledMapRenderer layer="background" />
          {agentIds.map((id, i) => (
            <AgentSprite key={id} agentId={id} colorIndex={i} onSelect={handleSelect} />
          ))}
          <TiledMapRenderer layer="foreground" />
        </pixiContainer>
      </Application>
    </div>
  );
}
```

### Pattern 2: Module-Level Sheet Cache

**What:** Agent sprite sheets loaded once into a `Map<agentName, Spritesheet>` at module scope, not in component state or Zustand.

**Why:** `useTick` fires 60 times/second. Storing sheets in Zustand or React state would cause re-renders or stale closures. Module-level Map is synchronous, O(1), no React overhead.

```typescript
// useAssets.ts
const sheetCache = new Map<string, Spritesheet>();

export async function loadAllGameAssets(): Promise<void> {
  extensions.add(tiledMapLoader);

  // Register tilemap
  Assets.add({ alias: 'tilemap', src: '/assets/tilemap/town.tmj' });

  // Register all agent atlases
  for (const name of AGENT_NAMES) {
    Assets.add({
      alias: `agent-${name}`,
      src: '/assets/agents/sprite.json',
      data: { imageFilename: `/assets/agents/${name}/texture.png` }
    });
  }

  // Load all in parallel
  await Promise.all([
    Assets.load('tilemap').then(({ container }) => {
      splitTiledContainer(container); // populates bgContainer / fgContainer module vars
    }),
    Assets.loadBundle('agents').then((sheets) => {
      for (const [alias, sheet] of Object.entries(sheets)) {
        sheetCache.set(alias.replace('agent-', ''), sheet as Spritesheet);
      }
    }),
  ]);
}

export function getAgentSheet(name: string): Spritesheet | undefined {
  return sheetCache.get(name);
}
```

### Pattern 3: Layer Name-Based Split (Not Index-Based)

**What:** Split pixi-tiledmap container children by checking `child.label` (the Tiled layer name), not by array index.

**Why:** If the Tiled map is re-exported and layer order shifts, index-based splitting silently produces wrong z-ordering. Name-based is stable across re-exports.

---

## Build Order

Build in this sequence — each step unblocks the next.

**Step 1 — Asset pipeline (no code, unblocks all render work)**
- Copy CuteRPG tileset PNGs from reference to `frontend/public/assets/tilemap/`
- Run conversion script: reference `sprite.json` (Phaser format) → PixiJS `ISpritesheetData` format
- Assign one agent texture PNG per named agent (8 agents)
- Result: all assets are in place and fetchable from the Vite dev server

**Step 2 — New town map in Tiled (critical path, longest task)**
- Author Agent Town-specific map in Tiled editor using CuteRPG tilesets
- Must include: stock exchange, wedding hall, park, homes (8), cafe, office + metadata layers (Sector/Arena/Collision blocks)
- Export as `town.tmj` to `frontend/public/assets/tilemap/`
- Write Python script to parse TMJ metadata layers → regenerate `backend/data/map/town.json`
- Verify sector/arena addresses match the backend 3-level scheme and existing agent JSON files

**Step 3 — `useAssets.ts` hook (depends on Step 1 assets being present)**
- Register pixi-tiledmap extension
- Implement `loadAllGameAssets()` with parallel bundle loading
- Implement `getAgentSheet(name)` from module-level cache
- Implement `getBgContainer()` / `getFgContainer()` for TiledMapRenderer

**Step 4 — `TiledMapRenderer.tsx` (depends on Step 3)**
- Receive `layer="background"|"foreground"` prop
- In `useEffect`, call `pixiParentRef.current.addChild(getBgContainer())` or `getFgContainer()`
- Handles the fact that pixi-tiledmap containers are imperative, not declarative

**Step 5 — `MapCanvas.tsx` modifications (depends on Steps 3-4)**
- Add assets-ready gate with loading overlay
- Replace `<TileMap />` with `<TiledMapRenderer layer="background" />` and `<TiledMapRenderer layer="foreground" />`
- Agent sprites render between the two TiledMapRenderer components

**Step 6 — `AgentSprite.tsx` modifications (depends on Step 3 for sheet access)**
- Replace `drawCircle` Graphics with `AnimatedSprite` using `getAgentSheet(agentId).animations`
- Add `facingRef`, direction detection logic in `useTick`
- Add texture swap on direction change
- Keep name/activity Text labels unchanged (repositioned relative to sprite center)

**Step 7 — UI polish (no render dependencies, can parallel with Steps 3-6)**
- Update sidebar/feed typography to harmonize with pixel-art palette
- Adjust font choices, border-radius, color values to match map aesthetic

**Critical path:** Step 2 (Tiled map authoring) is the longest task and is the prerequisite for generating the backend map data. Steps 3-6 can be developed with placeholder assets (even a simple 10×10 test map) and integrated once the real map is ready.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Static Import of the New Map JSON

**What people do:** `import mapData from '../data/town.tmj'` — treat the new Tiled file like the existing town.json static import.

**Why it's wrong:** The tilemap JSON with embedded tilesets will be 500KB–2MB. Vite will either reject it or inline it into the JS bundle, adding unacceptable parse time. The tileset PNGs themselves (10-30MB total) cannot be statically imported at all.

**Do this instead:** Place everything in `frontend/public/assets/`, reference by URL, use `Assets.load` at runtime.

### Anti-Pattern 2: Async Operations in useTick

**What people do:** Call `Assets.load(agentName)` inside `useTick` to lazily fetch sprite sheets.

**Why it's wrong:** `useTick` fires 60 times/second. Async calls inside it create unhandled promises and potential memory leaks. PixiJS deduplicates loads, but the overhead is still unacceptable on the animation hot path.

**Do this instead:** All assets load before the PixiJS scene mounts (assets gate). `getAgentSheet(name)` in `useTick` is a synchronous cache read.

### Anti-Pattern 3: Mounting AnimatedSprite with Empty Textures

**What people do:** Render `AgentSprite` immediately and let it show "nothing" until the sheet arrives.

**Why it's wrong:** `new AnimatedSprite([])` throws in PixiJS v8 — an empty textures array is invalid.

**Do this instead:** The assets gate ensures sheets are fully loaded before any PixiJS components mount. `AgentSprite` can assume `getAgentSheet(agentId)` returns a valid Spritesheet.

### Anti-Pattern 4: Reusing the Reference tilemap.json Directly

**What people do:** Copy the reference `tilemap.json` (The Ville — 140×100) to avoid Tiled editor work.

**Why it's wrong:** The reference map is designed for a Chinese university town. Its sector/arena addresses (`林氏家族的房子`, `霍布斯咖啡馆`) will not match Agent Town's backend buildings.json or agent JSON files. The map is also 140×100 vs Agent Town's 100×100 coordinate space — all agent coordinates will be out of bounds.

**Do this instead:** Reuse the tileset PNG assets (just copy the PNG files). Author the Agent Town layout from scratch in Tiled.

### Anti-Pattern 5: Index-Based Layer Splitting

**What people do:** Split pixi-tiledmap container children by position: `container.children[0..9]` = background, `container.children[10..11]` = foreground.

**Why it's wrong:** Re-exporting from Tiled or adding/removing layers silently shifts indices, causing wrong z-ordering with no error.

**Do this instead:** Split by `child.label` matching the Tiled layer name string. Names are stable across re-exports.

### Anti-Pattern 6: Storing Spritesheet References in Zustand

**What people do:** Add `agentSheets: Record<string, Spritesheet>` to `simulationStore` so components can subscribe.

**Why it's wrong:** Spritesheet objects are large non-serializable GPU objects. Storing them in Zustand triggers re-renders on every subscriber component when the store updates for any reason (agent position, feed updates, etc.).

**Do this instead:** Module-level `Map<string, Spritesheet>` in `useAssets.ts`. Export a `getAgentSheet(name)` accessor. Zero React involvement.

---

## Scaling Considerations

This is a single-user simulation browser app. The scaling concerns are GPU memory and load time, not server throughput.

| Concern | At 8 agents (target) | At 25 agents (stretch) |
|---------|---------------------|------------------------|
| AnimatedSprite GPU draw calls | 8 sprites, trivial | 25 — still well within WebGL budget |
| Tileset texture memory | ~15-30MB GPU (CuteRPG + interiors) | Same — tilemap is fixed |
| useTick lerp + direction logic | 8 iterations <0.1ms | 25 — still <0.5ms per frame |
| Sprite sheet load time | 8 × 96×128px ≈ 0.3MB total | 25 × same — still negligible |
| pixi-tiledmap layer rendering | 10 visible layers, static after load | Same |

Initial asset load time (~3-5s for all tileset PNGs) is the only UX concern — mitigated by the assets-ready loading overlay before the PixiJS scene mounts.

---

## Sources

- pixi-tiledmap v2.2.0 README: https://github.com/riebel/pixi-tiledmap
- pixi-tiledmap npm: https://www.npmjs.com/package/pixi-tiledmap
- PixiJS v8 AnimatedSprite API: https://pixijs.download/dev/docs/scene.AnimatedSprite.html
- PixiJS v8 Spritesheet API: https://pixijs.download/dev/docs/assets.Spritesheet.html
- PixiJS v8 Assets guide: https://pixijs.com/8.x/guides/components/assets
- @pixi/tilemap CompositeTilemap (texture unit limits): https://userland.pixijs.io/tilemap/docs/CompositeTilemap.html
- @pixi/react v8 useTick docs: https://react.pixijs.io/hooks/useTick/
- Reference implementation Phaser loading code: GenerativeAgentsCN/generative_agents/frontend/templates/main_script.html
- Reference sprite.json (Phaser atlas format): GenerativeAgentsCN/generative_agents/frontend/static/assets/village/agents/sprite.json
- Reference tilemap.json (17 layers, 18 tilesets, 140×100): GenerativeAgentsCN/generative_agents/frontend/static/assets/village/tilemap/

---

*Architecture research for: Agent Town v1.2 Pixel-Art RPG Rendering Upgrade*
*Researched: 2026-04-11*
