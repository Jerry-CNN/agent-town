# Requirements: Agent Town

**Defined:** 2026-04-08
**Updated:** 2026-04-11 (v1.2 milestone)
**Core Value:** Users can type any event and immediately see AI agents respond to it in a living, breathing town

## v1.0 Requirements (Complete)

### World & Map

- [x] **MAP-01**: 2D tile-map town rendered in the browser with top-down view
- [x] **MAP-02**: Agent sprites visible on the map, moving between tiles in real-time
- [x] **MAP-03**: Custom town with thematic locations (stock exchange, wedding hall, park, homes, shops, cafe, office)
- [x] **MAP-04**: BFS pathfinding so agents navigate around obstacles to reach destinations
- [x] **MAP-05**: User can click an agent on the map to inspect their current activity, personality, and recent memories

### Agent Cognition

- [x] **AGT-01**: Each agent has a distinct personality (name, traits, occupation, daily routine)
- [x] **AGT-02**: Agents autonomously plan daily schedules and decompose into sub-tasks
- [x] **AGT-03**: Agents perceive nearby events and other agents within a vision radius
- [x] **AGT-04**: Agents make LLM-powered decisions about what to do next based on perceptions and plans
- [x] **AGT-05**: Memory stream stores experiences weighted by recency, relevance, and importance
- [x] **AGT-06**: Agents retrieve relevant memories when making decisions (composite scoring retrieval)
- [x] **AGT-07**: Agents initiate multi-turn conversations with nearby agents based on context
- [x] **AGT-08**: Conversations affect agent schedules (agents revise plans after chatting)

### Event Injection

- [x] **EVT-01**: User can type a free-text event and submit it to the simulation
- [x] **EVT-02**: Broadcast mode delivers the event to all agents instantly
- [x] **EVT-03**: Whisper mode delivers the event to one specific agent
- [x] **EVT-04**: Whispered events spread organically through agent-to-agent conversations

### Simulation Control

- [x] **SIM-01**: Simulation runs in real-time with agents acting every few seconds
- [x] **SIM-02**: Real-time updates pushed to browser via WebSocket
- [x] **SIM-03**: User can pause and resume the simulation

### Configuration

- [x] **CFG-01**: User configures their LLM provider (OpenAI, Anthropic, OpenRouter, Ollama, etc.)
- [x] **CFG-02**: User provides their own API key for the selected provider

### Display

- [x] **DSP-01**: Activity feed showing real-time agent actions and conversations as a scrolling log
- [x] **DSP-02**: Agent labels on the map showing name and current activity above each sprite

### Infrastructure

- [x] **INF-01**: Fresh simulation starts by default on each visit
- [x] **INF-02**: All agent processing is async/concurrent (not sequential) for real-time performance
- [x] **INF-03**: Structured LLM output via Pydantic schemas with retry and fallback on parse failure

## v1.1 Requirements (Complete)

### Agent Abstraction

- [x] **ARCH-01**: Agent class unifies AgentConfig + AgentState into a single object with identity, runtime state, and system fields
- [x] **ARCH-02**: Agent class has cognition methods (perceive, decide, converse, reflect) that delegate to existing functions
- [x] **ARCH-03**: SimulationEngine uses Agent objects instead of separate config/state dicts

### Building System

- [x] **BLD-01**: Building class with properties (name, operating hours, purpose tag)
- [x] **BLD-02**: Buildings have wall tiles marked as collision so agents cannot walk through them
- [x] **BLD-03**: Agents respect building operating hours when choosing destinations

### Event System

- [x] **EVTS-01**: Event class tracks lifecycle (created, active, spreading, expired)
- [x] **EVTS-02**: Events track propagation — which agents heard the event and when
- [x] **EVTS-03**: Events expire after a configurable duration

### Visual

- [x] **VIS-01**: Building walls are rendered as visible outlines on the map
- [x] **VIS-02**: Agent name and activity text is readable at default zoom level

### LLM Optimization

- [x] **LLM-01**: Agent decisions use 2-level resolution (sector -> arena) with per-sector gating
- [x] **LLM-02**: Tick interval reduced from 30s to 10s for more responsive agents
- [x] **LLM-03**: Conversations detect repetition and terminate early instead of fixed turn count
- [x] **LLM-04**: asyncio.Semaphore controls concurrent LLM calls to prevent rate limits

