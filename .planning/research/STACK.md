# Stack Research

**Domain:** PixiJS v8 pixel-art tileset rendering — addendum for v1.2
**Researched:** 2026-04-11
**Confidence:** HIGH for pixi-tiledmap (verified via npm + GitHub), HIGH for PixiJS v8 Assets/AnimatedSprite API, MEDIUM for AssetPack pipeline (plugin API stable but less commonly paired with PixiJS v8 in the wild)

> This document **extends** the v1.1 STACK.md. The base stack (FastAPI, PixiJS 8.17.1, @pixi/react 8.0.5, Zustand, etc.) is unchanged and validated.
> Sections below cover only what is NEW for v1.2: tileset rendering, Tiled map loading, sprite sheet animation, and the asset pipeline.

---

## What Is New for v1.2

| Cluster | What Changes | New Dependencies? |
|---------|-------------|-------------------|
| Tiled map rendering | Replace Graphics primitives with tileset sprites from Tiled JSON | `pixi-tiledmap` |
| Animated agent sprites | Replace colored circles with 4-direction walk cycles from texture atlas | None — `Assets` + `AnimatedSprite` are in PixiJS 8.17.1 |
| Viewport pan/zoom | Replace static fit-to-screen with draggable/zoomable camera | `pixi-viewport` |
| Asset pipeline | Compress and pack raw PNGs into optimized sprite sheet atlases at build time | `@assetpack/core` (dev-only) |

---

## Core New Libraries

### pixi-tiledmap

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| pixi-tiledmap | 2.2.0 | Parse and render Tiled JSON maps in PixiJS v8 | Ground-up rewrite targeting PixiJS v8's `Assets`/`LoadParser` extension system. Zero runtime dependencies. Full layer-type support (tile, image, object, group). Handles multiple tilesets, flip/rotation flags, transparent color keying — all of which the reference's `tilemap.json` uses. Published April 2026. |

**Verified:** `npm view pixi-tiledmap` returns version 2.2.0, peer dep `pixi.js: ^8.0.0`, last modified 2026-04-12.

**Reference map compatibility:** The reference `tilemap.json` uses 18 tilesets (CuteRPG series + interiors + blocks), 17 layers, `transparentColor: "#ff00ff"`, and 32x32 tiles at 100x100 grid — all within pixi-tiledmap v2's documented feature set (transparent color keying, multi-tileset, multi-layer).

**Integration with @pixi/react:**

pixi-tiledmap is framework-agnostic and returns a standard PixiJS `Container`. The correct integration pattern inside @pixi/react:

```typescript
import { extensions, Assets } from 'pixi.js';
import { tiledMapLoader, TiledMap } from 'pixi-tiledmap';
import { useApplication, useExtend } from '@pixi/react';

// Register the loader once (in App.tsx or a setup hook)
extensions.add(tiledMapLoader);

// Inside a component:
const { app } = useApplication();
useEffect(() => {
  Assets.load('assets/tilemap.json').then(({ container }: { container: TiledMap }) => {
    app.stage.addChild(container);
  });
  return () => { app.stage.removeChildren(); };
}, [app]);
```

The map returns a `TiledMap` container with `getLayer(name)` for accessing individual layers (collision detection, spawning points, etc.). The "Collisions", "Sector Blocks", and "Arena Blocks" layers from the reference's 17-layer structure are accessible via `getLayer()` for backend-facing metadata extraction.

**Limitation:** zstd-compressed tile data is unsupported (browser `DecompressionStream` only handles gzip/deflate). Export maps from Tiled with no compression or zlib compression.

---

### pixi-viewport

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| pixi-viewport | 6.0.3 | Pan, zoom, and follow-agent camera for the 3200x3200 tile canvas | Only PixiJS viewport library with v8 support, peer dep `pixi.js: >=8`. Provides drag, wheel-zoom, pinch, clamp, follow-target plugins — configurable individually. Used widely in PixiJS game projects. |

**Verified:** `npm view pixi-viewport` returns 6.0.3, peer `pixi.js: >=8`.

**Why needed:** The 3200x3200px canvas is too large to display at 1:1 on a standard laptop screen. Current approach fits the whole map into the viewport by scaling the PixiJS Application. Adding pixi-viewport lets users pan to agents and zoom in, which is essential once agents are pixel-art sprites rather than colored dots visible at full-map view.

**Integration with @pixi/react:** pixi-viewport uses the `extend` API. It is the most commonly reported integration challenge for @pixi/react v8. The pattern:

```typescript
import { extend } from '@pixi/react';
import { Viewport } from 'pixi-viewport';

extend({ Viewport });

// TypeScript declaration (global.d.ts):
declare global {
  namespace JSX {
    interface IntrinsicElements {
      pixiViewport: PixiReactElementProps<typeof Viewport>;
    }
  }
}
```

