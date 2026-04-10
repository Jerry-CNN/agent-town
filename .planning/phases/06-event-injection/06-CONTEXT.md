# Phase 6: Event Injection - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning
**Mode:** Auto-generated (smart discuss — autonomous mode)

<domain>
## Phase Boundary

Users can type any free-text event, choose broadcast or whisper delivery, and watch the event propagate through agents — including organic gossip spread for whispered events. This is the core user interaction that makes the simulation interactive. Combines frontend UI (event input), backend event processing, and the existing conversation/memory systems for gossip propagation.

</domain>

<decisions>
## Implementation Decisions

### Event Input UI
- **D-01:** Text input field in the bottom bar (existing BottomBar component already has a disabled event input placeholder). Submit with Enter key, no page reload.
- **D-02:** Delivery mode selector: "Broadcast" (all agents) or "Whisper" (single agent). Simple toggle or radio button next to the input.
- **D-03:** For whisper mode, user selects the target agent from a dropdown or by clicking an agent on the map before submitting.

### Event Processing (Backend)
- **D-04:** Events received via WebSocket as a new message type (e.g., type="inject_event"). Backend processes immediately — no REST endpoint needed.
- **D-05:** Broadcast events inject into ALL agents' perception queues within one simulation tick. Each agent receives the event as a high-importance memory.
- **D-06:** Whisper events inject into ONLY the targeted agent's perception queue. Other agents have zero initial knowledge.

### Gossip Propagation
- **D-07:** Whispered events spread organically through the existing conversation system (Phase 3, D-11/D-12/D-13). When a whispered agent converses with another agent, the event may come up naturally based on memory retrieval and LLM conversation generation.
- **D-08:** No special gossip mechanism needed — the existing memory system (composite scoring with importance weighting) and conversation system (schedule revision after chat) already enable organic spread. The whispered event gets stored as a high-importance memory, which retrieval will surface in future conversations.

### Activity Feed Integration
- **D-09:** Injected events appear in the activity feed immediately (broadcast: "Event broadcast: {text}", whisper: "Whispered to {agent}: {text}").
- **D-10:** As gossip spreads through conversations, the activity feed shows the natural propagation (conversation entries mentioning the event topic).

### Claude's Discretion
- Exact UI styling of the event input and delivery selector
- Whether whisper target selection uses a dropdown or map click (or both)
- How to format the injected event in the LLM perception prompt
- Whether to add an event history panel (probably not for v1)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing codebase
- `frontend/src/components/BottomBar.tsx` — Has disabled event input placeholder, pause/resume buttons
- `frontend/src/hooks/useWebSocket.ts` — WebSocket dispatch with sendMessage ref
- `frontend/src/store/simulationStore.ts` — Zustand store with feed and agent state
- `backend/routers/ws.py` — WebSocket endpoint handling message types
- `backend/schemas.py` — WSMessage schema with type union
- `backend/simulation/engine.py` — SimulationEngine with broadcast callback, agent step loop
- `backend/agents/memory/store.py` — add_memory() for storing events as memories
- `backend/agents/cognition/perceive.py` — perceive() reads tile events
- `backend/agents/cognition/converse.py` — conversation system with memory storage

### Prior phase context
- `.planning/phases/03-agent-cognition/03-CONTEXT.md` — Memory, perception, conversation decisions
- `.planning/phases/04-simulation-engine-transport/04-CONTEXT.md` — WebSocket protocol, simulation loop
- `.planning/phases/05-frontend/05-CONTEXT.md` — Frontend layout, activity feed, BottomBar

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- BottomBar.tsx already has event input UI (disabled) — just enable and wire
- WebSocket sendMessage already works for pause/resume — same pattern for event injection
- add_memory() with importance scoring — reuse for storing injected events
- perceive() reads tile._events — can inject events into tile event dict
- Conversation system already stores summaries as memories — gossip propagation is automatic

### Established Patterns
- WSMessage type union for all WS communication
- Zustand store dispatch by message type
- SimulationEngine._emit callbacks for broadcasting state changes

### Integration Points
- Frontend sends inject_event WSMessage → backend ws.py receives → engine processes
- Engine injects into agent perception (broadcast) or single agent memory (whisper)
- Existing conversation system propagates whispered events naturally via memory retrieval

</code_context>

<specifics>
## Specific Ideas

- The gossip spreading for whispered events is the "magic moment" — users whisper something to one agent and watch it spread through conversations over the next few ticks
- The event input should feel immediate — type, hit enter, see the effect in the feed instantly
- Broadcast is the simpler case (inject everywhere); whisper + gossip is the differentiating feature

</specifics>

<deferred>
## Deferred Ideas

- Event injection history log (EVT-05) — deferred to v2
- Pre-built event templates (EVT-06) — deferred to v2
- Event targeting by location instead of agent — not in v1 scope

</deferred>

---

*Phase: 06-event-injection*
*Context gathered: 2026-04-10*
