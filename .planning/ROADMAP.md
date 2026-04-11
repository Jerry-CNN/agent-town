# Roadmap: Agent Town

**Created:** 2026-04-08
**Updated:** 2026-04-10 (v1.1 milestone added)
**Granularity:** Standard

---

## Milestones

- ✅ **v1.0 Core** - Phases 1-6 (shipped 2026-04-10)
- 🚧 **v1.1 Architecture & Polish** - Phases 7-12 (in progress)

---

## Phases

<details>
<summary>✅ v1.0 Core (Phases 1-6) - SHIPPED 2026-04-10</summary>

- [x] **Phase 1: Foundation** - Project scaffold, async infrastructure, LLM gateway, structured output, and configuration UI
- [x] **Phase 2: World & Navigation** - Tile map data model, BFS pathfinding, agent data structures, and thematic town layout
- [x] **Phase 3: Agent Cognition** - Memory stream, daily planning, perception, LLM decisions, and agent-to-agent conversations
- [x] **Phase 4: Simulation Engine & Transport** - Real-time async simulation loop, WebSocket push, and pause/resume control
- [x] **Phase 5: Frontend** - React/PixiJS map rendering, agent sprites, activity feed, agent inspection panel
- [x] **Phase 6: Event Injection** - Event UI, broadcast mode, whisper mode, and organic gossip spreading

### Phase 1: Foundation
**Goal**: The project runs end-to-end with async infrastructure, an LLM gateway supporting Ollama (local) and OpenRouter (cloud), provider config UI, structured output validated by Pydantic with retry/fallback, and the frontend app shell with map-dominant layout.
**Depends on**: Nothing (first phase)
**Requirements**: INF-01, INF-02, INF-03, CFG-01, CFG-02
**Success Criteria** (what must be TRUE):
  1. Running `uvicorn backend.main:app` starts without errors; GET /health returns 200.
  2. Ollama availability is auto-detected on startup; a non-blocking banner appears in the UI if Ollama is not running.
  3. An async task that simulates 10 concurrent agent "steps" completes all 10 in parallel (not sequentially), verified by test timestamps.
  4. A malformed LLM JSON response triggers automatic retry and fallback without crashing the server.
  5. Browser at localhost:5173 renders the map-dominant layout: PixiJS canvas, collapsible sidebar, bottom bar.
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md — Backend scaffold: FastAPI, dual-provider async LLM gateway (Ollama + OpenRouter via LiteLLM + instructor), /health /api/config /ws endpoints, Pydantic v2 schemas, concurrency + retry tests
- [x] 01-02-PLAN.md — Frontend scaffold: Vite/React/TS, map-dominant layout shell, PixiJS placeholder canvas, Zustand store, WebSocket hook, Biome config
- [x] 01-03-PLAN.md — Provider config UI + integration: first-visit setup modal, Ollama banner, localStorage persistence, e2e integration tests

---

### Phase 2: World & Navigation
**Goal**: A data-modeled tile-map town with named thematic locations exists in memory and BFS pathfinding routes agents around obstacles between any two tiles.
**Depends on**: Phase 1
**Requirements**: MAP-03, MAP-04, AGT-01
**Success Criteria** (what must be TRUE):
  1. The town map data structure loads all required locations (stock exchange, wedding hall, park, homes, shops, cafe, office) and obstacle tiles.
  2. Calling `find_path(start, goal)` on the map returns a valid BFS path that avoids obstacle tiles for any two reachable positions.
  3. Each pre-defined agent (minimum 5) has a distinct name, personality traits, occupation, and default daily routine stored in their data structure.
  4. A unit test confirms pathfinding produces no path when start and goal are disconnected by obstacles.
**Plans**: 3 plans

Plans:
- [x] 02-01-PLAN.md — World data model (Tile + Maze classes), programmatic 100x100 town map generator with thematic locations, BFS pathfinding with destination resolution, comprehensive unit tests
- [x] 02-02-PLAN.md — Agent personality schemas (Pydantic v2), 8 diverse agent JSON configs with traits/occupation/routine, agent loader module, agent validation tests
- [x] 02-03-PLAN.md — Cross-plan integration validation: agent spawn coords vs town.json walkability, sector existence checks, connected graph assertion

