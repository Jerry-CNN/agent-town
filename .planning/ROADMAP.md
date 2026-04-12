# Roadmap: Agent Town

**Created:** 2026-04-08
**Updated:** 2026-04-12 (v1.1 shipped)
**Granularity:** Standard

---

## Milestones

- v1.0 Core - Phases 1-6 (shipped 2026-04-10)
- v1.1 Architecture & Polish - Phases 7-9.2 (shipped 2026-04-12)
- v1.2 Agent Behavior - Phases 10-12 (planned)

---

## Phases

<details>
<summary>v1.0 Core (Phases 1-6) - SHIPPED 2026-04-10</summary>

- [x] **Phase 1: Foundation** - Project scaffold, async infrastructure, LLM gateway, structured output, and configuration UI
- [x] **Phase 2: World & Navigation** - Tile map data model, BFS pathfinding, agent data structures, and thematic town layout
- [x] **Phase 3: Agent Cognition** - Memory stream, daily planning, perception, LLM decisions, and agent-to-agent conversations
- [x] **Phase 4: Simulation Engine & Transport** - Real-time async simulation loop, WebSocket push, and pause/resume control
- [x] **Phase 5: Frontend** - React/PixiJS map rendering, agent sprites, activity feed, agent inspection panel
- [x] **Phase 6: Event Injection** - Event UI, broadcast mode, whisper mode, and organic gossip spreading

Full details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>v1.1 Architecture & Polish (Phases 7-9.2) - SHIPPED 2026-04-12</summary>

- [x] **Phase 7: OOP Foundation** - Agent/Building/Event classes, schema split, SimulationEngine migration (2/2 plans)
- [x] **Phase 8: Visual & Building Behavior** - Wall outlines, operating hours, readable text (2/2 plans)
- [x] **Phase 9: LLM Optimization** - 2-level cascade, adaptive tick, repetition detection, semaphore (3/3 plans)
- [x] **Phase 9.1: Backend Runtime Wiring** - Event lifecycle + Agent wrappers wired into runtime (1/1 plan, gap closure)
- [x] **Phase 9.2: Visual Text Restoration** - Activity text restored, WCAG AA contrast (1/1 plan, gap closure)

Full details: `.planning/milestones/v1.1-ROADMAP.md`

</details>

---

### v1.2 Agent Behavior (Planned)

**Milestone Goal:** Add reflection, relationship tracking, task state machines, and perception diffing to create deeper agent behavior.

- [ ] **Phase 10: Task & Perception Systems** - Task state machine with interrupt/resume; perception diff so agents react to changes not static scenes
- [ ] **Phase 11: Reflection System** - Poignancy accumulation, threshold-triggered insight generation as background asyncio tasks
- [ ] **Phase 12: Relationship Tracking** - Agent-to-agent relationship state (familiarity, sentiment, last interaction) visible in inspector

---

## Phase Details

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

### v1.2 Agent Behavior (planned)

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|-----------------|
| 10 | Task & Perception Systems | Task state machine, interrupt/resume, perception diff | TSK-01, TSK-02, TSK-03, PCPT-01, PCPT-02 | 4 |
| 11 | Reflection System | Poignancy accumulation, threshold-triggered thought memories, background task | RFL-01, RFL-02, RFL-03 | 4 |
| 12 | Relationship Tracking | Per-pair relationship state, initiation weighting, inspector display | REL-01, REL-02, REL-03 | 3 |

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 3/3 | Complete | 2026-04-10 |
| 2. World & Navigation | v1.0 | 3/3 | Complete | 2026-04-10 |
| 3. Agent Cognition | v1.0 | 3/3 | Complete | 2026-04-10 |
| 4. Simulation Engine & Transport | v1.0 | 2/2 | Complete | 2026-04-10 |
| 5. Frontend | v1.0 | 4/4 | Complete | 2026-04-10 |
| 6. Event Injection | v1.0 | 2/2 | Complete | 2026-04-10 |
| 7. OOP Foundation | v1.1 | 2/2 | Complete | 2026-04-11 |
| 8. Visual & Building Behavior | v1.1 | 2/2 | Complete | 2026-04-11 |
| 9. LLM Optimization | v1.1 | 3/3 | Complete | 2026-04-11 |
| 9.1 Backend Runtime Wiring | v1.1 | 1/1 | Complete | 2026-04-12 |
| 9.2 Visual Text Restoration | v1.1 | 1/1 | Complete | 2026-04-12 |
| 10. Task & Perception Systems | v1.2 | 0/? | Not started | - |
| 11. Reflection System | v1.2 | 0/? | Not started | - |
| 12. Relationship Tracking | v1.2 | 0/? | Not started | - |
