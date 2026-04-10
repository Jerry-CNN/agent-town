# Phase 4: Simulation Engine & Transport - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Phase Boundary

The simulation runs all agents concurrently in a real-time loop, pushes state updates to connected browser clients via WebSocket, and respects pause/resume commands. This phase wires together all Phase 3 cognition modules into a running simulation and exposes it to the browser. No rendering (Phase 5), no event injection UI (Phase 6).

</domain>

<decisions>
## Implementation Decisions

### Simulation Tick Model
- **D-01:** Agents act every 5-10 seconds. Each tick runs the full perceive -> decide -> act cycle. Gives LLM calls time to complete while keeping the town feeling alive.
- **D-02:** All agents process in parallel using asyncio.TaskGroup. Each agent's perceive/decide/act is independent. No semaphore throttling for v1 — if Ollama can't keep up, tick duration stretches naturally.
- **D-03:** On simulation start: load all agent configs, generate daily schedules for each agent (2 LLM calls per agent), then enter the tick loop.

### WebSocket Push Protocol
- **D-04:** Push all state changes to connected browsers: agent position updates, activity changes, conversation starts/ends, and injected events. The browser can reconstruct full state from the stream alone (success criterion 3).
- **D-05:** Full snapshot on WebSocket connect. When a client connects, send a snapshot message with all agent positions, activities, and simulation status. Then stream deltas. Handles page refresh gracefully.
- **D-06:** Expand the existing WSMessage schema with new payload types for agent_update (position + activity), conversation (turns), and simulation_status (running/paused).

### Pause/Resume Behavior
- **D-07:** Pause uses a shared asyncio.Event flag. The tick loop checks the flag before starting each agent's step. When paused, agents finish their current action but don't start a new tick. Resume sets the flag and the loop continues.
- **D-08:** Pause/resume commands sent via WebSocket from the browser. The existing /ws endpoint handles these as incoming messages.

### Agent Movement Pacing
- **D-09:** One tile per tick along the BFS path. Agent advances one tile each simulation tick (5-10 sec). Frontend (Phase 5) can interpolate smooth movement between ticks.
- **D-10:** When an agent decides to go somewhere, the simulation calls maze.find_path() and stores the path. Each tick pops the next tile from the path. Agent arrives when the path is empty.

### Claude's Discretion
- Exact tick interval within the 5-10 second range (probably 5 seconds for responsiveness)
- How to handle LLM calls that take longer than one tick (skip the agent's tick, or let it run long)
- WebSocket message batching (send individual events or batch per tick)
- How many WebSocket clients to support simultaneously (connection pool management)
- REST endpoints for pause/resume as alternative to WebSocket commands

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Reference implementation
- `~/projects/GenerativeAgentsCN/generative_agents/modules/run.py` -- Simulation loop: agent stepping, tick pacing, concurrent execution
- `~/projects/GenerativeAgentsCN/generative_agents/modules/agent.py` -- Agent step method: perceive -> decide -> act flow

### Existing codebase (Phase 1-3 outputs)
- `backend/routers/ws.py` -- WebSocket endpoint stub (Phase 1), expand for push protocol
- `backend/schemas.py` -- WSMessage schema, AgentConfig, AgentAction, all cognition models
- `backend/agents/cognition/perceive.py` -- perceive() function
- `backend/agents/cognition/decide.py` -- decide_action() function
- `backend/agents/cognition/converse.py` -- attempt_conversation(), run_conversation()
- `backend/agents/cognition/plan.py` -- generate_daily_schedule(), decompose_hour()
- `backend/agents/memory/store.py` -- add_memory(), reset_simulation()
- `backend/simulation/world.py` -- Maze.find_path(), Maze.resolve_destination()
- `backend/agents/loader.py` -- load_all_agents()
- `backend/gateway.py` -- complete_structured() with fallback parameter

### Prior phase context
- `.planning/phases/01-foundation/01-CONTEXT.md` -- LLM providers, app shell, error handling
- `.planning/phases/02-world-navigation/02-CONTEXT.md` -- Map model, agent data structures
- `.planning/phases/03-agent-cognition/03-CONTEXT.md` -- Memory, perception, schedule, conversation decisions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `WSMessage` schema with type/payload/timestamp — ready for new event types
- `websocket_endpoint()` in ws.py — stub with ping/pong, expand for simulation push
- All cognition functions are async and take `simulation_id` — ready to call from the simulation loop
- `asyncio.TaskGroup` (Python 3.11+) available for structured concurrency
- `load_all_agents()` returns typed AgentConfig list — ready for simulation initialization

### Established Patterns
- Async-first (FastAPI + asyncio) — simulation loop must be async
- Pydantic v2 for all data contracts — WebSocket messages should follow the same pattern
- `complete_structured()` with fallback — cognition calls never crash the simulation

### Integration Points
- Simulation loop calls cognition modules (perceive, decide, converse, plan) each tick
- WebSocket broadcasts state changes to all connected clients
- Maze.find_path() called when agent decides to move to a new destination
- Phase 5 (frontend) consumes the WebSocket stream to render agent positions and activity

</code_context>

<specifics>
## Specific Ideas

- The simulation loop should be a single async function that runs in the FastAPI lifespan context
- Each agent's state (current position, path, schedule, activity) needs a runtime AgentState object separate from the static AgentConfig
- WebSocket broadcast should use a connection manager pattern (list of active connections, broadcast helper)

</specifics>

<deferred>
## Deferred Ideas

- Simulation speed control (SIM-04) — deferred to v2
- User chooses agent count (SIM-05) — deferred to v2
- Event injection through WebSocket — that's Phase 6

</deferred>

---

*Phase: 04-simulation-engine-transport*
*Context gathered: 2026-04-10*
