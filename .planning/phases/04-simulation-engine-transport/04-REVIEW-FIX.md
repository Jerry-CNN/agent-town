---
phase: 04-simulation-engine-transport
fixed_at: 2026-04-10T03:09:50Z
review_path: .planning/phases/04-simulation-engine-transport/04-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 4: Code Review Fix Report

**Fixed at:** 2026-04-10T03:09:50Z
**Source review:** .planning/phases/04-simulation-engine-transport/04-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4
- Fixed: 4
- Skipped: 0

## Fixed Issues

### CR-01: Asyncio Race Condition on Cross-Agent Schedule Mutation

**Files modified:** `backend/simulation/engine.py`
**Commit:** aba2344
**Applied fix:** Captured a `schedule_b_snapshot = list(other_state.schedule)` immediately before the `await run_conversation(...)` call. Passed `schedule_b_snapshot` as the `remaining_schedule_b` argument (replacing the inline `list(other_state.schedule)`). After the await, added a guard: `if revised_b and other_state.schedule == schedule_b_snapshot` before writing back — if agent B's schedule was modified by a concurrent task during the LLM call, the write-back is skipped and a `logger.debug` message is emitted instead. This eliminates the window where agent A's write could silently clobber agent B's concurrent schedule mutation.

### WR-01: `ConnectionManager.connect()` Is Dead Code That Would Double-Accept

**Files modified:** `backend/simulation/connection_manager.py`, `backend/routers/ws.py`
**Commit:** b150807
**Applied fix:** Removed the `connect()` method from `ConnectionManager` entirely. Added a `register(websocket)` method that only appends an already-accepted socket to `active_connections`, with a docstring explaining the snapshot-first pattern (D-05) and why `connect()` was removed. Updated `ws.py` line 74 to call `manager.register(websocket)` instead of `manager.active_connections.append(websocket)`, making the registration intent explicit and eliminating the public attribute access.

### WR-02: Conversation Loop `break` Silently Skips Agents with Unavailable State

**Files modified:** `backend/simulation/engine.py`
**Commit:** e5670ca
**Applied fix:** Added a `logger.warning(...)` call when `other_state is None`, logging both `agent_name` and `other_name` with a message indicating the name is missing from `_agent_states`. The `continue` is preserved so None-state agents do not consume the one-conversation-check-per-tick budget. The existing `break` after a `should_talk = False` result is intentionally kept — it correctly limits the LLM call budget to one `attempt_conversation` check per tick and then falls through to the DECIDE phase (removing it would let the loop attempt multiple LLM conversation checks per tick, which would be incorrect).

### WR-03: Direct Write to Private Attribute `engine._broadcast_callback` from Outside the Class

**Files modified:** `backend/simulation/engine.py`, `backend/main.py`
**Commit:** 0178aba
**Applied fix:** Added `broadcast_callback: Callable | None = None` as an optional constructor parameter to `SimulationEngine.__init__`. The parameter is assigned directly to `self._broadcast_callback` at construction. Updated `main.py` lifespan to pass `broadcast_callback=_make_broadcast_callback(connection_manager)` at engine construction time, removing the post-construction `engine._broadcast_callback = ...` attribute write entirely.

---

_Fixed: 2026-04-10T03:09:50Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
