---
phase: 04-simulation-engine-transport
plan: 02
subsystem: websocket-transport
tags: [websocket, asyncio, fastapi, lifespan, connection-manager, broadcast]
requirements: [SIM-02, SIM-03]

dependency_graph:
  requires:
    - backend/simulation/engine.py (Plan 01: SimulationEngine, get_snapshot, pause, resume)
    - backend/schemas.py (WSMessage expanded here)
    - backend/routers/ws.py (stub expanded here)
    - backend/main.py (lifespan expanded here)
    - backend/simulation/map_generator.py
    - backend/simulation/world.py
    - backend/agents/loader.py
  provides:
    - ConnectionManager class (WebSocket multi-client broadcast, dead-connection removal)
    - WSMessage schema with all Phase 4 event types (snapshot, simulation_status, conversation, pause, resume)
    - WebSocket endpoint: snapshot-on-connect, pause/resume commands, graceful degradation
    - FastAPI lifespan: full engine + manager init, broadcast callback wiring, sim loop start/cancel
    - _make_broadcast_callback helper (engine dict -> WSMessage -> broadcast)
  affects:
    - Phase 5 (frontend): consumes the WebSocket stream for rendering agent positions and activity
    - Phase 6 (event injection): adds "event" type messages through ConnectionManager.broadcast

tech_stack:
  added: []
  patterns:
    - ConnectionManager pattern (list of WebSocket, broadcast with dead-connection removal)
    - Snapshot-before-register pattern (D-05: send snapshot FIRST, then add to active list)
    - app.state access via websocket.app (FastAPI WebSocket DI limitation workaround)
    - asyncio.create_task + sim_task.cancel() + CancelledError await (T-04-07 lifespan pattern)
    - _make_broadcast_callback closure (decoupled engine data dict -> WSMessage JSON)
    - Lifespan mock pattern with MockEngineFactory for WS endpoint tests

key_files:
  created:
    - backend/simulation/connection_manager.py
  modified:
    - backend/schemas.py
    - backend/routers/ws.py
    - backend/main.py
    - tests/test_simulation.py
    - tests/test_integration.py

decisions:
  - websocket.app.state access: FastAPI's DI does not inject Request into WebSocket endpoints; use websocket.app to reach app.state
  - Snapshot-before-register (D-05): client gets full state before being added to active_connections, preventing delta-before-baseline race condition
  - _make_broadcast_callback closure: wraps engine's raw dict into a validated WSMessage before broadcasting — keeps engine decoupled from WSMessage schema
  - Dead connections removed after broadcast loop (not during): avoids list mutation during iteration (T-04-06)
  - Lifespan test strategy: patch backend.main.SimulationEngine with MockEngineFactory so app.state.engine is our mock after lifespan runs

metrics:
  duration: "~35 minutes"
  completed: "2026-04-10"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 5
---

# Phase 04 Plan 02: WebSocket Transport — ConnectionManager, Lifespan Wiring, and Snapshot Protocol

**One-liner:** ConnectionManager broadcast with dead-connection removal, snapshot-before-register connect protocol, pause/resume WebSocket commands, and FastAPI lifespan that wires SimulationEngine to all connected clients via _make_broadcast_callback

## What Was Built

### ConnectionManager (`backend/simulation/connection_manager.py`)

A minimal broadcast hub for WebSocket connections. Key behaviors:
- `active_connections: list[WebSocket]` — mutable list of live connections
- `connect(ws)` — accepts + appends (callers must send snapshot first for D-05 pattern)
- `disconnect(ws)` — safe remove (no-op if not in list)
- `broadcast(message)` — sends text to all; dead connections (any exception on `send_text`) collected post-loop and removed (T-04-06: never mutate list during iteration)

### WSMessage Schema Expansion (`backend/schemas.py`)

`WSMessage.type` Literal expanded from 5 to 10 values:

| Type | Direction | Purpose |
|------|-----------|---------|
| agent_update | server→browser | Position + activity change (D-06) |
| conversation | server→browser | Multi-turn conversation turns (D-06) |
| simulation_status | server→browser | Running/paused state (D-06, D-08) |
| snapshot | server→browser | Full state on connect (D-05) |
| event | server→browser | User-injected events (Phase 6) |
| ping/pong | both | Keepalive |
| error | server→browser | Invalid message or server error |
| pause | browser→server | Halt simulation (D-08) |
| resume | browser→server | Restart simulation (D-08) |

