# Architecture Research

**Domain:** Web-based Generative Agents Simulation — v1.1 OOP Refactor + Visual Polish
**Researched:** 2026-04-10
**Confidence:** HIGH (full codebase read, reference implementation cross-referenced)

---

## Current Architecture (Baseline)

The v1.0 codebase is functional but structured as a procedural simulation loop wrapped
around static data containers. Understanding what exists is the prerequisite for all
integration decisions below.

### Backend Module Map

```
backend/
├── main.py                     # FastAPI app + lifespan (wires engine + manager)
├── gateway.py                  # LLM singleton: instructor + LiteLLM
├── config.py                   # Runtime provider state (mutable singleton)
├── schemas.py                  # ALL Pydantic models (flat file)
├── simulation/
│   ├── engine.py               # SimulationEngine + AgentState dataclass
│   ├── world.py                # Tile + Maze classes (BFS, address index)
│   ├── connection_manager.py   # WebSocket broadcast fan-out
│   └── map_generator.py        # town.json builder (static data)
├── agents/
│   ├── loader.py               # load_all_agents() -> list[AgentConfig]
│   ├── cognition/
│   │   ├── perceive.py         # perceive() -- pure Python, no LLM
│   │   ├── decide.py           # decide_action() -- 1 LLM call
│   │   ├── converse.py         # attempt_conversation() + run_conversation()
│   │   └── plan.py             # generate_daily_schedule() + decompose_hour()
│   └── memory/
│       ├── store.py            # ChromaDB add/score/reset -- asyncio.to_thread
│       └── retrieval.py        # retrieve_memories() -- composite scoring
├── prompts/                    # One file per prompt template
│   ├── action_decide.py
│   ├── conversation_start.py
│   ├── conversation_turn.py
│   ├── importance_score.py
│   ├── schedule_init.py
│   ├── schedule_decompose.py
│   └── schedule_revise.py
└── routers/
    ├── ws.py                   # WebSocket endpoint
    ├── agents.py               # REST: agent list
    ├── llm.py                  # REST: provider config
    └── health.py               # REST: health check
```

### Current Data Flow (Per-Tick)

```
SimulationEngine._tick_loop()
    asyncio.TaskGroup: all agents in parallel
        _agent_step_safe(name, state)
            _agent_step(name, state)
                perceive(coord, name, maze, all_agents_view)  -- pure Python
                    -> PerceptionResult{nearby_agents, nearby_events, location}
                if state.path: return   (movement handled by _movement_loop)
                attempt_conversation(...)  -- 1 LLM call (ConversationDecision)
                    if should_talk:
                        run_conversation(...)  -- 2-8 LLM calls
                        return
                decide_action(...)  -- 1 LLM call (AgentAction)
                    retrieve_memories(...)  -- ChromaDB query
                    maze.resolve_destination(action.destination) -> coord
                    maze.find_path(state.coord, dest_coord) -> path
                add_memory(...) -- ChromaDB write
                _emit_agent_update(name, state) -> broadcast callback
```

### Current State Ownership

| Data | Where Held | Type |
|------|-----------|------|
| Agent personality | AgentConfig (Pydantic) | Static, loaded from JSON |
| Agent runtime state | AgentState (dataclass) | Mutable, in _agent_states dict |
| Conversation cooldowns | _conversation_cooldowns dict | Module-level in converse.py |
| Memory | ChromaDB EphemeralClient | Async, per-simulation collection |
| Tile grid + BFS | Maze instance | Shared reference in SimulationEngine |
| WebSocket clients | ConnectionManager | Set of active WebSocket objects |
| Provider config | config.state singleton | Mutable global |

### Current Frontend Component Map