---

### Phase 3: Agent Cognition
**Goal**: Agents autonomously plan schedules, perceive their environment, retrieve memories, make LLM-powered decisions, and hold multi-turn conversations that revise their plans.
**Depends on**: Phase 2
**Requirements**: AGT-02, AGT-03, AGT-04, AGT-05, AGT-06, AGT-07, AGT-08
**Success Criteria** (what must be TRUE):
  1. An agent generates a daily schedule decomposed into sub-tasks when prompted, using an LLM call with structured Pydantic output.
  2. An agent's perception radius correctly returns all events and other agents within N tiles and ignores those outside the radius.
  3. After 10 experiences are stored in the memory stream, retrieval returns the top-k most relevant by composite score (recency x 0.5 + relevance x 3 + importance x 2).
  4. Two agents within proximity initiate a multi-turn conversation (at least 2 exchanges), and both agents produce revised schedules after the conversation ends.
  5. An LLM decision call given a perception input and memory context returns a structured action (destination + activity) without parse errors.
**Plans**: 3 plans

Plans:
- [x] 03-01-PLAN.md — ChromaDB memory stream with async wrappers, composite-scored retrieval, LLM importance scoring, all Phase 3 Pydantic v2 cognition schemas
- [x] 03-02-PLAN.md — Tile-grid perception scan within radius, two-level daily schedule generation via LLM with hourly blocks and sub-task decomposition
- [x] 03-03-PLAN.md — LLM-powered action decisions from perception+memory context, multi-turn conversation system with cooldown, post-conversation schedule revision

---

### Phase 4: Simulation Engine & Transport
**Goal**: The simulation runs all agents concurrently in a real-time loop, pushes state updates to connected browser clients via WebSocket, and respects pause/resume commands.
**Depends on**: Phase 3
**Requirements**: SIM-01, SIM-02, SIM-03
**Success Criteria** (what must be TRUE):
  1. Starting the simulation triggers all agents to act on independent async coroutines; no agent waits for another to finish before beginning its step.
  2. Every agent state change (position update, activity change, conversation start) is broadcast to the WebSocket within one simulation tick.
  3. A WebSocket client connected in the browser receives a stream of JSON events and can reconstruct current agent positions and activities from that stream alone.
  4. Pressing pause halts all agent processing within one tick; pressing resume restarts all agents from their paused state without data loss.
**Plans**: 2 plans

Plans:
- [x] 04-01-PLAN.md — SimulationEngine class: asyncio.TaskGroup concurrent tick loop, AgentState dataclass, perceive/decide/converse agent step, pause/resume via asyncio.Event, schedule generation on startup, exception isolation per agent
- [x] 04-02-PLAN.md — WebSocket transport: ConnectionManager for multi-client broadcast, WSMessage schema expansion, snapshot-on-connect, pause/resume WS commands, FastAPI lifespan wiring, full integration tests

---

### Phase 5: Frontend
**Goal**: The browser renders the tile map with moving agent sprites, labels, and an activity feed; users can click any agent to inspect their state.
**Depends on**: Phase 4
**Requirements**: MAP-01, MAP-02, MAP-05, DSP-01, DSP-02
**Success Criteria** (what must be TRUE):
  1. The browser displays a scrollable 2D top-down tile map with all thematic town locations visually distinguished.
  2. Agent sprites appear at correct tile positions and animate movement as they navigate paths in real-time without teleporting.
  3. Each agent displays a name label and their current activity text above their sprite at all times.
  4. Clicking an agent opens an inspection panel showing their personality traits, current activity, and last 5 memory entries.
  5. The activity feed scrolls in real-time showing agent actions, conversations, and activity changes as they happen.
**Plans**: 4 plans

