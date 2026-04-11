# Pitfalls Research

**Domain:** Refactoring + extending a working real-time generative agents simulation (v1.1 milestone)
**Researched:** 2026-04-10
**Confidence:** HIGH (drawn from codebase analysis + cross-verified sources)

This file covers pitfalls specific to the v1.1 milestone additions: OOP refactoring, PixiJS building wall rendering, LLM call optimization (3-level decisions, conversation gating, tick timing), and reflection/poignancy system. The v1.0 pitfalls (LLM cost explosion, async event loop blocking, JSON parsing fragility, WebSocket reconnection) are already documented in the earlier research and already addressed in the codebase. This document focuses on what can go wrong when adding these features to a running system.

---

## Critical Pitfalls

### Pitfall 1: OOP Refactor Breaks the _chroma_client Singleton and Wipes Live Memory

**What goes wrong:**
`backend/agents/memory/store.py` has a module-level `_chroma_client = chromadb.EphemeralClient()` singleton. If the OOP refactor introduces an `Agent` class or `MemoryStore` class that wraps this client, and tests or imports instantiate multiple class instances, each instantiation may create a new `EphemeralClient`. `EphemeralClient` is in-memory only — a second client instance is a completely separate memory store. Any simulation test that creates an `Agent` object for testing will silently operate on a different, empty memory store than the simulation engine, making test isolation misleading and causing agents to have empty memory mid-simulation if the client is re-created.

**Why it happens:**
Python modules are singletons on first import, so `_chroma_client` is shared by default. But when wrapping the functional store.py API inside a class, developers often move the client creation to `__init__`, inadvertently allowing multiple client instances. The current code has `MemoryStore = None` as a compatibility alias — any refactor that replaces this with an actual class instantiation pattern changes the semantics.

**How to avoid:**
Keep `_chroma_client` as a module-level singleton in `store.py`. The `Agent` class (or `MemoryStore` class) should call `store.add_memory(...)` and `store.retrieve_memories(...)` as before — inject `simulation_id` via the constructor, not a new ChromaDB client. Do not move ChromaDB client creation into any class `__init__`.

**Warning signs:**
- Tests pass but agents have empty memory on first tick during integration testing
- `col.count()` returns 0 for an agent that should have memories
- Memory retrieval silently returns `[]` instead of raising an error when the wrong client is used

**Phase to address:** OOP Refactoring phase. Must be the first thing verified after introducing any `Agent` class.

---

### Pitfall 2: Mutual Import Between Agent Class and Engine Breaks at Runtime

**What goes wrong:**
Currently `engine.py` imports from `agents/cognition/*.py` and `agents/memory/*.py` as pure function modules. If an `Agent` class is introduced in `agents/agent.py` that imports from `simulation/engine.py` (e.g., to access `Maze` or `AgentState`), and `engine.py` imports `Agent` from `agents/agent.py`, a circular import is created. Python will raise `ImportError: cannot import name 'Agent' from partially initialized module` at startup, not at the point of use.

**Why it happens:**
Circular imports are the single most common failure mode when refactoring flat function modules into classes that need to reference each other. The current flat structure (`engine.py` calls `perceive()`, `decide_action()`, etc. directly) has no circularity because the cognition modules import only from `schemas.py`. An `Agent` class that needs access to `Maze` for pathfinding, or an `Engine` that imports `Agent`, creates the cycle.

**How to avoid:**
Enforce a strict dependency direction: `schemas.py` -> `agents/*` -> `simulation/engine.py`. `Agent` class must not import anything from `simulation/`. Pass `Maze` and `SimulationEngine` references into agent methods via parameters (dependency injection), never via module-level imports inside `agents/`. If `Agent` needs to call maze methods, pass `maze` as a parameter to those methods. If needed, define shared interfaces in `schemas.py` using `Protocol` (structural typing) rather than importing the concrete class.

**Warning signs:**
- `ImportError` on startup after adding the `Agent` class
- `from __future__ import annotations` added everywhere to suppress the error (this hides the problem rather than fixing it)
- IDE shows no circular import but `python -c "import backend"` fails

**Phase to address:** OOP Refactoring phase. Test import chain with `python -c "from backend.agents.agent import Agent"` before writing any Agent class methods.

---

### Pitfall 3: OOP Refactor Silently Duplicates AgentState Into Agent Class, Creating Two Sources of Truth

