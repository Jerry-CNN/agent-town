# Agent Town

## What This Is

A web-based generative agents playground where users watch AI-powered characters live their daily lives in a 2D tile-map town. Users inject events — "a stock is going up," "there's a wedding tomorrow" — and watch agents react in real-time: heading to the trading hall, getting dressed for the ceremony, gossiping about the news. Built as an interactive reimplementation of the Generative Agents paper (reference: `~/projects/GenerativeAgentsCN/`), designed for the browser.

## Core Value

Users can type any event and immediately see AI agents respond to it in a living, breathing town — the magic is watching emergent behavior unfold.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] 2D tile-map town rendered in the browser with agents visible as sprites
- [ ] Agents autonomously plan daily schedules, move between locations, and perform activities
- [ ] Agents perceive nearby events and other agents, make LLM-powered decisions
- [ ] Memory system: agents remember experiences with recency/relevance/importance weighting
- [ ] Agents initiate conversations with each other based on proximity and context
- [ ] Reflection system: agents form higher-level insights from accumulated memories
- [ ] User can type a text event and choose delivery mode (broadcast to all OR whisper to one agent)
- [ ] Broadcast events are perceived by all agents instantly
- [ ] Whispered events spread organically through agent-to-agent conversations
- [ ] Simulation runs in real-time with agents acting every few seconds
- [ ] Custom town map with thematic locations (stock exchange, wedding hall, park, homes, shops, etc.)
- [ ] User configures their own LLM provider and API key (OpenAI, OpenRouter, Anthropic, Ollama, etc.)
- [ ] User chooses how many agents to spawn when starting a simulation
- [ ] Fresh simulation by default; optional save/load for persistence across sessions
- [ ] Real-time feed showing agent actions, conversations, and internal thoughts
- [ ] Single-user per simulation instance (architecture supports future multiplayer)

### Out of Scope

- Mobile app — web-first, responsive later
- Multiplayer / shared towns — single-user for v1, but architecture should not block it
- User-created custom maps — ship one good map, extensibility later
- Voice or audio — text-only interactions
- Hosted LLM — users bring their own API keys

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
*Last updated: 2026-04-08 after initialization*
