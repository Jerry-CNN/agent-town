# Project Research Summary

**Project:** Agent Town
**Domain:** LLM-powered agent simulation web app
**Researched:** 2026-04-10
**Confidence:** HIGH

## Executive Summary

Agent Town v1.1 is a refactoring and behavioral extension milestone on top of a working v1.0 system. No new dependencies are required — every capability (OOP Agent class, building wall rendering, reflection system, LLM optimization) is achievable with the installed stack (Python stdlib dataclasses, PixiJS 8 Graphics API, existing instructor/Pydantic, asyncio primitives).

The core risks are architectural, not technological. The most dangerous failure modes are: (1) the ChromaDB singleton getting duplicated during OOP refactoring, silently wiping agent memory; (2) circular imports between the new Agent class and SimulationEngine; and (3) LLM call explosion from naively porting the reference 3-level decision system to a real-time tick loop. All three are preventable with specific design constraints documented in PITFALLS.md.

The recommended build order places the OOP Agent class refactor first because the reflection poignancy accumulator, relationship tracking, and 3-level decision routing all attach to it. Building wall rendering is fully independent of the backend refactor and can proceed in parallel.

## Key Findings

### Recommended Stack

No new packages. All features use existing dependencies plus stdlib.

**Key patterns:**
- **`@dataclass` for Agent/Building/Event classes** — not ABC; project spec rules out subclassing. Pydantic stays for wire/validation schemas
- **PixiJS `Graphics.stroke()` for walls** — v8 API requires stroke after fill; use 3-4px width (2px disappears at default zoom)
- **`asyncio.Semaphore(8)` for LLM concurrency** — prevents rate limit hits with 25 agents x 3-5 calls per tick
- **`asyncio.create_task()` for reflection** — 3-6 LLM calls per reflection; must be background, never inline in agent step

### Expected Features

**Must have (table stakes):**
- Building walls visible on map — colored rectangles alone feel unfinished
- Agent names/activities readable at default zoom (current: 9-10px, need 18-22px)
- OOP Agent class encapsulating config + state + cognition methods
- Building/Location class with wall metadata
- Event class with lifecycle (created, active, expired)
- 3-level decision resolution (sector -> arena -> object) matching reference
- Conversation early termination on repetition

**Should have (differentiators):**
- Reflection system with poignancy-triggered insights
- Relationship tracking between agents
- Tick timing reduced from 30s to 10s for responsiveness

**Defer (v2+):**
- Agent subclassing / polymorphism
- LiteLLM response caching (MEDIUM confidence on key behavior)
- Persistent poignancy across server restarts

### Architecture Approach

The OOP refactor is self-contained: a new `Agent` class in `backend/agents/agent.py` unifying `AgentConfig` + `AgentState` with cognition methods that delegate to existing functions. `SimulationEngine` switches from two dicts (`configs` + `states`) to one dict of `Agent` objects. Building walls are frontend-only — derive wall line segments from `town.json` sector boundaries in a new `BuildingOverlay.tsx`. The 3-level decision changes `Maze.resolve_destination()` (5-line change) and adds gating flags per sector.

**Major components changed:**
1. **`Agent` class** (`agents/agent.py`) — owns config, state, and cognition methods; calls existing functions
2. **`Building` class** (`simulation/world.py`) — sector metadata with wall tiles, occupancy, properties
3. **`Event` class** (`schemas/events.py`) — lifecycle tracking for injected and perceived events
4. **`schemas.py` split** — 183 lines with 12 models needs domain-grouped files
5. **`BuildingOverlay.tsx`** — wall rendering from sector bounds, following existing TileMap pattern

### Critical Pitfalls