Plans:
- [x] 05-01-PLAN.md — Data layer: extend frontend types with full WSMessageType union, upgrade Zustand store with agent dispatch actions, wire WebSocket message routing, connect BottomBar pause/resume to backend
- [x] 05-02-PLAN.md — Tile map and backend memories: PixiJS sector zone rendering with colored rectangles and text labels from town.json, backend GET /api/agents/{name}/memories endpoint for inspector
- [x] 05-03-PLAN.md — Agent sprites: PixiJS colored circles with initial letters, name/activity labels, smooth lerp interpolation, click-to-select, pan/zoom viewport
- [x] 05-04-PLAN.md — Activity feed and inspector: formatted feed entries with colored agent names and timestamps, scroll-pause behavior, agent inspector panel with personality/memories display

---

### Phase 6: Event Injection
**Goal**: Users can type any free-text event, choose broadcast or whisper delivery, and watch the event propagate through agents -- including organic gossip spread for whispered events.
**Depends on**: Phase 5
**Requirements**: EVT-01, EVT-02, EVT-03, EVT-04
**Success Criteria** (what must be TRUE):
  1. The user can type a free-text event into an input field and submit it without page reload.
  2. A broadcast event immediately appears in all agents' perception queues within one simulation tick, visible in the activity feed.
  3. A whisper event targeted at one specific agent is received by only that agent initially; other agents have no knowledge of it.
  4. The whispered event spreads to at least one additional agent through a natural agent-to-agent conversation within a reasonable number of simulation ticks, and the activity feed shows the gossip propagating.
**Plans**: 2 plans

Plans:
- [x] 06-01-PLAN.md — Backend event injection: extend WSMessage with inject_event type, SimulationEngine.inject_event() method storing high-importance memories, ws.py handler with validation, backend tests
- [x] 06-02-PLAN.md — Frontend event UI: enable BottomBar input, broadcast/whisper toggle, whisper agent dropdown, inject_event WSMessage dispatch, frontend tests, human verification

</details>

---

### 🚧 v1.1 Architecture & Polish (In Progress)

**Milestone Goal:** Refactor the codebase to proper OOP abstractions, fix the visual experience, and optimize LLM call patterns.

- [ ] **Phase 7: OOP Foundation** - Agent/Building/Event classes replace scattered dicts; schemas.py split into domain-grouped modules
- [ ] **Phase 8: Visual & Building Behavior** - Building walls visible on map with collision; agent text readable at default zoom; buildings respect operating hours
- [ ] **Phase 9: LLM Optimization** - 3-level destination resolution, 10s tick interval, conversation repetition detection, semaphore concurrency control

### Planned: v1.2 Agent Behavior (after v1.1)

- [ ] **Phase 10: Task & Perception Systems** - Task state machine with interrupt/resume; perception diff so agents react to changes not static scenes
- [ ] **Phase 11: Reflection System** - Poignancy accumulation, threshold-triggered insight generation as background asyncio tasks
- [ ] **Phase 12: Relationship Tracking** - Agent-to-agent relationship state (familiarity, sentiment, last interaction) visible in inspector

---

## Phase Details

### Phase 7: OOP Foundation
**Goal**: The backend has an Agent class (unifying config + state + cognition), a Building class, and an Event class; SimulationEngine operates on Agent objects instead of separate dicts; schemas.py is split into domain-grouped files — with no behavior change, all existing tests passing, and WebSocket payloads unchanged.
**Depends on**: Phase 6
**Requirements**: ARCH-01, ARCH-02, ARCH-03, BLD-01, EVTS-01, EVTS-02, EVTS-03
**Success Criteria** (what must be TRUE):
  1. SimulationEngine holds a single `dict[str, Agent]` — no separate `configs` or `states` dicts remain.
  2. Calling `agent.perceive()`, `agent.decide()`, and `agent.converse()` delegates correctly to the existing function implementations (behavior unchanged, all agent cognition tests still pass).
  3. Each Building object carries name, operating hours, and purpose tag; the town loads without KeyError on any sector lookup.
  4. Each injected or perceived event is represented as an Event object with a `status` field that is one of: created, active, spreading, expired.
  5. Schemas previously in `schemas.py` are importable from their new domain-grouped module paths with no import errors across the codebase.
  6. WebSocket snapshot and agent_update payloads are byte-identical before and after the refactor — a contract test compares serialized output from old and new code paths.
**Plans**: TBD
**UI hint**: no

---

