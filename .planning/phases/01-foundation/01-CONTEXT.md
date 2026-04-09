# Phase 1: Foundation - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Project scaffold with async infrastructure, LLM gateway (Ollama-only for v1), structured Pydantic output with retry/fallback, and the app shell layout. This phase delivers a running FastAPI server, a React frontend shell with the map-dominant layout, and verified async concurrency.

</domain>

<decisions>
## Implementation Decisions

### LLM Provider
- **D-01:** v1 supports two providers: Ollama (local, free) and OpenRouter (cloud, requires API key). User chooses on first visit.
- **D-02:** Default model is Llama 3.1 8B for Ollama, or a sensible default for OpenRouter (e.g., meta-llama/llama-3.1-8b-instruct:free or similar free-tier model).
- **D-03:** CFG-01 (provider config) and CFG-02 (API key for OpenRouter) are in v1. CFG-03 (cost estimation) remains deferred to v2.

### App Shell Layout
- **D-04:** Map-dominant layout. Tile map takes most of the screen. Activity feed in a collapsible right sidebar. Event input and controls (pause/resume) in a bottom bar below the map.
- **D-05:** Agent inspector replaces the feed sidebar when an agent is clicked. Feed is hidden while inspecting; closing inspector restores the feed.

### Error Handling
- **D-06:** Claude's Discretion — pick the best approach for communicating LLM failures (Ollama timeout, model not found, malformed response) to the user. Non-blocking preferred; simulation should attempt retry before alerting.

### Cost Display
- **D-07:** Deferred to v2. No token counting or cost estimation in v1 since Ollama is free/local.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Reference Implementation
- `~/projects/GenerativeAgentsCN/generative_agents/` -- Agent architecture, memory system, simulation loop patterns to adapt
- `~/projects/GenerativeAgentsCN/generative_agents/modules/model/llm_model.py` -- LLM integration patterns (adapt for Ollama via LiteLLM)

### Research
- `.planning/research/STACK.md` -- Full tech stack decisions (FastAPI, PixiJS, LiteLLM, ChromaDB, etc.)
- `.planning/research/ARCHITECTURE.md` -- System architecture, component boundaries, data flow
- `.planning/research/PITFALLS.md` -- Critical pitfalls including async/sync mismatch, JSON parsing fragility

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project

### Established Patterns
- None yet — Phase 1 establishes the foundational patterns

### Integration Points
- FastAPI backend will serve the React frontend (static files or separate dev servers)
- WebSocket endpoint established in Phase 1 for use by Phase 4 (Simulation Engine)
- Pydantic schemas defined here will be used by Phase 3 (Agent Cognition) for all LLM calls

</code_context>

<specifics>
## Specific Ideas

- Ollama health check on app startup — graceful message if not running, with link to ollama.com
- LiteLLM wraps Ollama calls so switching to cloud providers in v2 requires zero agent logic changes
- The map area in Phase 1 can be a placeholder/empty canvas — actual tile rendering comes in Phase 5

</specifics>

<deferred>
## Deferred Ideas

- User-provided API keys and provider selection UI (v2 — CFG-01, CFG-02)
- Token counting and cost estimation display (v2 — CFG-03)
- Model routing per call type: cheap model for routine calls, expensive for complex (v2 — CFG-04)

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-04-09*
