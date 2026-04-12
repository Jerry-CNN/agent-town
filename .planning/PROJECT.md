# Agent Town

## What This Is

A web-based generative agents playground where users watch AI-powered characters live their daily lives in a 2D tile-map town. Users inject events — "a stock is going up," "there's a wedding tomorrow" — and watch agents react in real-time: heading to the trading hall, getting dressed for the ceremony, gossiping about the news. Built as an interactive reimplementation of the Generative Agents paper (reference: `~/projects/GenerativeAgentsCN/`), designed for the browser.

## Core Value

Users can type any event and immediately see AI agents respond to it in a living, breathing town — the magic is watching emergent behavior unfold.

## Current State

**Shipped:** v1.0 Core (2026-04-10), v1.1 Architecture & Polish (2026-04-12)

v1.1 delivered OOP refactoring (Agent/Building/Event classes), building walls with operating hours, 2-level LLM decision cascade with adaptive tick, conversation repetition detection, semaphore concurrency, and activity text restoration with contrast compliance.

**Next milestone:** v1.2 Agent Behavior — reflection system, relationship tracking, task state machine, perception diffing

## Requirements

### Validated

- [x] Custom town map with thematic locations (stock exchange, wedding hall, park, homes, shops, etc.) — Validated in Phase 2: World & Navigation
- [x] Agents have distinct personality traits, occupations, and daily routine templates — Validated in Phase 2: World & Navigation
- [x] Agents autonomously plan daily schedules and decompose into sub-tasks — Validated in Phase 3: Agent Cognition
- [x] Agents perceive nearby events and other agents within a vision radius — Validated in Phase 3: Agent Cognition
- [x] Agents make LLM-powered decisions about what to do next based on perceptions and plans — Validated in Phase 3: Agent Cognition
- [x] Memory system: agents remember experiences with recency/relevance/importance weighting — Validated in Phase 3: Agent Cognition
- [x] Agents retrieve relevant memories when making decisions (composite scoring retrieval) — Validated in Phase 3: Agent Cognition
- [x] Agents initiate multi-turn conversations with nearby agents based on context — Validated in Phase 3: Agent Cognition
- [x] Conversations affect agent schedules (agents revise plans after chatting) — Validated in Phase 3: Agent Cognition
- [x] 2D tile-map town rendered in the browser with agents visible as sprites — Validated in v1.0
- [x] User can type a text event and choose delivery mode (broadcast/whisper) — Validated in v1.0
- [x] Broadcast events perceived by all agents instantly — Validated in v1.0
- [x] Whispered events spread organically through agent-to-agent conversations — Validated in v1.0
- [x] Simulation runs in real-time with agents acting every few seconds — Validated in v1.0
- [x] User configures their own LLM provider and API key — Validated in v1.0
- [x] Fresh simulation by default — Validated in v1.0
- [x] Real-time feed showing agent actions and conversations — Validated in v1.0
- [x] Backend refactored to OOP: Agent/Building/Event classes with unified domain model — Validated in v1.1
- [x] Buildings have visible walls on the map with collision; operating hours enforced — Validated in v1.1
- [x] Text labels (agent names, activities) readable at default zoom with WCAG AA contrast — Validated in v1.1
- [x] 2-level LLM decision cascade (sector -> arena) with per-sector gating — Validated in v1.1
- [x] Conversation repetition detection and early termination — Validated in v1.1
- [x] Adaptive tick interval (10s) for faster agent responsiveness — Validated in v1.1
- [x] Semaphore-bounded concurrent LLM calls — Validated in v1.1
- [x] Event lifecycle wired into runtime (creation, propagation tracking, expiry) — Validated in v1.1

### Active

- [ ] Reflection system: agents form higher-level insights when poignancy threshold is crossed
- [ ] Relationship tracking: per-pair familiarity, sentiment, last interaction
- [ ] Task state machine: queued/active/interrupted/completed with interrupt/resume
- [ ] Perception diffing: agents react to changes, not static scenes

### Out of Scope

- Mobile app — web-first, responsive later
- Multiplayer / shared towns — single-user for v1, but architecture should not block it
- User-created custom maps — ship one good map, extensibility later
- Voice or audio — text-only interactions
- Hosted LLM — users bring their own API keys
- Agent subclassing / polymorphism — OOP is for structural clarity; all agents run same code paths with personality from LLM prompts

## Context

**Reference implementation:** `~/projects/GenerativeAgentsCN/` — a Python-based simulation using LlamaIndex for memory, BFS pathfinding on a tile grid, and structured LLM prompts for agent cognition. Runs as a batch simulation with post-hoc replay visualization.

**Key differences from reference:**
- Real-time web experience vs. batch simulation
- User-injected events vs. pre-scripted scenarios
- Custom town map vs. "the Ville"
- Configurable LLM provider vs. hardcoded Ollama/OpenAI
- Browser-rendered 2D map vs. offline replay

**Agent architecture (from reference, to adapt):**
- Memory stream with triple-weighted retrieval (recency × 0.5, relevance × 3, importance × 2)
- Daily schedule → hourly plans → 5-minute decomposed tasks
- Perception radius on tile grid → event collection → reaction decision
- Chat system: initiation check → multi-turn conversation → schedule revision
- Reflection triggered by accumulated emotional weight (poignancy threshold)
- Each simulation step = 5-20 LLM calls per agent

**Tech stack direction:** Python backend (FastAPI — preserves agent logic closest to reference) + React frontend (interactive 2D map with real-time updates via WebSocket). Vector store for agent memory (lightweight, per-simulation instance).

## Constraints

- **LLM Cost**: Each agent makes 5-20 LLM calls per step — design must support cheap models (GPT-4o-mini, Haiku) for routine calls and reserve expensive models for complex reasoning
- **Real-time UX**: Agents must appear to act fluidly — backend processes asynchronously, frontend interpolates movement
- **Single-user architecture**: No shared state between sessions, but avoid designs that would prevent future multiplayer
- **Browser rendering**: 2D tile map must run smoothly with 5-25 agents on a standard laptop

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python backend + React frontend | Python preserves agent logic from reference repo; React handles interactive 2D rendering | Good |
| WebSocket for real-time updates | Agents act asynchronously; push updates to browser as they happen | Good |
| User-provided LLM keys | Avoids hosting costs; lets users pick their preferred provider | Good |
| Custom town map (not reuse the Ville) | Town locations should match the use cases (stock exchange, wedding hall, etc.) | Good |
| Broadcast + whisper event modes | Gives users control over how information spreads through the simulation | Good |
| GPT-4o-mini as default model | Kimi K2.5 too slow; GPT-4o-mini is 1-2s with reliable JSON | Good (v1.1) |
| 2-level cascade instead of 3-level | Sector -> arena sufficient; object-level adds cost without UX benefit | Good (v1.1) |
| OpenRouter as default provider | Ollama unreliable with 8 agents; OpenRouter provides consistent cloud inference | Good (v1.1) |
| heard_by whisper-only (D-09) | Broadcasts don't need propagation tracking; keeps heard_by meaningful | Good (v1.1) |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-12 after v1.1 milestone shipped*