**What goes wrong:**
`engine.py` holds the authoritative runtime state in `self._agent_states: dict[str, AgentState]`. The `AgentState` dataclass stores `coord`, `path`, `current_activity`, and `schedule`. If a new `Agent` class is introduced with its own `self.coord`, `self.path`, `self.current_activity`, and `self.schedule` attributes (natural when converting to OOP), and `SimulationEngine` keeps its `_agent_states` dict, there are now two copies of each agent's state. The engine mutates `AgentState`; the frontend serializes from `get_snapshot()` which reads `AgentState`. The `Agent` class methods mutate the class's own attributes. The two drift apart silently — agents appear to be walking in the frontend while the `Agent` class thinks they are stationary.

**Why it happens:**
OOP refactoring instinct is to move all state into the class. But `SimulationEngine` already manages state centrally. The natural OOP design duplicates it.

**How to avoid:**
Choose one canonical owner for runtime state and eliminate the other. The cleanest approach: make `Agent` a thin wrapper around one `AgentState` (pass the dataclass by reference, have `Agent` methods mutate it directly). `SimulationEngine._agent_states` becomes `dict[str, Agent]` where each `Agent` holds its `AgentState`. There is still one `AgentState` per agent; `Agent` is just a class that groups the cognition methods with it. Alternatively, keep `AgentState` as the sole state container and make `Agent` a stateless service class (class methods that take `AgentState` as a parameter). Either works — the critical rule is: **one object owns each agent's runtime state**.

**Warning signs:**
- `agent.coord` and `engine._agent_states[name].coord` have different values mid-simulation
- `get_snapshot()` returns stale data while the frontend shows updated positions
- Saving state reads from `Agent` class but loading restores to `AgentState`, or vice versa

**Phase to address:** OOP Refactoring phase. Write a test that mutates state through the `Agent` class and verifies the same mutation is visible through the `engine.get_snapshot()` output before merging.

---

### Pitfall 4: Building Wall Tiles Added to town.json Break BFS Pathfinding for Agents Spawned Inside Sectors

**What goes wrong:**
Adding building walls to the tile map means new collision tiles are placed at the edges of sectors (cafe, stock-exchange, wedding-hall, etc.). Agents are currently spawned at `cfg.coord` from their JSON config files. If any agent's spawn coordinate becomes a collision tile after the map update (because a wall was placed there), the agent's starting position is inside an impassable tile. BFS pathfinding from a collision tile returns `[]` for every destination — the agent's `path` is always empty, so it never moves and never makes a new `decide_action` call (the early-return-if-path guard in `engine.py` line 294 never triggers, but `decide_action` is called, returns `destination="cafe"`, `resolve_destination("cafe")` picks a random walkable tile inside the sector, `find_path(collision_tile, dest)` returns `[]`, and the cycle repeats every tick with the agent standing frozen).

**Why it happens:**
Map changes are made in `town.json` and the map generator, but agent spawn coordinates are defined in separate per-agent JSON config files. The two are not cross-validated at startup.

**How to avoid:**
Run `maze.tile_at(cfg.coord).collision` for every agent config during `engine.initialize()` and raise a clear error (or log a warning and snap to nearest walkable tile) if any agent spawns on a collision tile. Also run this check in the `02-03-PLAN.md` integration validator (`cross-validate` test) after every map change. The `Maze.resolve_destination()` function already handles "no walkable tiles in sector" gracefully — apply the same logic for spawn coordinates.

**Warning signs:**
- Agent is visible at spawn but never moves, and no LLM errors appear in logs
- `find_path` consistently returns `[]` for a specific agent
- `maze.tile_at(state.coord).collision` is `True` for an agent that should be walking

**Phase to address:** Visual Overhaul / Building Walls phase. The integration validation test from Phase 2 must be re-run against the updated map before any agent cognition testing.

---

### Pitfall 5: PixiJS Wall Layer Added to TileMap Causes Full Graphics Redraw on Every Tick

**What goes wrong:**
`TileMap.tsx` currently uses `useCallback` with an empty deps array (`[]`) so the `drawMap` callback is memoized and never re-runs — the static map is drawn once and never redrawn. If building walls are implemented as a new collision tile filter that reads from a prop or store value (e.g., `const wallTiles = useSimulationStore(s => s.wallTiles)`), and that subscription is added to the draw callback's deps array, every WebSocket tick that touches the store triggers a Graphics redraw of the entire 3200x3200px map. At a 500ms movement loop tick, this is 2 redraws/second of the static map, causing visible jank.

