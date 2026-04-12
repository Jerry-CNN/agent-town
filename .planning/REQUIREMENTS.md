# Requirements: Agent Town

**Defined:** 2026-04-08
**Updated:** 2026-04-10 (v1.1 milestone)
**Core Value:** Users can type any event and immediately see AI agents respond to it in a living, breathing town

## v1.0 Requirements (Completed)

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

## v1.1 Requirements

Requirements for v1.1 milestone: Architecture & Polish.

### Agent Abstraction

- [ ] **ARCH-01**: Agent class unifies AgentConfig + AgentState into a single object with identity, runtime state, and system fields (relationships, perception state, poignancy, task queue)
- [ ] **ARCH-02**: Agent class has cognition methods (perceive, decide, converse, reflect) that delegate to existing functions
- [ ] **ARCH-03**: SimulationEngine uses Agent objects instead of separate config/state dicts

### Building System

- [ ] **BLD-01**: Building class with properties (name, operating hours, purpose tag)
- [ ] **BLD-02**: Buildings have wall tiles marked as collision so agents cannot walk through them
- [ ] **BLD-03**: Agents respect building operating hours when choosing destinations (closed buildings excluded from LLM context; agent re-decides from open options)

### Event System

- [ ] **EVTS-01**: Event class tracks lifecycle (created, active, spreading, expired)
- [ ] **EVTS-02**: Events track propagation — which agents heard the event and when
- [ ] **EVTS-03**: Events expire after a configurable duration

### Visual

- [ ] **VIS-01**: Building walls are rendered as visible outlines on the map
- [ ] **VIS-02**: Agent name and activity text is readable at default zoom level

### LLM Optimization

- [ ] **LLM-01**: Agent decisions use 3-level resolution (sector -> arena -> object) with per-sector gating
- [ ] **LLM-02**: Tick interval reduced from 30s to 10s for more responsive agents
- [ ] **LLM-03**: Conversations detect repetition and terminate early instead of fixed turn count
- [ ] **LLM-04**: asyncio.Semaphore controls concurrent LLM calls to prevent rate limits

## v1.2 Requirements

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
- [ ] **RFL-02**: When poignancy crosses threshold, agent generates higher-level insight memories ("thoughts")
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
- **DSP-04**: Conversation speech bubbles on the map
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

### v1.1 (In Progress)

| Requirement | Phase | Status |
|-------------|-------|--------|
| ARCH-01 | Phase 7 | Pending |
| ARCH-02 | Phase 9.1 | Pending |
| ARCH-03 | Phase 7 | Pending |
| BLD-01 | Phase 7 | Pending |
| EVTS-01 | Phase 9.1 | Pending |
| EVTS-02 | Phase 9.1 | Pending |
| EVTS-03 | Phase 9.1 | Pending |
| BLD-02 | Phase 8 | Pending |
| BLD-03 | Phase 8 | Pending |
| VIS-01 | Phase 8 | Pending |
| VIS-02 | Phase 9.2 | Pending |
| LLM-01 | Phase 9 | Pending |
| LLM-02 | Phase 9 | Pending |
| LLM-03 | Phase 9 | Pending |
| LLM-04 | Phase 9 | Pending |

**Coverage (v1.1):**
- v1.1 requirements: 15 total
- Mapped to phases: 15
- Unmapped: 0

### v1.2 (Planned)

| Requirement | Phase | Status |
|-------------|-------|--------|
| TSK-01 | Phase 10 | Pending |
| TSK-02 | Phase 10 | Pending |
| TSK-03 | Phase 10 | Pending |
| PCPT-01 | Phase 10 | Pending |
| PCPT-02 | Phase 10 | Pending |
| RFL-01 | Phase 11 | Pending |
| RFL-02 | Phase 11 | Pending |
| RFL-03 | Phase 11 | Pending |
| REL-01 | Phase 12 | Pending |
| REL-02 | Phase 12 | Pending |
| REL-03 | Phase 12 | Pending |

**Coverage (v1.2):**
- v1.2 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0

---
*Requirements defined: 2026-04-08*
*Last updated: 2026-04-10 after v1.1/v1.2 milestone split (Codex review)*
