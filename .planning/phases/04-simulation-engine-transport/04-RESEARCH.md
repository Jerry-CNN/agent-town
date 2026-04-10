# Phase 4: Simulation Engine & Transport - Research

**Researched:** 2026-04-10
**Domain:** Async simulation loop, FastAPI WebSocket broadcasting, asyncio concurrency control
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Simulation Tick Model**
- D-01: Agents act every 5-10 seconds. Each tick runs the full perceive -> decide -> act cycle.
- D-02: All agents process in parallel using asyncio.TaskGroup. No semaphore throttling for v1 — if Ollama can't keep up, tick duration stretches naturally.
- D-03: On simulation start: load all agent configs, generate daily schedules for each agent (2 LLM calls per agent), then enter the tick loop.

**WebSocket Push Protocol**
- D-04: Push all state changes to connected browsers: agent position updates, activity changes, conversation starts/ends, and injected events.
- D-05: Full snapshot on WebSocket connect. Send a snapshot message with all agent positions, activities, and simulation status. Then stream deltas.
- D-06: Expand the existing WSMessage schema with new payload types: agent_update (position + activity), conversation (turns), simulation_status (running/paused).

**Pause/Resume Behavior**
- D-07: Pause uses a shared asyncio.Event flag. The tick loop checks the flag before starting each agent's step. When paused, agents finish their current action but don't start a new tick.
- D-08: Pause/resume commands sent via WebSocket from the browser through the existing /ws endpoint.

**Agent Movement Pacing**
- D-09: One tile per tick along the BFS path.
- D-10: When an agent decides to go somewhere, the simulation calls maze.find_path() and stores the path. Each tick pops the next tile from the path.

