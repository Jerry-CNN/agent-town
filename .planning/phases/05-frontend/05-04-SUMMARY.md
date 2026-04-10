---
phase: 05-frontend
plan: 04
subsystem: frontend-activity-feed, frontend-inspector-panel
tags: [react, zustand, testing-library, vitest, tdd, websocket-feed, agent-inspector]
dependency_graph:
  requires: [05-01-websocket-dispatch, 05-02-memories-endpoint]
  provides: [formatted-activity-feed, agent-inspector-panel, sidebar-switching]
  affects: [05-05-agent-sprites]
tech_stack:
  added: []
  patterns:
    - useRef scroll-pause pattern (userScrolled ref tracks user scroll position)
    - Agent color hash function for consistent name-to-color mapping
    - useEffect + fetch for on-demand REST data in inspector
    - act() + waitFor() for async component tests with fetch mocking
key_files:
  created:
    - frontend/src/components/AgentInspector.tsx
    - frontend/src/tests/activityFeed.test.tsx
    - frontend/src/tests/inspector.test.tsx
  modified:
    - frontend/src/components/ActivityFeed.tsx
    - frontend/src/components/Layout.tsx
decisions:
  - "scrollIntoView mocked globally in test setup (window.HTMLElement.prototype.scrollIntoView = vi.fn()) because jsdom does not implement it"
  - "Agent color consistency: getAgentColor() uses simple character-sum hash (same index logic as AgentSprite) so feed name color matches map sprite color"
  - "Layout close handler uses useSimulationStore.getState().setSelectedAgent(null) (not a hook) to avoid unnecessary re-renders from hook subscription in Layout"
  - "Inspector memory keys use array index (not content hash) since ChromaDB does not guarantee stable memory IDs across fetches"
metrics:
  duration_minutes: 8
  completed_date: "2026-04-09"
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 2
---

# Phase 05 Plan 04: Activity Feed and Agent Inspector Summary

**One-liner:** Formatted activity feed with agent-colored conversation entries and HH:MM:SS timestamps plus an inspector panel showing agent profile, innate trait pills, current state, and last 5 ChromaDB memories fetched on demand.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (TDD RED) | Failing ActivityFeed tests | 03b2517 | frontend/src/tests/activityFeed.test.tsx |
| 1 (TDD GREEN) | Upgrade ActivityFeed | 7d7fa57 | frontend/src/components/ActivityFeed.tsx, frontend/src/tests/activityFeed.test.tsx |
| 2 | AgentInspector + Layout wiring | 653f635 | frontend/src/components/AgentInspector.tsx, frontend/src/components/Layout.tsx, frontend/src/tests/inspector.test.tsx |

## What Was Built

### Task 1: Upgraded ActivityFeed (TDD)

`frontend/src/components/ActivityFeed.tsx` now:

- Formats `conversation` messages as `[HH:MM:SS] AgentName: text` — agent name rendered as a `<span>` with a color derived from a character-sum hash matching the AgentSprite palette
- Formats `event` messages as `[HH:MM:SS] Event: text` with an amber label
- Falls back to type + JSON payload for unexpected message types
- Auto-scroll via `userScrolled` ref: `onScroll` handler checks if `scrollHeight - scrollTop - clientHeight < 10`; if user scrolled up, auto-scroll pauses until they return to the bottom
- `data-testid="feed-container"` on the scrollable outer div for test targeting
- Empty state shows "No activity yet." placeholder

`frontend/src/tests/activityFeed.test.tsx` (4 tests, all pass):

| Test | Coverage |
|------|----------|
| 1 | Conversation entry renders colored name, action text, HH:MM:SS timestamp |
| 2 | Event entry renders "Event:" prefix and event text |
| 3 | Empty feed shows "No activity yet." |
| 4 | Feed container has overflowY: auto |

### Task 2: AgentInspector Panel + Layout Wiring

`frontend/src/components/AgentInspector.tsx`:

