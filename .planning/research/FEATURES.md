# Feature Research

**Domain:** LLM-powered agent simulation web app — v1.1 milestone (OOP refactor, visual overhaul, LLM optimization, behavior fidelity)
**Researched:** 2026-04-10
**Confidence:** HIGH for OOP patterns and reflection system (reference implementation in repo, paper available). MEDIUM for PixiJS wall rendering (no dominant community standard). MEDIUM for LLM optimization (research literature available, not yet distilled for this specific use case).

---

## Scope of This Document

This is a **milestone-scoped** feature research update. v1.0 table stakes (tile-map rendering, agent movement, event injection, activity feed, pause/resume) are already shipped. This document focuses on:

1. **OOP class design** — Agent, Building/Location, Event class patterns
2. **PixiJS wall rendering** — building walls visible on the map, agents cannot walk through them
3. **LLM call optimization** — 3-level decisions, conversation gating, smarter tick timing
4. **Reflection/poignancy system** — higher-level insights, relationship tracking, reference repo parity

---

## Feature Landscape

### Table Stakes (Users Expect These — for v1.1 milestone)

Features that, once announced as "improvements," users expect to see complete. Missing any of these in v1.1 would make the milestone feel hollow.

| Feature | Why Expected | Complexity | Depends On |
|---------|--------------|------------|-----------|
| Building walls visible on map | "Map looks like a town" is in the milestone promise; colored rectangles alone feel unfinished | MEDIUM | Existing Tile.collision data in world.py, TileMap.tsx refactor |
| Agent names / activities readable at default zoom | Current 9px activity text and 10px name text are barely legible at default zoom level | LOW | AgentSprite.tsx font size + background pill |
| Sector name labels readable at default zoom | 13px at full zoom = illegible when MAP fits 100×100 tiles in viewport | LOW | TileMap.tsx label sizing, dynamic font scaling |
| OOP Agent class encapsulating cognition | Milestone states "Agent class with config + state + cognition methods"; flat functional modules are the current design | MEDIUM | engine.py, all cognition/ modules |
| Building/Location class with properties | Currently buildings are only tile collision flags; no typed class for querying occupancy, exits, sector identity | LOW-MEDIUM | world.py Maze/Tile refactor |
| Event class with lifecycle | Currently events are plain dicts in memory store; no typed class with propagation, expiry, or origin tracking | LOW-MEDIUM | schemas.py, store.py |
| LLM decide_action using 3-level resolution | Current decide.py makes a single LLM call choosing any sector; reference uses sector → arena → object cascade | HIGH | decide.py, schemas.py (AgentAction), Maze.address_tiles |
| Conversation gating LLM check | converse.py already has attempt_conversation() with LLM check; milestone wants this confirmed complete and tested | LOW | converse.py (already implemented but needs validation) |
| Conversation early termination on repetition | Reference agent.py has generate_chat_check_repeat — current implementation uses hard cap but no repetition detection | MEDIUM | converse.py, new prompt |

---

### Differentiators (Competitive Advantage — v1.1 additions)

Features that, if implemented well, make Agent Town clearly superior to existing demos.

| Feature | Value Proposition | Complexity | Depends On |
|---------|------------------|------------|-----------|
| Reflection system with poignancy threshold | Agents forming higher-level insights ("Isabella realizes the wedding will affect stock prices") creates narrative moments; no existing public demo has this | HIGH | New reflect.py cognition module, poignancy accumulator on AgentState, new prompt |
| Relationship tracking between agent pairs | Reference stores per-pair chat summaries; surfacing this in the inspector shows emergent social structure | MEDIUM | Associate.retrieve_chats pattern, AgentState relationship dict, inspector UI |
| Tick timing optimization (perception-first skip) | Current 30s TICK_INTERVAL means agents feel sluggish; reference does perception every tick, LLM decision only when needed | MEDIUM | engine.py tick loop refactor |
| Visual building walls (fake 3D top face) | A row of darker tiles above each sector boundary gives the illusion of a building wall without isometric complexity | LOW-MEDIUM | TileMap.tsx, town.json wall tile definitions |
| Activity text background pill | White/translucent background pill behind activity label makes text readable at any zoom | LOW | AgentSprite.tsx |

---

