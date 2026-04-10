/**
 * AgentSprite — PixiJS v8 component representing a single agent on the map.
 *
 * Renders:
 *   - Colored circle (radius 12px) with agent's first initial letter (D-04)
 *   - Name label below the circle (D-06)
 *   - Current activity text above the circle (D-06)
 *   - Smooth lerp animation between tile positions each frame (D-05)
 *   - Click handler to select the agent (D-11)
 *
 * Performance contract:
 *   - useTick reads position from getState() (not hook) — no per-frame React re-renders
 *   - Graphics draw callback is stable (useCallback with [color] deps — color never changes)
 *   - Activity text is updated via direct ref mutation (not setState)
 *
 * PixiJS v8 API:
 *   - g.setFillStyle({ color }); g.circle(cx, cy, r); g.fill();
 *   - useTick((ticker) => { ... }) runs every animation frame
 *   - Refs to pixi display objects: containerRef.current.x = ...
 */
import { useCallback, useRef, useEffect } from "react";
import { useTick } from "@pixi/react";
import { Graphics as PixiGraphics, Text as PixiText, Container as PixiContainer } from "pixi.js";
import { useSimulationStore } from "../store/simulationStore";

/** 8 distinct soft/pastel colors — one per agent slot (D-12) */
export const AGENT_COLORS: number[] = [
  0xe74c3c, // coral red
  0x3498db, // sky blue
  0x2ecc71, // mint green
  0xf39c12, // amber
  0x9b59b6, // lavender
  0x1abc9c, // teal
  0xe67e22, // peach
  0x34495e, // slate
];

/** Circle radius in pixels (D-04) */
const RADIUS = 12;

/** Lerp coefficient per frame (0.08 ≈ 95% converge within 1.5s at 60fps) */
const LERP = 0.08;

/** Max chars for activity label (D-06: avoid overflow) */
const MAX_ACTIVITY_LEN = 30;

function truncateActivity(text: string): string {
  if (text.length <= MAX_ACTIVITY_LEN) return text;
  return text.slice(0, MAX_ACTIVITY_LEN - 1) + "…";
}

interface AgentSpriteProps {
  agentId: string;
  colorIndex: number;
  onSelect: (id: string) => void;
}

/**
 * AgentSpriteInner contains all the PixiJS rendering logic.
 * Separated so useTick can run unconditionally (Rules of Hooks).
 */
function AgentSpriteInner({ agentId, colorIndex, onSelect }: AgentSpriteProps) {
  const color = AGENT_COLORS[colorIndex % AGENT_COLORS.length];

  // Refs to PixiJS display objects for imperative updates in useTick
  const containerRef = useRef<PixiContainer | null>(null);
  const activityTextRef = useRef<PixiText | null>(null);

  // Current interpolated pixel position (not React state — no re-renders)
  const currentPosRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  // Initialize position from store on first render
  useEffect(() => {
    const agent = useSimulationStore.getState().agents[agentId];
    if (agent) {
      currentPosRef.current = { x: agent.position.x, y: agent.position.y };
      if (containerRef.current) {
        containerRef.current.x = agent.position.x;
        containerRef.current.y = agent.position.y;
      }
    }
  }, [agentId]);

  // Stable draw callback for the circle graphic — color never changes per agent
  const drawCircle = useCallback(
    (g: PixiGraphics) => {
      g.clear();
      g.setFillStyle({ color });
      g.circle(0, 0, RADIUS);
      g.fill();
    },
    [color],
  );

  // Read initial agent state for name/initial (stable after first render)
  const initialAgent = useSimulationStore.getState().agents[agentId];
  const agentName = initialAgent?.name ?? agentId;
  const initialLetter = agentName.charAt(0).toUpperCase();
  const initialActivity = truncateActivity(initialAgent?.activity ?? "");

  // Lerp animation — runs every frame via PixiJS ticker (D-05)
  useTick(() => {
    const agent = useSimulationStore.getState().agents[agentId];
    if (!agent || !containerRef.current) return;

    const target = agent.position;
    const cur = currentPosRef.current;

    // Lerp toward target position
    cur.x += (target.x - cur.x) * LERP;
    cur.y += (target.y - cur.y) * LERP;

    // Apply to container directly (imperative — bypasses React render cycle)
    containerRef.current.x = cur.x;
    containerRef.current.y = cur.y;

    // Update activity label text imperatively
    if (activityTextRef.current) {
      const newActivity = truncateActivity(agent.activity ?? "");
      if (activityTextRef.current.text !== newActivity) {
        activityTextRef.current.text = newActivity;
      }
    }
  });

  const handleClick = useCallback(() => {
    onSelect(agentId);
  }, [agentId, onSelect]);

  return (
    // pixiContainer is the agent root — interactive for pointer events (D-11)
    <pixiContainer
      ref={containerRef}
      interactive={true}
      cursor="pointer"
      onPointerTap={handleClick}
    >
      {/* Colored circle background (D-04) */}
      <pixiGraphics draw={drawCircle} />

      {/* First initial letter — centered on circle (D-04) */}
      <pixiText
        text={initialLetter}
        x={-4}
        y={-6}
        style={{
          fontFamily: "system-ui, sans-serif",
          fontSize: 12,
          fontWeight: "bold",
          fill: 0xffffff,
        }}
      />

      {/* Activity text ABOVE the circle (D-06) */}
      <pixiText
        ref={activityTextRef}
        text={initialActivity}
        x={0}
        y={-28}
        anchor={{ x: 0.5, y: 1 }}
        style={{
          fontFamily: "system-ui, sans-serif",
          fontSize: 9,
          fill: 0x555555,
        }}
      />

      {/* Name label BELOW the circle (D-06) */}
      <pixiText
        text={agentName}
        x={0}
        y={16}
        anchor={{ x: 0.5, y: 0 }}
        style={{
          fontFamily: "system-ui, sans-serif",
          fontSize: 10,
          fill: 0x333333,
        }}
      />
    </pixiContainer>
  );
}

/**
 * AgentSprite — public component.
 *
 * Renders a colored circle with initial letter, name/activity labels,
 * smooth lerp movement, and click-to-select interaction.
 */
export function AgentSprite({ agentId, colorIndex, onSelect }: AgentSpriteProps) {
  return <AgentSpriteInner agentId={agentId} colorIndex={colorIndex} onSelect={onSelect} />;
}
