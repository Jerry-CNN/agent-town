# Roadmap: Agent Town

**Created:** 2026-04-08
**Milestone:** v1.0
**Granularity:** Standard
**Requirements:** 28 v1 requirements

---

## Phases

- [ ] **Phase 1: Foundation** - Project scaffold, async infrastructure, LLM gateway, structured output, and configuration UI
- [ ] **Phase 2: World & Navigation** - Tile map data model, BFS pathfinding, agent data structures, and thematic town layout
- [ ] **Phase 3: Agent Cognition** - Memory stream, daily planning, perception, LLM decisions, and agent-to-agent conversations
- [ ] **Phase 4: Simulation Engine & Transport** - Real-time async simulation loop, WebSocket push, and pause/resume control
- [ ] **Phase 5: Frontend** - React/PixiJS map rendering, agent sprites, activity feed, agent inspection panel
- [ ] **Phase 6: Event Injection** - Event UI, broadcast mode, whisper mode, and organic gossip spreading

---

## Phase Details

### Phase 1: Foundation

**Goal:** The project runs end-to-end with async infrastructure, an LLM gateway supporting Ollama (local) and OpenRouter (cloud), provider config UI, structured output validated by Pydantic with retry/fallback, and the frontend app shell with map-dominant layout.
**Requirements:** INF-01, INF-02, INF-03, CFG-01, CFG-02
**UI hint:** yes
**Depends on:** None

### Success Criteria

1. Running `uvicorn backend.main:app` starts without errors; GET /health returns 200.
2. Ollama availability is auto-detected on startup; a non-blocking banner appears in the UI if Ollama is not running.
3. An async task that simulates 10 concurrent agent "steps" completes all 10 in parallel (not sequentially), verified by test timestamps.
4. A malformed LLM JSON response triggers automatic retry and fallback without crashing the server.
5. Browser at localhost:5173 renders the map-dominant layout: PixiJS canvas, collapsible sidebar, bottom bar.

**Plans:** 3 plans

Plans:
- [x] 01-01-PLAN.md — Backend scaffold: FastAPI, dual-provider async LLM gateway (Ollama + OpenRouter via LiteLLM + instructor), /health /api/config /ws endpoints, Pydantic v2 schemas, concurrency + retry tests (Wave 1)
- [x] 01-02-PLAN.md — Frontend scaffold: Vite/React/TS, map-dominant layout shell, PixiJS placeholder canvas, Zustand store, WebSocket hook, Biome config (Wave 1, parallel to 01)
- [x] 01-03-PLAN.md — Provider config UI + integration: first-visit setup modal (Ollama/OpenRouter selector, API key input), Ollama banner, localStorage persistence, e2e integration tests, human verification checkpoint (Wave 2)

---

### Phase 2: World & Navigation

**Goal:** A data-modeled tile-map town with named thematic locations exists in memory and BFS pathfinding routes agents around obstacles between any two tiles.
**Requirements:** MAP-03, MAP-04, AGT-01
**UI hint:** no
**Depends on:** Phase 1

### Success Criteria

1. The town map data structure loads all required locations (stock exchange, wedding hall, park, homes, shops, cafe, office) and obstacle tiles.
2. Calling `find_path(start, goal)` on the map returns a valid BFS path that avoids obstacle tiles for any two reachable positions.
3. Each pre-defined agent (minimum 5) has a distinct name, personality traits, occupation, and default daily routine stored in their data structure.
4. A unit test confirms pathfinding produces no path when start and goal are disconnected by obstacles.

**Plans:** 3 plans

Plans:
- [x] 02-01-PLAN.md — World data model (Tile + Maze classes), programmatic 100x100 town map generator with thematic locations, BFS pathfinding with destination resolution, comprehensive unit tests (Wave 1)
- [x] 02-02-PLAN.md — Agent personality schemas (Pydantic v2), 8 diverse agent JSON configs with traits/occupation/routine, agent loader module, agent validation tests (Wave 1, parallel to 01)
- [x] 02-03-PLAN.md — Cross-plan integration validation: agent spawn coords vs town.json walkability, sector existence checks, connected graph assertion (Wave 2, depends on 01 + 02)