### Anti-Features (Commonly Requested, Often Problematic — v1.1 scope)

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Full isometric / 2.5D rendering | Requires depth-sorted sprites, z-buffer hacks, custom shaders; adds weeks of work for aesthetic that conflicts with the paper's Smallville visual | Stick to orthogonal top-down; add a single row of "wall top" tiles (darker shade) above building edges for depth illusion |
| True 4-level address hierarchy (world:sector:arena:object) | Reference uses 4-level but Agent Town's current 3-level (world:sector:arena) is simpler and sufficient for all current routing; adding object level means rewriting Maze + all prompts | Implement 3-level decision (sector → arena within sector → pick tile within arena); game_object level is out of scope for v1.1 |
| Agent subclassing / polymorphism | PROJECT.md explicitly calls this out of scope; all agents run same code path with personality from prompts | Personality is data (AgentScratch JSON), not code hierarchy |
| Real-time streaming thought display during LLM calls | Streaming 8 agents simultaneously at different latencies is chaotic; overlapping streaming bubbles on the map are unreadable | Store completed thoughts in memory, surface in inspector panel on click |
| Global relationship graph visualization | D3 force graph is a v2+ feature; building it in v1.1 risks pulling focus from the more impactful reflection system | Relationship tracking in data only; UI surfaced in agent inspector as a simple list |
| Persistent ChromaDB (disk-backed) | PersistentClient across simulation restarts is a v2+ save/load feature; EphemeralClient is correct for v1.1 | Keep EphemeralClient; reflection data lives in-process |

---

## OOP Class Design Patterns

### Agent Class — Standard Pattern

The reference implementation (GenerativeAgentsCN/modules/agent.py) establishes the canonical OOP structure for generative agents. Key observations from reading it directly:

**What the reference does well (adopt):**
- Single `Agent` class owns all state: spatial memory, schedule, associate (vector store), scratch (personality/current state), action (what they're doing now)
- `think()` is the top-level orchestration method — calls `percept()`, `make_plan()`, `reflect()` in sequence
- `_determine_action()` implements 3-level resolution: spatial lookup → `completion("determine_sector")` → `completion("determine_arena")` → `completion("determine_object")`
- `reflect()` has a hard guard: `if self.status["poignancy"] < self.think_config["poignancy_max"]: return` — no LLM call unless threshold crossed
- Poignancy accumulates on `self.status["poignancy"]` per perceived concept; reset to 0 after reflection runs

**Current Agent Town gap:**
- No Agent class; cognition is split across `cognition/perceive.py`, `cognition/decide.py`, `cognition/converse.py`, `cognition/plan.py` as standalone async functions called by `SimulationEngine._agent_step()`
- `AgentState` dataclass holds position/schedule but has no cognition methods
- Poignancy score is tracked nowhere; reflection system does not exist

**Recommended OOP target for v1.1:**
```
AgentState (existing dataclass) — keep as-is for position/path/schedule
Agent (new class) — wraps AgentState + AgentConfig, owns cognition:
  - perceive() → calls existing perceive.py function
  - decide() → calls existing decide.py function (add 3-level resolution)
  - converse() → calls existing converse.py functions
  - reflect() → new method, checks poignancy threshold
  - poignancy: int (accumulated per tick, reset on reflect)
  - relationships: dict[str, str] (other_name -> summary)
```

The migration is additive: wrap existing functions as methods, do not rewrite the function bodies.

### Building / Location Class — Pattern

Current `world.py` has `Tile` (per-cell) and `Maze` (grid + BFS). There is no Building class.

**Reference `maze.py` pattern:** Also has no Building class — buildings are just tiles with addresses. A Location/Building abstraction is optional.

**Recommended minimal Building class for v1.1:**
```python
@dataclass
class Location:
    name: str          # sector name, e.g. "cafe"
    tiles: set[tuple[int, int]]   # all tile coords in this sector
    walkable_tiles: set[tuple[int, int]]  # non-collision tiles
    label: str         # display name, e.g. "Café"
    color: int         # hex color for rendering

    def random_entry(self) -> tuple[int, int]:
        return random.choice(list(self.walkable_tiles))

    def is_occupied_by(self, agent_name: str, agent_states: dict) -> bool:
        return any(
            s.coord in self.tiles
            for n, s in agent_states.items()
            if n == agent_name
        )
```

`Maze` builds a `dict[str, Location]` from the address index at init time. This gives `decide.py` typed location data without rewriting pathfinding.

### Event Class — Pattern

Current events are plain strings stored in ChromaDB metadata. The reference has a rich `Event` class (subject, predicate, object, address, describe, emoji).

**For v1.1, event lifecycle tracking needed:**
- Origin: "user_injected" | "perceived" | "conversation" | "reflection"
- Propagation: broadcast (all agents) | whisper (one agent) | organic (conversation-spread)
- Created-at timestamp (already in ChromaDB metadata)
- Expiry: reflection events expire after 30 days (reference pattern)

The existing `add_memory()` function's `memory_type` field already partially encodes this. The v1.1 Event class should be a Pydantic model that wraps the `add_memory()` call:

```python
class SimEvent(BaseModel):
    content: str
    origin: Literal["user_injected", "perceived", "conversation", "reflection"]
    propagation: Literal["broadcast", "whisper", "organic"]
    importance: int = Field(ge=1, le=10)
    created_at: float = Field(default_factory=time.time)
```

---

## PixiJS Wall Rendering

### Table Stakes for Walls

The milestone requires "buildings have visible walls on the map; agents cannot walk through them."

**What already works:**
- `Tile.collision = True` tiles block BFS pathfinding in `Maze.find_path()` — agent collision is already implemented
- `TileMap.tsx` draws collision tiles as dark gray rectangles — walls are already prevented and shown

**What is missing:**
- Walls look like individual gray tiles, not building edges — no visual "this is a wall" affordance
- No "wall top face" effect — buildings look flat, not like 3D structures

### Orthogonal Wall Technique (table stakes for readability)

For a top-down orthogonal map (no isometric), the standard technique for building walls is:

1. **Floor fill**: colored rectangle filling the building footprint (already implemented as sector zones)
2. **Wall outline**: 2-4px stroke around the sector rectangle (add via `g.setStrokeStyle` + `g.stroke()` in PixiJS v8 Graphics API)
3. **Wall top face (optional depth illusion)**: Draw a darkened rectangle that is 1-2 tile heights tall at the *top edge* of each sector rectangle. This simulates a wall face that faces the viewer.

**PixiJS v8 Graphics API for stroke:**
```typescript
g.setStrokeStyle({ color: 0x555544, width: 3 });
g.rect(bounds.x, bounds.y, bounds.width, bounds.height);
g.stroke();
```

**Wall top face (depth illusion, no isometric needed):**
```typescript
// Draw a darker band at the top of each sector for wall depth illusion
const wallHeight = TILE_SIZE * 1.5; // 1-2 tile heights
g.setFillStyle({ color: darkenColor(bounds.color, 0.35) });
g.rect(bounds.x, bounds.y, bounds.width, wallHeight);
g.fill();
```

This is **LOW complexity** (pure Graphics API calls, no sprite sheets, no shader work) and gives a strong visual "building" impression in orthogonal top-down view. The reference Smallville map uses this pattern.

**Complexity assessment:** LOW-MEDIUM. The technique is simple but requires:
- Computing a `darkenColor()` utility (trivial math)
- Adjusting town.json so sector boundaries are "building outer edge" not "interior floor"
- Ensuring walkable tiles are interior (avoid placing agents on the wall face tiles)

### Anti-Pattern: Do Not Do Isometric

Switching to isometric for better wall visibility would require:
- Sprite depth sorting (zIndex per Y coordinate, per frame)
- Splitting sprites that "peek over" walls
- Custom shaders or GPU depth buffer tricks for per-pixel overlap
- Every sprite needing isometric offsets

This is a weeks-long detour. The wall top face technique gives 80% of the visual effect at 5% of the cost.

---

## LLM Call Optimization

### 3-Level Decision Resolution (sector → arena → within arena)

**Current state:** `decide_action()` makes 1 LLM call returning an `AgentAction` with `destination` (a sector name from the agent's known locations list). This maps to the reference's top-level sector decision only.

**Reference pattern** (`agent.py _determine_action()`):
1. Check spatial memory first: `address = self.spatial.find_address(describes[0], as_list=True)` — if the agent already knows where to go, no LLM call needed
2. If not found: `determine_sector` LLM call → adds sector to address
3. `determine_arena` LLM call if multiple arenas in sector → adds arena
4. `determine_object` LLM call if multiple objects in arena → adds object

**The key optimization:** The spatial lookup is a pure Python dict lookup — if the agent has already been to the activity's location, 0 LLM calls are made for navigation. LLM calls only occur for new activities or new locations.

**Recommended implementation for v1.1:**
- Add `AgentSpatial.find_address(activity: str) -> list[str] | None` that checks the spatial tree for known sector/arena for a given activity keyword
- Implement 3-level cascade in `decide_action()`:
  1. Spatial lookup → if hit, skip LLM navigation calls
  2. `determine_sector` prompt (1 LLM call) — existing sector list as candidates
  3. `determine_arena` prompt (1 LLM call) — only if sector has multiple arenas
- Skip level 3 (object) — Agent Town has 3-level address hierarchy, not 4-level

**LLM call count reduction:**
- Current: 1 call per tick always (decide_action)
- After: 0-2 calls per tick (0 if spatial hit, 1-2 for new locations)

### Conversation Gating (already partially implemented)

`attempt_conversation()` in converse.py already does:
1. Cooldown check (no LLM call if pair talked within 60s)
2. LLM call to decide whether to talk

**Gap:** The gating fires every tick when agents are nearby, even during movement ticks. The engine already has `if state.path: return` to skip conversation when moving. This is correct.

**Missing:** No check for whether both agents are in a "busy" activity (sleeping, already in conversation, walking to a critical appointment). The reference `_skip_react()` method adds this guard.

### Tick Timing Optimization

**Current:** TICK_INTERVAL = 30 seconds. This is very slow — agents feel frozen.

**Reference pattern:** Steps happen in wall-clock time; each step is ~1 simulation minute. The reference runs in batch mode with a different trade-off. For real-time web UX:

- **Perception + movement loop**: already runs at 500ms (movement_loop in engine.py) — correct
- **LLM decision loop**: should run as soon as an agent has finished moving (path is empty) and isn't in a conversation, not on a fixed timer

**Recommended optimization:** Change `_agent_step()` to skip the LLM decide call if the agent is still walking, and reduce TICK_INTERVAL to 8-10 seconds. The movement_loop already handles visual position at 500ms. The bottleneck is the LLM call latency (2-15s depending on model), not the tick interval.

**Expected improvement:** At 10s tick interval with 8 agents all running concurrently (asyncio.TaskGroup), and LLM latency of ~3s for decide, total cycle time is ~max(3s, 10s) = 10s. With 30s interval, agents get decisions only every 30s even if LLM responds in 3s.

### Conversation Early Termination (repetition detection)

**Reference:** `generate_chat_check_repeat` prompt asks LLM "does this response repeat what was already said?" If yes, terminates early.

**Current Agent Town:** Hard cap at MAX_TURNS=4. No repetition detection. Conversations always run full 4 turns even when they've concluded.

**Recommended:** Add a repetition check prompt after turn 2 (not turn 1 — too early). Saves 1-2 LLM calls per conversation. The check is cheap (short prompt, binary output).

---

## Reflection and Poignancy System

### What the Reference Does (HIGH confidence — read directly from agent.py + associate.py)

**Poignancy accumulation:**
- Every perceived concept gets a poignancy score: `node.poignancy = self.completion("poignancy_event", event)` or `"poignancy_chat"`
- The score is 1-10, LLM-generated, but idle events (`is idle` / `空闲`) are hardcoded to 1
- Accumulated on `self.status["poignancy"]` after each perception
- Reset to 0 after reflection runs

**Reflection trigger:** `if self.status["poignancy"] < self.think_config["poignancy_max"]: return` — threshold typically 150 in the reference config

**What reflection does:**
1. Retrieve recent events + thoughts from associate memory (top N by recency)
2. `reflect_focus` LLM call: generate 3 focus questions from those events
3. For each focus question: retrieve relevant memories, then `reflect_insights` LLM call: generate 5 insights
4. Each insight becomes a new "thought" in associate memory (with filling = evidence node IDs)
5. If there were recent conversations: also generate a "chat plan" and "chat memory" thought

**LLM call count for reflection:** 2 + (3 × 2) = 8 calls when triggered (focus + insights per question). Heavy but infrequent (only when threshold crossed).

**Agent Town adaptation:**
- Poignancy tracking is missing entirely from `AgentState`
- No `poignancy_event` or `poignancy_chat` prompts exist
- ChromaDB already stores memories; reflection thoughts would be stored with `memory_type="reflection"`

**What to implement for v1.1:**
- Add `poignancy: int = 0` to `AgentState`
- After each `perceive()` call, score each new perceived event (reuse `score_importance()` since it already does 1-10 scoring with idle shortcut — same semantics)
- Accumulate on `AgentState.poignancy`
- After accumulation check: if `poignancy >= threshold`, call new `reflect()` cognition function
- Reflection output stored in ChromaDB as memory_type="reflection"
- Surface reflection events in WebSocket broadcast so activity feed shows them distinctly

**Threshold calibration:** Reference uses 150. Agent Town ticks faster and has fewer agents, so start at 50. Tune empirically.

### Relationship Tracking

**Reference:** `associate.retrieve_chats(other_name)` returns past conversations with a specific agent. The `summarize_relation` completion generates a relationship summary ("Isabella and Klaus are neighbors; she finds him curious but opaque").

**Current Agent Town:** Conversation summaries are stored in ChromaDB with `memory_type="conversation"`. The data exists but there is no per-pair retrieval path or summary generation.

**What to implement for v1.1:**
- After each `run_conversation()`, generate a relationship summary for both agents (2 new LLM calls; add to `run_conversation()` return dict)
- Store summaries in `AgentState.relationships: dict[str, str]`
- Surface in agent inspector panel (already shows current activity — add a relationships tab)

**Complexity:** MEDIUM. The pattern is clear from the reference; the storage is already available via ChromaDB.

---

## Feature Dependencies

```
Existing: AgentState (position, schedule) + cognition/ functions (perceive, decide, converse, plan)

OOP Agent class
  └──wraps──> AgentState + cognition/ functions
  └──adds──> poignancy: int, relationships: dict
  └──required-by──> Reflection system

Reflection system
  └──requires──> OOP Agent class (poignancy accumulation)
  └──requires──> poignancy_event prompt (new)
  └──requires──> reflect_focus prompt (new)
  └──requires──> reflect_insights prompt (new)
  └──enhances──> Activity feed (reflection event type)

3-level LLM decision
  └──requires──> AgentSpatial.find_address() (spatial lookup method)
  └──requires──> determine_sector prompt (new)
  └──requires──> determine_arena prompt (new)
  └──enhances──> Agent responsiveness (fewer wasted LLM calls)

Building walls (visual)
  └──requires──> TileMap.tsx wall face drawing logic
  └──soft-depends-on──> town.json sector boundary alignment (wall face tiles must not be walkable)
  └──no-dependency-on──> OOP refactor (pure frontend change)

Conversation early termination
  └──requires──> generate_chat_check_repeat prompt (new)
  └──modifies──> converse.py run_conversation() turn loop
  └──no-dependency-on──> OOP refactor

Relationship tracking
  └──requires──> OOP Agent class (relationships dict on AgentState)
  └──requires──> summarize_relation prompt (new)
  └──enhances──> Agent inspector panel
```

---

## Prioritization for v1.1

| Feature | User Value | Build Effort | Priority |
|---------|-----------|--------------|----------|
| Building walls (visual stroke + top face) | HIGH — milestone promise, first-impression | LOW | P1 |
| Text readability (font size + background pill) | HIGH — legibility at zoom | LOW | P1 |
| OOP Agent class (wraps existing functions) | HIGH — structural clarity, enables reflection | MEDIUM | P1 |
| Location class in Maze | MEDIUM — cleaner decide_action, enables 3-level | LOW | P1 |
| Tick interval reduction (30s → 10s) | HIGH — agents feel responsive | LOW | P1 |
| 3-level LLM decision (spatial lookup first) | HIGH — LLM cost reduction + reference parity | HIGH | P2 |
| Conversation early termination | MEDIUM — saves 1-2 LLM calls per conversation | MEDIUM | P2 |
| Reflection system (poignancy + reflect()) | HIGH — major behavior fidelity feature | HIGH | P2 |
| Relationship tracking + inspector UI | MEDIUM — emergent social structure visible | MEDIUM | P2 |
| SimEvent Pydantic class (lifecycle) | LOW-MEDIUM — structural clarity, schema safety | LOW | P3 |

**P1 = must complete in v1.1, P2 = core v1.1 but can slip if P1 is large, P3 = do if time permits**

---

## Sources

- [Generative Agents paper (Park et al., 2023)](https://arxiv.org/abs/2304.03442) — HIGH confidence; primary source for reflection, poignancy, and 3-level action resolution
- [GenerativeAgentsCN/modules/agent.py](../../../GenerativeAgentsCN/generative_agents/modules/agent.py) — HIGH confidence; direct read of reference implementation; reflection(), _determine_action(), poignancy accumulation
- [GenerativeAgentsCN/modules/memory/associate.py](../../../GenerativeAgentsCN/generative_agents/modules/memory/associate.py) — HIGH confidence; direct read; Concept class, poignancy retrieval weights
- [PixiJS v8 Graphics API docs](https://pixijs.download/dev/docs/scene.Graphics.html) — HIGH confidence; setStrokeStyle, setFillStyle patterns for wall rendering
- [pixi-tiledmap](https://www.npmjs.com/package/pixi-tiledmap) — MEDIUM confidence; confirms PixiJS v8 has full orthogonal tilemap support
- [Agentic Plan Caching (arxiv 2025)](https://arxiv.org/abs/2506.14852) — MEDIUM confidence; confirms spatial caching reduces LLM calls 50%+ in agent workflows
- [KVFlow: Efficient Prefix Caching for Multi-Agent Workflows (arxiv 2025)](https://arxiv.org/html/2507.07400v1) — MEDIUM confidence; confirms prefix caching patterns applicable to per-agent prompts

---

*Feature research for: Agent Town v1.1 — OOP refactor, visual overhaul, LLM optimization, behavior fidelity*
*Researched: 2026-04-10*