- Props: `{ agentId: string; onClose: () => void }`
- Reads agent from Zustand store — shows "Agent not found." if missing
- **Header:** agent name (bold, 16px) + close button (aria-label="Close inspector")
- **Profile section:** Occupation, Age, innate trait pills (comma-split, rounded pill badges)
- **Current State section:** Activity, Location
- **Recent Memories section:** Fetches `GET /api/agents/{name}/memories?limit=5` on mount and agentId change; loading state while fetching; memory cards with importance-colored left border (red ≥8, orange ≥5, blue <5); importance badge and HH:MM timestamp per card

`frontend/src/components/Layout.tsx`:

- Imports `AgentInspector` and `useSimulationStore`
- Replaces the "Inspector placeholder" div with `<AgentInspector agentId={selectedAgentId!} onClose={() => useSimulationStore.getState().setSelectedAgent(null)} />`

`frontend/src/tests/inspector.test.tsx` (6 tests, all pass):

| Test | Coverage |
|------|----------|
| 1 | Agent name rendered in header |
| 2 | Occupation label + value + innate trait pills |
| 3 | Current activity displayed |
| 4 | Close button fires onClose |
| 5 | Memories fetched and rendered (waitFor async) |
| 6 | "Agent not found." when agentId missing from store |

## Test Results

| Suite | Tests | Status |
|-------|-------|--------|
| store.test.ts (pre-existing) | 5 | All pass |
| dispatch.test.ts (pre-existing) | 6 | All pass |
| providerSetup.test.tsx (pre-existing) | 6 | All pass |
| activityFeed.test.tsx (new) | 4 | All pass |
| inspector.test.tsx (new) | 6 | All pass |
| **Total** | **27** | **All pass** |

TypeScript: `npx tsc --noEmit` — clean, no errors.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] jsdom missing scrollIntoView implementation**

- **Found during:** Task 1 TDD RED run
- **Issue:** jsdom does not implement `HTMLElement.prototype.scrollIntoView`, causing all ActivityFeed tests to throw `TypeError: bottomRef.current?.scrollIntoView is not a function` before any assertions ran.
- **Fix:** Added `window.HTMLElement.prototype.scrollIntoView = vi.fn()` in `beforeAll` in the test file. Also needed to add `beforeAll` to the vitest import list.
- **Files modified:** frontend/src/tests/activityFeed.test.tsx
- **Commit:** 7d7fa57

**2. [Rule 1 - Bug] Unused `style` variable in Test 4 caused TypeScript error**

- **Found during:** Post-GREEN TypeScript check
- **Issue:** `const style = window.getComputedStyle(container!)` was declared but never used — the assertion used `(container as HTMLElement).style.overflowY` instead.
- **Fix:** Removed the unused `const style = ...` line.
- **Files modified:** frontend/src/tests/activityFeed.test.tsx
- **Commit:** 7d7fa57

**3. [Rule 1 - Bug] act() warnings from async fetch state updates in inspector tests**

- **Found during:** Task 2 test run
- **Issue:** Tests 1-6 triggered "not wrapped in act()" React warnings because the `useEffect` fetch in AgentInspector resolves asynchronously after render, updating `memories` and `loadingMemories` state outside `act()`.
- **Fix:** Wrapped `render(...)` calls in `await act(async () => { ... })` and added `await waitFor(() => ...)` to let async state settle before assertions.
- **Files modified:** frontend/src/tests/inspector.test.tsx

## Known Stubs

None — ActivityFeed formats real WSMessage data from the store. AgentInspector fetches real memories from the backend endpoint. No hardcoded placeholder data flows to the UI.

## Threat Flags

None — all trust boundaries are within the plan's threat model:
- T-05-09: Memory content rendered via JSX text interpolation (auto-escaped, no innerHTML)
- T-05-10: Personality data from static agent configs, not private user data
- T-05-11: GET /api/agents/* is localhost-only, no CSRF risk

## Self-Check: PASSED