### Phase 8: Visual & Building Behavior
**Goal**: The map shows visible building wall outlines agents cannot walk through; agent name and activity text is legible at default zoom; buildings with closing hours redirect agents to alternate destinations when closed.
**Depends on**: Phase 7
**Requirements**: BLD-02, BLD-03, VIS-01, VIS-02
**Success Criteria** (what must be TRUE):
  1. Building perimeters are rendered as visible outlines (3-4px stroke) on the PixiJS map; all thematic locations have distinct wall geometry.
  2. An agent navigating toward a wall tile is deflected by BFS — the pathfinder treats wall tiles as obstacles and the agent arrives at the nearest walkable alternative.
  3. Agent name labels and activity text display at 18-22px on a standard 1920x1080 monitor at the default zoom level without overlapping sprites.
  4. When a building is closed, the agent's LLM decide call receives "X is closed" in its context and re-selects from open destinations — the agent is never routed to a closed building.
**Plans**: TBD
**UI hint**: yes

---

### Phase 9: LLM Optimization
**Goal**: Agent destination decisions use 3-level sector-arena-object resolution; the tick interval is 10 seconds; conversations self-terminate on detected repetition; concurrent LLM calls are bounded by a semaphore.
**Depends on**: Phase 7
**Requirements**: LLM-01, LLM-02, LLM-03, LLM-04
**Success Criteria** (what must be TRUE):
  1. An agent's destination resolution makes at most one LLM call when the target sector is unchanged (per-sector gating skips arena/object calls for unambiguous sectors).
  2. The simulation tick interval is 10 seconds; agents visibly act more frequently than in v1.0 and `AGENT_STEP_TIMEOUT` is updated to `TICK_INTERVAL * 2` (20s) to match.
  3. A conversation between two agents whose last two exchanges are semantically similar terminates early and logs "conversation ended (repetition)" to the activity feed.
  4. With 10 agents running concurrent LLM calls, `asyncio.Semaphore(8)` prevents more than 8 simultaneous in-flight calls; a debug log confirms semaphore acquisition/release per call.
**Plans**: TBD
**UI hint**: no

---

### Phase 10: Task & Perception Systems
**Goal**: Each agent's current task has tracked state (queued, active, interrupted, completed); tasks interrupted by conversations resume afterward; agents scan perception only for new changes rather than re-reading the same static scene every tick.
**Depends on**: Phase 9
**Requirements**: TSK-01, TSK-02, TSK-03, PCPT-01, PCPT-02
**Success Criteria** (what must be TRUE):
  1. The agent inspector panel shows the current task with its state label (queued / active / interrupted / completed).
  2. When a conversation starts mid-task, the task transitions to `interrupted`; after the conversation ends the task resumes and the inspector shows it `active` again.
  3. An agent whose perception scan returns no new events or agents since the last tick does not trigger a decide/react LLM call — confirming the perception diff skips redundant processing.
  4. A new nearby agent or event appearing within an agent's vision radius triggers a reaction decision within one tick, even if nothing else changed.
**Plans**: TBD
**UI hint**: yes

---

### Phase 11: Reflection System
**Goal**: Agents accumulate poignancy from perceived events and conversations; when the poignancy threshold is crossed, a background asyncio task generates higher-level insight memories ("thoughts") without blocking the agent's simulation step.
**Depends on**: Phase 9
**Requirements**: RFL-01, RFL-02, RFL-03
**Success Criteria** (what must be TRUE):
  1. Each memory stored in the agent's stream carries a `poignancy` score (0-10); the agent's accumulated poignancy counter increments by that score on every memory write.
  2. When accumulated poignancy crosses the configured threshold, a reflection produces at least one "thought" memory visible in the agent inspector's memory list labeled with type `thought`.
  3. The reflection coroutine runs via `asyncio.create_task()` — the agent step that triggers it completes and the next agent begins without waiting for the reflection to finish.
  4. The activity feed shows a distinct entry (e.g., "[Agent] is reflecting...") when a reflection fires, confirming it is observable to the user.
**Plans**: TBD
**UI hint**: no

---