**Why it happens:**
Developers see that walls come from the same `town.json` data as sectors and route the wall data through the same Zustand store path as dynamic agent state. The store subscription causes the draw callback dependency to change on every update.

**How to avoid:**
Building wall data is static — it is defined in `town.json` at load time and never changes at runtime. Keep it out of Zustand entirely. Pre-compute `WALL_TILES` at module load time (same pattern as `COLLISION_TILES` and `SECTOR_BOUNDS` already in `TileMap.tsx`), add them to the static `drawMap` callback, and keep the empty `[]` deps array. The draw callback reads from module-level constants, not from any React state or store subscription, so it never re-runs after the initial render.

**Warning signs:**
- FPS drops visible in browser devtools after adding wall rendering
- `drawMap` callback appears in React profiler re-renders list
- Canvas flickers or repaints on every movement loop tick

**Phase to address:** Visual Overhaul / Building Walls phase. Use React DevTools Profiler to confirm `drawMap` runs exactly once before merging the wall rendering PR.

---

### Pitfall 6: 3-Level Decision (Sector → Arena → Object) Triples LLM Calls Per Tick With No Benefit Gating

**What goes wrong:**
The current `decide_action` makes one LLM call per agent per tick. Adding the reference repo's 3-level resolution (sector decision → arena decision → object decision) triples the LLM call count to 3 per agent per tick. With 8 agents and a 5-second tick, that is 24 LLM calls per tick rather than 8. At Ollama latency (~3-8 seconds per call), concurrent 24 calls cannot complete within one 5-second tick interval, causing the tick loop to run slower than `TICK_INTERVAL` and the simulation to feel unresponsive. The `asyncio.wait_for(timeout=TICK_INTERVAL*2)` guard (currently 60 seconds at 30-second tick) will silently skip agents whose 3-call chain takes too long.

**Why it happens:**
The reference implementation runs batch simulation (not real-time) and has no tick timing constraint. The 3-level decision is correct for offline simulation but must be conditioned for real-time use.

**How to avoid:**
Gate the lower two levels: only call arena-level LLM if the sector decision produced a sector that requires room-level specificity (multi-room buildings like the wedding hall or stock exchange). Only call object-level LLM if the arena decision produced an arena with interactive objects. Most sectors are small enough that the sector decision is sufficient — agents heading to the "park" or "cafe" do not need room or object selection. This keeps the typical decision at 1 LLM call, with 2-3 calls only for complex indoor sectors. Log per-tick LLM call counts to confirm the optimization holds.

**Warning signs:**
- Simulation tick wall time exceeds `TICK_INTERVAL` consistently (logs show tick taking 35+ seconds on a 30-second tick)
- `asyncio.wait_for` timeout warnings for agents in multi-room buildings
- Per-tick LLM call count scales with number of distinct sector types rather than agent count

**Phase to address:** LLM Optimization phase. Benchmark call count and tick duration before and after adding the 3-level decision. Target: average 1.2 LLM calls per agent per tick, not 3.

---

### Pitfall 7: Conversation Gating LLM Check Fires for Every Nearby Agent Every Tick, Multiplying Call Count

**What goes wrong:**
`engine.py` already calls `attempt_conversation()` which makes one LLM call (`conversation_start_prompt`) to decide whether to talk. If an agent perceives 3 nearby agents every tick and has an expired cooldown for all 3, this is 3 "should I talk?" LLM calls per tick per agent — before any actual conversation begins. With 8 agents each perceiving 2-3 neighbors, that is 16-24 gating LLM calls per tick in addition to the 8 decide_action calls. The cooldown (`COOLDOWN_SECONDS=60`) prevents conversation spam but does not prevent gating spam when many agents cluster.

**Why it happens:**
The current code has `break` after the first nearby agent check (line 366 in `engine.py`): it only checks the closest agent. But the refactored version may process all nearby agents before breaking, or the `break` may be removed during refactoring without noticing its purpose.

