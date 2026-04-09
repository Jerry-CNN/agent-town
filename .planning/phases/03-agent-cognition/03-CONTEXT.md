# Phase 3: Agent Cognition - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Agents autonomously plan daily schedules, perceive their environment within a tile-based vision radius, store and retrieve weighted memories via ChromaDB, make LLM-powered decisions about actions, and hold multi-turn conversations that revise their plans. No simulation loop (Phase 4), no rendering (Phase 5), no event injection (Phase 6).

</domain>

<decisions>
## Implementation Decisions

### Memory System
- **D-01:** ChromaDB for vector storage. One collection per simulation. Memories stored with metadata: agent_id, timestamp, importance score (1-10), memory type (observation/conversation/action/event).
- **D-02:** Retrieval scoring uses the reference paper's composite formula: recency x 0.5 + relevance x 3 + importance x 2. Relevance comes from ChromaDB vector similarity, recency is exponential decay from timestamp, importance is stored metadata.
- **D-03:** Importance scores assigned by LLM — each memory gets a 1-10 importance rating via an LLM call at storage time. Costs 1 extra call per memory but enables the full composite scoring.
- **D-04:** "Everything significant" gets stored: observations (saw another agent doing something), conversations (full dialogue), actions taken, events perceived. Broad capture; retrieval handles relevance filtering.
- **D-05:** Retrieval returns top 5-10 memories per decision query, ranked by composite score. Enough context for the LLM without overwhelming the prompt.

### Perception Model
- **D-06:** Tile-based vision radius (~5 tiles, Manhattan or Euclidean distance). Agent perceives everything within N tiles of their position. Simple, predictable, works with the 100x100 grid.
- **D-07:** Agents perceive: other agents (name, current activity), injected events within radius, and location context (what sector/arena they're in). Full awareness matching the reference.

### Schedule & Planning
- **D-08:** Two-level schedule: LLM generates hourly blocks ("8am: open cafe"), then decomposes each hour into 5-15 minute sub-tasks. 2 LLM calls per full schedule generation.
- **D-09:** Hybrid daily routines from Phase 2 (D-10): config provides a rough template, LLM expands into the full hourly+sub-task schedule at simulation start.
- **D-10:** Replanning triggers after conversations and significant events. When an agent finishes a conversation or perceives a notable event, an LLM call revises their remaining daily plan. This satisfies AGT-08.

### Conversation System
- **D-11:** Conversation trigger: proximity + LLM check. When two agents are within perception radius, an LLM call decides whether they'd talk based on personalities, current activities, and context. Most natural approach.
- **D-12:** Conversations last 2-4 turns with natural ending. LLM decides when to end, capped at ~4 turns. Each turn = 1 LLM call per agent. Natural but bounded cost.
- **D-13:** After conversation ends, each agent gets an LLM call to revise their remaining daily schedule based on what was discussed. E.g., "Heard about the wedding -> visit wedding hall this afternoon."

### Claude's Discretion
- Embedding model choice for ChromaDB (default all-MiniLM-L6-v2 is likely fine)
- Exact perception radius value (reference uses ~5 tiles — adjust for 100x100 map feel)
- Conversation initiation cooldown to prevent chat spam
- Prompt templates for each cognition call type (schedule generation, perception reaction, memory importance, conversation, schedule revision)
- How to structure the "decision" LLM call that picks an agent's next action (AGT-04)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Reference implementation
- `~/projects/GenerativeAgentsCN/generative_agents/modules/agent.py` -- Agent class: schedule planning, perception, decision-making, conversation logic
- `~/projects/GenerativeAgentsCN/generative_agents/modules/memory.py` -- Memory stream: storage, retrieval with composite scoring, importance rating
- `~/projects/GenerativeAgentsCN/generative_agents/modules/converse.py` -- Conversation system: initiation check, multi-turn dialogue, schedule revision after chat
- `~/projects/GenerativeAgentsCN/generative_agents/modules/plan.py` -- Daily schedule generation, hourly decomposition, sub-task planning
- `~/projects/GenerativeAgentsCN/generative_agents/modules/perceive.py` -- Perception radius, event collection, nearby agent detection

### Existing codebase (Phase 1 + Phase 2 outputs)
- `backend/gateway.py` -- `complete_structured()` is the single LLM integration point for all cognition calls
- `backend/schemas.py` -- `AgentConfig`, `AgentScratch`, `AgentSpatial`, `AgentAction` models to extend
- `backend/simulation/world.py` -- `Maze` class for pathfinding and tile queries, `Tile` for spatial context
- `backend/agents/loader.py` -- `load_all_agents()` returns typed agent configs with personality data
- `backend/data/agents/*.json` -- Agent personality configs with `scratch.daily_plan` templates and `spatial.tree`

### Project research
- `.planning/research/STACK.md` -- ChromaDB, sentence-transformers, instructor decisions
- `.planning/research/ARCHITECTURE.md` -- System architecture, component boundaries
- `.planning/research/PITFALLS.md` -- Async/sync mismatch, JSON parsing fragility

### Prior phase context
- `.planning/phases/01-foundation/01-CONTEXT.md` -- LLM providers, structured output patterns
- `.planning/phases/02-world-navigation/02-CONTEXT.md` -- Map model, agent data structures, address hierarchy

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `complete_structured(messages, response_model)` -- Generic async LLM call with retry/fallback. All cognition calls go through this.
- `AgentConfig` / `AgentScratch` -- Personality data (innate traits, daily_plan template, learned background) ready for prompt injection
- `AgentSpatial.tree` -- Agent's spatial knowledge of known locations, useful for schedule planning
- `Maze.resolve_destination(sector)` -- Resolves location names to walkable tile coords for agent navigation
- `Maze.tile_at(coord)` -- Gets tile info at a position for perception context

### Established Patterns
- Pydantic v2 models for all data structures -- extend `schemas.py` with new cognition models (ScheduleEntry, Memory, Conversation, etc.)
- Async-first architecture (FastAPI + asyncio) -- all cognition calls must be async
- `instructor.from_litellm()` for structured LLM output -- use for schedule generation, decision-making, importance scoring

### Integration Points
- Agent cognition module will be called by Phase 4's simulation loop every tick
- Memory system (ChromaDB) is a standalone service initialized at simulation start
- Conversation results feed into the activity feed (Phase 5) and event propagation (Phase 6)

</code_context>

<specifics>
## Specific Ideas

- The reference implementation's memory stream with triple-weighted retrieval is proven and should be followed closely
- Schedule revision after conversations is the key mechanism for emergent behavior (AGT-08) -- this is what makes the gossip system work in Phase 6
- LLM calls are the bottleneck -- design the prompt templates to work well with cheap models (Llama 3.1 8B via Ollama)

</specifics>

<deferred>
## Deferred Ideas

- Reflection system (AGT-09) -- agents form higher-level insights from accumulated memories. Deferred to v2.
- Relationship models (AGT-10) -- agents track and update mental models of other agents. Deferred to v2.
- Poignancy threshold for triggering reflection -- not needed without reflection system.

</deferred>

---

*Phase: 03-agent-cognition*
*Context gathered: 2026-04-09*
