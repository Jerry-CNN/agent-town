/**
 * MapCanvas — top-level PixiJS Application wrapper for Agent Town.
 *
 * Renders the PixiJS WebGL canvas into the React tree via @pixi/react v8.
 * The map auto-scales to fill the available viewport — no pan/zoom controls.
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

export function MapCanvas() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  const [offsetX, setOffsetX] = useState(0);
  const [offsetY, setOffsetY] = useState(0);

  // Agent IDs from store
  const agents = useSimulationStore((s) => s.agents);
  const agentIds = useMemo(() => Object.keys(agents), [agents]);
  const setSelectedAgent = useSimulationStore((s) => s.setSelectedAgent);

  // Auto-fit: scale the 3200x3200 map to fill the container
  useEffect(() => {
    function updateScale() {
      const el = containerRef.current;
      if (!el) return;
      const w = el.clientWidth;
      const h = el.clientHeight;
      // Fit the map to the smaller dimension (contain)
      const s = Math.min(w / MAP_SIZE_PX, h / MAP_SIZE_PX);
      setScale(s);
      // Center the map if there's extra space on one axis
      setOffsetX((w - MAP_SIZE_PX * s) / 2);
      setOffsetY((h - MAP_SIZE_PX * s) / 2);
    }
    updateScale();
    window.addEventListener("resize", updateScale);
    return () => window.removeEventListener("resize", updateScale);
  }, []);

  const handleAgentSelect = useCallback(
    (id: string) => {
      setSelectedAgent(id);
    },
    [setSelectedAgent],
  );

  return (
    <div ref={containerRef} style={{ width: "100%", height: "100%", overflow: "hidden" }}>
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
