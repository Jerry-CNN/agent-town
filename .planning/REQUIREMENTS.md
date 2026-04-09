# Requirements: Agent Town

**Defined:** 2026-04-08
**Core Value:** Users can type any event and immediately see AI agents respond to it in a living, breathing town

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### World & Map

- [ ] **MAP-01**: 2D tile-map town rendered in the browser with top-down view
- [ ] **MAP-02**: Agent sprites visible on the map, moving between tiles in real-time
- [ ] **MAP-03**: Custom town with thematic locations (stock exchange, wedding hall, park, homes, shops, cafe, office)
- [ ] **MAP-04**: BFS pathfinding so agents navigate around obstacles to reach destinations
- [ ] **MAP-05**: User can click an agent on the map to inspect their current activity, personality, and recent memories

### Agent Cognition

- [ ] **AGT-01**: Each agent has a distinct personality (name, traits, occupation, daily routine)
- [ ] **AGT-02**: Agents autonomously plan daily schedules and decompose into sub-tasks
- [ ] **AGT-03**: Agents perceive nearby events and other agents within a vision radius
- [ ] **AGT-04**: Agents make LLM-powered decisions about what to do next based on perceptions and plans
- [ ] **AGT-05**: Memory stream stores experiences weighted by recency, relevance, and importance
- [ ] **AGT-06**: Agents retrieve relevant memories when making decisions (composite scoring retrieval)
- [ ] **AGT-07**: Agents initiate multi-turn conversations with nearby agents based on context
- [ ] **AGT-08**: Conversations affect agent schedules (agents revise plans after chatting)

### Event Injection

- [ ] **EVT-01**: User can type a free-text event and submit it to the simulation
- [ ] **EVT-02**: Broadcast mode delivers the event to all agents instantly
- [ ] **EVT-03**: Whisper mode delivers the event to one specific agent
- [ ] **EVT-04**: Whispered events spread organically through agent-to-agent conversations

### Simulation Control

- [ ] **SIM-01**: Simulation runs in real-time with agents acting every few seconds
- [ ] **SIM-02**: Real-time updates pushed to browser via WebSocket
- [ ] **SIM-03**: User can pause and resume the simulation

### Configuration

- [ ] **CFG-01**: User configures their LLM provider (OpenAI, Anthropic, OpenRouter, Ollama, etc.)
- [ ] **CFG-02**: User provides their own API key for the selected provider
- [ ] **CFG-03**: Cost estimation displays approximate token usage and cost per simulation step

### Display

- [ ] **DSP-01**: Activity feed showing real-time agent actions and conversations as a scrolling log
- [ ] **DSP-02**: Agent labels on the map showing name and current activity above each sprite

### Infrastructure

- [ ] **INF-01**: Fresh simulation starts by default on each visit
- [ ] **INF-02**: All agent processing is async/concurrent (not sequential) for real-time performance
- [ ] **INF-03**: Structured LLM output via Pydantic schemas with retry and fallback on parse failure

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Agent Cognition (v2)

- **AGT-09**: Reflection system where agents form higher-level insights from accumulated memories
- **AGT-10**: Agents maintain and update relationship models of other agents

### Event Injection (v2)

- **EVT-05**: Event injection history log with timestamps
- **EVT-06**: Pre-built event templates users can click (stock crash, festival, election, etc.)

### Simulation Control (v2)

- **SIM-04**: Simulation speed control (slow down or speed up)
- **SIM-05**: User chooses how many agents to spawn (5-25)

### Configuration (v2)

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
| User-as-agent embodiment | Muddies the observer role; HN feedback confirms this |
| LLM streaming for all agents | Overwhelming; activity feed is sufficient |
| Custom agent creation | Pre-defined cast for v1 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| MAP-01 | Phase 5 | Pending |
| MAP-02 | Phase 5 | Pending |
| MAP-03 | Phase 2 | Pending |
| MAP-04 | Phase 2 | Pending |
| MAP-05 | Phase 5 | Pending |
| AGT-01 | Phase 2 | Pending |
| AGT-02 | Phase 3 | Pending |
| AGT-03 | Phase 3 | Pending |
| AGT-04 | Phase 3 | Pending |
| AGT-05 | Phase 3 | Pending |
| AGT-06 | Phase 3 | Pending |
| AGT-07 | Phase 3 | Pending |
| AGT-08 | Phase 3 | Pending |
| EVT-01 | Phase 6 | Pending |
| EVT-02 | Phase 6 | Pending |
| EVT-03 | Phase 6 | Pending |
| EVT-04 | Phase 6 | Pending |
| SIM-01 | Phase 4 | Pending |
| SIM-02 | Phase 4 | Pending |
| SIM-03 | Phase 4 | Pending |
| CFG-01 | Phase 1 | Pending |
| CFG-02 | Phase 1 | Pending |
| CFG-03 | Phase 1 | Pending |
| DSP-01 | Phase 5 | Pending |
| DSP-02 | Phase 5 | Pending |
| INF-01 | Phase 1 | Pending |
| INF-02 | Phase 1 | Pending |
| INF-03 | Phase 1 | Pending |

**Coverage:**
- v1 requirements: 28 total
- Mapped to phases: 28
- Unmapped: 0

---
*Requirements defined: 2026-04-08*
*Last updated: 2026-04-08 after roadmap creation*
