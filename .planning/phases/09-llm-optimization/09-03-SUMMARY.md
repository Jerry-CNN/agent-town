---
phase: 09-llm-optimization
plan: "03"
subsystem: engine-integration-frontend
tags:
  - websocket
  - engine
  - frontend
  - llm-optimization
  - race-condition
  - provider-ux
dependency_graph:
  requires:
    - 09-01
    - 09-02
  provides:
    - tick_interval_update WS type registered (prevents simulation crash)
    - engine gating wired with schedule_changed parameter
    - conversation race prevention via _active_conversations set
    - OpenRouter/Kimi K2.5 as default provider
    - Settings button to reopen provider modal
    - Tick interval display in bottom bar
  affects:
    - backend/schemas/ws.py
    - backend/simulation/engine.py
    - backend/config.py
    - backend/routers/llm.py
    - frontend/src/components/ProviderSetup.tsx
    - frontend/src/components/Layout.tsx
    - frontend/src/components/BottomBar.tsx
    - frontend/src/App.tsx
    - frontend/src/store/simulationStore.ts
    - frontend/src/types/index.ts
    - frontend/src/hooks/useWebSocket.ts
tech_stack:
  added: []
  patterns:
    - frozenset pair-key pattern for symmetric conversation deduplication
    - dynamic attribute _last_schedule_block on Agent for schedule change detection
    - props.initialConfig pre-population pattern for reopenable settings modals
key_files:
  created: []
  modified:
    - backend/schemas/ws.py
    - backend/simulation/engine.py
    - backend/config.py
    - backend/routers/llm.py
    - frontend/src/components/ProviderSetup.tsx
    - frontend/src/components/Layout.tsx
    - frontend/src/components/BottomBar.tsx
    - frontend/src/App.tsx
    - frontend/src/store/simulationStore.ts
    - frontend/src/types/index.ts
    - frontend/src/hooks/useWebSocket.ts
decisions:
  - "OpenRouter/Kimi K2.5 set as default — user-configured per memory note, matches D-01/D-02"
  - "schedule_changed uses _last_schedule_block dynamic attr on Agent rather than a new dataclass field — avoids schema migration and keeps gating logic fully in engine"
  - "_active_conversations cleared at tick START not at tick END — ensures clean state before concurrent TaskGroup, not after (prevents carry-over from aborted ticks)"
  - "tick_interval_update broadcast sent AFTER sleep calculation but BEFORE sleep — client sees the interval that will actually be used for next sleep"
metrics:
  duration: "~30 minutes"
  completed_date: "2026-04-11"
  tasks_completed: 2
  files_modified: 11
---

# Phase 09 Plan 03: Engine Integration and Frontend UX Summary

Engine integration completing the Phase 9 optimization loop: tick_interval_update WS type registered (Codex P0-1 crash fix), per-sector gating wired with schedule_changed param (Codex P1-2/P1-6), conversation race prevention via _active_conversations set (Codex P1-4), terminated_reason forwarded in conversation broadcasts (Codex P2-7), OpenRouter/Kimi K2.5 as pre-selected default (D-01/D-02), Settings button to reopen provider modal (D-03), and adaptive tick interval displayed in bottom bar (D-06).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1a | Register tick_interval_update WS type, wire engine gating/race-prevention, update backend defaults | 779271c | backend/schemas/ws.py, backend/simulation/engine.py, backend/config.py, backend/routers/llm.py |
| 1b | Frontend: settings button, tick interval display, OpenRouter-first provider modal | ccab0ed | frontend/src/components/ProviderSetup.tsx, Layout.tsx, BottomBar.tsx, App.tsx, simulationStore.ts, types/index.ts, useWebSocket.ts |

## What Was Built

### Backend (Task 1a)

**Codex P0-1 — Critical simulation crash fix:**
`tick_interval_update` added to WSMessage type Literal in `backend/schemas/ws.py`. Without this, `_make_broadcast_callback` in `main.py` wraps every engine broadcast in `WSMessage(...)`, causing a Pydantic validation error that propagates into the TaskGroup running the tick loop and crashes the entire simulation.