### Phase 12: Relationship Tracking
**Goal**: Agents maintain per-pair relationship records (familiarity score, sentiment, last interaction timestamp); relationship history influences whether an agent initiates a conversation; relationships are visible in the inspector.
**Depends on**: Phase 11
**Requirements**: REL-01, REL-02, REL-03
**Success Criteria** (what must be TRUE):
  1. After two agents converse, both agents' relationship records for each other update: familiarity increments and last-interaction timestamp is set.
  2. An agent with a low familiarity score toward a nearby agent is less likely to initiate a conversation than toward a high-familiarity agent — the initiation check uses the relationship record.
  3. The agent inspector panel shows a "Relationships" section listing known agents with their familiarity level and sentiment (positive / neutral / negative).
**Plans**: TBD
**UI hint**: yes

---

## Phase Summary

### v1.1 Architecture & Polish

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|-----------------|
| 7 | OOP Foundation | Agent/Building/Event classes; SimulationEngine on Agent objects; schemas split; WS backward compat | ARCH-01, ARCH-02, ARCH-03, BLD-01, EVTS-01, EVTS-02, EVTS-03 | 6 |
| 8 | Visual & Building Behavior | Wall outlines, walkable collision, readable text, operating hours gating | BLD-02, BLD-03, VIS-01, VIS-02 | 4 |
| 9 | LLM Optimization | 3-level resolution, 10s tick, conversation termination, semaphore | LLM-01, LLM-02, LLM-03, LLM-04 | 4 |

### v1.2 Agent Behavior (planned)

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|-----------------|
| 10 | Task & Perception Systems | Task state machine, interrupt/resume, perception diff | TSK-01, TSK-02, TSK-03, PCPT-01, PCPT-02 | 4 |
| 11 | Reflection System | Poignancy accumulation, threshold-triggered thought memories, background task | RFL-01, RFL-02, RFL-03 | 4 |
| 12 | Relationship Tracking | Per-pair relationship state, initiation weighting, inspector display | REL-01, REL-02, REL-03 | 3 |

## Coverage (v1.1)

| Requirement | Phase |
|-------------|-------|
| ARCH-01 | Phase 7 |
| ARCH-02 | Phase 7 |
| ARCH-03 | Phase 7 |
| BLD-01 | Phase 7 |
| EVTS-01 | Phase 7 |
| EVTS-02 | Phase 7 |
| EVTS-03 | Phase 7 |
| BLD-02 | Phase 8 |
| BLD-03 | Phase 8 |
| VIS-01 | Phase 8 |
| VIS-02 | Phase 8 |
| LLM-01 | Phase 9 |
| LLM-02 | Phase 9 |
| LLM-03 | Phase 9 |
| LLM-04 | Phase 9 |
| TSK-01 | Phase 10 |
| TSK-02 | Phase 10 |
| TSK-03 | Phase 10 |
| PCPT-01 | Phase 10 |
| PCPT-02 | Phase 10 |
| RFL-01 | Phase 11 |
| RFL-02 | Phase 11 |
| RFL-03 | Phase 11 |
| REL-01 | Phase 12 |
| REL-02 | Phase 12 |
| REL-03 | Phase 12 |

**Total mapped: 26/26 (100%)**

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 3/3 | Complete | 2026-04-10 |
| 2. World & Navigation | v1.0 | 3/3 | Complete | 2026-04-10 |
| 3. Agent Cognition | v1.0 | 3/3 | Complete | 2026-04-10 |
| 4. Simulation Engine & Transport | v1.0 | 2/2 | Complete | 2026-04-10 |
| 5. Frontend | v1.0 | 4/4 | Complete | 2026-04-10 |
| 6. Event Injection | v1.0 | 2/2 | Complete | 2026-04-10 |
| 7. OOP Foundation | v1.1 | 0/? | Not started | - |
| 8. Visual & Building Behavior | v1.1 | 0/? | Not started | - |
| 9. LLM Optimization | v1.1 | 0/? | Not started | - |
| 10. Task & Perception Systems | v1.1 | 0/? | Not started | - |
| 11. Reflection System | v1.1 | 0/? | Not started | - |
| 12. Relationship Tracking | v1.1 | 0/? | Not started | - |