**How to avoid:**
The existing `break` on line 366 is load-bearing — it ensures at most one gating LLM call per tick per agent. Do not remove it during refactoring. Additionally, add a fast pre-filter before the LLM gating call: if the nearby agent is already in a conversation (track this with an `in_conversation: bool` flag on `AgentState`), skip the gating LLM call entirely and try the next candidate. The most important guard is to sort `perception.nearby_agents` by distance and only gate-check the single closest agent who is not on cooldown and not already in conversation.

**Warning signs:**
- LLM call count per tick exceeds `(number of agents) * 2`
- `attempt_conversation` appears in LLM call logs multiple times per agent per tick
- Removing the `break` during refactor is followed by 3-5x increase in per-tick latency

**Phase to address:** LLM Optimization phase. The `break` in `engine.py` line 366 must be explicitly preserved with a code comment explaining its purpose during OOP refactoring.

---

### Pitfall 8: Reflection Poignancy Accumulator Is Per-Process, Resets on Server Restart With No Persistence

**What goes wrong:**
The reflection system accumulates poignancy scores between reflection events. The accumulator (e.g., `agent.poignancy_sum: float`) lives in the `Agent` class or `AgentState` dataclass. When the FastAPI server restarts (deployment, code change, crash recovery), all in-memory accumulators reset to 0. Agents that were close to the reflection threshold never trigger it after a restart — they silently lose the accumulated emotional weight. This is invisible to users but means reflection never fires correctly in long sessions with any server restart.

**Why it happens:**
The poignancy accumulator is naturally placed in-memory because it changes every tick. Developers do not think of it as persistent state because it is not a user-visible field. But it is part of the agent's cognitive state that must survive restarts if the simulation is meant to run for hours.

**How to avoid:**
Store `poignancy_sum` per agent in ChromaDB metadata or as a special memory type ("poignancy_checkpoint") so it survives restarts. On `engine.initialize()`, retrieve the last stored poignancy value for each agent and restore the accumulator from it. Since this is written infrequently (only when the value changes meaningfully), the storage cost is negligible. Alternatively, if restart survival is deferred, document clearly that reflection behavior resets on server restart and that long simulation sessions should not restart the server.

**Warning signs:**
- Reflection never triggers in tests that restart the server between steps
- Agents in a long-running session never show reflection behavior despite many high-importance events
- `poignancy_sum` is always 0 on the second run of a simulation test

**Phase to address:** Reflection System phase. Decide at the start of this phase whether poignancy persistence is required for v1.1 or explicitly deferred, and document it.

---

### Pitfall 9: Reflection LLM Call Fires Inside the Agent Tick, Blocking the Movement Loop

**What goes wrong:**
The reflection call is expensive — it retrieves the 100 most poignant memories, runs a summarization LLM call (much longer prompt than decide_action), and stores the result. If reflection is triggered inside `_agent_step()` synchronously, it blocks that agent's tick coroutine for 5-20 seconds. Because `asyncio.wait_for(timeout=60s)` wraps each agent step, a reflection call that takes 20 seconds still completes, but the agent misses 4 movement loop cycles during that time (the movement loop runs every 500ms, but the agent's position is not updated while the coroutine is suspended in the LLM call). Visually, the agent freezes for 20 seconds mid-walk.

**Why it happens:**
Reflection is naturally placed at the end of an agent step (after deciding action) when the poignancy threshold is crossed. This is correct architecturally but wrong for the real-time UX when the call is slow.

**How to avoid:**
Fire reflection as a background `asyncio.create_task()`, not inline in `_agent_step()`. The agent continues its normal tick (perception → decide → move) while reflection runs concurrently in the background. Guard the background task with a per-agent `_reflecting: bool` flag to prevent double-triggering if the threshold is crossed again before the first reflection completes. When the background task finishes, store the reflection memory and reset the poignancy accumulator. Use `asyncio.create_task()` not `asyncio.ensure_future()` (the latter is deprecated in Python 3.10+).

**Warning signs:**
- Agent freezes for 10-20 seconds at apparently random intervals during long simulations
- `asyncio.wait_for` timeout fires specifically when poignancy threshold is crossed
- Reflection appears in LLM call logs as taking 5x longer than decide_action calls

**Phase to address:** Reflection System phase. The background task pattern must be designed before the reflection LLM call is implemented.

---

### Pitfall 10: Changing TICK_INTERVAL From 30 to a Shorter Value Breaks the `asyncio.wait_for` Timeout Guard

