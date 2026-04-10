/**
 * MapCanvas — top-level PixiJS Application wrapper for Agent Town.
 *
 * Renders the PixiJS WebGL canvas into the React tree via @pixi/react v8.
 * Contains a viewport container (pan/zoom target for Plan 03) and TileMap child.
 *
 * Layout decisions:
 *   D-02: 32px tile size, 100x100 grid = 3200x3200px canvas
 *   D-03: Pan/zoom will be wired in Plan 03 — viewport container is the hook point
 *   D-12: Background 0xd0d0c8 (warm gray) matches the road color in TileMap
 *
 * @pixi/react v8 API notes:
 *   - extend() must be called before any JSX usage of pixi components
 *   - resizeTo={window} is intentionally avoided — parent div controls canvas size
 *   - pixiContainer is the viewport; agents and TileMap are children of it (Plan 03)
 */
import { Application, extend } from "@pixi/react";
import { Container, Graphics, Text } from "pixi.js";
import { TileMap } from "./TileMap";

// Register PixiJS display objects with @pixi/react v8 extend API
// Must include all primitives used in JSX across this subtree.
extend({ Container, Graphics, Text });

/** Background/road color matches TileMap's road color (D-12) */
const BG_COLOR = 0xd0d0c8;

/**
 * MapCanvas mounts the PixiJS Application and renders the town tile map.
 *
 * The pixiContainer at the root of the scene is the viewport — Plan 03 will
 * add pointer/wheel event handlers here for pan and zoom.
 */
export function MapCanvas() {
  return (
    <Application
      background={BG_COLOR}
    >
      {/* Viewport container — pan/zoom target (Plan 03 hook point) */}
      <pixiContainer>
        {/* Static tile map with colored sector zones and labels */}
        <TileMap />
      </pixiContainer>
    </Application>
  );
}
