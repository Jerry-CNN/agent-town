/**
 * MapCanvas — top-level PixiJS Application wrapper for Agent Town.
 *
 * Renders the PixiJS WebGL canvas into the React tree via @pixi/react v8.
 * Provides a viewport container with click-drag pan and mouse-wheel zoom (D-03).
 * Renders AgentSprite children for all agents in the Zustand store (MAP-02).
 *
 * Layout decisions:
 *   D-02: 32px tile size, 100x100 grid = 3200x3200px canvas
 *   D-03: Click-drag pans the map. Mouse wheel zooms in/out. Camera centers on town initially.
 *   D-11: Clicking an agent circle calls setSelectedAgent(id). Dragging does NOT select.
 *   D-12: Background 0xd0d0c8 (warm gray) matches TileMap road color.
 *
 * Pan/zoom implementation:
 *   - HTML div wrapper captures mouse/pointer events (onMouseDown/Move/Up/Leave + onWheel)
 *   - hasDragged ref distinguishes drag from click (>5px threshold — Pitfall 4)
 *   - Viewport pixiContainer gets x/y (pan) and scale (zoom) props from React state
 *   - Zoom toward cursor: newPan = cursor - (cursor - oldPan) * (newZoom / oldZoom)
 *
 * Agent rendering:
 *   - agentIds from Zustand store drives AgentSprite list
 *   - colorIndex = stable array index (agents keyed by name, Object.keys order stable per session)
 *   - Each AgentSprite reads its own position from store inside useTick
 */
import { useState, useRef, useCallback } from "react";
import { Application, extend } from "@pixi/react";
import { Container, Graphics, Text } from "pixi.js";
import { TileMap } from "./TileMap";
import { AgentSprite } from "./AgentSprite";
import { useSimulationStore } from "../store/simulationStore";

// Register PixiJS display objects with @pixi/react v8 extend API.
// Must include all primitives used in JSX across this subtree.
extend({ Container, Graphics, Text });

/** Background/road color matches TileMap's road color (D-12) */
const BG_COLOR = 0xd0d0c8;

/** Map canvas size in pixels (D-02: 100 tiles × 32px) */
const MAP_SIZE_PX = 3200;

/** Zoom bounds (Claude's discretion per CONTEXT.md) */
const MIN_ZOOM = 0.3;
const MAX_ZOOM = 2.0;

/** Initial zoom level — fits most of the map in a typical browser window */
const INITIAL_ZOOM = 0.5;

/** Drag threshold in pixels before we treat a mousedown+mouseup as a drag (not a click) */
const DRAG_THRESHOLD = 5;

/** Initial pan: center the 3200×3200 map in the viewport at initial zoom */
function initialPan(): { x: number; y: number } {
  const visibleW = window.innerWidth * 0.75; // map takes ~75% of screen width
  const visibleH = window.innerHeight;
  return {
    x: (visibleW - MAP_SIZE_PX * INITIAL_ZOOM) / 2,
    y: (visibleH - MAP_SIZE_PX * INITIAL_ZOOM) / 2,
  };
}

interface DragState {
  active: boolean;
  startX: number;
  startY: number;
  startPanX: number;
  startPanY: number;
}

/**
 * MapCanvas mounts the PixiJS Application and renders:
 *   1. TileMap — static town sectors and labels
 *   2. AgentSprite — one per agent in the store, with lerp movement and click-to-select
 *
 * The wrapping div captures mouse/wheel events for pan/zoom (D-03).
 */
export function MapCanvas() {
  // Viewport transform state — drives pixiContainer x/y/scale props
  const pan0 = initialPan();
  const [panX, setPanX] = useState(pan0.x);
  const [panY, setPanY] = useState(pan0.y);
  const [zoom, setZoom] = useState(INITIAL_ZOOM);

  // Drag tracking ref — mutable, no re-renders
  const dragRef = useRef<DragState>({
    active: false,
    startX: 0,
    startY: 0,
    startPanX: 0,
    startPanY: 0,
  });

  // hasDragged: true if pointer moved >DRAG_THRESHOLD px during current press
  // Prevents pan gesture from also triggering agent selection (Pitfall 4)
  const hasDraggedRef = useRef(false);

  // Agent IDs from store — drives AgentSprite list
  const agentIds = useSimulationStore((s) => Object.keys(s.agents));
  const setSelectedAgent = useSimulationStore((s) => s.setSelectedAgent);

  // --- Pan handlers ---

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      dragRef.current = {
        active: true,
        startX: e.clientX,
        startY: e.clientY,
        startPanX: panX,
        startPanY: panY,
      };
      hasDraggedRef.current = false;
    },
    [panX, panY],
  );

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    const drag = dragRef.current;
    if (!drag.active) return;

    const dx = e.clientX - drag.startX;
    const dy = e.clientY - drag.startY;

    // Mark as drag once threshold exceeded
    if (
      !hasDraggedRef.current &&
      (Math.abs(dx) > DRAG_THRESHOLD || Math.abs(dy) > DRAG_THRESHOLD)
    ) {
      hasDraggedRef.current = true;
    }

    if (hasDraggedRef.current) {
      setPanX(drag.startPanX + dx);
      setPanY(drag.startPanY + dy);
    }
  }, []);

  const handleMouseUp = useCallback(() => {
    dragRef.current.active = false;
  }, []);

  const handleMouseLeave = useCallback(() => {
    // Prevent "stuck drag" when pointer exits the canvas area
    dragRef.current.active = false;
  }, []);

  // --- Zoom handler ---

  const handleWheel = useCallback(
    (e: React.WheelEvent) => {
      e.preventDefault();

      const newZoom = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, zoom * (1 - e.deltaY * 0.001)));
      const ratio = newZoom / zoom;

      // Zoom toward the cursor position:
      // newPan = cursorOffset - (cursorOffset - oldPan) * ratio
      const rect = (e.currentTarget as HTMLDivElement).getBoundingClientRect();
      const cursorX = e.clientX - rect.left;
      const cursorY = e.clientY - rect.top;

      setPanX(cursorX - (cursorX - panX) * ratio);
      setPanY(cursorY - (cursorY - panY) * ratio);
      setZoom(newZoom);
    },
    [zoom, panX, panY],
  );

  // --- Agent click handler ---

  const handleAgentSelect = useCallback(
    (id: string) => {
      // Only fire if this was a tap, not a drag
      if (!hasDraggedRef.current) {
        setSelectedAgent(id);
      }
    },
    [setSelectedAgent],
  );

  // --- Viewport background click (deselect on empty area) ---

  const handleViewportClick = useCallback(() => {
    if (!hasDraggedRef.current) {
      setSelectedAgent(null);
    }
  }, [setSelectedAgent]);

  return (
    <div
      style={{ width: "100%", height: "100%", overflow: "hidden", cursor: "grab" }}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseLeave}
      onWheel={handleWheel}
    >
      <Application background={BG_COLOR}>
        {/* Viewport container — receives pan (x/y) and zoom (scale) (D-03) */}
        <pixiContainer
          x={panX}
          y={panY}
          scale={zoom}
          interactive={true}
          onPointerTap={handleViewportClick}
        >
          {/* Static tile map layer */}
          <TileMap />

          {/* Agent sprites — one per agent in store (MAP-02) */}
          {agentIds.map((agentId, index) => (
            <AgentSprite
              key={agentId}
              agentId={agentId}
              colorIndex={index}
              onSelect={handleAgentSelect}
            />
          ))}
        </pixiContainer>
      </Application>
    </div>
  );
}