The `events` prop must be set to `app.renderer.events` (via `useApplication()`) — NOT `app.renderer.plugins.interaction` which was removed in v8.

**Performance note:** Wrap the TiledMap container in a `Container({ isRenderGroup: true })` before adding to viewport. PixiJS v8 render groups offload transform (pan/zoom) calculations to the GPU, which eliminates CPU overhead when the camera moves over the 3200px map. This is critical for the tile density involved.

---

## PixiJS v8 Built-ins Used for Sprites (No New Packages)

These capabilities are already in PixiJS 8.17.1 — no additional installs needed.

### Assets API for Texture Atlas Loading

```typescript
// Load agent sprite sheet (PixiJS texture atlas JSON format)
const sheet = await Assets.load<Spritesheet>('assets/agents/sprite.json');

// Access named animation frames
const downWalkFrames = sheet.animations['down-walk'];   // Texture[]
const upWalkFrames   = sheet.animations['up-walk'];
const leftWalkFrames = sheet.animations['left-walk'];
const rightWalkFrames = sheet.animations['right-walk'];
```

The reference `sprite.json` uses PixiJS texture atlas format with frames named `down-walk.000`, `down-walk.001`, etc. — exactly the format `Assets.load` parses natively via the built-in `spritesheetAsset` loader.

**Important:** Load all sprite atlases during app initialization (before the simulation starts) using `Assets.addBundle` + `Assets.loadBundle`. This avoids mid-simulation asset loading stalls.

```typescript
Assets.addBundle('agents', {
  agentSprite: 'assets/agents/sprite.json',
});
await Assets.loadBundle('agents');
```

### AnimatedSprite in @pixi/react

```typescript
// Walk cycle for one agent
const textures = sheet.animations[`${direction}-walk`]; // Texture[]

<pixiAnimatedSprite
  textures={textures}
  animationSpeed={0.15}   // ~9fps from 60fps ticker — typical RPG walk speed
  isPlaying={isMoving}    // stop animation when agent is standing still
  anchor={0.5}
  x={agent.x * TILE_SIZE}
  y={agent.y * TILE_SIZE}
/>
```

`pixiAnimatedSprite` is the @pixi/react v8 JSX element (auto-derived from `AnimatedSprite` via the pixi prefix convention). It accepts `textures`, `animationSpeed`, `isPlaying`, and all standard Container props.

The `useTick` hook drives per-frame position updates (smooth interpolation between tile positions):

```typescript
useTick(() => {
  // interpolate agent.renderX toward agent.targetX each frame
});
```

### BitmapText for Agent Name Labels

For v1.2, swap agent name labels from `pixiText` (per-frame canvas rasterization) to `pixiBitmapText`. At 25 agents each with a name label updating on position change, canvas rasterization becomes measurable overhead. BitmapText uses a pre-rasterized glyph atlas — GPU-resident, no per-frame CPU cost.

PixiJS 8.17 ships MSDF BitmapFont support — glyphs remain crisp at any zoom level, which matters now that the viewport zooms in/out.

```typescript
import { BitmapFont } from 'pixi.js';

// Generate from a web font (one-time setup):
BitmapFont.install({ name: 'AgentLabel', style: { fontFamily: 'Press Start 2P', fontSize: 8 } });

// Usage in JSX:
<pixiBitmapText text={agent.name} fontFamily="AgentLabel" fontSize={8} anchor={[0.5, 1]} />
```

For a pixel-art aesthetic, use a pixel font (e.g., "Press Start 2P" from Google Fonts) loaded via `Assets.load` before BitmapFont.install.

---

## Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pixi-tiledmap | 2.2.0 | Parse and render Tiled JSON maps | Required — replaces Graphics primitives for the tileset-based map |
| pixi-viewport | 6.0.3 | Pan/zoom camera for the large tile canvas | Required — 3200px map needs interactive camera now that it has visual detail |
| @assetpack/core | 1.7.0 | Asset pipeline: compress PNGs → WebP, pack folders into sprite sheets | Dev-only, optional but strongly recommended — raw PNGs from the reference are unoptimized |

---

## Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Tiled Map Editor (desktop app) | Author the Agent Town map visually with CuteRPG tilesets | Free, open-source. Export as JSON (.tmj). Use **no compression** or **zlib** compression — not zstd. 32x32 tile size. Available at mapeditor.org. |
| Free Texture Packer (free-tex-packer.com) | Pack individual agent PNG frames into a PixiJS texture atlas | Free alternative to TexturePacker. Export format: "PixiJS". Input: 32x32 per-direction frames. Output: `sprite.json` + `sprite.png`. |
| @assetpack/core | Automate sprite sheet packing and PNG→WebP compression at build time | Run via CLI or as a Vite plugin stub. Watches `raw-assets/` and outputs to `public/assets/`. Saves 40-70% on PNG sizes. |