### Claude's Discretion
- Exact tick interval within 5-10 second range (probably 5 seconds for responsiveness)
- How to handle LLM calls that take longer than one tick (skip the agent's tick, or let it run long)
- WebSocket message batching (send individual events or batch per tick)
- How many WebSocket clients to support simultaneously (connection pool management)
- REST endpoints for pause/resume as alternative to WebSocket commands

### Deferred Ideas (OUT OF SCOPE)
- Simulation speed control (SIM-04) — deferred to v2
- User chooses agent count (SIM-05) — deferred to v2
- Event injection through WebSocket — that's Phase 6
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SIM-01 | Simulation runs in real-time with agents acting every few seconds | asyncio.TaskGroup tick loop inside FastAPI lifespan; 5-second tick interval; asyncio.Event for pause gate |
| SIM-02 | Real-time updates pushed to browser via WebSocket | ConnectionManager pattern with broadcast(); snapshot on connect; delta events per tick |
| SIM-03 | User can pause and resume the simulation | asyncio.Event flag checked before each agent tick; WebSocket commands pause/resume modify the flag |
</phase_requirements>

---

## Summary

Phase 4 wires together all Phase 3 cognition modules into a running simulation loop and exposes it to browser clients via WebSocket. The three central problems are: (1) running all agents concurrently without blocking the FastAPI event loop, (2) broadcasting agent state changes to all connected WebSocket clients reliably, and (3) implementing a clean pause/resume mechanism without data loss.

All three problems are solved by well-established Python asyncio patterns already compatible with the existing codebase. The FastAPI lifespan context manager is the correct location for the simulation loop task. `asyncio.TaskGroup` (Python 3.11+, already used in tests) handles per-agent concurrency. The `asyncio.Event` flag is the idiomatic pause gate. The ConnectionManager pattern (documented in official FastAPI docs) handles multi-client WebSocket broadcast.

The most important design choice is **per-agent exception isolation**: a single agent's LLM failure must not kill the entire simulation tick. Because `asyncio.TaskGroup` raises an ExceptionGroup when any child task fails, each agent's step coroutine must catch and absorb its own exceptions internally. This is the critical pitfall that will cause silent simulation death if missed.

**Primary recommendation:** Implement `SimulationEngine` as a standalone class with `start()`, `pause()`, `resume()`, `tick()`, and `_agent_step()` methods. Mount the simulation task in the existing FastAPI lifespan. Store `ConnectionManager` and `SimulationEngine` on `app.state` for access from WebSocket handlers.

---

## Standard Stack

### Core (already installed — verified in pyproject.toml)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | >=0.135 | HTTP + WebSocket server, lifespan hook | Lifespan context manager is the correct home for the simulation loop task [VERIFIED: pyproject.toml] |
| asyncio (stdlib) | Python 3.11+ | TaskGroup, Event, create_task | Python 3.11 TaskGroup provides structured concurrency with ExceptionGroup propagation [VERIFIED: pyproject.toml requires-python >=3.11] |
| Pydantic v2 | >=2.12 | WSMessage schema expansion | Already used for all data contracts [VERIFIED: pyproject.toml] |
| starlette WebSocket | via FastAPI | WebSocket server-side connection | FastAPI's built-in WebSocket; no extra package needed [VERIFIED: pyproject.toml] |

### Supporting (no new installs needed)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| asyncio.Event | stdlib | Pause gate flag | Set = running, cleared = paused. Tick loop awaits event.wait() before starting each agent step |
| asyncio.create_task | stdlib | Launch simulation loop in lifespan | Non-blocking; task lives for app lifetime |
| asyncio.CancelledError | stdlib | Shutdown handling | Catch in simulation loop for clean shutdown when lifespan exits |

**No new dependencies required for Phase 4.** All needed libraries are already installed.

**Version verification:**
```bash
# pyproject.toml confirmed:
# fastapi>=0.135, pydantic>=2.12, asyncio via Python 3.11+
uv run python -c "import fastapi; print(fastapi.__version__)"
```

---

## Architecture Patterns

### Recommended Project Structure

```
backend/
├── simulation/
│   ├── __init__.py
│   ├── world.py          # Maze (Phase 2, done)
│   ├── map_generator.py  # (Phase 2, done)
│   ├── engine.py         # NEW: SimulationEngine class (tick loop, pause, state)
│   └── connection_manager.py  # NEW: ConnectionManager (WebSocket broadcast)
├── routers/
│   └── ws.py             # EXPAND: add snapshot, pause/resume command handling
├── schemas.py            # EXPAND: new WSMessage payload types
└── main.py               # EXPAND: lifespan starts simulation loop, mounts state
```

### Pattern 1: SimulationEngine with asyncio.TaskGroup

**What:** A class that owns the tick loop, agent state dict, and pause flag. Each tick spawns per-agent coroutines in a single TaskGroup.

**When to use:** Always — this is the single point of orchestration for the simulation.

**Critical detail:** Each agent's step must catch ALL exceptions internally. TaskGroup cancels all sibling tasks when one raises. Per-agent isolation requires wrapping `_agent_step()` in a broad try/except.

```python
# Source: Python 3.11 asyncio docs + existing codebase patterns
import asyncio
from backend.agents.cognition.perceive import perceive
from backend.agents.cognition.decide import decide_action
from backend.schemas import AgentConfig

class SimulationEngine:
    def __init__(self, maze, agents: list[AgentConfig], simulation_id: str):
        self.maze = maze
        self.simulation_id = simulation_id
        self._running = asyncio.Event()  # set = allowed to run
        self._running.clear()            # start paused
        self._agent_states: dict[str, AgentState] = {}  # runtime state, not config
        self._connection_manager = None  # set by caller

    async def start(self, connection_manager):
        """Initialize agent states, generate schedules, then enter tick loop."""
        self._connection_manager = connection_manager
        # D-03: generate schedules for all agents before first tick
        async with asyncio.TaskGroup() as tg:
            for cfg in self._configs:
                tg.create_task(self._init_agent(cfg))
        self._running.set()  # allow ticking
        await self._tick_loop()

    async def _tick_loop(self):
        """Main simulation loop. Checks pause flag before each tick."""
        while True:
            await self._running.wait()  # D-07: blocks when paused
            try:
                async with asyncio.TaskGroup() as tg:
                    for name, state in self._agent_states.items():
                        tg.create_task(self._agent_step_safe(name, state))
            except* Exception as eg:
                # Log but never crash the loop (ExceptionGroup from TaskGroup)
                pass
            await asyncio.sleep(TICK_INTERVAL)

    async def _agent_step_safe(self, agent_name: str, state: "AgentState"):
        """Per-agent step with full exception isolation."""
        try:
            await self._agent_step(agent_name, state)
        except Exception as exc:
            # Isolation: one agent's failure never kills others
            logger.warning("Agent %s step failed: %s", agent_name, exc)

    def pause(self):
        self._running.clear()

    def resume(self):
        self._running.set()
```

### Pattern 2: AgentState — Runtime State Object

**What:** A separate dataclass holding runtime simulation state for each agent. Decoupled from the static `AgentConfig` loaded from JSON.

**When to use:** Simulation engine creates one `AgentState` per `AgentConfig` on startup. Phase 5 (frontend) reads positions from these.

**Why necessary:** `AgentConfig` (from `loader.py`) is the static config. The simulation needs mutable runtime state: current position (changes each tick), path queue (list of tiles to traverse), current schedule (modified by conversations), and current activity string (broadcast to clients).

```python
# Source: derived from GenerativeAgentsCN agent.py pattern + existing AgentConfig schema
from dataclasses import dataclass, field

@dataclass
class AgentState:
    """Runtime simulation state — one per agent, mutable each tick."""
    name: str
    config: AgentConfig           # static personality + spatial knowledge
    coord: tuple[int, int]        # current tile position (updated each tick)
    path: list[tuple[int, int]]   # remaining BFS path tiles (popped each tick, D-10)
    current_activity: str         # what the agent is doing (broadcast to clients)
    schedule: list                # remaining ScheduleEntry list (modified by converse)
```

### Pattern 3: ConnectionManager — WebSocket Broadcast

**What:** In-memory list of active WebSocket connections with broadcast() method. Documented in official FastAPI WebSocket guide.

**When to use:** One singleton per app instance, stored on `app.state`. Used by SimulationEngine to push updates.

**Critical detail:** Broadcast must handle dead connections without crashing. Catch `WebSocketDisconnect` or `RuntimeError` per connection and remove from list.

```python
# Source: FastAPI official WebSocket documentation
# https://fastapi.tiangolo.com/advanced/websockets/
import asyncio
import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str) -> None:
        """Send to all connected clients. Dead connections are removed, not raised."""
        dead = []
        for ws in self.active_connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active_connections.remove(ws)
```

### Pattern 4: FastAPI Lifespan — Simulation Task Lifecycle

**What:** `asyncio.create_task()` inside the lifespan context manager starts the simulation loop as a background task. The task lives for the full app lifetime.

**When to use:** This is the only correct location for a long-running simulation loop in FastAPI. `BackgroundTasks` is designed for request-scoped fire-and-forget work, not continuous loops.

```python
# Source: FastAPI lifespan documentation + [CITED: fastapi.tiangolo.com/advanced/events/]
from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI
from backend.simulation.engine import SimulationEngine
from backend.simulation.connection_manager import ConnectionManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Existing Ollama probe (keep as-is from Phase 1)
    ...

    # Phase 4: initialize simulation and connection manager
    connection_manager = ConnectionManager()
    engine = SimulationEngine(...)
    app.state.connection_manager = connection_manager
    app.state.engine = engine

    # Start the simulation loop as a background task
    sim_task = asyncio.create_task(engine.start(connection_manager))

    yield

    # Shutdown: cancel simulation loop cleanly
    sim_task.cancel()
    try:
        await sim_task
    except asyncio.CancelledError:
        pass
```

### Pattern 5: WSMessage Schema Expansion

**What:** Extend the existing `WSMessage.type` Literal to cover all new event types. Add typed payload models for each event type.

```python
# Source: existing schemas.py + D-06 decisions
class WSMessage(BaseModel):
    """Expanded WebSocket message contract for Phase 4."""
    type: Literal[
        "agent_update",      # position + activity change (D-06)
        "conversation",      # conversation turns (D-06)
        "simulation_status", # running/paused state (D-06)
        "snapshot",          # full state on connect (D-05)
        "event",             # injected event (Phase 6, keep from existing schema)
        "ping", "pong", "error",
    ]
    payload: dict
    timestamp: float
```

### Pattern 6: WebSocket Command Handling (Pause/Resume)

**What:** The ws.py endpoint receives incoming WebSocket messages from the browser. `pause` and `resume` commands modify the simulation engine's asyncio.Event flag.

```python
# Source: existing ws.py stub pattern + D-08 decisions
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, request: Request):
    engine: SimulationEngine = request.app.state.engine
    manager: ConnectionManager = request.app.state.connection_manager
    await manager.connect(websocket)
    # Send snapshot immediately on connect (D-05)
    await _send_snapshot(websocket, engine)
    try:
        while True:
            text = await websocket.receive_text()
            msg = WSMessage.model_validate_json(text)
            if msg.type == "ping":
                await websocket.send_text(WSMessage(type="pong", ...).model_dump_json())
            elif msg.type == "pause":
                engine.pause()
            elif msg.type == "resume":
                engine.resume()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

### Anti-Patterns to Avoid

- **TaskGroup without per-agent exception isolation:** If `_agent_step()` raises and is not caught internally, `asyncio.TaskGroup` cancels ALL sibling agents and raises ExceptionGroup from the `async with` block. One bad LLM response kills the entire tick. Always wrap individual agent steps in try/except.
- **Blocking calls in the simulation loop:** `maze.find_path()` is pure Python (fast, O(tiles)). ChromaDB calls use `asyncio.to_thread()` already. No new blocking calls should be added to the simulation tick path.
- **Using `BackgroundTasks` for the simulation loop:** FastAPI's `BackgroundTasks` runs after a request response is sent — it is request-scoped. For an always-on simulation loop, use `asyncio.create_task()` in the lifespan context.
- **Calling `asyncio.Event.wait()` without timeout in tests:** Tests that pause a simulation and then don't resume will hang indefinitely. Always use `asyncio.wait_for(event.wait(), timeout=N)` in test contexts.
- **Mutating `active_connections` while iterating in broadcast:** Remove dead connections to a separate list, then remove after the loop (see Pattern 3 above).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| WebSocket multi-client tracking | Custom connection registry | ConnectionManager pattern (stdlib list) | Official FastAPI pattern; handles connect/disconnect lifecycle correctly |
| Pause/resume flag | Threading.Event or custom flag class | `asyncio.Event` | Thread-safe in asyncio context; `wait()` is awaitable and doesn't busy-spin |
| Concurrent agent steps | Manual `asyncio.gather()` with error handling | `asyncio.TaskGroup` with per-agent try/except | TaskGroup gives structured concurrency with ExceptionGroup; Python 3.11+ standard |
| Background simulation loop | Flask-style thread or `threading.Timer` | `asyncio.create_task()` in lifespan | Single event loop; no thread-safety issues with WebSocket state |
| Agent path storage | Re-running BFS every tick | Store `path: list[tuple]` in AgentState, pop one tile per tick | BFS on every tick is O(tiles) per agent per tick — unnecessary; compute once on destination decision |

**Key insight:** This phase is almost entirely wiring — the heavy lifting (BFS, cognition, memory) is done. The simulation loop is ~100 lines of asyncio plumbing connecting already-implemented modules.

---

## Common Pitfalls

### Pitfall 1: TaskGroup Cancels All Agents on One Failure
**What goes wrong:** Agent A's LLM call times out and raises an exception. TaskGroup cancels agents B, C, D, E mid-step. The tick loop catches ExceptionGroup and re-enters, but all agents lost their in-progress work.
**Why it happens:** `asyncio.TaskGroup` is designed for "all-or-nothing" structured concurrency — if one task fails, the group cancels all others. This is correct behavior for many use cases but wrong for independent simulation agents.
**How to avoid:** Wrap each `_agent_step()` in a broad `try/except Exception` inside the coroutine itself. The TaskGroup's child task never raises, so sibling agents are never cancelled.
**Warning signs:** Logs show all agents pausing simultaneously; tick loop shows ExceptionGroup in logs.

### Pitfall 2: Snapshot Race — Client Misses First N Ticks
**What goes wrong:** Client connects, the simulation sends 3 delta updates before the snapshot is sent. Client's state is inconsistent.
**Why it happens:** If snapshot sending is async and delta broadcasts happen concurrently, ordering is not guaranteed.
**How to avoid:** Send snapshot synchronously before adding the client to `active_connections`. The flow: (1) accept WebSocket, (2) send snapshot, (3) add to `active_connections` list. This way the client receives the snapshot first, then only new deltas.
**Warning signs:** Client shows agents at wrong initial positions on fresh connection.

### Pitfall 3: Pause Flag Checked Too Late — Agent Completes N Ticks After Pause
**What goes wrong:** User presses pause. The current tick's TaskGroup has already started all agent steps. Those steps run to completion (including LLM calls). Pause doesn't take effect until the start of the NEXT tick.
**Why it happens:** `asyncio.Event.wait()` is called at the top of the tick loop, not inside individual agent steps.
**How to avoid:** This is EXPECTED behavior per D-07 ("agents finish their current action but don't start a new tick"). Document clearly; don't try to interrupt mid-tick.
**Warning signs:** Believing pause is instantaneous and designing UI feedback around it.

### Pitfall 4: WebSocket Receive Loop Blocks Push
**What goes wrong:** The WebSocket endpoint is stuck in `await websocket.receive_text()`. Meanwhile, `manager.broadcast()` tries to send to this connection. This appears to work but can deadlock in high-load scenarios.
**Why it happens:** A single coroutine can't simultaneously await `receive_text()` and process `send_text()` from broadcast without care.
**How to avoid:** The existing ws.py stub pattern is correct — the receive loop processes commands and the broadcast happens from the simulation engine's task (different coroutine). FastAPI's WebSocket uses starlette's ASGI WebSocket which supports concurrent send/receive via the event loop. No explicit lock needed for send vs. receive.
**Warning signs:** WebSocket messages stop appearing in browser after several minutes under load.

### Pitfall 5: LLM Calls Stretch Tick Duration Unpredictably
**What goes wrong:** Tick is set to 5 seconds. One agent's LLM call takes 8 seconds. The entire tick takes 8 seconds (TaskGroup waits for all agents). Other agents also take varying times.
**Why it happens:** D-02 deliberately omits semaphore throttling for v1. TaskGroup with no timeout means the tick stretches to the slowest agent.
**How to avoid:** This is EXPECTED behavior per D-02 ("tick duration stretches naturally"). Document tick interval as a minimum, not a fixed rate. For the "Claude's Discretion" item on handling slow LLM calls: use `asyncio.wait_for(agent_step(), timeout=TICK_INTERVAL * 2)` inside `_agent_step_safe()` — if an agent takes more than 2x the tick duration, skip their step for this tick and log a warning.
**Warning signs:** Perceived simulation speed drops from 5s/tick to 20s/tick when Ollama is slow.

### Pitfall 6: Missing `simulation_id` in Agent State Initialization
**What goes wrong:** `generate_daily_schedule()`, `add_memory()`, and all cognition functions require `simulation_id`. If not passed during initialization, ChromaDB collection lookups fail silently.
**Why it happens:** `simulation_id` is a runtime concept — it doesn't exist in the static `AgentConfig` JSON files.
**How to avoid:** Generate a `simulation_id` (e.g., `str(uuid.uuid4())`) once in `SimulationEngine.__init__()`. Pass it to every cognition call. Call `reset_simulation(simulation_id)` from `store.py` at engine startup to clear stale ChromaDB data (INF-01).
**Warning signs:** Memory retrieval returns empty results for all agents on first tick.

---

## Code Examples

### Agent Step: Full Perceive → Decide → Move Sequence

```python
# Source: reference implementation GenerativeAgentsCN/generative_agents/modules/agent.py
# + existing codebase perceive.py, decide.py patterns
async def _agent_step(self, agent_name: str, state: AgentState) -> None:
    """Single agent tick: perceive -> decide -> move or converse."""
    config = state.config

    # Build agent dict for perception (all agents' current positions + activities)
    all_agents_view = {
        name: {"coord": s.coord, "current_activity": s.current_activity}
        for name, s in self._agent_states.items()
    }

    # 1. PERCEIVE (no LLM — fast)
    perception = perceive(
        agent_coord=state.coord,
        agent_name=agent_name,
        maze=self.maze,
        all_agents=all_agents_view,
    )

    # 2. MOVE: advance one tile along existing path (D-09, D-10)
    if state.path:
        next_tile = state.path.pop(0)
        state.coord = next_tile
        # Broadcast position update
        await self._broadcast_agent_update(agent_name, state)
        return  # movement tick: no decide call needed

    # 3. DECIDE (LLM — slow)
    action = await decide_action(
        simulation_id=self.simulation_id,
        agent_name=agent_name,
        agent_scratch=config.scratch,
        agent_spatial=config.spatial,
        current_activity=state.current_activity,
        perception=perception,
        current_schedule=state.schedule,
    )

    # 4. Resolve destination and compute path
    if action.destination != "idle":
        destination_coord = self.maze.resolve_destination(action.destination)
        if destination_coord:
            state.path = self.maze.find_path(state.coord, destination_coord)
            state.path = state.path[1:] if len(state.path) > 1 else []

    # 5. Update activity and broadcast
    state.current_activity = action.activity
    await self._broadcast_agent_update(agent_name, state)
```

### Snapshot Message on Client Connect

```python
# Source: D-05 design decision
async def _send_snapshot(self, websocket: WebSocket) -> None:
    """Send full simulation state to a newly connected client."""
    agent_states = [
        {
            "name": name,
            "coord": list(state.coord),
            "activity": state.current_activity,
        }
        for name, state in self._agent_states.items()
    ]
    snapshot = WSMessage(
        type="snapshot",
        payload={
            "agents": agent_states,
            "simulation_status": "running" if self._running.is_set() else "paused",
        },
        timestamp=time.time(),
    )
    await websocket.send_text(snapshot.model_dump_json())
```

### Broadcast Agent Update

```python
# Source: D-04 design decision + ConnectionManager pattern
async def _broadcast_agent_update(self, agent_name: str, state: AgentState) -> None:
    update = WSMessage(
        type="agent_update",
        payload={
            "name": agent_name,
            "coord": list(state.coord),
            "activity": state.current_activity,
        },
        timestamp=time.time(),
    )
    await self._connection_manager.broadcast(update.model_dump_json())
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `asyncio.gather()` for concurrent tasks | `asyncio.TaskGroup` | Python 3.11 (Oct 2022) | Structured concurrency; ExceptionGroup instead of silently swallowed errors |
| Flask startup hooks for background work | FastAPI lifespan + `asyncio.create_task()` | FastAPI 0.93 (2023) | Clean task lifecycle tied to app startup/shutdown |
| Manual thread-based pause flags | `asyncio.Event` | asyncio stdlib | Awaitable, no busy-spin, no threading issues |

**Deprecated/outdated:**
- `@app.on_event("startup")`: Deprecated in FastAPI; use `lifespan` parameter instead. The existing `main.py` already uses `lifespan` correctly.
- `asyncio.gather(..., return_exceptions=True)`: Still valid but less structured than TaskGroup. TaskGroup preferred for Python 3.11+.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Tick interval of 5 seconds is responsive enough for the MVP | Standard Stack / tick model | Agents may feel sluggish at 5s on slow hardware; adjustable constant |
| A2 | `maze.find_path()` is fast enough to call synchronously (no asyncio.to_thread wrapping needed) | Architecture Patterns Pattern 1 | BFS on a large map could block event loop; add to_thread if map >200x200 tiles |
| A3 | Conversation detection (attempt_conversation) runs inside the agent step for nearby agents | Code Examples | Conversation logic placement in tick not explicitly decided; may need explicit design |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.

For A3: D-11 says conversation trigger = "proximity check + LLM decision." The perceive() output provides `nearby_agents`. The simulation loop should call `attempt_conversation()` for each nearby agent pair after the perceive step. This is consistent with the reference implementation's `_reaction()` method in agent.py. Recommend planner adds this as an explicit step in the agent step sequence.

---

## Open Questions

1. **Where does conversation logic fit in the agent step?**
   - What we know: `attempt_conversation()` and `run_conversation()` are implemented in converse.py. Perceive returns `nearby_agents`. The CONTEXT.md says D-11: proximity check + LLM decision.
   - What's unclear: Should conversation happen inside `_agent_step()` for the initiating agent, or as a separate pair-level step? Who "owns" a conversation — agent A, agent B, or the engine?
   - Recommendation: The engine detects pairs of nearby agents and calls `attempt_conversation()` from the engine level after running all agent percepts. If a conversation starts, `run_conversation()` runs as a separate coroutine and its output (revised schedules) updates both agents' `AgentState.schedule`. This mirrors the reference implementation's `_chat_with()` pattern.

2. **Tick interval discretion: 5 seconds or adaptive?**
   - What we know: D-01 says 5-10 seconds. CONTEXT.md says "probably 5 seconds for responsiveness."
   - What's unclear: Whether 5 seconds is fast enough for Ollama with 5 agents (5 agents × ~3s LLM = 15s minimum with parallelism, but with Ollama single-threaded that's actually serial).
   - Recommendation: Use 5 seconds as the `TICK_INTERVAL` constant. Add a comment that tick duration stretches naturally (D-02). The actual wall-clock time per tick is `max(TICK_INTERVAL, slowest_agent_LLM_time)`.

