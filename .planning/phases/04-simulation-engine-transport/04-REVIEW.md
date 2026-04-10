---
phase: 04-simulation-engine-transport
reviewed: 2026-04-09T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - backend/simulation/engine.py
  - backend/simulation/connection_manager.py
  - backend/routers/ws.py
  - backend/main.py
  - backend/schemas.py
  - tests/test_simulation.py
findings:
  critical: 1
  warning: 3
  info: 2
  total: 6
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-04-09
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Phase 4 implements the simulation engine tick loop, WebSocket transport, and per-agent exception isolation. The overall architecture is solid — asyncio.TaskGroup concurrency, pause/resume via Event, snapshot-first connection pattern, and per-agent timeout isolation are all correctly implemented. The connection manager's dead-connection cleanup is safe (collects then removes after iteration).

One critical asyncio race condition exists in the conversation path: agent A's step mutates agent B's schedule object directly after an `await`, while agent B's concurrent task may already be accessing or mutating the same object. Three warnings cover dead code (`ConnectionManager.connect()`), an incorrect `break` placement that silently skips agents with unavailable states, and direct access to a private attribute from outside the class. Two info items cover a private-attribute API smell and an untyped schema field.

## Critical Issues

### CR-01: Asyncio Race Condition on Cross-Agent Schedule Mutation