### @assetpack/core Setup (dev dependency)

AssetPack automates the raw-assets → optimized-assets pipeline. For this project, the primary value is PNG compression (reducing the CuteRPG tileset PNGs, which are often uncompressed) and ensuring consistent output paths.

```bash
npm install -D @assetpack/core @assetpack/plugin-compress @assetpack/plugin-texture-packer
```

Basic config (`assetpack.config.ts`):

```typescript
import { compress } from '@assetpack/plugin-compress';
import { texturePacker } from '@assetpack/plugin-texture-packer';

export default {
  entry: './raw-assets',
  output: './public/assets',
  pipes: [
    texturePacker({ nameStyle: 'short' }),   // packs {tps}-tagged folders
    compress({ png: true, webp: true }),       // outputs both formats for browser fallback
  ],
};
```

Folders tagged with `{tps}` in `raw-assets/` are packed into a sprite sheet atlas. Untagged PNG files are compressed in place.

**Note:** `@assetpack/core` 1.7.0 was last published November 2025. It is stable but not under active development. For v1.2, its only role is compression and atlas generation — a one-time pipeline step, not a real-time dependency. If it proves difficult to configure, manual TexturePacker or Free Texture Packer output is a valid substitute.

---

## Installation

```bash
# New runtime dependencies
npm install pixi-tiledmap@^2.2.0 pixi-viewport@^6.0.3

# New dev dependencies (asset pipeline)
npm install -D @assetpack/core@^1.7.0 @assetpack/plugin-compress@^0.8.0 @assetpack/plugin-texture-packer@^0.8.0
```

No new Python backend dependencies for v1.2. The pixel-art upgrade is entirely frontend.

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| pixi-tiledmap | @pixi/tilemap | `@pixi/tilemap` (v5.0.2) is a low-level rectangular tilemap renderer — it does NOT parse Tiled JSON. It requires manual tile index → texture mapping. pixi-tiledmap wraps `@pixi/tilemap` internally and adds the full Tiled parsing layer. Use pixi-tiledmap. |
| pixi-tiledmap | pixi-tiled (npm) | Last published 2018, targets PixiJS v4-5. Dead. |
| pixi-tiledmap | Custom Tiled JSON parser | The reference format uses 18 tilesets, 17 layers, transparent color keying, and flip flags. Writing a correct parser from scratch is a substantial undertaking. pixi-tiledmap handles all of it. |
| pixi-viewport | PixiJS renderGroup + manual transform | Render groups provide GPU-accelerated transforms but require manual drag/wheel/pinch event handling. pixi-viewport provides all input plugins out of the box. For a simulation tool with a camera, pixi-viewport is the right tradeoff. |
| pixi-viewport | Native browser scroll | Browser scroll events don't compose well with the PixiJS canvas. Agent-follow mode (clicking an agent to track it) is trivial with pixi-viewport's `follow` plugin. |
| Free Texture Packer | TexturePacker (paid) | TexturePacker is the industry standard but costs $40. Free Texture Packer produces compatible PixiJS JSON output. For a small project with one agent sprite sheet, it's sufficient. |
| @assetpack/core | Manual compression | Raw CuteRPG PNGs are 512x512 uncompressed — large for browser delivery. Manual compression with squoosh or sharp is viable but not repeatable. AssetPack makes it part of the build. |

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Phaser | Already using PixiJS v8. Phaser's tilemap API is not compatible with PixiJS. | pixi-tiledmap |
| @pixi/tilemap directly | Low-level, requires manual Tiled JSON parsing. pixi-tiledmap wraps it correctly. | pixi-tiledmap |
| Three.js for rendering | 3D engine overkill, breaks entire existing render architecture | PixiJS 8.17.1 already installed |
| Spine animation runtime | Agent walk cycles are 4-direction tile-based cycles, not complex skeletal animation. Spine adds 200KB+ to bundle for no benefit here. | AnimatedSprite with texture atlas |
| `cacheAsTexture` on the full 3200x3200 map | PixiJS docs explicitly warn against `cacheAsTexture` on containers exceeding 4096x4096 — GPU limits. At 3200x3200 it's technically under, but the map updates as agents move, so caching defeats the purpose. | render groups (`isRenderGroup: true`) on the map container |

---

## Stack Patterns by Variant

**If the Tiled map export uses zstd compression (default in newer Tiled versions):**
- Re-export from Tiled with "No compression" or "zlib" compression in File → Export As → Map format options
- pixi-tiledmap will throw on zstd tiles in the browser; zlib decompression works via `DecompressionStream`

