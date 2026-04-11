/**
 * TileMap — PixiJS v8 component that renders the Agent Town tile grid.
 *
 * Reads town.json sector data at import time (static JSON, no runtime fetch).
 * Draws:
 *   1. Road background (full canvas, warm gray)
 *   2. Collision tiles (sparse border walls, dark gray) — drawn as individual rects
 *   3. Sector zones (colored filled rectangles — one per sector bounding box)
 *   4. Sector labels (pixiText centered in each zone)
 *
 * Design decisions:
 *   D-01: Colored rectangles with text labels. Green=park, brown=buildings, gray=roads.
 *   D-02: 32px tile size, 100x100 grid → 3200x3200px canvas.
 *   D-12: Soft/pastel colors. Clean, minimal, professional simulation tool aesthetic.
 *
 * PixiJS v8 Graphics API:
 *   g.setFillStyle({ color: 0xRRGGBB }); g.rect(x, y, w, h); g.fill();
 *
 * useCallback with EMPTY deps array — map data is static, prevents per-frame re-draw.
 * (Pitfall 3 from research: draw callbacks with changing deps cause frame-rate drops.)
 */
import { useCallback } from "react";
import { Graphics as PixiGraphics, TextStyle } from "pixi.js";
import townData from "../data/town.json";

/** Tile size in pixels (D-02) */
const TILE_SIZE = 32;

/** Map dimension in tiles (D-02) */
const MAP_SIZE = 100;

/** Road / background color (D-12: warm gray) */
const COLOR_ROAD = 0xd0d0c8;

/** Collision wall tile color (D-12: dark gray) */
const COLOR_COLLISION = 0x888880;

/** Sector color palette (D-12: soft/pastel) */
const SECTOR_COLORS: Record<string, number> = {
  park: 0xa8d5a2,           // sage green
  cafe: 0xd4a96a,           // warm tan
  shop: 0xc9b99a,           // muted brown
  office: 0x9bb5c8,         // slate blue
  "stock-exchange": 0xc8b4e0, // soft purple
  "wedding-hall": 0xf0c8d4, // blush pink
  // All home-* sectors use cream color (matched by prefix below)
};

/** Fallback color for any unrecognized sector (home-* and others) */
const COLOR_HOME = 0xe8d5b7; // cream

/** Resolve the display color for a sector name */
function sectorColor(name: string): number {
  if (name in SECTOR_COLORS) return SECTOR_COLORS[name];
  if (name.startsWith("home-")) return COLOR_HOME;
  return 0xcccccc; // generic fallback
}

/** Darken a hex color by a factor (0-1). Pure math, no library needed. */
function darkenColor(hex: number, factor: number): number {
  const r = Math.floor(((hex >> 16) & 0xff) * (1 - factor));
  const g_ch = Math.floor(((hex >> 8) & 0xff) * (1 - factor));
  const b = Math.floor((hex & 0xff) * (1 - factor));
  return (r << 16) | (g_ch << 8) | b;
}

/** Format a sector name for display (hyphen → space, title case) */
function formatSectorLabel(name: string): string {
  return name
    .split("-")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

interface TileCoord {
  coord: [number, number];
  collision?: boolean;
  address?: string[];
}

interface SectorBounds {
  sector: string;
  x: number;        // pixel x (top-left)
  y: number;        // pixel y (top-left)
  width: number;    // pixel width
  height: number;   // pixel height
  color: number;
  label: string;
}

/** Pre-compute sector bounding boxes from town.json at module load time. */
function computeSectorBounds(): SectorBounds[] {
  const tiles = townData.tiles as TileCoord[];
  const sectorCoords: Record<string, [number, number][]> = {};

  for (const tile of tiles) {
    const addr = tile.address;
    if (!addr || addr.length < 1) continue;
    const sector = addr[0];
    if (!sectorCoords[sector]) sectorCoords[sector] = [];
    sectorCoords[sector].push(tile.coord);
  }

  return Object.entries(sectorCoords).map(([sector, coords]) => {
    const xs = coords.map((c) => c[0]);
    const ys = coords.map((c) => c[1]);
    const minX = Math.min(...xs);
    const minY = Math.min(...ys);
    const maxX = Math.max(...xs);
    const maxY = Math.max(...ys);
    return {
      sector,
      x: minX * TILE_SIZE,
      y: minY * TILE_SIZE,
      width: (maxX - minX + 1) * TILE_SIZE,
      height: (maxY - minY + 1) * TILE_SIZE,
      color: sectorColor(sector),
      label: formatSectorLabel(sector),
    };
  });
}

/** Pre-compute collision tile coordinates from town.json. */
function computeCollisionTiles(): [number, number][] {
  const tiles = townData.tiles as TileCoord[];
  return tiles
    .filter((t) => t.collision && (!t.address || t.address.length === 0))
    .map((t) => t.coord);
}

// Computed once at module load — safe because town.json is static.
const SECTOR_BOUNDS = computeSectorBounds();
const COLLISION_TILES = computeCollisionTiles();
const CANVAS_SIZE = MAP_SIZE * TILE_SIZE; // 3200px

/** Label text style — reused across all sector labels */
const LABEL_STYLE = new TextStyle({
  fontFamily: "Inter, system-ui, sans-serif",
  fontSize: 28,
  fontWeight: "700",
  fill: 0x222222,
  align: "center",
  stroke: { color: 0xffffff, width: 3 },
});

/**
 * TileMap renders the static town map into the parent PixiJS container.
 *
 * Usage inside a @pixi/react Application:
 *   <pixiContainer>
 *     <TileMap />
 *   </pixiContainer>
 */
export function TileMap() {
  /**
   * Draw the road background + collision walls + sector zones.
   *
   * EMPTY deps array — map data never changes at runtime.
   * (Pitfall 3: deps that change each render cause continuous redraws.)
   */
  const drawMap = useCallback((g: PixiGraphics) => {
    g.clear();

    // 1. Road background — full canvas in warm gray
    g.setFillStyle({ color: COLOR_ROAD });
    g.rect(0, 0, CANVAS_SIZE, CANVAS_SIZE);
    g.fill();

    // 2. Collision tiles (border walls) — dark gray, individual rects
    g.setFillStyle({ color: COLOR_COLLISION });
    for (const [cx, cy] of COLLISION_TILES) {
      g.rect(cx * TILE_SIZE, cy * TILE_SIZE, TILE_SIZE, TILE_SIZE);
    }
    g.fill();

    // 3. Sector zones — colored filled rectangles with wall outlines
    for (const bounds of SECTOR_BOUNDS) {
      // Floor fill (existing)
      g.setFillStyle({ color: bounds.color });
      g.rect(bounds.x, bounds.y, bounds.width, bounds.height);
      g.fill();

      // Wall stroke outline (D-01: 3px dark stroke per D-02)
      g.setStrokeStyle({ color: darkenColor(bounds.color, 0.35), width: 3 });
      g.rect(bounds.x, bounds.y, bounds.width, bounds.height);
      g.stroke();
    }
  }, []);

  return (
    <>
      {/* Map graphics layer */}
      <pixiGraphics draw={drawMap} />

      {/* Sector labels — centered text overlay for each zone */}
      {SECTOR_BOUNDS.map((bounds) => (
        <pixiText
          key={bounds.sector}
          text={bounds.label}
          style={LABEL_STYLE}
          x={bounds.x + bounds.width / 2}
          y={bounds.y + bounds.height / 2}
          anchor={0.5}
        />
      ))}
    </>
  );
}