**What goes wrong:**
`TICK_INTERVAL = 30` in `engine.py`. The timeout guard is `asyncio.wait_for(..., timeout=TICK_INTERVAL * 2)` = 60 seconds. If `TICK_INTERVAL` is reduced to 5 or 10 seconds for better responsiveness, the timeout becomes 10 or 20 seconds. With Ollama on a laptop, a single LLM call can take 8-15 seconds. The 3-call chain (sector → arena → object) could take 24-45 seconds. The timeout fires mid-agent-step, the agent is skipped, and the agent's activity is never updated that tick. With many agents skipping ticks due to timeout, the simulation diverges: some agents act every tick, others act once every 3-5 ticks.

**Why it happens:**
`TICK_INTERVAL * 2` as a timeout seemed sensible when all LLM calls completed in 1-5 seconds against OpenRouter. Ollama call times are 3-4x longer and not accounted for in the timeout multiplier.

**How to avoid:**
Decouple the timeout from `TICK_INTERVAL`. Define `AGENT_STEP_TIMEOUT_SECONDS` as an independent constant, defaulting to 120 seconds (2 minutes), regardless of tick interval. This allows short tick intervals (fast movement, responsive UI) while giving slow LLM agents time to complete their calls. Emit a warning (not a silent skip) when an agent step times out, so users running Ollama can see when their LLM is too slow for the simulation. Consider surfacing an estimated "recommended tick interval" based on measured LLM call latency.

**Warning signs:**
- Timeout warnings appear in logs immediately after reducing `TICK_INTERVAL`
- Agents appear to act irregularly — some acting every tick, others skipping multiple ticks
- `AGENT_STEP_TIMEOUT_SECONDS` and `TICK_INTERVAL` are the same variable

**Phase to address:** LLM Optimization / Tick Timing phase. The first thing to do when changing `TICK_INTERVAL` is update the timeout constant independently.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Keep `AgentState` dataclass as-is and add `Agent` class alongside it | No engine refactor needed, ships fast | Two sources of truth for agent runtime state; state drift bugs in edge cases | Only if `Agent` class methods are pure functions that take `AgentState` as a parameter (no hidden state copy) |
| Implement reflection poignancy accumulator as in-memory only | No persistence logic needed | Reflection never fires correctly after any server restart in long sessions | v1.1 if explicitly documented; must be fixed in v1.2 before public launch |
| Skip the conversation gating `in_conversation` flag | Simpler AgentState schema | Agents can gate-check each other while already in a conversation, wasting LLM calls | Never — the guard is cheap (a bool flag) and the cost without it is high |
| Add wall tiles without re-running cross-validation integration test | Faster map iteration | Agents spawn inside walls and freeze silently, invisible until manual testing | Never — the validation test runs in under 5 seconds |
| Use `zIndex` sorting for map layer ordering in PixiJS | Simple to implement | Performance regressions at scale (zIndex triggers array re-sort on every render) | Acceptable for static map layers that never change order; not for agent sprites |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `Agent` class + `store.py` ChromaDB singleton | Moving `EphemeralClient` into `Agent.__init__`, creating multiple in-memory databases | Keep `_chroma_client` module-level in `store.py`; `Agent` calls module functions, never creates its own client |
| `engine.py` + new `Agent` class | Importing `Agent` in `engine.py` AND importing anything from `simulation/` in `agents/agent.py` | Dependency direction: `schemas` → `agents` → `engine`; never reverse; use constructor injection for `Maze` |
| PixiJS `drawMap` callback + `town.json` wall data | Routing wall tile data through Zustand store, subscribing in the draw callback deps | Pre-compute `WALL_TILES` at module load time from static `town.json`; keep deps array `[]` |
| 3-level LLM decision + real-time tick | Calling all 3 levels unconditionally every tick | Gate arena/object calls behind sector-requires-room-selection check; most agents use 1 call |
| Reflection trigger + agent step coroutine | Triggering reflection inline in `_agent_step()` | Use `asyncio.create_task()` for reflection; protect with `_reflecting: bool` flag to prevent double-trigger |
| Conversation gating + multiple nearby agents | Removing the `break` in the nearby-agent loop during refactor | The `break` after the first conversation gate check is load-bearing; document it explicitly in the refactored code |
| Poignancy accumulator + server restart | Storing accumulator only in-memory | Store last value as ChromaDB metadata or a "checkpoint" memory entry; restore on `initialize()` |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| `drawMap` callback re-running on store updates | Canvas flickers every 500ms movement tick; FPS drops from 60 to 15-20 | Keep all wall/sector data as module-level constants; never subscribe to Zustand in `drawMap` deps | Immediately when any Zustand selector is added to the `useCallback` deps array |
| 3 LLM calls per agent per tick unconditionally | Tick wall time exceeds `TICK_INTERVAL`; `asyncio.wait_for` timeouts fire for all agents | Gate arena/object calls behind necessity check; measure average calls/tick in staging | At 8+ agents with Ollama; at 5+ agents with cloud provider under rate limits |
| Reflection blocking the movement loop | Agent freezes for 15-20 seconds mid-walk | Fire reflection as `asyncio.create_task()`; decouple from agent step coroutine | Every time poignancy threshold is crossed with a slow LLM |
| Conversation gating for all nearby agents | 3x increase in per-tick LLM calls when agents cluster | Only gate-check the single closest eligible agent per tick | When 3+ agents share a sector simultaneously (common in stock exchange, wedding hall scenarios) |
| BFS on 100x100 grid with new wall tiles | Pathfinding takes 20-50ms per call; with 8 agents concurrent, that is 160-400ms of CPU per tick | BFS is already O(N) on walkable tiles; new walls reduce N, improving performance; no special action needed | Does not break but worth measuring if walls create many isolated small sub-graphs |