### WebSocket Endpoint Rewrite (`backend/routers/ws.py`)

Replaced the Phase 1 stub with the full Phase 4 push protocol:
1. Accept connection
2. Access `engine` and `manager` from `websocket.app.state` (FastAPI WebSocket DI limitation)
3. Graceful degradation: if engine not ready, send error + close
4. **Snapshot-first** (D-05): `engine.get_snapshot()` → `WSMessage(type="snapshot")` → send → then `manager.active_connections.append(websocket)`
5. Receive loop: parse WSMessage, dispatch `pause`→`engine.pause()`+broadcast status, `resume`→`engine.resume()`+broadcast status, `ping`→pong
6. `finally`: `manager.disconnect(websocket)` always runs

### FastAPI Lifespan Wiring (`backend/main.py`)

Updated lifespan sequence:
1. Ollama probe (existing)
2. `ConnectionManager()` created
3. `generate_town_map()` + `Maze(config)` — full 100x100 town loaded
4. `load_all_agents()` — all agent configs from disk
5. `SimulationEngine(maze, agents, simulation_id)` created
6. `engine._broadcast_callback = _make_broadcast_callback(connection_manager)` wired
7. `app.state.engine` and `app.state.connection_manager` set
8. `await engine.initialize()` — ChromaDB reset + schedule generation
9. `sim_task = asyncio.create_task(engine.run())` — tick loop starts

Shutdown: `sim_task.cancel()` + `await sim_task` + `except CancelledError: pass` (T-04-07).

### `_make_broadcast_callback` Helper

Closure that converts engine's raw `dict` (with `"type"` key) into a validated `WSMessage` and broadcasts the JSON string to all connected clients. Decouples engine from the WSMessage schema.

### Tests Added (9 new tests, 158 total)

| Test | File | What it proves |
|------|------|---------------|
| `test_connection_manager_broadcast` | test_simulation.py | broadcast() sends to all active connections |
| `test_connection_manager_dead_connection` | test_simulation.py | dead WS removed silently, good WS still receives |
| `test_ws_snapshot_on_connect` | test_simulation.py | First WS message is type="snapshot" with agents/status |
| `test_ws_pause_command` | test_simulation.py | pause WSMessage calls engine.pause() |
| `test_ws_resume_command` | test_simulation.py | resume WSMessage calls engine.resume() |
| `test_broadcast_reaches_all_clients` | test_simulation.py | ConnectionManager.broadcast reaches all active WS |
| `test_full_lifecycle` | test_simulation.py | initialize→schedule→snapshot→pause→resume full cycle |
| `test_broadcast_callback_integration` | test_simulation.py | engine._emit_agent_update flows to WS via callback |
| `test_lifespan_creates_engine` | test_simulation.py | lifespan sets app.state.engine + connection_manager |

## Decisions Made

1. **`websocket.app.state` not `request.app.state`**: FastAPI's DI system does not inject `Request` into WebSocket endpoints (only HTTP). `websocket.app` accesses the ASGI app through the connection scope — the correct and idiomatic pattern.

2. **Snapshot-before-register** (D-05): The client receives the full state snapshot BEFORE being appended to `manager.active_connections`. This eliminates the race condition where a broadcast delta arrives before the client has baseline state (Pitfall 2 from RESEARCH.md).

3. **`_make_broadcast_callback` closure**: The engine emits raw dicts; the callback wraps them in `WSMessage` for schema validation and JSON serialization. Keeps the engine decoupled from transport concerns.

4. **Dead connections after loop** (T-04-06): The `dead` list is collected during the broadcast loop but removed after it completes. This is the correct pattern — mutating a list during iteration in Python causes items to be skipped.

5. **Lifespan test strategy**: The three WS endpoint tests that use `TestClient(app)` trigger the full lifespan. Patching `backend.main.SimulationEngine` with `MockEngineFactory` injects our mock engine so `app.state.engine` is controlled. The `_make_lifespan_patches` helper encapsulates all 7 required patches.

