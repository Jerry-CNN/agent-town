---
phase: 08-visual-building-behavior
plan: "01"
subsystem: frontend
tags: [pixi, rendering, visual, agent-labels, sector-outlines]
dependency_graph:
  requires: []
  provides: [wall-stroke-outlines, agent-label-pills, readable-sector-labels]
  affects: [frontend/src/components/TileMap.tsx, frontend/src/components/AgentSprite.tsx]
tech_stack:
  added: []
  patterns: [pixi-v8-stroke-after-fill, fixed-width-pill-draw, module-level-pure-utility]
key_files:
  created: []
  modified:
    - frontend/src/components/TileMap.tsx
    - frontend/src/components/AgentSprite.tsx
decisions:
  - "darkenColor utility computes stroke color as 35% darker than fill — no external library needed"
  - "Fixed-width pills (180px activity, 120px name) avoid redraw on text change per Pitfall 3"
  - "useCallback deps kept empty on all pill draw fns — pill dimensions are static constants"
metrics:
  duration_minutes: 15
  completed: "2026-04-11T18:48:31Z"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 2
---

# Phase 08 Plan 01: Visual Building Behavior — Map Outlines & Agent Labels Summary

**One-liner:** 3px dark stroke outlines on sector bounding boxes + white-on-dark-pill agent labels at 16-20px replacing unreadable 9-12px dark text.

## What Was Built

### Task 1: TileMap wall stroke outlines + 28px sector labels (commit `62a4ae5`)

Modified `frontend/src/components/TileMap.tsx`:

- Added `darkenColor(hex, factor)` pure utility function at module level — computes a darker shade of any hex color by reducing each RGB channel by `factor * 100%`. Used to derive stroke color from sector fill color (35% darker).
- In `drawMap` useCallback, added `g.setStrokeStyle({ color: darkenColor(bounds.color, 0.35), width: 3 })` + `g.rect(...)` + `g.stroke()` after each sector's fill pass. Building outlines are now visible as dark-bordered rectangles.
- Updated `LABEL_STYLE`: `fontSize` 13 → 28, `fontWeight` "600" → "700", `fill` 0x333333 → 0x222222, added `stroke: { color: 0xffffff, width: 3 }` for white halo contrast.
- `useCallback` deps array preserved as `[]` — no per-frame redraws.

### Task 2: AgentSprite background pills + increased font sizes (commit `84e4dde`)

Modified `frontend/src/components/AgentSprite.tsx`:

- `MAX_ACTIVITY_LEN` reduced from 30 to 25 (D-07).
- Added `drawActivityPill` useCallback: draws a 180x22px rounded rect (`roundRect(-90, -42, 180, 22, 6)`) with `color: 0x111111, alpha: 0.65`. Fixed width covers 25-char text at 16px without needing text measurement.
- Added `drawNamePill` useCallback: draws a 120x24px rounded rect (`roundRect(-60, 14, 120, 24, 6)`) with same fill.
- Both pill callbacks have empty deps `[]` — pill dimensions are static.
- JSX render order: pill Graphics drawn BEFORE corresponding text node so text sits on top.
- Font sizes updated: activity 9px → 16px, name 10px → 20px, initial letter 12px → 16px. All text fill changed from dark (0x333333/0x555555) to white (0xffffff) since background is dark.

## Verification

- `npx tsc --noEmit` — zero type errors (both tasks)
- `useCallback` deps still `[]` on `drawMap`, `drawActivityPill`, `drawNamePill`
- `darkenColor` exists as module-level pure function
- `g.setStrokeStyle` + `g.stroke()` confirmed in SECTOR_BOUNDS loop
- All font sizes, fill colors, and pill positions confirmed via grep

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. Both modifications wire directly to existing PixiJS render pipeline with no placeholder data.

## Threat Flags

None. Changes are purely client-side rendering additions. No new network endpoints, auth paths, or trust boundaries introduced. Threat register entries T-08-01 and T-08-02 remain accepted per plan.

## Self-Check: PASSED

- `frontend/src/components/TileMap.tsx` — FOUND, modified
- `frontend/src/components/AgentSprite.tsx` — FOUND, modified
- Commit `62a4ae5` — FOUND (feat(08-01): add wall stroke outlines and 28px sector labels to TileMap)
- Commit `84e4dde` — FOUND (feat(08-01): add background pills and increase agent label font sizes)
