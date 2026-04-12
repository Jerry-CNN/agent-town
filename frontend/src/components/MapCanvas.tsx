/**
 * MapCanvas — top-level PixiJS Application wrapper for Agent Town.
 *
 * Renders the PixiJS WebGL canvas into the React tree via @pixi/react v8.
 * Supports mouse-wheel zoom and click-drag pan for map navigation.
 * Renders AgentSprite children for all agents in the Zustand store (MAP-02).
 */
import { useMemo, useRef, useEffect, useCallback, useState } from "react";
import { Application, extend } from "@pixi/react";
import { Container, Graphics, Text } from "pixi.js";
import { TileMap } from "./TileMap";
import { AgentSprite } from "./AgentSprite";
import { useSimulationStore } from "../store/simulationStore";

// Register PixiJS display objects with @pixi/react v8 extend API.
extend({ Container, Graphics, Text });

/** Background/road color (D-12) */
const BG_COLOR = 0xd0d0c8;

/** Map world size in pixels (D-02: 100 tiles × 32px) */
const MAP_SIZE_PX = 3200;

/** Fixed zoom scale — shows most of the map while keeping agents readable */
const FIXED_SCALE = 0.45;

export function MapCanvas() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  const [offsetX, setOffsetX] = useState(0);
  const [offsetY, setOffsetY] = useState(0);

  // Pan state
  const isPanning = useRef(false);
  const panStart = useRef({ x: 0, y: 0 });
  const offsetStart = useRef({ x: 0, y: 0 });

  // Agent IDs from store
  const agents = useSimulationStore((s) => s.agents);
  const agentIds = useMemo(() => Object.keys(agents), [agents]);
  const setSelectedAgent = useSimulationStore((s) => s.setSelectedAgent);

  // Fixed zoom: center the map at FIXED_SCALE on mount and resize
  useEffect(() => {
    function centerMap() {
      const el = containerRef.current;
      if (!el) return;
      setScale(FIXED_SCALE);
      setOffsetX((el.clientWidth - MAP_SIZE_PX * FIXED_SCALE) / 2);
      setOffsetY((el.clientHeight - MAP_SIZE_PX * FIXED_SCALE) / 2);
    }
    centerMap();
    window.addEventListener("resize", centerMap);
    return () => window.removeEventListener("resize", centerMap);
  }, []);

  // Click-drag pan
  const onPointerDown = useCallback((e: React.PointerEvent) => {
    isPanning.current = true;
    panStart.current = { x: e.clientX, y: e.clientY };
    offsetStart.current = { x: offsetX, y: offsetY };
    (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
  }, [offsetX, offsetY]);

  const onPointerMove = useCallback((e: React.PointerEvent) => {
    if (!isPanning.current) return;
    const dx = e.clientX - panStart.current.x;
    const dy = e.clientY - panStart.current.y;
    setOffsetX(offsetStart.current.x + dx);
    setOffsetY(offsetStart.current.y + dy);
  }, []);

  const onPointerUp = useCallback(() => {
    isPanning.current = false;
  }, []);

  const handleAgentSelect = useCallback(
    (id: string) => {
      setSelectedAgent(id);
    },
    [setSelectedAgent],
  );

  return (
    <div
      ref={containerRef}
      style={{ width: "100%", height: "100%", overflow: "hidden", cursor: isPanning.current ? "grabbing" : "grab" }}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerLeave={onPointerUp}
    >
      <Application background={BG_COLOR} resizeTo={containerRef as React.RefObject<HTMLElement>}>
        <pixiContainer x={offsetX} y={offsetY} scale={scale}>
          {/* Static tile map layer */}
          <TileMap />

          {/* Agent sprites */}
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