## v1.2 Requirements

Requirements for v1.2 milestone: Pixel Art UI.

### Tile Map Rendering

- [ ] **TILE-01**: User sees a pixel-art tile map with CuteRPG tilesets instead of colored rectangles
- [ ] **TILE-02**: User sees full building interiors with furniture and room layouts rendered from Tiled layers
- [ ] **TILE-03**: User sees agents walk behind foreground objects (trees, roofs) via proper depth ordering
- [ ] **TILE-04**: User sees a loading screen while tile map assets are being loaded

### Agent Sprites

- [ ] **SPRT-01**: User sees animated agent sprites with directional walk cycles (4 directions, 4 frames each) instead of colored circles
- [ ] **SPRT-02**: User sees agents face their movement direction as they walk
- [ ] **SPRT-03**: User sees agents stop in an idle pose when they reach their destination
- [ ] **SPRT-04**: User sees agent portraits (32x32 thumbnails) in the agent inspector sidebar
- [ ] **SPRT-05**: User sees pixel-art styled speech/activity bubbles above agents

### Town Design

- [ ] **TOWN-01**: User sees an Agent Town-specific map designed in Tiled with thematic buildings (stock exchange, wedding hall, cafe, park, homes, office, shop)
- [ ] **TOWN-02**: Backend town.json is regenerated from the Tiled map export preserving sector/arena coordinate structure
- [ ] **TOWN-03**: Agent collision detection uses the Tiled collision layer instead of hardcoded collision data

### UI Polish

- [ ] **UIPOL-01**: User sees sidebar and control colors harmonized with the pixel-art map aesthetic
- [ ] **UIPOL-02**: User sees pixel-art typography for map labels and key UI elements
- [ ] **UIPOL-03**: User sees a loading overlay with progress indication while assets load at startup

### Asset Pipeline

- [ ] **PIPE-01**: CuteRPG tilesets and agent sprite sheets are ported from reference repo into frontend assets
- [ ] **PIPE-02**: Reference sprite atlas (Phaser format) is converted to PixiJS-compatible format
- [ ] **PIPE-03**: PixiJS initializes with scaleMode nearest to preserve pixel-art crispness

## v1.3 Requirements

Deferred to next milestone (Agent Behavior). Tracked but not in current roadmap.

### Task System

- [ ] **TSK-01**: Tasks have state tracking (queued, active, interrupted, completed)
- [ ] **TSK-02**: Tasks can be interrupted by conversations and resumed afterward
- [ ] **TSK-03**: Agent's current task state is visible in the inspector panel

### Perception System

- [ ] **PCPT-01**: Agents track what changed since their last perception scan (new events, new nearby agents)
- [ ] **PCPT-02**: Agents react to changes rather than re-scanning the same static scene every tick

### Reflection

- [ ] **RFL-01**: Agents accumulate poignancy from perceived events and conversations
- [ ] **RFL-02**: When poignancy crosses threshold, agent generates higher-level insight memories
- [ ] **RFL-03**: Reflection runs as background asyncio task, never blocking the agent step

### Relationship System

- [ ] **REL-01**: Agents track relationships with other agents (familiarity, sentiment, last interaction)
- [ ] **REL-02**: Relationship history affects conversation initiation and content
- [ ] **REL-03**: Relationships are viewable in the agent inspector panel

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Event Injection (v2)

- **EVT-05**: Event injection history log with timestamps
- **EVT-06**: Pre-built event templates users can click (stock crash, festival, election, etc.)

### Simulation Control (v2)

- **SIM-04**: Simulation speed control (slow down or speed up)
- **SIM-05**: User chooses how many agents to spawn (5-25)

### Configuration (v2)

- **CFG-03**: Cost estimation displays approximate token usage and cost per simulation step
- **CFG-04**: Model routing per call type (cheap model for routine, expensive for complex)

### Persistence (v2)

- **PER-01**: Save full simulation state (agents, memories, positions, conversations)
- **PER-02**: Load a previously saved simulation
- **PER-03**: Auto-save periodic checkpoints

### Display (v2)

- **DSP-03**: Visible thought stream for inspected agent (internal monologue)
- **DSP-05**: Memory timeline visualization
- **DSP-06**: Relationship graph between agents

## Out of Scope

