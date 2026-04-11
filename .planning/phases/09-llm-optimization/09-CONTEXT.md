# Phase 9: LLM Optimization - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Optimize LLM call patterns for reliability and speed: change default provider to OpenRouter, add adaptive tick timing, implement 2-level decision cascade, add conversation repetition detection, and bound concurrency with a semaphore. Also add a provider settings button so users can switch providers without clearing localStorage.

</domain>

<decisions>
## Implementation Decisions

### Provider Default
- **D-01:** OpenRouter is the recommended/pre-selected provider in the setup modal. Ollama is still available as "Local (advanced)" option for users who want offline/local LLM.
- **D-02:** Default model for OpenRouter: Kimi K2.5 (user's choice). Should be pre-filled in the model field when OpenRouter is selected.
- **D-03:** Add a settings/gear button to the UI header (Layout.tsx) that reopens the provider setup modal. Users should be able to switch providers anytime without clearing localStorage.

### Tick Interval Tuning
- **D-04:** Adaptive tick interval. Measure average LLM response time across recent calls (rolling window of last 10-20 calls). Set tick to `max(10, avg_response_time * 1.5)` seconds. This means fast providers (OpenRouter) get ~10s ticks, slow providers (Ollama) get proportionally longer ticks automatically.
- **D-05:** Update AGENT_STEP_TIMEOUT to `tick_interval * 2` dynamically — it must track the adaptive tick, not be hardcoded.
- **D-06:** Display current tick interval somewhere subtle in the UI (e.g., bottom bar) so users understand the simulation speed.

### 3-Level Decision Resolution
- **D-07:** 2-level cascade: sector → arena. Agent first picks a sector (e.g., "cafe"), then picks an arena within it (e.g., "kitchen" or "seating"). Skip object level — we don't have interactable objects.
- **D-08:** Per-sector gating: if the agent's destination sector is unchanged from last tick and no new perceptions triggered a re-evaluation, skip the LLM call entirely (0 calls). Only re-decide when something changes.
- **D-09:** Arena-level resolution only for sectors that have sub-arenas in town.json. Single-room sectors (like homes) skip the arena call.

### Conversation Termination
- **D-10:** Simple string similarity using Python's `difflib.SequenceMatcher`. Compare the last 2 conversation turns. If `ratio() > 0.6`, terminate the conversation early.
- **D-11:** When terminated, log "conversation ended (repetition)" to the activity feed so the user can see it.
- **D-12:** This replaces the current fixed MAX_TURNS cap — conversations now end either by repetition detection OR a maximum of 6 turns (raised from 4 to give more room before repetition kicks in).

### Concurrency Control
- **D-13:** `asyncio.Semaphore(8)` in gateway.py wrapping all LLM calls. Limits concurrent in-flight calls regardless of provider. With OpenRouter this prevents rate limiting; with Ollama this prevents queue pileup.
- **D-14:** Debug logging on semaphore acquire/release so users can see concurrency behavior in the console.

### Claude's Discretion
- Rolling window size for adaptive tick (10 or 20 calls)
- Exact Kimi K2.5 model ID on OpenRouter
- Settings button icon and placement
- Whether to show "Tick: Xs" label in bottom bar or just tooltip

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Backend (files being modified)
- `backend/gateway.py` — LLM singleton with instructor. Add semaphore wrapper + latency tracking here
- `backend/simulation/engine.py` — TICK_INTERVAL (currently 30), AGENT_STEP_TIMEOUT, _agent_step decide flow
- `backend/agents/cognition/decide.py` — decide_action() with open_locations. Add arena-level resolution
- `backend/agents/cognition/converse.py` — run_conversation() with MAX_TURNS. Add repetition detection
- `backend/config.py` — AppState with provider/model fields

### Frontend (files being modified)
- `frontend/src/components/ProviderSetup.tsx` — Provider selection modal. Reorder to OpenRouter-first
- `frontend/src/components/Layout.tsx` — Header bar. Add settings button
- `frontend/src/components/BottomBar.tsx` — Bottom controls. Optional tick interval display

### Reference
- `~/projects/GenerativeAgentsCN/generative_agents/modules/agent.py` — 3-level _determine_action() cascade
- `.planning/research/FEATURES.md` — 3-level decision research findings
- `.planning/research/PITFALLS.md` — Pitfall 3 (break removal), Pitfall 5 (timeout mismatch)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `gateway.py` `complete_structured()` — single LLM call function; semaphore wraps this
- `decide.py` `_extract_known_locations()` — already extracts sector names from spatial tree
- `converse.py` `run_conversation()` — has MAX_TURNS constant and turn loop
- `ProviderSetup.tsx` — already supports both providers; just needs reordering

### Established Patterns
- LLM calls go through `complete_structured()` in gateway.py — single choke point for semaphore
- Provider config stored in localStorage and sent to backend via `/api/config` POST
- `TICK_INTERVAL` is a module-level constant in engine.py — needs to become mutable for adaptive

### Integration Points
- `gateway.py` is the single LLM entry point — semaphore + latency tracking here affects all calls
- `engine.py` reads TICK_INTERVAL for tick loop sleep — needs to read adaptive value instead
- `ProviderSetup.tsx` sends config to `/api/config` — model field needs to carry Kimi K2.5 default

</code_context>

<specifics>
## Specific Ideas

- User chose Kimi K2.5 specifically as the default OpenRouter model
- The "instructor retry exception" errors flooding logs need to be handled gracefully (catch + log once, not spam)
- Settings button should let users switch providers mid-simulation without restarting

</specifics>

<deferred>
## Deferred Ideas

- **Model routing per call type** (CFG-04, v2) — cheap model for routine calls, expensive for complex. Related but out of Phase 9 scope.
- **LiteLLM response caching** — research had MEDIUM confidence on cache key behavior. Defer to v1.2.

</deferred>

---

*Phase: 09-llm-optimization*
*Context gathered: 2026-04-11*