---

## "Looks Done But Isn't" Checklist

These are features that appear complete during development but have hidden failure modes only visible in integration or after refactoring.

- [ ] **OOP refactor preserves singleton ChromaDB client** — verify `_chroma_client` is still a module-level singleton after refactor; run `assert store._chroma_client is store._chroma_client` (identity check, not equality).
- [ ] **Circular import absence** — run `python -c "from backend.agents.agent import Agent; from backend.simulation.engine import SimulationEngine"` as a CI check; must not raise `ImportError`.
- [ ] **Single source of truth for agent runtime state** — after refactor, verify `engine.get_snapshot()` and `Agent.to_dict()` (or equivalent) return identical coord/activity for the same agent.
- [ ] **Wall tiles validated against agent spawn coords** — re-run the Phase 2 cross-validation test after any `town.json` change; test must assert no agent spawns on a collision tile.
- [ ] **drawMap runs once** — use React DevTools Profiler flamegraph; `drawMap` should appear in exactly one render and never again. Any subsequent appearance indicates a deps array regression.
- [ ] **Per-tick LLM call count is bounded** — log LLM call count per tick; assert average is <= 1.5 calls per agent per tick (allowing for occasional 2-call sector+arena decisions).
- [ ] **Reflection fires at threshold, not before** — add a test that stores N-1 high-importance memories (below threshold) and verifies no reflection; then adds one more and verifies exactly one reflection triggers.
- [ ] **Reflection does not block agent movement** — verify via timing logs that agent position updates continue at 500ms intervals even while a reflection background task is running.
- [ ] **TICK_INTERVAL change does not break timeout guard** — after any `TICK_INTERVAL` change, verify `AGENT_STEP_TIMEOUT_SECONDS` is still set independently and not derived from `TICK_INTERVAL * 2`.
- [ ] **Conversation gating break is preserved** — search `engine.py` (or the refactored equivalent) for the conversation loop; confirm exactly one `break` after the first gate check; confirm no PR removes it silently.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Circular import discovered after OOP refactor ships | MEDIUM | Extract the shared type into `schemas.py` as a `Protocol`; update both modules to import from `schemas`; no behavior change required |
| Agent spawns on collision tile after map update | LOW | Add snap-to-nearest-walkable logic to `initialize()`; re-run cross-validation test; update offending agent config coord |
| `drawMap` re-running discovered post-merge | LOW | Identify the Zustand selector added to deps array; move to module-level constant; verify with profiler |
| Reflection blocking tick discovered in QA | MEDIUM | Wrap reflection call in `asyncio.create_task()`; add `_reflecting` guard flag; test that movement loop continues uninterrupted during reflection |
| Poignancy accumulator lost on restart discovered in long-session testing | MEDIUM | Add `poignancy_checkpoint` write to ChromaDB on every accumulator increment above a delta threshold; add restore logic in `initialize()` |
| 3-level LLM calls causing tick overrun discovered in load test | MEDIUM | Add `requires_room_selection: bool` field to sector config in `town.json`; gate arena/object calls behind this flag; re-benchmark |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| ChromaDB singleton broken by OOP refactor | OOP Refactoring | `assert store._chroma_client is store._chroma_client` in CI |
| Circular import from Agent/Engine mutual dependency | OOP Refactoring | `python -c "import backend.agents.agent; import backend.simulation.engine"` as smoke test |
| Duplicate AgentState / Agent class state drift | OOP Refactoring | Test that `engine.get_snapshot()` matches `Agent` class state after mutation |
| Agent spawning on collision tile after wall map update | Visual Overhaul (Building Walls) | Re-run Phase 2 cross-validation test against new town.json |
| `drawMap` re-running on store updates | Visual Overhaul (Building Walls) | React DevTools Profiler: drawMap appears in exactly one render |
| 3-level decision tripling LLM call count per tick | LLM Optimization | Per-tick LLM call count log; assert avg <= 1.5 calls per agent |
| Conversation gating firing for all nearby agents | LLM Optimization | Confirm `break` after first gate check is preserved; per-tick call count check |
| TICK_INTERVAL change breaking timeout guard | LLM Optimization / Tick Timing | `AGENT_STEP_TIMEOUT_SECONDS` defined independently; verified after any `TICK_INTERVAL` change |
| Reflection poignancy accumulator lost on restart | Reflection System | Integration test: store poignancy, restart server, verify accumulator restored |
| Reflection blocking movement loop | Reflection System | Timing log: verify 500ms position updates continue during reflection background task |

