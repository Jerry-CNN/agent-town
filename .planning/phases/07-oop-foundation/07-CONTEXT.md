# Phase 7: OOP Foundation - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Restructure the backend from flat dicts + standalone functions to Agent/Building/Event classes. SimulationEngine operates on Agent objects. schemas.py splits into domain-grouped modules. No behavior change — all existing tests must pass, WebSocket payloads must be byte-identical before and after.

</domain>

<decisions>
## Implementation Decisions

### Agent Class Design
- **D-01:** Agent class unifies AgentConfig + AgentState into one object. All fields are mutable (including identity fields like traits) to keep the door open for future trait evolution, even though v1.1 won't mutate them.
- **D-02:** Agent accesses memory via module-level calls: `store.add_memory(self.name, ...)`. The ChromaDB singleton stays in `store.py` — never moved into Agent.__init__ or wrapped in a class. This is a hard constraint from Codex pitfall analysis.
- **D-03:** Agent class lives in `backend/agents/agent.py`. Must NOT import from `engine.py` to avoid circular imports. Receives Maze and other engine dependencies via method parameters.
- **D-04:** Cognition methods on Agent (`perceive()`, `decide()`, `converse()`) delegate to existing standalone functions in `cognition/`. The functions themselves stay unchanged — Agent methods are thin wrappers that pass `self` fields as arguments.
- **D-05:** The `break` on engine.py:366 (limits conversation gating to one LLM call per tick per agent) must be preserved during the refactor. Add an explicit comment explaining why.

### Building Data Source
- **D-06:** Building properties (operating hours, purpose tag) defined in a separate `backend/data/map/buildings.json` file. Follows the existing data-driven pattern (agent configs are separate JSON files, town.json is generated map data). Do not mix building metadata into town.json.
- **D-07:** Building class lives in `backend/simulation/world.py` alongside Tile and Maze. Loaded from buildings.json at startup, indexed by sector name.

### Event Lifecycle Rules
- **D-08:** Events expire by tick count (e.g., 10 ticks). Simple, deterministic, no sim-time clock needed. Configurable threshold.
- **D-09:** Broadcast events do NOT track propagation (who heard them). Only whisper events track propagation — since broadcasts reach everyone instantly, propagation tracking only matters for gossip.
- **D-10:** Event lifecycle states: created -> active -> spreading (whisper only) -> expired. Broadcast events go created -> active -> expired (skip spreading).

### Schema Split Strategy
- **D-11:** Split schemas.py by domain into a `backend/schemas/` package:
  - `schemas/agent.py` — AgentConfig, AgentScratch, AgentSpatial, AgentAction
  - `schemas/cognition.py` — DailySchedule, ScheduleEntry, SubTask, ScheduleRevision, PerceptionResult, ConversationDecision, ConversationTurn
  - `schemas/events.py` — Event (new), Memory, ImportanceScore
  - `schemas/ws.py` — WSMessage, ProviderConfig, LLMTestResponse
  - `schemas/__init__.py` — re-exports all models for backward compatibility (`from backend.schemas import AgentConfig` still works)

### Claude's Discretion
- Event expiry tick count (recommended: 10 ticks)
- Internal Agent field naming conventions
- Exact method signatures for Agent cognition wrappers

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Reference Implementation
- `~/projects/GenerativeAgentsCN/generative_agents/modules/agent.py` — Reference Agent class structure (OOP pattern to adapt)

### Current Codebase (files being refactored)
- `backend/schemas.py` — All current Pydantic models (being split)
- `backend/simulation/engine.py` — SimulationEngine with AgentState (being refactored to use Agent objects)
- `backend/simulation/world.py` — Tile + Maze classes (Building class added here)
- `backend/agents/cognition/perceive.py` — perceive() function (Agent.perceive() will wrap this)
- `backend/agents/cognition/decide.py` — decide_action() function (Agent.decide() will wrap this)
- `backend/agents/cognition/converse.py` — attempt_conversation() + run_conversation() (Agent.converse() will wrap these)
- `backend/agents/cognition/plan.py` — generate_daily_schedule() (Agent method will wrap this)
- `backend/agents/memory/store.py` — ChromaDB singleton (DO NOT MOVE — D-02)
- `backend/agents/loader.py` — Loads AgentConfig from JSON (will load Agent objects instead)

### Research
- `.planning/research/PITFALLS.md` — Critical pitfalls for OOP refactor (ChromaDB singleton, circular imports, load-bearing break)
- `.planning/research/ARCHITECTURE.md` — Integration points and build order
- `.planning/research/SUMMARY.md` — Executive summary with phase ordering rationale

### Data Files
- `backend/data/agents/*.json` — Agent personality JSON configs (pattern for buildings.json)
- `backend/data/map/town.json` — Generated tile map (DO NOT add building metadata here — D-06)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AgentConfig` (Pydantic) — becomes the identity core of Agent class
- `AgentState` (dataclass) — becomes the runtime state of Agent class
- All cognition functions (`perceive`, `decide_action`, `attempt_conversation`, `generate_daily_schedule`) — stay as-is, Agent methods delegate to them
- `Tile` and `Maze` classes — Building class integrates with these
- `loader.py` — pattern for loading Agent objects from JSON

### Established Patterns
- Pydantic for validation/wire schemas, dataclass for mutable runtime state
- Module-level singletons for shared resources (ChromaDB client, LLM gateway)
- asyncio.TaskGroup for concurrent agent processing
- JSON files in `backend/data/` for entity configurations

### Integration Points
- `engine.py` — Main consumer of Agent objects (currently holds separate dicts)
- `ws.py` — WebSocket handler creates snapshot payloads from engine state
- `main.py` — FastAPI lifespan wires engine + connection manager
- Frontend types (`frontend/src/types/index.ts`) — must not break; WS payloads unchanged

</code_context>

<specifics>
## Specific Ideas

- Codex (GPT-5.4) reviewed this roadmap and identified serialization backward-compat as the #1 risk. A contract test comparing WS payloads before/after is a hard success criterion.
- The reference repo's Agent class (GenerativeAgentsCN/modules/agent.py) is the pattern to adapt — single class owning config + state + cognition methods.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-oop-foundation*
*Context gathered: 2026-04-10*