```
frontend/src/
├── App.tsx                     # Root: ProviderSetup gate -> Layout
├── main.tsx                    # React 19 entry
├── store/simulationStore.ts    # Zustand store (agents, feed, WS state)
├── hooks/useWebSocket.ts       # WS lifecycle + message dispatch
├── types/index.ts              # Shared TypeScript interfaces
├── data/town.json              # Static map (imported at build time)
└── components/
    ├── Layout.tsx              # Flex layout: MapCanvas | ActivityFeed | AgentInspector
    ├── MapCanvas.tsx           # @pixi/react Application wrapper + auto-scale
    ├── TileMap.tsx             # Static tile grid (colored rects + sector labels)
    ├── AgentSprite.tsx         # Per-agent: circle + initial + activity + lerp
    ├── AgentInspector.tsx      # Right panel: selected agent details
    ├── ActivityFeed.tsx        # Bottom/side feed: WS event log
    ├── BottomBar.tsx           # Event injection UI (broadcast/whisper)
    ├── ProviderSetup.tsx       # LLM provider config gate
    └── OllamaStatusBanner.tsx  # Ollama health indicator
```

---

## v1.1 Target: What Changes vs What Stays

### What STAYS Unchanged

These components are correct and are not touched by v1.1:

| Component | Why It Stays |
|-----------|-------------|
| gateway.py complete_structured() | LLM abstraction is correct. 3-level decision is a prompt/logic change, not a gateway change |
| agents/memory/store.py | Memory storage is correct. Reflection adds calls to existing functions |
| agents/memory/retrieval.py | Composite scoring is correct and paper-aligned |
| simulation/connection_manager.py | WebSocket fan-out is correct |
| simulation/map_generator.py | Map data generation is static |
| config.py | Provider config singleton is correct |
| All routers (ws.py, agents.py, health.py, llm.py) | No new endpoints; WS message contracts unchanged |
| All prompt templates in prompts/ | Templates stay; new prompts are added alongside |
| Frontend: useWebSocket.ts, simulationStore.ts, App.tsx, Layout.tsx, ProviderSetup.tsx, OllamaStatusBanner.tsx, BottomBar.tsx | No WS contract changes, no store schema changes |
| Frontend: AgentInspector.tsx, ActivityFeed.tsx | Read from store only; unchanged unless store shape changes |

### What CHANGES (Modified)

| Component | What Changes | Why |
|-----------|-------------|-----|
| simulation/engine.py AgentState | Add reflection_poignancy: int field | Reflection needs accumulated poignancy across ticks |
| simulation/engine.py _agent_step | Add reflection call after perceive; add 3-level decision routing | Reflection hook; 3-level decision replaces flat decide_action |
| simulation/engine.py TICK_INTERVAL | Reduce from 30s toward 10s | Faster agent responsiveness; actual value tuned by LLM latency |
| simulation/world.py Maze | Add sector-level arena address lookup support | 3-level decision needs to resolve sector:arena strings |
| schemas.py | Add Event model, ReflectionInsight model, ThreeLevelAction model | New structured LLM output types |
| agents/cognition/decide.py decide_action() | Replace flat sector choice with 3-level sequential LLM calls | Reference implementation fidelity |
| agents/cognition/converse.py run_conversation() | Add early termination on repetition detection | Conversation termination feature |
| frontend/src/components/TileMap.tsx | Add wall rendering: draw border lines around sector bounding boxes | Building walls visual |
| frontend/src/types/index.ts | Add BuildingWall type if derived wall segments need typing | Depends on approach |

### What is NEW (Additive)

| New Component | Location | Purpose |
|--------------|----------|---------|
| agents/cognition/reflect.py | backend/agents/cognition/ | Reflection system: poignancy threshold triggers insight generation |
| prompts/reflect_focus.py | backend/prompts/ | Prompt: "what are the 3 most salient questions based on memories?" |
| prompts/reflect_insights.py | backend/prompts/ | Prompt: "what 5 insights can be inferred from these memories?" |
| prompts/determine_sector.py | backend/prompts/ | 3-level decision: sector selection |
| prompts/determine_arena.py | backend/prompts/ | 3-level decision: arena selection |
| prompts/determine_object.py | backend/prompts/ | 3-level decision: object selection |
| agents/relationships.py | backend/agents/ | In-memory relationship tracker (who has talked to whom, topic tags) |
| frontend/src/components/BuildingOverlay.tsx | frontend/src/components/ | PixiJS layer that renders wall lines over TileMap |