---

## Sources

- [Asyncio race conditions and shared state (Inngest Blog)](https://www.inngest.com/blog/no-lost-updates-python-asyncio) — HIGH confidence (technical deep-dive with specific asyncio primitive gaps)
- [Circular imports in Python: causes, fixes, best practices (DataCamp)](https://www.datacamp.com/tutorial/python-circular-import) — HIGH confidence (official patterns, cross-verified with Python docs)
- [Avoiding circular imports in Python (Brex Tech Blog)](https://medium.com/brexeng/avoiding-circular-imports-in-python-7c35ec8145ed) — HIGH confidence (production engineering blog, specific Protocol-based solution)
- [Banish state-mutating methods from data classes (Redowan's Reflections)](https://rednafi.com/python/dataclasses-and-methods/) — HIGH confidence (canonical reference for OOP vs dataclass boundary)
- [Fixing circular imports with typing.Protocol (PythonTest)](https://pythontest.com/fix-circular-import-python-typing-protocol/) — MEDIUM confidence (specific to Python typing, patterns verified with Python 3.11+ docs)
- [PixiJS v8 Graphics API (official)](https://pixijs.download/v8.0.0/docs/scene.Graphics.html) — HIGH confidence (official docs)
- [PixiJS: Optimizing rendering with v8 Culling API (Richard Fu)](https://www.richardfu.net/optimizing-rendering-with-pixijs-v8-a-deep-dive-into-the-new-culling-api/) — MEDIUM confidence (community author, patterns match official PixiJS v8 migration guide)
- [Improving PIXI Graphics Performance (pixijs/pixijs Discussion #10521)](https://github.com/pixijs/pixijs/discussions/10521) — HIGH confidence (official GitHub discussion, core contributor response)
- [Asyncio Semaphore: starvation risk (Super Fast Python)](https://superfastpython.com/asyncio-race-conditions/) — HIGH confidence (specific race condition patterns for asyncio.TaskGroup)
- [LLM parallel processing: batch size and timeout patterns (DEV Community)](https://dev.to/jamesli/llm-parallel-processing-in-practice-key-techniques-for-performance-enhancement-20g0) — MEDIUM confidence (community blog, patterns match asyncio docs)
- [Limit concurrency with asyncio.Semaphore (Redowan's Reflections)](https://rednafi.com/python/limit-concurrency-with-semaphore/) — HIGH confidence (production patterns, cross-verified with Python asyncio docs)
- Direct codebase analysis of `engine.py`, `store.py`, `retrieval.py`, `converse.py`, `TileMap.tsx`, `MapCanvas.tsx` — HIGH confidence (first-party source, patterns inferred from existing implementation)

---
*Pitfalls research for: v1.1 milestone — OOP refactoring, building walls, LLM optimization, reflection system*
*Researched: 2026-04-10*