---

### Phase 3: Agent Cognition

**Goal:** Agents autonomously plan schedules, perceive their environment, retrieve memories, make LLM-powered decisions, and hold multi-turn conversations that revise their plans.
**Requirements:** AGT-02, AGT-03, AGT-04, AGT-05, AGT-06, AGT-07, AGT-08
**UI hint:** no
**Depends on:** Phase 2

### Success Criteria

1. An agent generates a daily schedule decomposed into sub-tasks when prompted, using an LLM call with structured Pydantic output.
2. An agent's perception radius correctly returns all events and other agents within N tiles and ignores those outside the radius.
3. After 10 experiences are stored in the memory stream, retrieval returns the top-k most relevant by composite score (recency x 0.5 + relevance x 3 + importance x 2).
4. Two agents within proximity initiate a multi-turn conversation (at least 2 exchanges), and both agents produce revised schedules after the conversation ends.
5. An LLM decision call given a perception input and memory context returns a structured action (destination + activity) without parse errors.

**Plans:** 3 plans

Plans:
- [x] 03-01-PLAN.md — ChromaDB memory stream with async wrappers, composite-scored retrieval, LLM importance scoring, all Phase 3 Pydantic v2 cognition schemas (Wave 1)
- [x] 03-02-PLAN.md — Tile-grid perception scan within radius, two-level daily schedule generation via LLM with hourly blocks and sub-task decomposition (Wave 2)
- [x] 03-03-PLAN.md — LLM-powered action decisions from perception+memory context, multi-turn conversation system with cooldown, post-conversation schedule revision (Wave 3)

---

### Phase 4: Simulation Engine & Transport

**Goal:** The simulation runs all agents concurrently in a real-time loop, pushes state updates to connected browser clients via WebSocket, and respects pause/resume commands.
**Requirements:** SIM-01, SIM-02, SIM-03
**UI hint:** no
**Depends on:** Phase 3

### Success Criteria

1. Starting the simulation triggers all agents to act on independent async coroutines; no agent waits for another to finish before beginning its step.
2. Every agent state change (position update, activity change, conversation start) is broadcast to the WebSocket within one simulation tick.
3. A WebSocket client connected in the browser receives a stream of JSON events and can reconstruct current agent positions and activities from that stream alone.
4. Pressing pause halts all agent processing within one tick; pressing resume restarts all agents from their paused state without data loss.

**Plans:** 2 plans

Plans:
- [x] 04-01-PLAN.md — SimulationEngine class: asyncio.TaskGroup concurrent tick loop, AgentState dataclass, perceive/decide/converse agent step, pause/resume via asyncio.Event, schedule generation on startup, exception isolation per agent (Wave 1)
- [x] 04-02-PLAN.md — WebSocket transport: ConnectionManager for multi-client broadcast, WSMessage schema expansion, snapshot-on-connect, pause/resume WS commands, FastAPI lifespan wiring, full integration tests (Wave 2, depends on 01)

---

### Phase 5: Frontend

**Goal:** The browser renders the tile map with moving agent sprites, labels, and an activity feed; users can click any agent to inspect their state.
**Requirements:** MAP-01, MAP-02, MAP-05, DSP-01, DSP-02
**UI hint:** yes
**Depends on:** Phase 4

### Success Criteria

1. The browser displays a scrollable 2D top-down tile map with all thematic town locations visually distinguished.
2. Agent sprites appear at correct tile positions and animate movement as they navigate paths in real-time without teleporting.
3. Each agent displays a name label and their current activity text above their sprite at all times.
4. Clicking an agent opens an inspection panel showing their personality traits, current activity, and last 5 memory entries.
5. The activity feed scrolls in real-time showing agent actions, conversations, and activity changes as they happen.

**Plans:** 4 plans

