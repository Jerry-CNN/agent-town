# Phase 06: Event Injection - Research

**Researched:** 2026-04-10
**Domain:** WebSocket message extension, agent memory injection, React form state management
**Confidence:** HIGH — all major findings verified against the actual codebase; no external library research required (stack is fully established)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Text input field in the bottom bar (existing BottomBar component already has a disabled event input placeholder). Submit with Enter key, no page reload.
- **D-02:** Delivery mode selector: "Broadcast" (all agents) or "Whisper" (single agent). Simple toggle or radio button next to the input.
- **D-03:** For whisper mode, user selects the target agent from a dropdown or by clicking an agent on the map before submitting.
- **D-04:** Events received via WebSocket as a new message type (e.g., type="inject_event"). Backend processes immediately — no REST endpoint needed.
- **D-05:** Broadcast events inject into ALL agents' perception queues within one simulation tick. Each agent receives the event as a high-importance memory.
- **D-06:** Whisper events inject into ONLY the targeted agent's perception queue. Other agents have zero initial knowledge.
- **D-07:** Whispered events spread organically through the existing conversation system (Phase 3, D-11/D-12/D-13). When a whispered agent converses with another agent, the event may come up naturally based on memory retrieval and LLM conversation generation.
- **D-08:** No special gossip mechanism needed — the existing memory system (composite scoring with importance weighting) and conversation system (schedule revision after chat) already enable organic spread. The whispered event gets stored as a high-importance memory, which retrieval will surface in future conversations.
- **D-09:** Injected events appear in the activity feed immediately (broadcast: "Event broadcast: {text}", whisper: "Whispered to {agent}: {text}").
- **D-10:** As gossip spreads through conversations, the activity feed shows the natural propagation (conversation entries mentioning the event topic).

### Claude's Discretion
- Exact UI styling of the event input and delivery selector
- Whether whisper target selection uses a dropdown or map click (or both)
- How to format the injected event in the LLM perception prompt
- Whether to add an event history panel (probably not for v1)

### Deferred Ideas (OUT OF SCOPE)
- Event injection history log (EVT-05) — deferred to v2
- Pre-built event templates (EVT-06) — deferred to v2
- Event targeting by location instead of agent — not in v1 scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EVT-01 | User can type a free-text event and submit it to the simulation | BottomBar.tsx has disabled input ready to enable; sendMessage pattern established by pause/resume |
| EVT-02 | Broadcast mode delivers the event to all agents instantly | Engine exposes `_agent_states` dict; `add_memory()` in store.py is async and takes any agent_id |
| EVT-03 | Whisper mode delivers the event to one specific agent | Same `add_memory()` path; engine receives target name in WSMessage payload |
| EVT-04 | Whispered events spread organically through agent-to-agent conversations | Memory retrieval composite scoring surfaces high-importance memories; conversation system stores summaries as memories for other agents |
</phase_requirements>

---

## Summary

Phase 6 is primarily a **wiring phase**, not a new systems phase. The entire infrastructure exists: WebSocket message dispatch (`ws.py`), memory storage (`add_memory()` in `store.py`), a broadcast callback (`_broadcast_callback`), and an already-present-but-disabled UI input in `BottomBar.tsx`. The work is connecting these existing pieces in the right order.

The two meaningful design tasks are: (1) choosing how to represent the `inject_event` message in `WSMessage.type` Literal — the schema must be extended to add this inbound type — and (2) deciding where in `_agent_step()` injected events become visible. The cleanest injection point is `add_memory()` with `memory_type="event"` and high importance, which the existing `perceive()` composite scoring will naturally surface during future decision calls.

Gossip spreading (EVT-04) requires zero new code. When the whisper recipient converses with another agent (via the already-running `run_conversation()` flow), the conversation summary stored as a memory for the listening agent seeds their future perception. The mechanism is the importance-weighted retrieval system that already exists in `retrieval.py`.