**Codex P1-4 — Conversation race prevention:**
`self._active_conversations: set[frozenset[str]] = set()` added to `SimulationEngine.__init__`. In `_agent_step()`, a `pair_key = frozenset({agent_name, other_name})` is claimed before `agent.converse()` and discarded after. The set is cleared at the start of each tick in `_tick_loop()`. This prevents two agents from both passing `check_cooldown()` simultaneously and running duplicate conversations with conflicting schedule writes.

**Codex P1-2/P1-6 — Per-sector gating with schedule_changed:**
`_get_current_schedule_describe()` helper added to `SimulationEngine` — walks agent's schedule in reverse to find the current entry by sim time. In `_agent_step()`, `schedule_changed` is computed by comparing the current schedule block describe against `agent._last_schedule_block` (dynamic attr). Passed to `decide_action()` along with `last_sector` and `new_perceptions`. When `decide_action` returns `None` (gating skip), the function returns early. `agent.last_sector` updated after each non-gated action.

**Codex P2-7 — Conversation terminated_reason forwarding:**
`_emit_conversation()` updated to include `terminated_reason` in the broadcast payload when present in the conversation result dict.

**D-06 — Tick interval broadcast:**
After each tick's sleep calculation, `tick_interval_update` broadcast sent to all connected clients with `round(current_tick, 1)`.

**D-01/D-02 — Provider defaults:**
`OPENROUTER_DEFAULT_MODEL` updated to `"openrouter/moonshotai/kimi-k2.5"`. `AppState.provider` default changed from `"ollama"` to `"openrouter"`.

**D model in /api/config response:**
`backend/routers/llm.py` POST /api/config response now includes `model` field.

### Frontend (Task 1b)

**D-01/D-02 — OpenRouter-first provider modal:**
`ProviderSetup.tsx` rewritten: `useState<Provider>("openrouter")` default (via `initialConfig?.provider ?? "openrouter"`), OpenRouter radio first, Ollama renamed to "Ollama (Local -- advanced)". Model text input appears when OpenRouter selected, pre-filled with `openrouter/moonshotai/kimi-k2.5`. Model value POSTed to `/api/config` and stored in Zustand/localStorage.

**D-03 — Settings button and modal reopen:**
`Layout.tsx` accepts `onOpenSettings: () => void` prop and renders a "Settings" button in the header. `App.tsx` adds `showSettings` state; renders `ProviderSetup` when `providerConfig === null` OR `showSettings === true`. When opened via settings, `initialConfig={providerConfig}` pre-populates fields and `onClose` callback dismisses the modal.

**D-06 — Tick interval display:**
`BottomBar.tsx` reads `tickInterval` from store and renders `Tick: {tickInterval}s` label. `simulationStore.ts` adds `tickInterval: 10` initial state and `setTickInterval` action. `useWebSocket.ts` handles `tick_interval_update` messages and extracts `tick_interval` from snapshot messages.

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Notes

**Pre-existing test failures (out of scope):**
4 tests were failing before this plan and remain failing after (verified with git stash):
- `tests/test_health.py::test_health_returns_200_with_correct_keys` — 404 on /health
- `tests/test_integration.py::test_health_check_returns_200` — same
- `tests/test_integration.py::test_config_ollama_returns_configured` — integration test
- `tests/test_integration.py::test_config_openrouter_returns_configured` — integration test
- `tests/test_simulation.py::test_movement_one_tile_per_tick` — coordinate assertion

These are pre-existing failures unrelated to Phase 9 changes. 281 other tests pass.

## Known Stubs

None — all data paths are wired. `tickInterval` initializes to `10` (the `min_interval` from `get_adaptive_tick_interval`) and updates via WebSocket on first tick/snapshot.

## Threat Flags

No new security-relevant surface introduced beyond what is documented in the plan's threat model (T-09-07 through T-09-10, all accepted).

## Self-Check: PASSED

All commits verified:
- `779271c` — backend changes (ws.py, engine.py, config.py, llm.py)
- `ccab0ed` — frontend changes (7 files)

All key files verified present with correct content via grep checks.
