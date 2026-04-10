---
phase: 06-event-injection
plan: 02
subsystem: frontend-event-input
tags: [frontend, event-injection, websocket, zustand, react, testing-library]
dependency_graph:
  requires: [06-01]
  provides: [bottombar-event-input, inject_event-frontend-dispatch]
  affects: [frontend/src/types/index.ts, frontend/src/components/BottomBar.tsx, frontend/src/tests/eventInjection.test.tsx]
tech_stack:
  added: []
  patterns: [controlled-input, zustand-selector, conditional-render, data-testid]
key_files:
  created:
    - frontend/src/tests/eventInjection.test.tsx
  modified:
    - frontend/src/types/index.ts
    - frontend/src/components/BottomBar.tsx
decisions:
  - "Whisper target auto-selects first agent key on mode switch — prevents empty target on first submit"
  - "option[disabled] for empty-agents case is intentional UX (not the input disabled attribute) — acceptance criteria grep returns 1 but the text input itself has no disabled attr"
  - "Store-level tests (Tests 12-13) added alongside DOM tests to exercise message construction without rendering overhead"
metrics:
  duration_minutes: 5
  completed_at: "2026-04-10T05:10:37Z"
  tasks_completed: 1
  files_modified: 3
  tests_added: 13
---

# Phase 6 Plan 02: Frontend Event Injection UI Summary

**One-liner:** BottomBar event input enabled with broadcast/whisper delivery toggle, whisper agent dropdown from Zustand state, and inject_event WSMessage dispatch on Enter/Send.

## What Was Built

Frontend half of the event injection system — the user-facing controls for typing and sending events:

1. **Type union extension** (`frontend/src/types/index.ts`): Added `"inject_event"` to the `WSMessageType` union as the 11th type, matching the backend schema extension from Plan 01.

2. **BottomBar rewrite** (`frontend/src/components/BottomBar.tsx`): Replaced the disabled input placeholder with a fully wired event injection UI:
   - Controlled text input (enabled, white text, focus border) with Enter-key submission
   - Broadcast / Whisper pill-button toggle (`data-testid="delivery-mode"`) — broadcast uses #3a86ff, whisper uses #9b59b6
   - Conditional whisper target `<select>` (`data-testid="whisper-target"`) populated from `Object.keys(useSimulationStore.agents)` — exact agent name keys per T-06-08
   - "No agents available" disabled option when the store has no agents
   - Auto-selects first agent key when switching to whisper mode to prevent empty target submission
   - Submit button (`data-testid="submit-event"`) with Send label and accent color matching delivery mode
   - Guard: `if (!eventText.trim()) return` prevents empty/whitespace submissions reaching the backend (T-06-07)
   - Dispatches via `getSendMessage()` with payload `{ text, mode, target? }` and `timestamp: Date.now() / 1000`
   - Input clears after successful submission via `setEventText("")`

3. **Test suite** (`frontend/src/tests/eventInjection.test.tsx`): 13 tests covering:
   - Input is enabled (not disabled)
   - Typing updates controlled value
   - Click Send dispatches inject_event with correct broadcast payload
   - Input clears after submission
   - Enter key triggers dispatch and clears input
   - Empty input does not dispatch (client-side guard)
   - Whitespace-only input does not dispatch
   - Delivery mode toggle renders both buttons
   - Whisper dropdown appears only in whisper mode
   - Whisper dispatch includes target agent name
   - Empty agent store shows "No agents available" option
   - Store-level broadcast construction (no DOM)
   - Store-level whisper construction with target (no DOM)

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add inject_event to WSMessageType and implement BottomBar event input UI | a6f1201 | frontend/src/types/index.ts, frontend/src/components/BottomBar.tsx, frontend/src/tests/eventInjection.test.tsx |
| 2 | Verify end-to-end event injection flow | checkpoint | awaiting human verification |

## Verification Results

```
cd frontend && npm test -- --run
6 test files, 40 tests passed

uv run pytest tests/ -x -q
178 passed, 1 warning
```

All acceptance criteria met:
- `grep -c "inject_event" frontend/src/types/index.ts` → 1 (>=1)
- `grep -c "disabled" frontend/src/components/BottomBar.tsx` → 1 (only `<option disabled>` placeholder, not the text input)
- `grep -c "handleSubmitEvent\|handleSubmit" frontend/src/components/BottomBar.tsx` → 3 (>=1)
- `grep -c "whisperTarget\|whisper-target" frontend/src/components/BottomBar.tsx` → 5 (>=1)
- `grep -c "deliveryMode\|delivery-mode" frontend/src/components/BottomBar.tsx` → 10 (>=1)
- `grep -c "getSendMessage" frontend/src/components/BottomBar.tsx` → 3 (>=1)
- `grep -c "inject_event" frontend/src/components/BottomBar.tsx` → 1 (>=1)

## Checkpoint: Human Verification Required

**Task 2 — End-to-end verification** is a `checkpoint:human-verify` gate. The autonomous implementation is complete. Human verification steps:

1. Start the backend: `cd /Users/sainobekou/projects/agent-town && uv run uvicorn backend.main:app --reload`
2. Start the frontend: `cd frontend && npm run dev` then visit http://localhost:5173
3. Verify the BottomBar shows an enabled text input (not grayed out)
4. Verify a delivery mode selector (Broadcast / Whisper) is visible
5. Type "A meteor is heading toward the town" and press Enter with Broadcast selected
6. Check the activity feed shows "Event broadcast: A meteor is heading toward the town" with gold Event: label
7. Switch to Whisper mode, select an agent from the dropdown
8. Type "I have a secret treasure map" and press Enter
9. Check the activity feed shows "Whispered to [agent name]: I have a secret treasure map"
10. Verify the input clears after each submission
11. Try pressing Enter with empty input — nothing should happen
12. (Optional) Watch for gossip spreading as agents converse after a whisper (EVT-04)

## Deviations from Plan

**1. [Rule 2 - Missing Critical Functionality] Whisper target auto-selection on mode switch**
- **Found during:** Task 1 implementation
- **Issue:** Without auto-selecting the first agent when switching to Whisper mode, the whisperTarget state would be empty ("") and a submit would send an empty target to the backend
- **Fix:** Added `if (mode === "whisper" && !whisperTarget && agentKeys.length > 0) setWhisperTarget(agentKeys[0])` in `handleDeliveryModeChange`
- **Files modified:** frontend/src/components/BottomBar.tsx
- **Commit:** a6f1201

## Threat Mitigations Applied

| Threat ID | Mitigation | Location |
|-----------|-----------|---------|
| T-06-07 | `if (!eventText.trim()) return` before send call | frontend/src/components/BottomBar.tsx |
| T-06-08 | Whisper target dropdown uses `Object.keys(agents)` — exact match with backend agent state keys | frontend/src/components/BottomBar.tsx |
| T-06-09 | Accepted — no authentication on WSMessage for single-user v1 | — |

## Known Stubs

None — all behavior is wired end-to-end. The BottomBar dispatches real inject_event WSMessages, the backend (Plan 01) processes them and broadcasts event confirmations, and the ActivityFeed (Phase 5) already renders `type="event"` messages with gold labels.

## Threat Flags

None — no new network endpoints or auth paths introduced. The inject_event message type is handled within the existing `/ws` WebSocket endpoint established in Phase 4.

## Self-Check: PASSED

Files exist:
- FOUND: frontend/src/types/index.ts (modified)
- FOUND: frontend/src/components/BottomBar.tsx (rewritten)
- FOUND: frontend/src/tests/eventInjection.test.tsx (created)

Commits exist:
- FOUND: a6f1201 (feat BottomBar event injection)