**File:** `backend/simulation/engine.py:311`
**Issue:** In `_agent_step`, when agent A decides to converse with agent B, it calls `await run_conversation(...)` and then directly assigns to `other_state.schedule` (agent B's mutable state). Because all agent steps run concurrently inside the same `asyncio.TaskGroup`, agent B's own `_agent_step_safe` task is running simultaneously. The `await` at line 294 (`await run_conversation(...)`) yields control to the event loop, which can schedule agent B's step. When agent A resumes and writes `other_state.schedule = list(revised_b)` at line 311, agent B may have already read or partially overwritten its schedule in a concurrent tick, causing one write to silently clobber the other.

This is a classic asyncio shared-mutable-state race: `await` creates preemption points where other tasks can run and modify the same objects.

**Fix:** Pass schedule copies into `run_conversation` (already done for the input at line 302 — `list(other_state.schedule)`) but protect the write-back with a guard. The simplest correct fix is to only apply `revised_b` if the agent's schedule has not changed since the snapshot was taken:

```python
# Snapshot other agent's schedule before the await
schedule_b_snapshot = list(other_state.schedule)

convo_result = await run_conversation(
    ...
    remaining_schedule_b=schedule_b_snapshot,
)

revised_b = convo_result.get("revised_schedule_b", [])
# Only apply if other agent's schedule was not modified during the await
if revised_b and other_state.schedule == schedule_b_snapshot:
    other_state.schedule = list(revised_b)
```

Alternatively, use a per-agent asyncio.Lock to serialize schedule mutations:
```python
# In AgentState, add:
schedule_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

# In _agent_step, before writing revised_b:
async with other_state.schedule_lock:
    if revised_b:
        other_state.schedule = list(revised_b)
```

## Warnings

### WR-01: `ConnectionManager.connect()` Is Dead Code That Would Double-Accept

**File:** `backend/simulation/connection_manager.py:47-58` and `backend/routers/ws.py:39,74`
**Issue:** `ConnectionManager.connect()` calls `await websocket.accept()` then appends the socket to `active_connections`. However, `ws.py` never calls this method. Instead, it calls `await websocket.accept()` at line 39 directly, then sends the snapshot, then does `manager.active_connections.append(websocket)` at line 74. The `connect()` method is entirely unused in production code.

This creates two risks:
1. `connect()` is misleading dead code — a future developer may call it, which would invoke `accept()` on an already-accepted WebSocket, raising a Starlette `RuntimeError`.
2. The class docstring's usage example shows `manager.active_connections.append(websocket)` as the correct pattern, contradicting the existence of `connect()`.

**Fix:** Either remove `connect()` and make the append-after-snapshot pattern the documented approach, or refactor `ws.py` to use a two-step API that separates accept from registration:

```python
# Option A: Remove connect(), document the pattern in class docstring
# ConnectionManager becomes a pure broadcast/disconnect manager.

# Option B: Add a register-only method used by ws.py after snapshot:
def register(self, websocket: WebSocket) -> None:
    """Add an already-accepted WebSocket to the active broadcast list."""
    self.active_connections.append(websocket)

# Then in ws.py line 74, replace:
manager.active_connections.append(websocket)
# With:
manager.register(websocket)
```

### WR-02: Conversation Loop `break` Silently Skips Agents with Unavailable State

**File:** `backend/simulation/engine.py:276-317`
**Issue:** The `for nearby in perception.nearby_agents:` loop contains a `continue` at line 281 when `other_state is None`, and a `break` at line 317 when `should_talk` is `False`. The intended behavior (per comment) is "only attempt one conversation per tick per agent." However, when the first nearby agent has `other_state is None` (e.g., the state dict is stale or the name is misspelled), the loop `continue`s to the second nearby agent. If the second agent has `should_talk = False`, the loop breaks. But the comment implies the intent is to attempt exactly one non-None agent per tick.

The actual subtle bug: if `other_state is None` for the first agent but `should_talk` is not evaluated (due to continue), the loop checks the next agent. This means the `break` after a False `should_talk` limits evaluation to only one attempted conversation, but agents with `None` state are silently skipped without counting toward that one attempt. The behavior is inconsistent — some nearby agents are silently ignored rather than triggering the one-attempt-per-tick limit.

More critically, if `other_state is None`, it likely means a name key is missing from `_agent_states`, which is a data integrity issue worth logging.

**Fix:** Log a warning when `other_state is None` and clarify the one-attempt-per-tick logic:

```python
for nearby in perception.nearby_agents:
    other_name = nearby["name"]
    other_activity = nearby.get("activity", "")
    other_state = self._agent_states.get(other_name)
    if other_state is None:
        logger.warning(
            "Agent %s perceived unknown agent %s — skipping",
            agent_name, other_name,
        )
        continue

    should_talk = await attempt_conversation(...)

    if should_talk:
        ...
        return

    # One LLM conversation-check per tick regardless of outcome
    break
```

### WR-03: Direct Write to Private Attribute `engine._broadcast_callback` from Outside the Class

**File:** `backend/main.py:110`
**Issue:** The lifespan function sets `engine._broadcast_callback = _make_broadcast_callback(connection_manager)` by directly writing a private attribute (prefixed with `_`). This bypasses any future validation or lifecycle logic that might be needed when wiring the callback, and it documents an external coupling to an internal implementation detail.

Additionally, the `SimulationEngine.__init__` sets `self._broadcast_callback: Callable | None = None` (engine.py line 113) without a setter method. If the callback type or signature changes, callers cannot be caught by type checkers since the attribute type annotation (`Callable`) is too broad.

**Fix:** Add a public setter or constructor parameter:

```python
# Option A: Constructor parameter (preferred — makes dependency explicit)
class SimulationEngine:
    def __init__(
        self,
        maze: Maze,
        agents: list[AgentConfig],
        simulation_id: str,
        broadcast_callback: Callable | None = None,
    ) -> None:
        ...
        self._broadcast_callback = broadcast_callback

# In main.py lifespan:
engine = SimulationEngine(
    maze=maze,
    agents=agents,
    simulation_id=simulation_id,
    broadcast_callback=_make_broadcast_callback(connection_manager),
)

# Option B: Public setter
def set_broadcast_callback(self, callback: Callable) -> None:
    """Wire the broadcast callback after construction."""
    self._broadcast_callback = callback
```

## Info

### IN-01: `_make_broadcast_callback` Does Not Handle Missing `type` Key

**File:** `backend/main.py:39-44`
**Issue:** The broadcast callback at line 40 accesses `data["type"]` with a plain key lookup. If any caller passes a dict without a `"type"` key, this raises an unhandled `KeyError`. While the current callers (`_emit_agent_update`, `_emit_conversation`) always include `"type"`, this is an implicit contract with no validation.

**Fix:** Use `.get()` with a fallback or add a guard:

```python
async def callback(data: dict) -> None:
    msg_type = data.get("type")
    if msg_type is None:
        logger.warning("Broadcast callback received data without 'type': %s", data)
        return
    msg = WSMessage(
        type=msg_type,
        payload={k: v for k, v in data.items() if k != "type"},
        timestamp=time.time(),
    )
    await manager.broadcast(msg.model_dump_json())
```

### IN-02: `WSMessage.payload` Field Is Untyped `dict`

**File:** `backend/schemas.py:43`
**Issue:** `payload: dict` accepts any dict, including `dict[str, Any]` values that cannot be JSON-serialized (e.g., non-serializable objects, circular references). At runtime, `model_dump_json()` would raise a `PydanticSerializationError` if non-serializable values are placed in `payload`. There is no type-level enforcement.

**Fix:** Tighten the type annotation to indicate JSON-serializable content:

```python
from typing import Any
payload: dict[str, Any]
```

This does not enforce JSON-serializability at the type level, but it is more explicit than bare `dict` and works correctly with Pydantic v2's JSON serialization pipeline. For stricter enforcement, a `@field_validator` could be added.

---

_Reviewed: 2026-04-09_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