**Primary recommendation:** Extend `WSMessage.type` Literal with `"inject_event"`, handle it in `ws.py`, call `engine.inject_event(text, mode, target)` which calls `add_memory()` for each eligible agent, then broadcast an `"event"` WSMessage back to all clients for the feed.

---

## Standard Stack

No new libraries required. [VERIFIED: pyproject.toml, frontend/package.json]

All necessary tools are already installed:
- FastAPI + Starlette WebSocket — `ws.py` already routes message types
- Pydantic v2 `WSMessage` — `schemas.py` Literal union just needs `"inject_event"` added
- ChromaDB `add_memory()` — async, accepts `memory_type="event"`, `importance` param
- Zustand `simulationStore` — `appendFeed()` already handles `"event"` type messages
- React controlled input — `useState` for text and delivery mode (no additional library)

## Architecture Patterns

### Existing WSMessage Flow (VERIFIED against codebase)

```
Frontend (BottomBar.tsx)
    → getSendMessage()(inject_event WSMessage)
    → ws.py receive_text loop
    → engine.inject_event(text, mode, target)
    → add_memory() for each eligible agent
    → _broadcast_callback({ type: "event", ... })
    → ConnectionManager.broadcast()
    → Frontend useWebSocket.ts case "event"
    → store.appendFeed(msg)
    → ActivityFeed.tsx renders feed entry
```

[VERIFIED: useWebSocket.ts line 93-95 — `"event"` case already calls `store.appendFeed(msg)`]
[VERIFIED: ActivityFeed.tsx lines 60-78 — `"event"` type already renders with gold "Event:" label]
[VERIFIED: schemas.py line 38 — `"event"` already in WSMessage Literal]

### Pattern 1: Engine inject_event method

**What:** New public method on `SimulationEngine` that takes `(text: str, mode: str, target: str | None)` and calls `add_memory()` for all relevant agents.

**When to use:** Called from `ws.py` when `message.type == "inject_event"` is received.

**Injection approach — memory not tile events:**

The existing `perceive()` reads `tile._events` for perception. But injecting into tile events requires knowing which tile the agent is on and is ephemeral (cleared when no agent reads it). The more robust approach is direct `add_memory()` with `memory_type="event"` and `importance=8` (high, to ensure retrieval surfaces it). This way the event persists in the agent's memory stream and will be retrieved by the composite scorer during future `decide_action()` calls.

```python
# Inside SimulationEngine (new method)
async def inject_event(self, text: str, mode: str, target: str | None = None) -> None:
    """Inject a user event into agent memory streams.

    Broadcast: stores in ALL agents' memory with importance=8.
    Whisper: stores only in the named target agent's memory with importance=8.

    High importance (8/10) ensures the composite retrieval scorer surfaces
    this memory in the agent's next decide_action() call.
    """
    if mode == "broadcast":
        targets = list(self._agent_states.keys())
    elif mode == "whisper" and target and target in self._agent_states:
        targets = [target]
    else:
        logger.warning("inject_event: invalid mode=%s or unknown target=%s", mode, target)
        return

    content_template = f"Event: {text}"
    for agent_name in targets:
        await add_memory(
            simulation_id=self.simulation_id,
            agent_id=agent_name,
            content=content_template,
            memory_type="event",
            importance=8,
        )
```

[VERIFIED: `add_memory()` signature in store.py lines 53-93]
[VERIFIED: `_agent_states` dict keyed by agent name in engine.py line 116]

### Pattern 2: WSMessage type extension

**What:** Add `"inject_event"` to the `WSMessage.type` Literal in `schemas.py`.

The Literal currently includes 9 types. Add one more for the inbound command.

```python
# schemas.py — extend the Literal
type: Literal[
    "agent_update",
    "conversation",
    "simulation_status",
    "snapshot",
    "event",
    "ping",
    "pong",
    "error",
    "pause",
    "resume",
    "inject_event",   # NEW: inbound command from browser — Phase 6
]
```

[VERIFIED: schemas.py lines 31-42 — current Literal, space for new type confirmed]

