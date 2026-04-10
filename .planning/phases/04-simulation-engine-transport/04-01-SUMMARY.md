---
phase: 04-simulation-engine-transport
plan: 01
subsystem: simulation-engine
tags: [asyncio, concurrency, simulation, agents, tick-loop]
requirements: [SIM-01, SIM-03]

dependency_graph:
  requires:
    - backend/agents/cognition/perceive.py
    - backend/agents/cognition/decide.py
    - backend/agents/cognition/converse.py
    - backend/agents/cognition/plan.py
    - backend/agents/memory/store.py
    - backend/simulation/world.py
    - backend/agents/loader.py
    - backend/schemas.py
  provides:
    - SimulationEngine class (tick loop, pause/resume, agent step orchestration)
    - AgentState dataclass (runtime mutable state per agent)
    - TICK_INTERVAL constant
  affects:
    - backend/main.py (Plan 02: lifespan mounts SimulationEngine)
    - backend/routers/ws.py (Plan 02: WebSocket wires to engine.pause/resume)
    - backend/simulation/connection_manager.py (Plan 02: broadcast callback attachment)

tech_stack:
  added: []
  patterns:
    - asyncio.TaskGroup for structured concurrency (D-02, Python 3.11+)
    - asyncio.Event for pause gate (D-07, no busy-spin)
    - asyncio.wait_for timeout on per-agent steps (Pitfall 5 mitigation)
    - Per-agent exception isolation via broad try/except in _agent_step_safe (T-04-01)
    - Callback hook pattern for broadcast (decoupled from ConnectionManager until Plan 02)

key_files:
  created:
    - backend/simulation/engine.py
    - tests/test_simulation.py
  modified: []

decisions:
  - TICK_INTERVAL = 5 seconds (within D-01 range of 5-10s, chosen for responsiveness)
  - Per-agent timeout = TICK_INTERVAL * 2 = 10s (Pitfall 5: skip slow LLM agents, not block)
  - _broadcast_callback hook pattern: SimulationEngine holds None until Plan 02 wires ConnectionManager
  - Conversation phase runs before decide phase in _agent_step (mirrors reference agent.py pattern)
  - Only one conversation attempt per agent per tick (break after first nearby agent checked)

metrics:
  duration: "~25 minutes"
  completed: "2026-04-09"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 0
---

# Phase 04 Plan 01: SimulationEngine with Tick Loop and Concurrent Agent Processing

**One-liner:** asyncio.TaskGroup tick loop with asyncio.Event pause gate, per-agent exception isolation via timeout + broad except, and perceive->move/converse/decide agent step sequence

## What Was Built

`SimulationEngine` — the core orchestrator that wires all Phase 3 cognition modules into a running simulation loop. It takes a `Maze` and a list of `AgentConfig` objects, generates daily schedules for all agents on startup, then runs an infinite tick loop where all agents process concurrently via `asyncio.TaskGroup`.

### AgentState Dataclass

Runtime mutable state for each agent, separate from the static `AgentConfig`. Fields:
- `coord: tuple[int, int]` — current tile position, updated each tick
- `path: list[tuple[int, int]]` — BFS path queue; one tile popped per tick
- `current_activity: str` — broadcast to clients
- `schedule: list` — modified by conversations

### SimulationEngine Class

Key methods:
- `initialize()` — resets ChromaDB (INF-01), creates AgentState for each config, generates daily schedules in parallel via TaskGroup (D-03), stores initial observation memories
- `run()` — sets the running event and enters `_tick_loop()`
- `_tick_loop()` — blocks on `asyncio.Event.wait()` when paused (D-07), runs all agents via TaskGroup, catches ExceptionGroup, increments tick count, sleeps TICK_INTERVAL
- `_agent_step_safe()` — wraps `_agent_step()` with `asyncio.wait_for(timeout=TICK_INTERVAL*2)` and broad `except Exception` (T-04-01)
- `_agent_step()` — perceive → if path: move one tile → elif nearby agents: attempt conversation → else: decide + compute path
- `pause()` / `resume()` — `asyncio.Event.clear()` / `.set()`
- `get_snapshot()` — returns all agent positions, activities, and simulation status
- `_emit_agent_update()` / `_emit_conversation()` — callback hooks for Plan 02

### Tests (10 total)

| Test | What it proves |
|------|---------------|
| `test_agents_run_concurrently` | 3 agents with 0.05s delay finish in <0.14s (proves TaskGroup parallelism) |
| `test_exception_isolation` | AgentA RuntimeError does not cancel AgentB (T-04-01) |
| `test_pause_halts_next_tick` | `pause()` clears event; `asyncio.wait_for` times out on cleared event |
| `test_resume_restores_state` | Agent state mutations survive pause/resume (no reset) |
| `test_agent_state_dataclass` | AgentState fields are mutable and correctly typed |
| `test_initialize_generates_schedules` | 2 agents each get 3 schedule entries; reset_simulation called once |
| `test_movement_one_tile_per_tick` | Agent advances exactly one tile per tick when path is set |
| `test_movement_skips_decide_when_path_exists` | decide_action not called during movement tick |
| `test_decide_computes_new_path` | Empty path triggers decide; new path stored minus current position |
| `test_get_snapshot` | Returns correct agent positions, activities, and "paused" status |

## Decisions Made

1. **TICK_INTERVAL = 5s**: Bottom of the 5-10s range from D-01. Chosen for maximum responsiveness. The actual tick wall-clock time is `max(5s, slowest_LLM_time)` per D-02.

2. **Per-agent timeout = 10s**: `asyncio.wait_for(timeout=TICK_INTERVAL * 2)` skips slow agents rather than blocking the entire tick. Matches Pitfall 5 recommendation from research.

3. **Callback hook for broadcast**: `_broadcast_callback: Callable | None = None`. Plan 02 attaches `ConnectionManager.broadcast` at startup. This avoids a hard circular dependency between engine and the yet-to-exist connection manager.

4. **Conversation before decide**: In `_agent_step()`, the conversation check runs after the movement check but before the decide call. This mirrors the reference implementation's `_reaction()` pattern. One conversation attempt per tick (break after first nearby agent).

5. **ExceptionGroup catch in _tick_loop**: Belt-and-suspenders guard. `_agent_step_safe()` absorbs all individual agent failures, but the `except* Exception` on TaskGroup handles edge cases where an exception escapes the wrapper.

## Deviations from Plan

None — plan executed exactly as written.

All 10 required tests are present. Both TDD phases (RED: tests fail; GREEN: engine created; all pass) were completed correctly. Full suite went from 139 → 149 tests with no regressions.

## Known Stubs

None — no placeholder values or disconnected data sources in this plan.

## Threat Flags

No new security surface introduced. SimulationEngine has no external-facing input in Plan 01 — all inputs come from internal modules. WebSocket input validation is Plan 02's responsibility (T-04-01 mitigated, T-04-02 mitigated, T-04-03 accepted per plan).

## Self-Check

### Files created:
- `backend/simulation/engine.py` — 424 lines (min 120 required)
- `tests/test_simulation.py` — 469 lines (min 80 required)

### Commits:
- `eb24649` — feat(04-01): SimulationEngine with tick loop, pause/resume, and exception isolation

### Test counts:
- Simulation tests: 10/10 pass
- Full suite: 149/149 pass

## Self-Check: PASSED
