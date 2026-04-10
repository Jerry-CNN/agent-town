---
phase: 06-event-injection
plan: 01
subsystem: backend-event-pipeline
tags: [websocket, memory, event-injection, schema, tdd]
dependency_graph:
  requires: []
  provides: [inject_event-schema, engine-inject_event, ws-inject_event-handler]
  affects: [backend/schemas.py, backend/simulation/engine.py, backend/routers/ws.py, tests/test_event_injection.py]
tech_stack:
  added: []
  patterns: [tdd-red-green, ws-elif-chain, asyncio-to-thread, pydantic-literal-extension]
key_files:
  created:
    - tests/test_event_injection.py
  modified:
    - backend/schemas.py
    - backend/simulation/engine.py
    - backend/routers/ws.py
decisions:
  - "Hardcode importance=8 for injected events — skips score_importance() LLM call per research recommendation; injected events are inherently high priority"
  - "Truncate event text to 500 chars in engine.inject_event() (T-06-03 DoS mitigation)"
  - "Validation of empty text and invalid mode in ws.py upstream of engine call (T-06-01, T-06-02)"
  - "Invalid whisper target logs warning and returns without error to client — engine silently rejects, ws.py still broadcasts the event confirmation"
metrics:
  duration_minutes: 20
  completed_at: "2026-04-10T05:05:29Z"
  tasks_completed: 2
  files_modified: 4
  tests_added: 15
---

# Phase 6 Plan 01: Backend Event Injection Pipeline Summary

**One-liner:** WebSocket inject_event pipeline with broadcast/whisper modes, importance-8 ChromaDB memory storage, input validation, and activity-feed confirmation broadcast.

## What Was Built

Backend plumbing that routes user-injected events from WebSocket into agent memory streams:

1. **Schema extension** (`backend/schemas.py`): Added `"inject_event"` to the `WSMessage.type` Literal union as the 11th type — the inbound command from the browser that triggers event injection.

2. **Engine method** (`backend/simulation/engine.py`): New `async def inject_event(text, mode, target)` on `SimulationEngine`. Broadcast mode stores a `memory_type="event"`, `importance=8` memory in all agents' ChromaDB streams via `add_memory()`. Whisper mode stores only for the named target. Unknown targets or invalid modes log a warning and return without storing. Text truncated to 500 chars (T-06-03).

3. **WebSocket handler** (`backend/routers/ws.py`): New `elif message.type == "inject_event":` branch after the resume handler. Validates non-empty text (T-06-01) and mode in `{"broadcast", "whisper"}` (T-06-02), returning `type="error"` to the sender on failure. On success: awaits `engine.inject_event()`, then broadcasts a `type="event"` confirmation with D-09 label format to all connected clients.

4. **Test suite** (`tests/test_event_injection.py`): 15 tests covering schema validation, broadcast/whisper/invalid-target engine behavior, truncation, WebSocket integration for all handler branches, and D-09 label format verification.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| TDD RED | Failing tests for schema, engine, ws.py | c762300 | tests/test_event_injection.py |
| 1 | Schema extension + engine.inject_event() | 764c6d9 | backend/schemas.py, backend/simulation/engine.py |
| 2 | ws.py inject_event handler + broadcast | 72b9709 | backend/routers/ws.py |

## Verification Results

```
uv run pytest tests/test_event_injection.py -x -q
15 passed in 7.18s

uv run pytest tests/ -x -q
178 passed, 1 warning in 4.70s
```

All acceptance criteria met:
- `grep -c "inject_event" backend/schemas.py` → 2 (≥1)
- `grep -c "async def inject_event" backend/simulation/engine.py` → 1
- `grep -c "importance.*8" backend/simulation/engine.py` → 2 (≥1)
- `grep -c "add_memory" backend/simulation/engine.py` → 4 (≥2)
- `grep -c "inject_event" backend/routers/ws.py` → 2 (≥2)
- `grep -c "await engine.inject_event" backend/routers/ws.py` → 1
- `grep -c "manager.broadcast" backend/routers/ws.py` → 3 (≥3)
- `grep -c "Event text is empty" backend/routers/ws.py` → 1

## Deviations from Plan

None — plan executed exactly as written.

The TDD flow followed the plan's specified sequence: RED (failing tests committed first), GREEN (implementation making all 15 tests pass), no REFACTOR needed (code was clean as written).

## Threat Mitigations Applied

| Threat ID | Mitigation | Location |
|-----------|-----------|---------|
| T-06-01 | Empty/whitespace-only text returns type="error" to sender | backend/routers/ws.py |
| T-06-02 | Unknown mode returns type="error" to sender | backend/routers/ws.py |
| T-06-03 | Text truncated to 500 chars before add_memory() | backend/simulation/engine.py |
| T-06-04 | Unknown whisper target logs warning, stores nothing | backend/simulation/engine.py |
| T-06-05 | Accepted — no rate-limiting for single-user v1 | — |
| T-06-06 | Accepted — event text echoed to all clients is acceptable for v1 | — |

## Known Stubs

None — all behavior is wired end-to-end. The activity feed rendering for `type="event"` was already complete in ActivityFeed.tsx (Phase 5), so injected events will appear immediately in the frontend feed when Plan 02 wires up the BottomBar input.

## Threat Flags

None — no new network endpoints or auth paths introduced. The inject_event message type is handled within the existing `/ws` WebSocket endpoint with the same trust boundary already established in Phase 4.

## Self-Check: PASSED

Files exist:
- FOUND: tests/test_event_injection.py
- FOUND: backend/schemas.py (modified)
- FOUND: backend/simulation/engine.py (modified)
- FOUND: backend/routers/ws.py (modified)

Commits exist:
- FOUND: c762300 (test RED)
- FOUND: 764c6d9 (feat schema + engine)
- FOUND: 72b9709 (feat ws.py handler)