---

## Integration Points (Detailed)

### 1. Agent OOP Refactor: What Actually Changes

The current split is AgentConfig (static Pydantic) + AgentState (mutable dataclass),
both held in dicts inside SimulationEngine. The v1.1 "Agent class" consolidates these
without changing the external interface that routers and WebSocket use.

**Integration boundary:** SimulationEngine._agent_states dict changes from
dict[str, AgentState] to dict[str, Agent]. Everything that currently calls
state.coord, state.path, state.current_activity, state.config, state.schedule
must be updated to use the new unified Agent object.

**Callers that touch _agent_states or state:**

- engine._agent_step() -- primary consumer, reads and mutates state fields
- engine._movement_loop() -- reads state.path, writes state.coord
- engine._emit_agent_update() -- reads state.coord, state.current_activity
- engine.inject_event() -- reads state.path, clears it
- engine.get_snapshot() -- reads state.coord, state.current_activity
- engine.initialize() -- creates AgentState instances
- converse.run_conversation() -- receives state.config.scratch and state.schedule as args (passed by value, no cascade refactor needed)

**Refactor scope:** Contained to engine.py + new Agent class definition in a new file
backend/agents/agent.py. No router or WebSocket schema changes.

**Recommended Agent class structure:**

```python
class Agent:
    # Static (from AgentConfig JSON)
    name: str
    config: AgentConfig        # kept as sub-object, not flattened

    # Runtime (was AgentState fields)
    coord: tuple[int, int]
    path: list[tuple[int, int]]
    current_activity: str
    schedule: list[ScheduleEntry]

    # New in v1.1
    reflection_poignancy: int  # accumulated; reset to 0 after reflection fires
    relationships: dict[str, str]  # agent_name -> relationship_note
```

Cognition functions (perceive, decide_action, attempt_conversation, etc.) keep their
current function signatures -- they accept individual fields as arguments, not the Agent
object. This avoids a cascade refactor across all cognition modules.

### 2. Building Class: What It Actually Adds

The reference implementation has no separate Building class -- buildings are groups of
tiles with a shared sector address. The Maze.address_tiles dict already indexes
sector -> set of tile coords.

The v1.1 "Building class" is primarily for providing wall geometry to the frontend.

**Data flow for building walls -- recommended approach (Option B, frontend-only):**

The collision tile data is already in town.json. The frontend derives wall lines by
detecting sector boundary tiles (tiles whose neighbor on any of the 4 cardinal directions
is either a collision tile or a different sector). This is pure frontend geometry computed
once at module load, matching the pattern of computeSectorBounds() in TileMap.tsx.

BuildingOverlay.tsx does the computation at module load, draws wall line segments via
g.moveTo / g.lineTo / g.stroke(). Zero backend changes required.

If sector interiors need explicit wall metadata later, add a walls key to town.json at
that point -- this is a one-time map authoring task, not an architecture change.

### 3. Event Class: What It Actually Adds

Currently events are stored directly as add_memory() calls with memory_type="event".
The Tile._events dict exists in world.py but inject_event() bypasses it entirely -- events
go straight to ChromaDB without touching the tile grid.

**What an Event class buys for v1.1:**
- Source tagging: "user_inject" vs "conversation" vs "reflection"
- Expiry: events fade from Tile._events after N ticks
- Tile-based event display on the frontend (future)

**Recommended Event schema to add to schemas.py:**

