# Agent Town

## What This Is

A web-based generative agents playground where users watch AI-powered characters live their daily lives in a 2D tile-map town. Users inject events — "a stock is going up," "there's a wedding tomorrow" — and watch agents react in real-time: heading to the trading hall, getting dressed for the ceremony, gossiping about the news. Built as an interactive reimplementation of the Generative Agents paper (reference: `~/projects/GenerativeAgentsCN/`), designed for the browser.

## Core Value

Users can type any event and immediately see AI agents respond to it in a living, breathing town — the magic is watching emergent behavior unfold.

## Current Milestone: v1.1 Architecture & Polish

**Goal:** Refactor the codebase to proper OOP abstractions, fix the visual experience, and bring agent behavior closer to the reference implementation.

**Target features:**
- Backend OOP refactoring — Agent class, Building/Location class, Event class with proper lifecycle
- UI/visual overhaul — building walls, readable text, map looks like an actual town
- LLM call optimization — 3-level decisions, conversation gating, smarter tick timing
- Agent behavior fidelity — reflection system, relationship tracking, reference repo parity

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

### Active

- [ ] Backend refactored to OOP: Agent class (config + state + cognition methods), Building class (walls, properties), Event class (lifecycle, propagation)
- [ ] Buildings have visible walls on the map; agents cannot walk through them
- [ ] Text labels (agent names, activities, sector names) are readable at default zoom
- [ ] LLM decisions use 3-level resolution (sector → arena → object) matching reference repo
- [ ] Conversation gating: LLM check before initiating conversations
- [ ] Conversation termination: agents detect repetition and end conversations early
- [ ] Reflection system: agents form higher-level insights when poignancy threshold is crossed
- [ ] Tick timing optimized for faster agent responsiveness

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
| Python backend + React frontend | Python preserves agent logic from reference repo; React handles interactive 2D rendering | -- Pending |
| WebSocket for real-time updates | Agents act asynchronously; push updates to browser as they happen | -- Pending |
| User-provided LLM keys | Avoids hosting costs; lets users pick their preferred provider | -- Pending |
| Custom town map (not reuse the Ville) | Town locations should match the use cases (stock exchange, wedding hall, etc.) | -- Pending |
| Broadcast + whisper event modes | Gives users control over how information spreads through the simulation | -- Pending |

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
*Last updated: 2026-04-10 after milestone v1.1 started*