| Feature | Reason |
|---------|--------|
| Mobile app | Web-first; responsive design later |
| Multiplayer / shared towns | Single-user for v1; architecture should not block it |
| User-created custom maps | Ship one good map; extensibility later |
| Voice or audio | Text-only interactions |
| Hosted LLM | Users bring their own API keys |
| User-as-agent embodiment | Muddies the observer role |
| LLM streaming for all agents | Overwhelming; activity feed is sufficient |
| Custom agent creation | Pre-defined cast for v1 |
| Agent subclassing / polymorphism | OOP is for structural clarity; all agents run same code with personality from LLM prompts |
| Zoom & pan controls | Fixed viewport sufficient for v1.2; pixi-viewport deferred |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

### v1.0 (Complete)

| Requirement | Phase | Status |
|-------------|-------|--------|
| INF-01 | Phase 1 | Complete |
| INF-02 | Phase 1 | Complete |
| INF-03 | Phase 1 | Complete |
| CFG-01 | Phase 1 | Complete |
| CFG-02 | Phase 1 | Complete |
| MAP-03 | Phase 2 | Complete |
| MAP-04 | Phase 2 | Complete |
| AGT-01 | Phase 2 | Complete |
| AGT-02 | Phase 3 | Complete |
| AGT-03 | Phase 3 | Complete |
| AGT-04 | Phase 3 | Complete |
| AGT-05 | Phase 3 | Complete |
| AGT-06 | Phase 3 | Complete |
| AGT-07 | Phase 3 | Complete |
| AGT-08 | Phase 3 | Complete |
| SIM-01 | Phase 4 | Complete |
| SIM-02 | Phase 4 | Complete |
| SIM-03 | Phase 4 | Complete |
| MAP-01 | Phase 5 | Complete |
| MAP-02 | Phase 5 | Complete |
| MAP-05 | Phase 5 | Complete |
| DSP-01 | Phase 5 | Complete |
| DSP-02 | Phase 5 | Complete |
| EVT-01 | Phase 6 | Complete |
| EVT-02 | Phase 6 | Complete |
| EVT-03 | Phase 6 | Complete |
| EVT-04 | Phase 6 | Complete |

### v1.1 (Complete)

| Requirement | Phase | Status |
|-------------|-------|--------|
| ARCH-01 | Phase 7 | Complete |
| ARCH-02 | Phase 9.1 | Complete |
| ARCH-03 | Phase 7 | Complete |
| BLD-01 | Phase 7 | Complete |
| EVTS-01 | Phase 9.1 | Complete |
| EVTS-02 | Phase 9.1 | Complete |
| EVTS-03 | Phase 9.1 | Complete |
| BLD-02 | Phase 8 | Complete |
| BLD-03 | Phase 8 | Complete |
| VIS-01 | Phase 8 | Complete |
| VIS-02 | Phase 9.2 | Complete |
| LLM-01 | Phase 9 | Complete |
| LLM-02 | Phase 9 | Complete |
| LLM-03 | Phase 9 | Complete |
| LLM-04 | Phase 9 | Complete |

### v1.2 (Active)

| Requirement | Phase | Status |
|-------------|-------|--------|
| PIPE-01 | Phase 10 | Pending |
| PIPE-02 | Phase 10 | Pending |
| PIPE-03 | Phase 10 | Pending |
| TOWN-01 | Phase 11 | Pending |
| TOWN-02 | Phase 11 | Pending |
| TOWN-03 | Phase 11 | Pending |
| TILE-01 | Phase 12 | Pending |
| TILE-02 | Phase 12 | Pending |
| TILE-03 | Phase 12 | Pending |
| TILE-04 | Phase 12 | Pending |
| SPRT-01 | Phase 13 | Pending |
| SPRT-02 | Phase 13 | Pending |
| SPRT-03 | Phase 13 | Pending |
| SPRT-04 | Phase 13 | Pending |
| SPRT-05 | Phase 13 | Pending |
| UIPOL-01 | Phase 14 | Pending |
| UIPOL-02 | Phase 14 | Pending |
| UIPOL-03 | Phase 14 | Pending |

**Coverage (v1.2):**
- v1.2 requirements: 18 total (note: original count of 16 excluded TILE-04/UIPOL-03 loading screen split)
- Mapped to phases: 18
- Unmapped: 0

---
*Requirements defined: 2026-04-08*
*Last updated: 2026-04-11 after v1.2 roadmap created*
