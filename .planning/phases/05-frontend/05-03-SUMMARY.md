---
phase: 05-frontend
plan: 03
subsystem: frontend/map-rendering
tags: [pixi, agent-sprites, lerp, pan-zoom, zustand, click-select]
dependency_graph:
  requires: [05-01, 05-02]
  provides: [agent-sprites-on-map, pan-zoom-viewport, click-to-select]
  affects: [05-04]
tech_stack:
  added: []
  patterns:
    - useTick with getState() for per-frame position reads (no React re-renders)
    - useRef for PixiJS display object imperative mutation
    - hasDragged ref threshold (>5px) to disambiguate drag from click
    - Zoom-toward-cursor formula: newPan = cursor - (cursor - oldPan) * ratio
    - Stable useCallback draw callback with color dependency (never changes per agent)
key_files:
  created:
    - frontend/src/components/AgentSprite.tsx
  modified:
    - frontend/src/components/MapCanvas.tsx
decisions:
  - "useTick reads agent position via getState() (not useSimulationStore hook) — prevents per-frame React re-renders (Pitfall 2)"
  - "hasDraggedRef with 5px threshold prevents pan from triggering agent selection (Pitfall 4)"
  - "Activity text updated via activityTextRef.current.text mutation (not React state) for 60fps performance"
  - "Zoom centers on cursor using newPan = cursor - (cursor - oldPan) * (newZoom/oldZoom)"
  - "INITIAL_ZOOM=0.5 and centering calculation using window.innerWidth*0.75 for map-dominant layout (D-13)"
metrics:
  duration_minutes: 10
  completed_date: "2026-04-10"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 1
---

# Phase 05 Plan 03: Agent Sprites and Pan/Zoom Viewport Summary

**One-liner:** PixiJS useTick lerp-animated agent circle sprites with name/activity labels, plus click-drag pan and mouse-wheel zoom-to-cursor viewport in MapCanvas.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | AgentSprite component | 0807863 | frontend/src/components/AgentSprite.tsx |
| 2 | Pan/zoom viewport and agent rendering | 427cc40 | frontend/src/components/MapCanvas.tsx |

## What Was Built

### Task 1: AgentSprite (frontend/src/components/AgentSprite.tsx)

A PixiJS v8 React component rendering one agent on the map:

- **Circle sprite:** 12px radius filled circle in one of 8 AGENT_COLORS (coral red, sky blue, mint green, amber, lavender, teal, peach, slate), drawn via `useCallback`-wrapped `g.circle(0, 0, 12); g.fill()` (D-04)
- **Initial letter:** White bold system-ui text centered on the circle (D-04)
- **Activity text above:** `y=-28`, anchored center-bottom, truncated to 30 chars, updated imperatively via `activityTextRef.current.text` inside `useTick` (D-06)
- **Name label below:** `y=16`, anchored center-top, static (renders on mount from store state) (D-06)
- **Lerp animation:** `useTick` reads `getState().agents[agentId].position` each frame, applies `currentPos += (target - currentPos) * 0.08`, writes to `containerRef.current.x/y` directly — bypasses React render cycle (D-05)
- **Click handler:** `onPointerTap` on the container calls `onSelect(agentId)` which MapCanvas routes to `setSelectedAgent` (D-11)

Key performance contract: `getState()` (not `useSimulationStore` hook) is used inside `useTick` so there are zero React re-renders per animation frame.

### Task 2: MapCanvas update (frontend/src/components/MapCanvas.tsx)

MapCanvas now owns the pan/zoom viewport and renders all agent sprites:

**Pan (click-drag):**
- Wrapping `<div>` captures `onMouseDown`, `onMouseMove`, `onMouseUp`, `onMouseLeave`
- `dragRef` tracks: `{ active, startX, startY, startPanX, startPanY }`
- `hasDraggedRef` flips to `true` once pointer moves >5px — prevents drag from triggering agent selection
- On move: `setPanX(startPanX + dx); setPanY(startPanY + dy)`

**Zoom (mouse wheel):**
- `onWheel` on the same div, `e.preventDefault()` to block browser scroll
- `newZoom = clamp(zoom * (1 - deltaY * 0.001), 0.3, 2.0)`
- Zoom-toward-cursor: `newPan = cursor - (cursor - oldPan) * (newZoom / oldZoom)`

**Viewport container:**
- `<pixiContainer x={panX} y={panY} scale={zoom}>` wraps TileMap and all AgentSprites
- Initial pan centers the 3200×3200 map at `INITIAL_ZOOM=0.5` in the visible area

**Agent rendering:**
- `agentIds = useSimulationStore(s => Object.keys(s.agents))` — subscribes to agent list changes
- Maps to `<AgentSprite key={agentId} agentId={agentId} colorIndex={index} onSelect={handleAgentSelect} />`
- `handleAgentSelect` checks `hasDraggedRef.current` before calling `setSelectedAgent(id)`
- `handleViewportClick` on the viewport container calls `setSelectedAgent(null)` on empty-area tap

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Merge main branch to get Plan 01/02 foundation**

- **Found during:** Pre-task setup
- **Issue:** Worktree `worktree-agent-a029c5e0` was forked at commit `0406c14` (before Plan 01/02 commits). Plan 03 depends_on [05-01, 05-02]. The required types, store actions, and MapCanvas hook points were missing.
- **Fix:** `git merge main --no-edit` fast-forwarded the worktree to `966121f`, bringing in all Plan 01/02 commits including types, store, TileMap, and the Plan 02 MapCanvas hook point.
- **Files affected:** All Plan 01/02 files (merged, not modified)

**2. [Rule 1 - Bug] onPointerTap (camelCase) not onpointertap (lowercase)**

- **Found during:** Task 1 TypeScript verification
- **Issue:** First write used lowercase `onpointertap` following the plan's code example. TypeScript error: `Property 'onpointertap' does not exist on type 'PixiReactElementProps<typeof Container>'. Did you mean 'onPointerTap'?`
- **Fix:** Changed to `onPointerTap` (camelCase) — @pixi/react v8 uses React-style camelCase event names, not lowercase DOM event names.
- **Files modified:** frontend/src/components/AgentSprite.tsx

## Known Stubs

None — agent sprites render live positions from the Zustand store. When no agents are in the store (before WebSocket snapshot arrives), the map renders with no sprites (correct empty state). All labels display real data.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes. All rendering is WebGL canvas (T-05-07: not DOM innerHTML, no XSS vector). Agent count bounded by backend (T-05-08: 8 agents max in v1).

## Self-Check: PASSED

Files created/modified:

- [x] FOUND: frontend/src/components/AgentSprite.tsx
- [x] FOUND: frontend/src/components/MapCanvas.tsx

Commits verified:

- [x] FOUND: 0807863 (feat(05-03): add AgentSprite with lerp animation, labels, and click handler)
- [x] FOUND: 427cc40 (feat(05-03): add pan/zoom viewport and agent sprite rendering to MapCanvas)

Tests: 17 passed (all existing), 0 failures. TypeScript: 0 errors.