```python
class Event(BaseModel):
    text: str
    source: Literal["user_inject", "conversation", "observation", "reflection"]
    importance: int              # 1-10
    created_at: float
    expires_at: float | None     # None = permanent; set for N-tick fade
    target: str | None           # None = tile-based; agent name for whisper
```

inject_event() in engine.py writes the Event to both Tile._events (for perception) and
ChromaDB (for memory retrieval). The perception scan in perceive.py already reads
Tile._events -- so injected events will surface in nearby_events for the first time.

### 4. Three-Level Decision: What Changes in decide.py

Currently decide_action() asks the LLM for a sector name in a single call. The reference
_determine_action() makes three sequential LLM calls: sector -> arena -> object.

**Integration in existing code:**

The decide_action() function signature stays the same (returns AgentAction). Internally:
- Call 1: determine_sector prompt -> sector name from agent's known sectors
- Call 2: determine_arena prompt -> arena within that sector from agent_spatial.tree
- Call 3: determine_object prompt -> object within that arena from agent_spatial.tree
- Construct destination as "sector:arena" for Maze.resolve_destination()

Maze.resolve_destination() currently only handles sector-level strings (key = world:sector).
It needs to also accept arena-level strings (key = world:sector:arena). The address index
already supports this -- Maze.address_tiles is indexed at both "world:sector" and
"world:sector:arena" levels via Tile.get_addresses().

**LLM call budget change:** +2 calls per decide tick per agent. For 8 agents this adds
up to 16 additional LLM calls per tick -- the key cost driver for the optimization work.

### 5. Reflection System: New Module

The reference reflect() method fires when status["poignancy"] exceeds poignancy_max
(typically 150). In v1.0, poignancy is not tracked at all.

**Integration points:**

1. PerceptionResult gets a new field poignancy_delta: int. perceive() returns a delta
   based on a heuristic: non-idle event = +1, conversation event = +2. No LLM call.

2. reflect.py new module:
   - Input: agent_name, simulation_id, agent_scratch
   - Retrieves top N recent memories via retrieve_memories()
   - Calls reflect_focus prompt -> 3 salient questions (1 LLM call)
   - For each question, retrieves focused memories and calls reflect_insights prompt (3 LLM calls)
   - Stores each insight as add_memory(memory_type="thought", importance=scored)
   - Returns (does not mutate agent directly)

3. _agent_step() adds after perceive():
   ```python
   agent.reflection_poignancy += perception.poignancy_delta
   if agent.reflection_poignancy >= POIGNANCY_THRESHOLD:
       asyncio.create_task(reflect(agent.name, simulation_id, agent.config.scratch))
       agent.reflection_poignancy = 0
   ```

   Reflection fires as a background task to avoid blocking the tick. Thought memories
   are available for the next tick's memory retrieval.

**POIGNANCY_THRESHOLD:** Start at 150 (reference value). Tune down if reflection never
fires in practice with cheap models that assign low importance scores.

### 6. Relationship Tracking: New Module

The reference tracks chats per agent and uses them during reflection. In v1.0, relationship
state is implicit in ChromaDB memories only.

**Recommended structure:**

```python
# backend/agents/relationships.py
class RelationshipTracker:
    _pairs: dict[frozenset[str], list[str]]  # pair -> list of conversation summaries

    def record(self, agent_a: str, agent_b: str, summary: str) -> None: ...
    def get_history(self, agent_a: str, agent_b: str) -> list[str]: ...
```

**Wiring:** RelationshipTracker instance created in main.py lifespan, stored on app.state,
passed to SimulationEngine constructor (same pattern as broadcast_callback). Engine passes
it to converse.run_conversation() after conversations complete.

### 7. Building Walls Rendering: Frontend Only

**Current state:** TileMap.tsx draws colored rectangles per sector bounding box. No wall
lines exist.

**Target state:** Each sector gets a visible border drawn as a line stroke over the
background fill. Agents inside a building appear to be within walls.

**BuildingOverlay.tsx approach:**