1. **ChromaDB singleton duplication** — moving `EphemeralClient()` into Agent.__init__ silently creates empty memory stores. Keep `_chroma_client` module-level forever; Agent calls `store.add_memory()` as before
2. **Circular imports Agent <-> Engine** — Agent needs Maze, Engine needs Agent. Fix: Agent takes Maze via method params, not imports
3. **`break` on engine.py:366 is load-bearing** — limits conversation gating to one LLM call per tick per agent. Removing it during refactor multiplies LLM calls by nearby agent count
4. **Reflection inline blocks agent step** — 5-20x longer than decide_action; must use `asyncio.create_task()`, never `await` inline
5. **Reducing TICK_INTERVAL without updating AGENT_STEP_TIMEOUT** — timeout is `TICK_INTERVAL * 2`; changing one without the other breaks the guard

## Implications for Roadmap

### Phase 1: OOP Foundation
**Rationale:** Everything else attaches to Agent/Building/Event classes. Must be first.
**Delivers:** Agent class, Building class, Event class, schemas.py split. No behavior change — all tests pass.
**Avoids:** Pitfalls 1 (ChromaDB singleton) and 2 (circular imports) by design.

### Phase 2: Visual Overhaul
**Rationale:** Highest user-visible payoff, lowest complexity. Fully parallel with Phase 1 if needed.
**Delivers:** BuildingOverlay with wall rendering, readable text sizes (18-22px), sector label scaling.
**Addresses:** All table-stakes visual complaints from v1.0 testing.

### Phase 3: LLM Optimization
**Rationale:** Must benchmark call counts before reflection adds more calls.
**Delivers:** 3-level decision resolution with per-sector gating, tick interval reduction (30s -> 10s), asyncio.Semaphore concurrency control, conversation repetition detection + early termination.
**Avoids:** Pitfalls 3 (break removal) and 5 (timeout mismatch).

### Phase 4: Reflection System
**Rationale:** Depends on stable Agent class (poignancy field) and correct tick timing.
**Delivers:** Poignancy accumulation on memory, threshold-triggered reflection, reflect_focus + reflect_insights LLM calls, "thought" memory type.

### Phase 5: Relationship Tracking
**Rationale:** Additive, low-risk, depends on reflection being stable.
**Delivers:** RelationshipTracker module, summarize_relation prompt, relationship display in inspector UI.

### Phase Ordering Rationale

- OOP first because reflection/relationships attach to Agent class fields
- Visual parallel because it's frontend-only with zero backend dependencies
- LLM optimization before reflection to establish correct tick timing and call budgets
- Reflection before relationships because relationships use reflection history

### Research Flags

Phases with standard patterns (skip research-phase):
- **All phases** — Phase 1 uses stdlib dataclasses, Phase 2 uses confirmed PixiJS 8 API, Phases 3-5 adapt patterns directly from the reference implementation

Empirical tuning needed:
- **Phase 4:** Poignancy threshold (50 vs reference 150) — needs tuning during implementation

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | No new dependencies; all patterns verified against installed versions |
| Features | HIGH | Reference implementation directly readable; all patterns clear |
| Architecture | HIGH | Full codebase read; integration points confirmed |
| Pitfalls | HIGH | 7/10 pitfalls from direct code analysis with line numbers |

**Overall confidence:** HIGH

### Gaps to Address

- **Poignancy threshold value** — 50 recommended, reference uses 150; tune empirically during Phase 4
- **LiteLLM cache key behavior** — MEDIUM confidence; test before relying on it for optimization
- **Per-tick LLM call count post-3-level** — must measure with logging during Phase 3; target 1.2 avg calls/agent/tick
- **Wall tile walkability** — verify sector boundaries in town.json align with visual wall placement

## Sources

### Primary (HIGH confidence)
- GenerativeAgentsCN reference implementation — agent.py, associate.py, start.py (direct codebase read)
- Agent Town v1.0 codebase — engine.py, store.py, TileMap.tsx, schemas.py (direct read)
- PixiJS v8 official docs — Graphics API stroke/fill order

### Secondary (MEDIUM confidence)
- LiteLLM 1.83+ caching API — documented but cache key behavior not independently verified
- Python asyncio best practices — create_task pattern for background work

---
*Research completed: 2026-04-10*
*Ready for roadmap: yes*