The frontend `WSMessageType` in `types/index.ts` must mirror this — add `"inject_event"` to the union there as well.

[VERIFIED: types/index.ts lines 32-42 — current union definition]

### Pattern 3: ws.py handler branch

**What:** Add an `elif message.type == "inject_event":` branch in the ws.py receive loop, mirroring the `pause`/`resume` pattern.

```python
elif message.type == "inject_event":
    text = message.payload.get("text", "").strip()
    mode = message.payload.get("mode", "broadcast")
    target = message.payload.get("target")  # str | None
    if not text:
        error_msg = WSMessage(type="error", payload={"detail": "Event text is empty"}, timestamp=time.time())
        await websocket.send_text(error_msg.model_dump_json())
        continue
    await engine.inject_event(text=text, mode=mode, target=target)
    # Broadcast event confirmation to activity feed
    label = f"Event broadcast: {text}" if mode == "broadcast" else f"Whispered to {target}: {text}"
    event_msg = WSMessage(type="event", payload={"text": label}, timestamp=time.time())
    await manager.broadcast(event_msg.model_dump_json())
```

[VERIFIED: ws.py lines 92-118 — pause/resume pattern to mirror]

### Pattern 4: BottomBar.tsx state and dispatch

**What:** Convert the disabled input into a controlled React input with local state for text and delivery mode.

BottomBar is currently a presentational component with no local state. It needs `useState` for:
- `eventText: string` — controlled input value
- `deliveryMode: "broadcast" | "whisper"` — toggle state
- `whisperTarget: string` — selected agent name (for whisper mode)

The agent list for the whisper dropdown comes from `useSimulationStore((state) => state.agents)`.

```tsx
// BottomBar.tsx — new state additions
const [eventText, setEventText] = useState("");
const [deliveryMode, setDeliveryMode] = useState<"broadcast" | "whisper">("broadcast");
const [whisperTarget, setWhisperTarget] = useState("");
const agents = useSimulationStore((state) => state.agents);

function handleSubmit() {
  if (!eventText.trim()) return;
  const send = getSendMessage();
  if (!send) return;
  send({
    type: "inject_event",
    payload: {
      text: eventText.trim(),
      mode: deliveryMode,
      target: deliveryMode === "whisper" ? whisperTarget : undefined,
    },
    timestamp: Date.now() / 1000,
  });
  setEventText("");
}

// Input: onKeyDown check for Enter key
// <input ... onKeyDown={(e) => { if (e.key === "Enter") handleSubmit(); }} />
```

[VERIFIED: BottomBar.tsx lines 1-82 — existing disabled input and getSendMessage pattern]
[VERIFIED: simulationStore.ts lines 22-78 — agents dict structure, getSendMessage export]

### Recommended Project Structure for Phase 6 changes

```
backend/
├── schemas.py                     — add "inject_event" to WSMessage.type Literal
├── routers/ws.py                  — add inject_event handler branch
└── simulation/engine.py           — add inject_event() method

frontend/src/
├── types/index.ts                 — add "inject_event" to WSMessageType union
└── components/BottomBar.tsx       — enable input, add mode toggle, whisper dropdown
```

No new files required for core functionality.

### Anti-Patterns to Avoid