```typescript
// Computed once at module load from town.json
function computeWallLines(): WallSegment[] {
  // For each sector, walk the perimeter tiles
  // Return {x1, y1, x2, y2} segments forming building borders
}

export function BuildingOverlay() {
  const drawWalls = useCallback((g: PixiGraphics) => {
    g.clear();
    for (const seg of WALL_LINES) {
      g.moveTo(seg.x1, seg.y1);
      g.lineTo(seg.x2, seg.y2);
    }
    g.stroke({ color: 0x555544, width: 2 });
  }, []);  // empty deps -- wall lines are static
  return <pixiGraphics draw={drawWalls} />;
}
```

**Integration:** Add <BuildingOverlay /> between <TileMap /> and agent sprites in
MapCanvas.tsx. Rendered in PixiJS scene graph order: TileMap -> BuildingOverlay -> agents.

### 8. LLM Call Optimization: Budget and Levers

Current per-agent per-tick worst case (full conversation):
- attempt_conversation(): 1 call
- run_conversation(): up to 8 turns + 2 importance + 2 schedule_revise = 12 calls
- Total: 13 calls per agent per conversation tick

After 3-level decision (no conversation):
- decide_action() three-level: 3 calls

**Optimization levers for v1.1:**

1. Activity heuristic gate before attempt_conversation() LLM call: if both agents are
   in "working" or "sleeping" activities, return False without an LLM call. Saves 1 call
   per nearby pair per tick.

2. Repetition detection in run_conversation(): if the last 2 turns from the same speaker
   have very similar text (local string similarity check, no LLM), force end_conversation=True.
   Reduces average conversation length from MAX_TURNS toward 2-3 turns.

3. cheap_model parameter in complete_structured(): pass a cheaper model for high-frequency
   low-stakes calls (importance_score, conversation_turn). Use configured model for
   reflect_insights and three-level decision calls.

4. Reduce TICK_INTERVAL from 30s to 10s default: asyncio.TaskGroup already runs all agents
   concurrently so the bottleneck is the slowest agent LLM response, not the number of
   agents. With GPT-4o-mini or Haiku, p95 LLM latency is well under 10s.

---

## Recommended Build Order

Dependencies determine order. Each step is independently buildable and testable.

### Step 1: Agent OOP Refactor (Foundation)

Create backend/agents/agent.py with Agent class consolidating AgentConfig + AgentState
plus the new reflection_poignancy field. Update SimulationEngine._agent_states.
Update all field accesses in engine.py.

No behavior change. All existing tests pass.

### Step 2: Reflection System (Requires Step 1 for reflection_poignancy)

Add reflect.py, add poignancy_delta to PerceptionResult, add reflection check in
_agent_step(), add POIGNANCY_THRESHOLD, add reflect_focus.py and reflect_insights.py prompts.

No change to movement or decisions. Adds new "thought" memories visible in activity feed.

### Step 3: Three-Level Decision (Requires Step 1 for Agent.config.spatial access)

Replace decide_action() internals with 3-level sequential LLM calls.
Add determine_sector.py, determine_arena.py, determine_object.py prompts.
Update Maze.resolve_destination() to accept "sector:arena" strings.

Behavior change: agents navigate to arenas within sectors, not just sector-level.

### Step 4: Building Walls + Visual Overhaul (No backend dependencies, parallel with 2-3)

Add BuildingOverlay.tsx. Improve TileMap.tsx label sizes and font weights.
Tune AgentSprite.tsx text sizes for readability at default zoom.

Pure frontend. Can be developed while Steps 2-3 are in progress.

### Step 5: Relationship Tracking (Requires Step 2 -- reflection uses relationship history)

Add backend/agents/relationships.py RelationshipTracker.
Wire into converse.run_conversation() and reflect.py.
Thread tracker instance through SimulationEngine constructor.

### Step 6: Conversation Improvements + Tick Optimization (Requires Steps 1-3)

