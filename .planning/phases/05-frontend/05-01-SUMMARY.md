---
phase: 05-frontend
plan: 01
subsystem: frontend-data-layer
tags: [zustand, websocket, dispatch, typescript, tdd]
dependency_graph:
  requires: []
  provides: [agent-state-in-store, websocket-dispatch-by-type, pause-resume-commands]
  affects: [05-02, 05-03, 05-04]
tech_stack:
  added: []
  patterns: [module-level-ref-for-non-reactive-state, switch-dispatch-on-ws-message-type]
key_files:
  created:
    - frontend/src/tests/dispatch.test.ts
  modified:
    - frontend/src/types/index.ts
    - frontend/src/store/simulationStore.ts
    - frontend/src/hooks/useWebSocket.ts
    - frontend/src/components/BottomBar.tsx
decisions:
  - "Module-level _sendMessage ref (not Zustand state) avoids re-renders on every WS connect/disconnect"
  - "updateAgentPosition creates a new entry for unknown agents to handle race conditions safely"
  - "isPaused is driven exclusively by backend simulation_status broadcast, not local toggle in BottomBar"
metrics:
  duration_minutes: 4
  completed_date: "2026-04-10"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 4
---

# Phase 05 Plan 01: WebSocket Dispatch and Zustand Agent State Summary

**One-liner:** Typed WebSocket dispatch routing snapshot/agent_update/conversation/status messages to correct Zustand actions, with BottomBar wired to send pause/resume commands to backend.

## What Was Built

Plan 01 upgrades the frontend data layer from a naive "dump everything to feed" WebSocket handler into a fully typed message dispatch system. Agent positions and activities are now stored in the Zustand store as pixel-coordinate values (coord * TILE_SIZE), ready for PixiJS rendering in Plans 02 and 03.

### Types (frontend/src/types/index.ts)

- Added `TILE_SIZE = 32` constant
- Added `SnapshotAgent` interface matching the backend `get_snapshot()` payload
- Extended `WSMessageType` to cover the full backend Literal union: `snapshot | agent_update | conversation | simulation_status | event | ping | pong | error | pause | resume`
- Added personality fields to `AgentState`: `occupation`, `innate`, `age`, `currentLocation`
- Added `updateAgentsFromSnapshot`, `updateAgentPosition`, `setSendMessage` to `SimulationStore` interface

### Store (frontend/src/store/simulationStore.ts)

- `updateAgentsFromSnapshot(agents)`: converts coord arrays to pixel positions (`coord[0]*32`, `coord[1]*32`), replaces agents Record entirely
- `updateAgentPosition(name, coord, activity)`: updates single agent pixel position; creates minimal entry if agent doesn't exist yet (safe against race conditions)
- `setSendMessage` / `getSendMessage`: module-level non-reactive ref stores the WebSocket send function without triggering Zustand re-renders on WS lifecycle events

### Hook (frontend/src/hooks/useWebSocket.ts)

Replaced the blanket `appendFeed` call with a `switch` on `msg.type`:

| Message Type | Action |
|---|---|
| `snapshot` | `updateAgentsFromSnapshot(payload.agents)` + `setPaused` |
| `agent_update` | `updateAgentPosition(name, coord, activity)` |
| `conversation` | `appendFeed(msg)` |
| `simulation_status` | `setPaused(status === "paused")` |
| `event` | `appendFeed(msg)` |
| `pong` | `console.debug` |
| `error` | `console.warn` |
| `ping` | ignored |

On `ws.onopen`: stores `setSendMessage((msg) => ws.send(JSON.stringify(msg)))`.
On `ws.onclose` and cleanup: clears `setSendMessage(null)`.

### BottomBar (frontend/src/components/BottomBar.tsx)

- Removed local `setPaused(!isPaused)` toggle
- Button now calls `getSendMessage()` and sends `{ type: "pause" | "resume", payload: {}, timestamp: Date.now()/1000 }`
- `isPaused` is driven exclusively by the `simulation_status` broadcast from the backend — single source of truth

## Test Results

| Suite | Tests | Status |
|---|---|---|
| store.test.ts (pre-existing) | 5 | All pass |
| dispatch.test.ts (new) | 6 | All pass |
| providerSetup.test.tsx (pre-existing) | 6 | All pass |
| **Total** | **17** | **All pass** |

TypeScript: `npx tsc --noEmit` — clean, no errors.

## Commits

| Hash | Type | Description |
|---|---|---|
| aea5fd0 | test | TDD RED: failing dispatch tests for snapshot, agent_update, sendMessage |
| 86cb3ee | feat | Task 1: extend types and Zustand store with agent dispatch actions |
| ff5ddff | feat | Task 2: upgrade WebSocket dispatch and wire BottomBar pause/resume |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — no data flows to UI with empty/mock values. The BottomBar event input is intentionally `disabled` pending Phase 6 wiring, which is documented in the plan.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced beyond what the plan's threat model covers. T-05-01 (malformed message try/catch) is implemented in the `ws.onmessage` handler.

## Self-Check: PASSED

Files created:
- FOUND: /Users/sainobekou/projects/agent-town/frontend/src/tests/dispatch.test.ts

Files modified:
- FOUND: /Users/sainobekou/projects/agent-town/frontend/src/types/index.ts
- FOUND: /Users/sainobekou/projects/agent-town/frontend/src/store/simulationStore.ts
- FOUND: /Users/sainobekou/projects/agent-town/frontend/src/hooks/useWebSocket.ts
- FOUND: /Users/sainobekou/projects/agent-town/frontend/src/components/BottomBar.tsx

Commits verified:
- FOUND: aea5fd0
- FOUND: 86cb3ee
- FOUND: ff5ddff