- **Injecting into tile._events instead of add_memory():** Tile events are ephemeral and only visible to agents currently within the perception radius. Direct memory injection persists across ticks and is guaranteed to be retrieved.
- **Adding a REST endpoint for event injection:** D-04 locks this to WebSocket. The existing `getSendMessage()` pattern already works.
- **Calling `score_importance()` for injected events:** The LLM importance scoring costs an extra LLM call per agent per event. Hardcode `importance=8` for injected events — they are user-initiated and inherently significant. Skip the LLM call entirely.
- **Storing verbatim event text in tile._events and memory:** Store in memory only. If you also mutate tile._events, the perceive() function will pick it up as a tile event AND as a memory, double-injecting the signal.
- **Mutating agent state from the ws.py coroutine directly:** `engine._agent_states` is read/written by the tick loop coroutine. All mutation must go through `engine.inject_event()` which is called from the ws.py coroutine (same event loop — no thread safety issue, but must not bypass the engine's owned state).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Gossip propagation | Custom gossip spread mechanism | Existing `run_conversation()` + `add_memory()` | Already working: conversation stores summaries as memories for both agents; high-importance memories retrieved in future conversations |
| Event feed display | New feed component | Existing `ActivityFeed.tsx` + `appendFeed()` | `"event"` type already renders with gold "Event:" label (lines 60-78 of ActivityFeed.tsx) |
| Agent list for whisper | Separate API call for agent names | `useSimulationStore(state => state.agents)` | Agent states already in Zustand store, populated on snapshot |
| WS dispatch | New message routing system | `ws.py` elif chain | Established pattern — pause/resume already works this way |
| Importance scoring | LLM call per injected event | Hardcoded `importance=8` | Injected events are high priority by definition; saves LLM cost per agent |

**Key insight:** EVT-04 (gossip spreading) is already implemented by Phase 3. The conversation system stores summaries as memories for both participants. When the whisper recipient talks to another agent, the conversation prompt retrieves recent high-importance memories — the injected event will surface. The "organic" spread is the existing system working as designed.

---

## Common Pitfalls

### Pitfall 1: inject_event is async but ws.py runs synchronously between awaits
**What goes wrong:** `engine.inject_event()` calls `add_memory()` which uses `asyncio.to_thread()`. If you call it without `await` in ws.py, the memory is never stored.
**Why it happens:** Missing `await` in the ws.py elif branch.
**How to avoid:** Always `await engine.inject_event(...)` in the ws.py handler.
**Warning signs:** Events appear in the feed (the broadcast succeeds) but agents never react.

### Pitfall 2: Whisper target validation — agent not in engine state
**What goes wrong:** User types an agent name that doesn't exist; `engine._agent_states.get(target)` returns None; no memory stored; no error feedback.
**Why it happens:** No validation between the dropdown selection and the actual engine state dict.
**How to avoid:** In `inject_event()`, validate `target in self._agent_states` before calling `add_memory()`. Return an error via the ws.py `"error"` message type if invalid.
**Warning signs:** Silent failure — activity feed shows "Whispered to X" but no reaction.

### Pitfall 3: Empty event text submitted
**What goes wrong:** User hits Enter on an empty input; backend stores an empty "Event: " memory for all agents.
**Why it happens:** No client-side or server-side empty-string guard.
**How to avoid:** Guard in both BottomBar.tsx (`if (!eventText.trim()) return;`) and ws.py (`if not text: return error`).
**Warning signs:** Spurious empty memory entries pollute ChromaDB retrieval results.

### Pitfall 4: "inject_event" not in WSMessage Literal — Pydantic validation error
**What goes wrong:** Frontend sends `type: "inject_event"` but backend `WSMessage.model_validate_json()` rejects it with a Pydantic validation error. ws.py returns an error message and logs a warning. The event is silently dropped.
**Why it happens:** Forgot to extend the `WSMessage.type` Literal in `schemas.py` and/or `types/index.ts`.
**How to avoid:** Update both files before adding the ws.py handler.
**Warning signs:** Console shows "Invalid WebSocket message" and the activity feed shows nothing.

### Pitfall 5: Zustand agents dict is keyed by name — select value must match exactly
**What goes wrong:** Whisper dropdown option values don't exactly match `state.agents` keys. The `target` string sent to the backend doesn't match `engine._agent_states` keys. Whisper silently fails.
**Why it happens:** Agents dict keys are agent names from the snapshot (e.g., "Alice Chen"). If the dropdown uses a different format, the key lookup fails.
**How to avoid:** Iterate `Object.keys(agents)` directly to populate the dropdown — use the exact key as both the `value` and display text of each `<option>`.
**Warning signs:** `engine.inject_event()` logs "unknown target" warning.

### Pitfall 6: Broadcast to paused simulation
**What goes wrong:** User injects a broadcast event while simulation is paused. `add_memory()` succeeds, but no agents run `decide_action()` so the event is never "perceived" in practice until resumed.
**Why it happens:** The tick loop blocks on `_running.wait()` when paused.
**How to avoid:** This is acceptable behavior — the event is stored in memory and will be retrieved on resume. No special handling needed. Document in UX that events injected while paused take effect on resume.

---

## Code Examples

Verified patterns from the existing codebase:

### Pause/resume ws.py pattern (model for inject_event handler)
```python
# Source: backend/routers/ws.py lines 96-118
elif message.type == "pause":
    engine.pause()
    logger.info("Simulation paused via WebSocket command")
    status_msg = WSMessage(
        type="simulation_status",
        payload={"status": "paused"},
        timestamp=time.time(),
    )
    await manager.broadcast(status_msg.model_dump_json())
```

### sendMessage pattern from BottomBar.tsx (model for event injection)
```typescript
// Source: frontend/src/components/BottomBar.tsx lines 8-18
function handlePauseResume() {
  const send = getSendMessage();
  if (send) {
    send({
      type: isPaused ? "resume" : "pause",
      payload: {},
      timestamp: Date.now() / 1000,
    });
  }
  // Do NOT call store action locally — backend broadcast is single source of truth
}
```

### add_memory() signature (for inject_event implementation)
```python
# Source: backend/agents/memory/store.py lines 53-93
async def add_memory(
    simulation_id: str,
    agent_id: str,
    content: str,
    memory_type: str,   # "observation" | "conversation" | "action" | "event"
    importance: int,    # 1-10; use 8 for injected events
) -> None:
```

### ActivityFeed "event" rendering (already complete — no changes needed)
```tsx
// Source: frontend/src/components/ActivityFeed.tsx lines 60-78
if (msg.type === "event") {
  const text = (msg.payload.text as string) ?? JSON.stringify(msg.payload);
  return (
    <div ...>
      <span style={{ color: "#f39c12", fontWeight: "bold" }}>Event:</span>{" "}
      {text}
    </div>
  );
}
```

### _broadcast_callback shape (for _emit_event method)
```python
# Source: backend/simulation/engine.py lines 386-402
async def _emit_agent_update(self, agent_name: str, state: AgentState) -> None:
    if self._broadcast_callback is not None:
        await self._broadcast_callback({
            "type": "agent_update",
            "name": agent_name,
            "coord": list(state.coord),
            "activity": state.current_activity,
        })
```

---

## State of the Art

| Old Approach | Current Approach | Status |
|--------------|------------------|--------|
| Tile._events injection | Direct add_memory() injection | Preferred — persists across ticks |
| REST POST /api/events | WebSocket inject_event message | Decided (D-04) — consistent with existing WS-only protocol |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | importance=8 is sufficient for injected events to surface in composite retrieval scoring | Architecture Patterns | If wrong: agents don't react to events. Mitigation: make importance configurable or test with a lower-importance baseline |
| A2 | Gossip spreading works without any prompt-level changes because conversation summaries already include the event topic | Architecture Patterns | If wrong: the LLM may not mention the injected event in the conversation. Mitigation: verify by observing a whisper → conversation → memory chain in integration testing |

---

## Open Questions

1. **Should the whisper dropdown support clicking an agent sprite on the map (D-03)?**
   - What we know: D-03 says "dropdown OR clicking." The dropdown is simpler to implement.
   - What's unclear: Click-to-select requires TileMap/AgentSprite to expose an event back to BottomBar — cross-component communication.
   - Recommendation: Implement dropdown first (simpler, no cross-component plumbing). Map-click can be a follow-up.

2. **Importance level for injected events — is 8 well-calibrated?**
   - What we know: Scale is 1-10. Importance 8 = "highly significant." Action memories use importance=3.
   - What's unclear: Whether an importance-8 event is always retrieved when 50 memories are in the pool.
   - Recommendation: Use 8 for injected events. The composite scorer also weights recency and relevance; a very recent importance-8 event will rank near the top regardless of semantic similarity.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 6 is purely code changes wiring existing components. No new external dependencies, tools, runtimes, databases, or CLI utilities beyond those already installed and verified in prior phases.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-asyncio 1.3.0 (backend) / Vitest 4.1.4 (frontend) |
| Config file | pyproject.toml `[tool.pytest.ini_options]` (backend) / vite.config.ts (frontend, no separate vitest.config) |
| Quick run command | `cd /Users/sainobekou/projects/agent-town && uv run pytest tests/ -x -q` |
| Full suite command | `cd /Users/sainobekou/projects/agent-town && uv run pytest tests/ -q && cd frontend && npm test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EVT-01 | BottomBar input is enabled; Enter key dispatches inject_event WSMessage | unit (frontend) | `cd frontend && npm test` | ❌ Wave 0 |
| EVT-02 | inject_event with mode="broadcast" stores memory for all agents | unit (backend) | `uv run pytest tests/test_event_injection.py -x -q` | ❌ Wave 0 |
| EVT-03 | inject_event with mode="whisper" stores memory only for target agent | unit (backend) | `uv run pytest tests/test_event_injection.py -x -q` | ❌ Wave 0 |
| EVT-04 | High-importance memory retrieved in subsequent decide_action() call | integration | `uv run pytest tests/test_event_injection.py::test_whisper_memory_retrieved -x -q` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q` (backend unit tests)
- **Per wave merge:** `uv run pytest tests/ -q && cd frontend && npm test`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_event_injection.py` — covers EVT-02, EVT-03, EVT-04 (backend unit + integration)
- [ ] `frontend/src/tests/event-injection.test.tsx` — covers EVT-01 (frontend unit: BottomBar input state and dispatch)

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | Server-side: strip empty text; validate mode is "broadcast" or "whisper"; validate target is a known agent name |
| V6 Cryptography | no | — |

### Known Threat Patterns for Event Injection

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Empty event text spam | DoS | Server-side guard: reject empty or whitespace-only text before `add_memory()` |
| Fabricated agent name in whisper | Tampering | Validate `target in engine._agent_states` before any storage |
| Extremely long event text | DoS | Truncate at reasonable limit (e.g., 500 chars) before storing in ChromaDB |
| Rapid-fire event injection | DoS | The existing LLM cost model limits agent reactivity; no special rate-limiting needed for v1 single-user |

---

## Sources

### Primary (HIGH confidence)
- Codebase: `backend/routers/ws.py` — existing pause/resume WSMessage handler pattern
- Codebase: `backend/simulation/engine.py` — SimulationEngine structure, `_agent_states`, `_broadcast_callback`
- Codebase: `backend/agents/memory/store.py` — `add_memory()` signature and async wrapper
- Codebase: `backend/schemas.py` — `WSMessage` Literal union (current state)
- Codebase: `frontend/src/components/BottomBar.tsx` — disabled input, getSendMessage pattern
- Codebase: `frontend/src/components/ActivityFeed.tsx` — "event" type already rendered
- Codebase: `frontend/src/hooks/useWebSocket.ts` — "event" case already calls appendFeed
- Codebase: `frontend/src/types/index.ts` — WSMessageType union (current state)
- Codebase: `frontend/src/store/simulationStore.ts` — agents dict, appendFeed, getSendMessage

### Secondary (MEDIUM confidence)
- `tests/test_simulation.py` — fixture patterns for engine unit testing

### Tertiary (LOW confidence)
None.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; all existing
- Architecture: HIGH — verified against actual code for each integration point
- Pitfalls: HIGH — each pitfall traced to a specific code path in the codebase
- Gossip spreading (EVT-04): MEDIUM — mechanism correct but LLM prompt behavior is non-deterministic; integration test needed to confirm

**Research date:** 2026-04-10
**Valid until:** Stable — no external dependencies; only valid while codebase structure matches verified files