Add activity heuristic gate before attempt_conversation() LLM call.
Add repetition detection to run_conversation().
Add cheap_model routing in gateway.complete_structured().
Reduce TICK_INTERVAL default and make it configurable.

---

## Component Boundary Table

| Boundary | Communication | v1.1 Change? |
|----------|--------------|--------------|
| engine.py <-> cognition/ | Function calls, typed args | Add poignancy_delta to PerceptionResult; reflection call added |
| engine.py <-> memory/ | add_memory(), reset_simulation() | No change |
| cognition/reflect.py <-> memory/ | retrieve_memories(), add_memory() | New caller, existing functions |
| cognition/converse.py <-> relationships.py | tracker.record() | New call added after each conversation |
| engine.py <-> simulation/world.py | maze.find_path(), maze.resolve_destination() | resolve_destination() accepts "sector:arena" strings |
| Backend <-> Frontend | WebSocket JSON (WSMessage) | No schema changes; building walls go via town.json static import |
| MapCanvas.tsx <-> BuildingOverlay.tsx | Parent renders child in PixiJS tree | New component added |
| TileMap.tsx <-> town.json | Static import | May add walls key later; no change in Step 4 |
| gateway.py <-> all cognition | complete_structured() | Add cheap_model optional param in Step 6 |

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Flattening AgentConfig into Agent

**What people do:** Copy all AgentConfig fields directly onto the Agent class,
eliminating the config sub-object.

**Why it's wrong:** loader.py returns list[AgentConfig] and the JSON schema is stable.
Existing tests and the WebSocket snapshot serialize config.scratch.innate etc. Flattening
requires touching every reference throughout the codebase.

**Do this instead:** Keep Agent.config: AgentConfig as a sub-object. Promote only the
fields the engine accesses on every tick (coord, path, current_activity, schedule,
reflection_poignancy) to the top level of Agent.

### Anti-Pattern 2: Cascade-Refactoring Cognition Function Signatures

**What people do:** Change perceive(), decide_action(), attempt_conversation() to accept
Agent objects instead of individual fields.

**Why it's wrong:** These functions have existing tests built against their current
signatures. Changing them risks breaking test coverage and creates a larger diff.

**Do this instead:** Keep cognition functions accepting individual fields. engine._agent_step()
extracts fields from the Agent object before passing them. This is the existing pattern
(config = state.config, config.scratch, etc.) -- extend it, do not replace it.

### Anti-Pattern 3: Sending Building Wall Geometry via WebSocket

**What people do:** Add building metadata to the engine snapshot and send wall coordinates
over the WebSocket on every new client connection.

**Why it's wrong:** Wall geometry is static -- it never changes during simulation. Sending
it over WebSocket adds pointless payload. The frontend already imports town.json at build
time for sector colors.

**Do this instead:** Compute wall segments in BuildingOverlay.tsx from the already-imported
town.json at module load time. Zero runtime cost, zero backend change.

### Anti-Pattern 4: Blocking the Event Loop with Reflection

**What people do:** Add await reflect(...) synchronously inside _agent_step() when the
threshold is crossed, blocking that agent's task for the duration of 4-15 LLM calls.

**Why it's wrong:** Reflection takes significantly longer than a normal decide step. Running
it inline will trigger the TICK_INTERVAL*2 timeout guard and skip the agent entirely.

**Do this instead:** Fire reflection as asyncio.create_task() when the threshold is
crossed. Clear reflection_poignancy immediately. The thought memories will be available
for the next tick's memory retrieval. This matches the reference behavior.

### Anti-Pattern 5: Growing schemas.py Without Bounds

**What people do:** Add all new Pydantic models to schemas.py.

**Why it's wrong:** schemas.py is already 183 lines with 12 models. Adding Event,
ReflectionInsight, ThreeLevelAction, RelationshipEntry makes it unmaintainable.

