# Phase 2: World & Navigation - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

A data-modeled tile-map town with named thematic locations exists in memory and BFS pathfinding routes agents around obstacles between any two tiles. Agent data structures (personality, occupation, routine templates) are defined and loadable from config. No rendering — that's Phase 5.

</domain>

<decisions>
## Implementation Decisions

### Town layout
- **D-01:** Large map (100x100+ tiles), matching the reference implementation's scale. Supports 8-10 agents with room to spread out across neighborhoods.
- **D-02:** Thematic locations from PROJECT.md: stock exchange, wedding hall, park, homes (multiple), shops, cafe, office. No additions for v1.
- **D-03:** Neighborhood cluster arrangement — residential area (homes), commercial area (shops, cafe, office), civic area (stock exchange, wedding hall), green space (park). Agents commute between clusters.
- **D-04:** 32px tile size, standard for pixel-art tile maps. 100x100 grid = 3200x3200px canvas.

### Map data format
- **D-05:** Tiled JSON format. Map defined as a Tiled-compatible JSON file with tile layers, loaded and parsed at runtime by the backend.
- **D-06:** Dedicated collision layer in the Tiled map marks walkable vs obstacle tiles. Pathfinding reads this layer, separate from visual tile layers.
- **D-07:** Claude generates the Tiled JSON programmatically during this phase. User reviews the output.

### Agent cast
- **D-08:** 8-10 pre-defined agents with diverse occupations (trader, baker, florist, office worker, barista, etc.). Each agent has a natural reason to visit specific locations.
- **D-09:** Agent personality data stored in JSON config files — one per agent, containing name, traits, occupation, home location, and daily routine template. Like the reference repo's agent.json pattern.
- **D-10:** Hybrid daily routines — config provides a rough template (e.g., "morning: cafe, afternoon: work, evening: home"). LLM fills in details and adapts based on events in Phase 3.
- **D-11:** Agents spawn at a mixture of home and workplace locations when simulation starts. Not all at home, not all at work — varied initial state for a more interesting first impression.

### Pathfinding
- **D-12:** Pure BFS shortest path algorithm. All walkable tiles have equal cost. Matches the reference implementation. Sufficient for v1.
- **D-13:** Destination resolution: agent resolves a location name (e.g., "cafe") to any walkable tile within that location's zone. Agents spread out naturally inside buildings.

### Location metadata
- **D-14:** Minimal metadata per location — name and associated tile coordinates only. The LLM infers what activities are possible from the location name. No operating hours, capacity, or activity type enums in Phase 2.

### Claude's Discretion
- Interior room depth: whether locations have sub-areas (hierarchical addressing like the reference) or are flat named zones. Claude decides based on what Phase 3 agent cognition will need.
- Agent movement speed per simulation step. Claude picks based on map size and natural feel.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Reference implementation
- `~/projects/GenerativeAgentsCN/generative_agents/modules/maze.py` — Tile class, Maze class, BFS pathfinding algorithm, collision handling
- `~/projects/GenerativeAgentsCN/generative_agents/modules/agent.py` — Agent data structure, personality/scratch model, pathfinding integration, movement logic
- `~/projects/GenerativeAgentsCN/generative_agents/frontend/static/assets/village/maze.json` — Tiled JSON map format, tile layer structure, collision layer example
- `~/projects/GenerativeAgentsCN/generative_agents/frontend/static/assets/village/agents/` — Agent JSON config format (personality, occupation, daily routine)

### Project research
- `.planning/research/STACK.md` — Tech stack decisions (pixi-tiledmap for Tiled JSON loading, Pydantic for data models)
- `.planning/research/ARCHITECTURE.md` — System architecture, component boundaries
- `.planning/research/PITFALLS.md` — Critical pitfalls to avoid

### Prior phase context
- `.planning/phases/01-foundation/01-CONTEXT.md` — Foundation decisions (LLM providers, app shell layout, Pydantic patterns)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/schemas.py`: Existing Pydantic schema patterns (AgentAction, WSMessage) — extend with agent/map models
- `backend/gateway.py`: LLM gateway already set up — agent cognition (Phase 3) will use this for routine generation
- `backend/config.py`: Config patterns established — agent JSON configs should follow similar loading patterns

### Established Patterns
- Pydantic v2 models for all data structures (from Phase 1)
- Async-first architecture (FastAPI + asyncio) — pathfinding can be called from async context
- Project uses `uv` for Python dependency management

### Integration Points
- Agent data models defined here will be consumed by Phase 3 (cognition), Phase 4 (simulation loop), and Phase 5 (frontend rendering)
- Map/tile data will be served to the frontend via the existing WebSocket connection (Phase 4) or REST endpoint
- BFS pathfinding will be called by the simulation engine (Phase 4) every time an agent needs to move

</code_context>

<specifics>
## Specific Ideas

- Reference implementation's hierarchical addressing (world:sector:arena:game_object) is worth studying for the interior depth decision
- Agent configs should be easy to edit by hand — JSON files, not embedded in Python code
- Initial agent positions should create an immediately interesting scene when the user first loads the simulation

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-world-navigation*
*Context gathered: 2026-04-09*