3. **Conversation WebSocket event: during tick or deferred?**
   - What we know: D-04 says broadcast conversation starts/ends. D-06 adds conversation payload type.
   - What's unclear: Conversation runs 2-4 turns inside one tick. Should each turn be broadcast as it happens, or only the final summary?
   - Recommendation: Broadcast each turn as it happens (type="conversation", payload includes speaker + text). This gives the activity feed (Phase 5/DSP-01) live conversation text. Final summary stored to memory only.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ asyncio.TaskGroup | D-02, SIM-01 | Verified (pyproject.toml requires-python >=3.11) | 3.11+ | — |
| FastAPI lifespan | Simulation loop mount point | Verified (fastapi>=0.135 in pyproject.toml) | 0.135+ | — |
| ChromaDB EphemeralClient | Memory on simulation start | Verified (chromadb>=1.5.7) | 1.5.7+ | — |
| Maze.find_path(), resolve_destination() | D-09, D-10 agent movement | Verified (world.py implemented) | — | — |
| All cognition modules (perceive, decide, converse, plan) | Agent step | Verified (Phase 3 complete) | — | — |
| load_all_agents() | D-03 initialization | Verified (loader.py implemented) | — | — |
| reset_simulation() | INF-01 fresh start | Verified (store.py implemented) | — | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-asyncio 1.3.0 |
| Config file | pyproject.toml (`[tool.pytest.ini_options]` asyncio_mode = "auto") |
| Quick run command | `uv run pytest tests/test_simulation.py -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SIM-01 | All agents act concurrently (not sequentially) | unit | `uv run pytest tests/test_simulation.py::test_agents_run_concurrently -x` | Wave 0 |
| SIM-01 | Pause flag halts agent processing within one tick | unit | `uv run pytest tests/test_simulation.py::test_pause_halts_next_tick -x` | Wave 0 |
| SIM-01 | Resume restarts from paused state without data loss | unit | `uv run pytest tests/test_simulation.py::test_resume_restores_state -x` | Wave 0 |
| SIM-02 | Agent update broadcast sent to all connected clients | unit | `uv run pytest tests/test_simulation.py::test_broadcast_reaches_all_clients -x` | Wave 0 |
| SIM-02 | Snapshot sent on WebSocket connect | integration | `uv run pytest tests/test_integration.py::test_ws_snapshot_on_connect -x` | Wave 0 |
| SIM-03 | Pause WebSocket command calls engine.pause() | unit | `uv run pytest tests/test_simulation.py::test_ws_pause_command -x` | Wave 0 |
| SIM-03 | Resume WebSocket command calls engine.resume() | unit | `uv run pytest tests/test_simulation.py::test_ws_resume_command -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_simulation.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_simulation.py` — covers all SIM-01, SIM-02, SIM-03 behaviors above
- [ ] Test fixtures for `SimulationEngine` with mocked cognition modules (avoid real LLM calls in tests)
- [ ] Shared `AgentState` fixture in conftest.py

*(Existing `tests/conftest.py` needs `mock_engine` and `mock_connection_manager` fixtures for simulation tests.)*

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth in Phase 4 (single-user v1) |
| V3 Session Management | no | Single-user; no sessions |
| V4 Access Control | no | Single-user |
| V5 Input Validation | yes | WSMessage Pydantic validation on all incoming WebSocket commands |
| V6 Cryptography | no | No crypto in simulation transport |

### Known Threat Patterns for WebSocket + Simulation

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed WebSocket message crashing engine | Denial of Service | WSMessage.model_validate_json() with try/except already in ws.py; errors return type="error" response |
| Pause flood (rapid pause/resume commands) | Denial of Service | asyncio.Event set/clear is idempotent; no cost to rapid toggling; not a DoS vector |
| Infinite tick loop on task cancellation | Denial of Service | Tick loop must handle asyncio.CancelledError by re-raising, not catching |
| Simulation state corruption from concurrent writes | Tampering | AgentState is only written from within the simulation task (single writer); ConnectionManager list only modified in WebSocket disconnect handlers; no lock needed in single-process asyncio model |

---

## Sources

### Primary (HIGH confidence)
- FastAPI lifespan docs — asyncio.create_task() in lifespan pattern: [https://fastapi.tiangolo.com/advanced/events/](https://fastapi.tiangolo.com/advanced/events/) [CITED]
- FastAPI WebSocket ConnectionManager pattern: [https://fastapi.tiangolo.com/advanced/websockets/](https://fastapi.tiangolo.com/advanced/websockets/) [CITED]
- Python 3.11 asyncio.TaskGroup: [https://docs.python.org/3/library/asyncio-task.html](https://docs.python.org/3/library/asyncio-task.html) [CITED]
- Existing codebase (perceive.py, decide.py, converse.py, plan.py, store.py, ws.py, loader.py, world.py) — direct read [VERIFIED: file reads]
- pyproject.toml — dependency versions confirmed [VERIFIED: file read]

### Secondary (MEDIUM confidence)
- FastAPI WebSocket broadcasting with multiple clients: [hexshift.medium.com — Managing Multiple WebSocket Clients in FastAPI] [WebSearch verified with FastAPI official docs]
- asyncio.Event for pause/resume pattern: Python docs + SuperFastPython examples [WebSearch]

### Tertiary (LOW confidence)
- Reference implementation pattern for simulation loop: GenerativeAgentsCN/generative_agents/modules/game.py, agent.py — direct read, adapted not ported [VERIFIED: file reads, but mapping to async context is ASSUMED]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies verified in pyproject.toml; no new installs needed
- Architecture patterns: HIGH — ConnectionManager from official FastAPI docs; TaskGroup from official Python docs; lifespan pattern from official FastAPI docs
- Pitfalls: HIGH — TaskGroup exception behavior verified from Python 3.11 docs; others derived from direct codebase reading

**Research date:** 2026-04-10
**Valid until:** 2026-05-10 (stable stdlib patterns; FastAPI WebSocket API is stable)