Plans:
- [x] 05-01-PLAN.md — Data layer: extend frontend types with full WSMessageType union, upgrade Zustand store with agent dispatch actions (snapshot, agent_update, simulation_status), wire WebSocket message routing, connect BottomBar pause/resume to backend (Wave 1)
- [x] 05-02-PLAN.md — Tile map and backend memories: PixiJS sector zone rendering with colored rectangles and text labels from town.json, backend GET /api/agents/{name}/memories endpoint for inspector (Wave 1, parallel to 01)
- [x] 05-03-PLAN.md — Agent sprites: PixiJS colored circles with initial letters, name/activity labels, smooth lerp interpolation, click-to-select, pan/zoom viewport (Wave 2, depends on 01 + 02)
- [x] 05-04-PLAN.md — Activity feed and inspector: formatted feed entries with colored agent names and timestamps, scroll-pause behavior, agent inspector panel with personality/memories display (Wave 2, parallel to 03, depends on 01)

---

### Phase 6: Event Injection

**Goal:** Users can type any free-text event, choose broadcast or whisper delivery, and watch the event propagate through agents -- including organic gossip spread for whispered events.
**Requirements:** EVT-01, EVT-02, EVT-03, EVT-04
**UI hint:** yes
**Depends on:** Phase 5

### Success Criteria

1. The user can type a free-text event into an input field and submit it without page reload.
2. A broadcast event immediately appears in all agents' perception queues within one simulation tick, visible in the activity feed.
3. A whisper event targeted at one specific agent is received by only that agent initially; other agents have no knowledge of it.
4. The whispered event spreads to at least one additional agent through a natural agent-to-agent conversation within a reasonable number of simulation ticks, and the activity feed shows the gossip propagating.

**Plans:** TBD

---

## Phase Summary

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|-----------------|
| 1 | Foundation | Async infra, LLM gateway (Ollama + OpenRouter), provider config, app shell | INF-01, INF-02, INF-03, CFG-01, CFG-02 | 5 |
| 2 | World & Navigation | Tile map, BFS pathfinding, agent data structures | MAP-03, MAP-04, AGT-01 | 4 |
| 3 | Agent Cognition | Memory, planning, perception, LLM decisions, conversations | AGT-02, AGT-03, AGT-04, AGT-05, AGT-06, AGT-07, AGT-08 | 5 |
| 4 | Simulation Engine & Transport | Real-time loop, WebSocket push, pause/resume | SIM-01, SIM-02, SIM-03 | 4 |
| 5 | Frontend | Map rendering, sprites, labels, feed, agent inspection | MAP-01, MAP-02, MAP-05, DSP-01, DSP-02 | 5 |
| 6 | Event Injection | Event UI, broadcast, whisper, gossip spreading | EVT-01, EVT-02, EVT-03, EVT-04 | 4 |

## Coverage

| Requirement | Phase |
|-------------|-------|
| INF-01 | Phase 1 |
| INF-02 | Phase 1 |
| INF-03 | Phase 1 |
| CFG-01 | Phase 1 |
| CFG-02 | Phase 1 |
| CFG-03 | v2 (deferred) |
| MAP-03 | Phase 2 |
| MAP-04 | Phase 2 |
| AGT-01 | Phase 2 |
| AGT-02 | Phase 3 |
| AGT-03 | Phase 3 |
| AGT-04 | Phase 3 |
| AGT-05 | Phase 3 |
| AGT-06 | Phase 3 |
| AGT-07 | Phase 3 |
| AGT-08 | Phase 3 |
| SIM-01 | Phase 4 |
| SIM-02 | Phase 4 |
| SIM-03 | Phase 4 |
| MAP-01 | Phase 5 |
| MAP-02 | Phase 5 |
| MAP-05 | Phase 5 |
| DSP-01 | Phase 5 |
| DSP-02 | Phase 5 |
| EVT-01 | Phase 6 |
| EVT-02 | Phase 6 |
| EVT-03 | Phase 6 |
| EVT-04 | Phase 6 |

**Total mapped: 27/28 (1 deferred to v2: CFG-03)**

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 0/3 | Not started | - |
| 2. World & Navigation | 0/3 | Not started | - |
| 3. Agent Cognition | 0/3 | Not started | - |
| 4. Simulation Engine & Transport | 0/2 | Not started | - |
| 5. Frontend | 0/4 | Not started | - |
| 6. Event Injection | 0/? | Not started | - |