**If agent sprite sheets need per-agent color tinting (different colored outfits):**
- Use `pixiSprite.tint = 0xRRGGBB` rather than separate texture atlases per agent
- A single base sprite sheet with white/neutral colors can be tinted 25 different colors at runtime with zero additional assets

**If the full tileset map causes frame drops (17 layers × 10,000 tiles):**
- Enable `isRenderGroup: true` on the map container — GPU-resident transforms eliminate CPU overhead during pan/zoom
- Cull off-screen layers: pixi-tiledmap layers are standard PixiJS Containers; set `layer.cullable = true` and call `Culler.shared.cull(stage, app.screen)` in the tick loop

**If the pixel font for BitmapText doesn't load before simulation start:**
- Load it in the asset preload bundle (`Assets.addBundle`) before the WebSocket connects
- The simulation start button should gate on `Assets.loadBundle` completion

---

## Version Compatibility

| Pair | Compatible With | Notes |
|------|-----------------|-------|
| pixi-tiledmap 2.2.0 | pixi.js ^8.0.0 | Peer dep confirmed. Do not mix with PixiJS v7 — v2 uses the v8 `extensions` API. |
| pixi-viewport 6.0.3 | pixi.js >=8 | Peer dep confirmed. Pass `app.renderer.events` to the viewport `events` option (not the removed `plugins.interaction`). |
| @pixi/react 8.0.5 + pixi-viewport 6.0.3 | Requires `extend({ Viewport })` pattern | The extend API registration is required before JSX can use `<pixiViewport>`. TypeScript types need manual declaration in `global.d.ts`. |
| @assetpack/core 1.7.0 + @assetpack/plugin-texture-packer 0.8.0 | Matched minor versions | Use matching 0.8.0 plugin versions — mismatching core/plugin versions causes type errors in the pipeline config. |
| pixi-tiledmap 2.2.0 + Tiled map format | Tiled 1.x JSON spec | Export from any Tiled 1.x version. TMJ (JSON) is the preferred format. Avoid TMX (XML) for this project — the TypeScript import is cleaner with JSON. |
| PixiJS 8.17.1 AnimatedSprite + @pixi/react 8.0.5 | `pixiAnimatedSprite` JSX element | AnimatedSprite is a PixiJS built-in — no separate package. The JSX element name is `pixiAnimatedSprite` per @pixi/react v8's pixi-prefix convention. |

---

## Sources

- pixi-tiledmap npm registry — version 2.2.0, peer deps, last modified: `npm view pixi-tiledmap`
- pixi-tiledmap GitHub (riebel/pixi-tiledmap) — API, usage, integration pattern, limitations: https://github.com/riebel/pixi-tiledmap
- pixi-viewport npm registry — version 6.0.3, peer dep `pixi.js: >=8`: `npm view pixi-viewport`
- pixi-viewport GitHub (pixijs-userland/pixi-viewport) — v8 compatibility, events migration: https://github.com/pixijs-userland/pixi-viewport
- @pixi/react v8 hooks documentation — useTick, useApplication, extend: https://react.pixijs.io/hooks/useTick/
- PixiJS v8 render groups — isRenderGroup, GPU transforms for large worlds: https://pixijs.com/8.x/guides/concepts/render-groups
- PixiJS v8 Assets API — Assets.load, addBundle, loadBundle, spritesheet parser: https://pixijs.com/8.x/guides/components/assets
- PixiJS v8 culling API — cullable, Culler.shared.cull: https://www.richardfu.net/optimizing-rendering-with-pixijs-v8-a-deep-dive-into-the-new-culling-api/
- PixiJS v8 AnimatedSprite + texture atlas tutorial: https://www.codeandweb.com/texturepacker/tutorials/how-to-create-sprite-sheets-and-animations-with-pixijs
- @assetpack/core npm — version 1.7.0, last published Nov 2025: `npm view @assetpack/core`
- AssetPack Vite integration guide: https://pixijs.io/assetpack/docs/guide/getting-started/vite/
- Free Texture Packer (free alternative to TexturePacker): https://free-tex-packer.com/
- Reference tilemap.json analysis — 18 tilesets, 17 layers, 32x32, transparentColor: local file at GenerativeAgentsCN/generative_agents/frontend/static/assets/village/tilemap/tilemap.json
- Reference sprite.json analysis — PixiJS texture atlas format, down/up/left/right walk frames: local file at GenerativeAgentsCN/generative_agents/frontend/static/assets/village/agents/sprite.json

---

*Stack research for: Agent Town v1.2 — pixel-art tileset rendering upgrade*
*Researched: 2026-04-11*