6. **`test_ws_ping_pong` regression fix**: The integration test was written against the Phase 1 stub. Updated to consume the snapshot first, then send ping — matching the new snapshot-first protocol.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking Issue] `Request` injection not available in FastAPI WebSocket endpoints**
- **Found during:** Task 1 implementation — `TypeError: websocket_endpoint() missing 1 required positional argument: 'request'`
- **Issue:** The plan specified `from starlette.requests import Request` injected as a parameter. FastAPI's DI system only injects `Request` for HTTP endpoints, not WebSocket endpoints.
- **Fix:** Replaced `request.app.state` with `websocket.app.state` — accessing the FastAPI app through the WebSocket connection's ASGI scope. Removed the `Request` import entirely.
- **Files modified:** `backend/routers/ws.py`

**2. [Rule 3 - Blocking Issue] `asyncio.get_event_loop()` raises RuntimeError in Python 3.14**
- **Found during:** Task 1 TDD — `RuntimeError: There is no current event loop in thread 'MainThread'`
- **Issue:** Two sync test functions called `asyncio.get_event_loop().run_until_complete()` which is deprecated/broken in Python 3.14. No current event loop in non-async context.
- **Fix:** Converted `test_connection_manager_broadcast` and `test_connection_manager_dead_connection` to `@pytest.mark.asyncio` async tests using `await` directly.
- **Files modified:** `tests/test_simulation.py`

**3. [Rule 1 - Bug] `TestClient(app)` runs the lifespan, overwriting pre-set `app.state.engine`**
- **Found during:** Task 1 TDD — `test_ws_pause_command` failed because lifespan overwrote the mock engine with a real engine (which then failed LLM calls)
- **Issue:** Setting `app.state.engine = mock_engine` before `TestClient(app)` is useless — the lifespan context manager runs on `TestClient.__enter__()` and sets `app.state.engine` itself.
- **Fix:** Created `_make_lifespan_patches()` helper that patches all 7 lifespan dependencies (`load_all_agents`, `generate_town_map`, `Maze`, `SimulationEngine`, `reset_simulation`, `generate_daily_schedule`, `add_memory`) so the lifespan runs without real I/O and sets `app.state.engine` to our mock via `MockEngineFactory`.
- **Files modified:** `tests/test_simulation.py`

**4. [Rule 1 - Bug] `test_ws_ping_pong` regression from snapshot-first protocol**
- **Found during:** Task 1 — full suite run showed `AssertionError: assert 'error' == 'pong'`
- **Issue:** The existing `test_ws_ping_pong` integration test sent ping as the first message. The new WS endpoint now sends a snapshot first (D-05), and returns an error if engine is None (which it was, before lifespan ran in that test).
- **Fix:** Updated `test_ws_ping_pong` in `tests/test_integration.py` to (a) mock `app.state.engine` and `app.state.connection_manager`, (b) consume the snapshot first, then send ping and assert pong.
- **Files modified:** `tests/test_integration.py`

## Known Stubs

None — all data flows are wired. The broadcast callback is attached at lifespan startup; agent updates from the engine flow through `ConnectionManager.broadcast` to all connected WebSocket clients.

## Threat Flags

No new security surface introduced beyond what the plan's threat model covers:
- T-04-04: Invalid WebSocket message parsing — mitigated (WSMessage.model_validate_json in try/except; returns error type)
- T-04-05: pause/resume flood — accepted (asyncio.Event set/clear is idempotent)
- T-04-06: Dead connection removal — mitigated (post-loop removal, never during iteration)
- T-04-07: CancelledError on shutdown — mitigated (sim_task.cancel() + await + except CancelledError: pass)
- T-04-08: Snapshot information disclosure — accepted (single-user v1, no PII)

## Self-Check

### Files created/modified:
- `backend/simulation/connection_manager.py` — FOUND (91 lines)
- `backend/schemas.py` — FOUND (expanded WSMessage with 10 types)
- `backend/routers/ws.py` — FOUND (snapshot-first, pause/resume, app.state access)
- `backend/main.py` — FOUND (full lifespan with SimulationEngine + ConnectionManager)
- `tests/test_simulation.py` — FOUND (19 simulation tests, up from 10)
- `tests/test_integration.py` — FOUND (updated test_ws_ping_pong)

### Commits:
- `0738396` — feat(04-02): ConnectionManager, WSMessage expansion, and WebSocket endpoint rewrite
- `05438b3` — feat(04-02): FastAPI lifespan wiring and full integration tests

### Test counts:
- Simulation tests: 19/19 pass
- Full suite: 158/158 pass (was 149 before Phase 4, was 155 after Task 1)

## Self-Check: PASSED