**Do this instead:** Add domain-grouped files alongside schemas.py for v1.1 additions:
backend/schemas/events.py, backend/schemas/reflection.py, backend/schemas/decision.py.
Keep schemas.py for foundational models referenced everywhere (AgentConfig, AgentScratch,
AgentSpatial, PerceptionResult, WSMessage, Memory, ScheduleEntry). Additive -- no refactor
of existing imports required.

---

## Modified Data Flow After v1.1

### Agent Step

```
_agent_step(agent: Agent)
    all_agents_view = snapshot of all agents' coords and activities

    perception = perceive(agent.coord, agent.name, maze, all_agents_view)
    -> PerceptionResult{nearby_agents, nearby_events, location, poignancy_delta}  [NEW field]

    agent.reflection_poignancy += perception.poignancy_delta
    if agent.reflection_poignancy >= POIGNANCY_THRESHOLD:
        asyncio.create_task(reflect(...))   [NEW -- background task]
        agent.reflection_poignancy = 0

    if agent.path: return  (movement loop handles walking)

    if perception.nearby_agents:
        if _passes_activity_heuristic(agent, other):   [NEW gate]
            should_talk = await attempt_conversation(...)
            if should_talk:
                result = await run_conversation(...)
                tracker.record(a, b, result.summary)   [NEW]
                return

    action = await decide_action_three_level(          [MODIFIED internals]
        ...same signature...
    )
    -> ThreeLevelAction{sector, arena, object, activity}

    dest_coord = maze.resolve_destination("sector:arena")  [MODIFIED]
    path = maze.find_path(agent.coord, dest_coord)
    agent.path = path[1:]
    agent.current_activity = action.activity
    await _emit_agent_update(...)
    await add_memory(...)
```

### Reflection Flow (Async Background Task)

```
asyncio.create_task(reflect(agent_name, sim_id, agent_scratch))
    memories = retrieve_memories(sim_id, agent_name, focus_query, top_k=20)
    questions = complete_structured(reflect_focus_prompt, ReflectionFocus)  -- 1 LLM call
    for question in questions[:3]:
        focused = retrieve_memories(sim_id, agent_name, question, top_k=5)
        insights = complete_structured(reflect_insights_prompt, ReflectionInsights)  -- 1 LLM call
        for insight in insights[:5]:
            importance = score_importance(...)
            add_memory(sim_id, agent_name, insight, "thought", importance)
    -- Total: 3-6 LLM calls, all async/non-blocking
```

---

## Scalability Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 5-10 agents (current) | asyncio.TaskGroup concurrent tick is correct; no changes needed |
| 15-25 agents | Cheap model routing (Step 6) becomes necessary; reflection background tasks accumulate -- add semaphore to bound concurrent reflection tasks |
| 25+ agents | EphemeralClient ChromaDB starts to strain; switch to PersistentClient with file-backed store for better memory management |

These are not v1.1 concerns -- the current single-user 5-10 agent scope is well within
the existing architecture's capacity.

---

## Sources

- Full read: backend/simulation/engine.py, world.py, agents/cognition/*, agents/memory/*, gateway.py, schemas.py, routers/ws.py
- Full read: frontend/src/components/*, frontend/src/store/simulationStore.ts, frontend/src/types/index.ts
- Reference implementation (direct read): GenerativeAgentsCN/generative_agents/modules/agent.py -- reflect(), _determine_action(), percept(), make_plan() methods
- Reference implementation (direct read): GenerativeAgentsCN/generative_agents/modules/maze.py -- Tile._events, update_events(), add_event()
- CLAUDE.md stack decisions: confirmed all technology choices (LiteLLM, instructor, FastAPI, PixiJS v8, @pixi/react v8, Zustand) stay unchanged in v1.1

---
*Architecture research for: Agent Town v1.1 OOP Refactor + Visual Polish + LLM Optimization*
*Researched: 2026-04-10*
