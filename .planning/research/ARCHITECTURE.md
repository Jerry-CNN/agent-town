# Architecture Research

**Domain:** LLM-powered agent simulation web app
**Researched:** 2026-04-08
**Confidence:** MEDIUM — core patterns HIGH (FastAPI + WebSocket + asyncio well-documented); specifics for generative-agent-style simulation inferred from reference paper + analogous systems

---

## Standard Architecture

### System Overview (ASCII diagram)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          BROWSER (React + Phaser 3)                         │
│                                                                              │
│  ┌──────────────────────┐   ┌───────────────────────────────────────────┐  │
│  │   React UI Shell     │   │          Phaser 3 Canvas                  │  │
│  │  - Event injection   │   │  - 2D tile map render (Tiled JSON)        │  │
│  │  - Agent feed panel  │   │  - Sprite agents (animated)               │  │
│  │  - Config / settings │   │  - Smooth position interpolation          │  │
│  │  - LLM key entry     │   │  - Camera pan / zoom                      │  │
│  └──────────┬───────────┘   └──────────────────┬────────────────────────┘  │
│             │  React ↔ Phaser via EventEmitter  │                            │
│             └──────────────────┬────────────────┘                           │
│                                │ WebSocket (JSON messages)                  │
└────────────────────────────────┼────────────────────────────────────────────┘
                                 │
                  ┌──────────────▼──────────────┐
                  │     FastAPI Web Layer        │
                  │  - WebSocket endpoint        │
                  │  - REST: config, save/load   │
                  │  - Connection manager        │
                  │  - Session registry          │
                  └──────────────┬──────────────┘
                                 │ asyncio internal
          ┌──────────────────────┼───────────────────────┐
          │                      │                       │
   ┌──────▼──────┐     ┌────────▼────────┐   ┌─────────▼──────────┐
   │ Simulation  │     │  Event Bus      │   │  Session Store      │
   │ Engine      │     │  (asyncio Queue │   │  (in-memory dict,   │
   │             │     │   per session)  │   │   optional JSON     │
   │ - Tick loop │     └────────┬────────┘   │   snapshots)        │
   │ - World map │              │            └────────────────────┘
   │ - BFS nav   │     ┌────────▼────────┐
   │ - Agent mgr │     │   Agent Pool    │
   └──────┬──────┘     │ (N concurrent   │
          │            │  coroutines)    │
          │            └────────┬────────┘
          │                     │
          │            ┌────────▼────────┐
          │            │  Per-Agent      │
          │            │  Cognition      │
          │            │                 │
          │            │  perceive →     │
          │            │  plan →         │
          │            │  react →        │
          │            │  act →          │
          │            │  reflect        │
          │            └────────┬────────┘
          │                     │
   ┌──────▼─────────────────────▼──────────────┐
   │               Support Layer                │
   │                                            │
   │  ┌─────────────────┐  ┌─────────────────┐ │
   │  │  Memory System  │  │  LLM Gateway    │ │
   │  │                 │  │                 │ │
   │  │  ChromaDB/FAISS │  │  litellm        │ │
   │  │  per-agent ns   │  │  - model select │ │
   │  │  recency+rel    │  │  - semaphore    │ │
   │  │  +importance    │  │    rate limit   │ │
   │  └─────────────────┘  └─────────────────┘ │
   └────────────────────────────────────────────┘
```

### Component Responsibilities (table)

| Component | Responsibility | Owns | Does NOT Own |
|-----------|---------------|------|--------------|
| **React UI Shell** | User input, config, sidebar feed, event injection form | LLM key config, event submission | Game canvas rendering, agent state |
| **Phaser 3 Canvas** | 2D tile map + sprite rendering, camera, animation | Visual representation, interpolated positions | Agent logic, WebSocket connection |
| **FastAPI Web Layer** | HTTP REST + WebSocket, session lifecycle, routing | Connection registry, session ID generation | Simulation logic |
| **Connection Manager** | Track active WebSocket connections per session | Broadcast queue flush | Simulation state |
| **Simulation Engine** | Tick clock, world grid, agent scheduling, BFS pathfinding | Authoritative world state | LLM calls, rendering |
| **Agent Pool** | Per-agent coroutine lifecycle, concurrency | Task creation/cancellation | Tick pacing (defers to engine) |
| **Agent Cognition** | perceive → plan → react → act → reflect cycle | Prompt construction, LLM response parsing | Memory storage (delegates to Memory System) |
| **Memory System** | Vector store per agent, scored retrieval, memory insertion | Embeddings, ChromaDB/FAISS collections | Cognition decisions |
| **LLM Gateway** | Unified call interface, model routing, rate limiting | litellm wrapper, semaphore, retry/fallback | Prompt content |
| **Event Bus** | asyncio.Queue per session for simulation events | In-process pub/sub | Persistence |
| **Session Store** | Serialized simulation snapshot (JSON) | Agent state, positions, memories | Real-time streaming |

---

## Recommended Project Structure

```
agent-town/
├── backend/
│   ├── main.py                        # FastAPI app entry, lifespan hooks
│   ├── api/
│   │   ├── ws.py                      # WebSocket endpoint, connection manager
│   │   ├── sessions.py                # REST: create/save/load simulation
│   │   └── config.py                  # REST: LLM provider key validation
│   ├── simulation/
│   │   ├── engine.py                  # Tick loop, world clock, agent scheduling
│   │   ├── world.py                   # TileGrid, collision map, location hierarchy
│   │   ├── pathfinding.py             # BFS on tile grid, walkability cache
│   │   └── events.py                  # Event types, broadcast/whisper routing
│   ├── agents/
│   │   ├── agent.py                   # Agent dataclass, per-agent coroutine entry
│   │   ├── cognition/
│   │   │   ├── perceive.py            # Collect nearby events/agents from world grid
│   │   │   ├── plan.py                # Daily schedule, hourly decomposition
│   │   │   ├── react.py               # Reaction decision (act vs re-plan)
│   │   │   ├── act.py                 # Emit action, update position intent
│   │   │   └── reflect.py             # Reflection trigger, insight synthesis
│   │   └── memory/
│   │       ├── store.py               # ChromaDB/FAISS wrapper, per-agent namespace
│   │       ├── retrieval.py           # Scored retrieval (recency × relevance × importance)
│   │       └── embedding.py           # Embed text via LLM or local model
│   ├── llm/
│   │   ├── gateway.py                 # litellm wrapper, model routing per call type
│   │   ├── rate_limiter.py            # asyncio.Semaphore, per-provider limits
│   │   └── prompts/                   # Prompt templates per cognition step
│   │       ├── perceive.txt
│   │       ├── plan.txt
│   │       ├── reflect.txt
│   │       └── ...
│   ├── persistence/
│   │   ├── snapshot.py                # Serialize/deserialize full simulation state
│   │   └── storage.py                 # File-based save/load (JSON + vector store dump)
│   └── config.py                      # Pydantic settings, env vars
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx                    # React root, WebSocket provider
│   │   ├── ws/
│   │   │   └── useSimulation.ts       # WebSocket hook, message dispatch
│   │   ├── ui/
│   │   │   ├── EventPanel.tsx         # Event injection input
│   │   │   ├── AgentFeed.tsx          # Real-time thought/action log
│   │   │   ├── ConfigModal.tsx        # LLM provider + key settings
│   │   │   └── AgentCount.tsx         # Spawn config
│   │   ├── game/
│   │   │   ├── PhaserGame.tsx         # React wrapper, Phaser instance ref
│   │   │   ├── scenes/
│   │   │   │   ├── TownScene.ts       # Main scene: tilemap + sprites
│   │   │   │   └── PreloadScene.ts    # Asset loading
│   │   │   ├── entities/
│   │   │   │   └── AgentSprite.ts     # Sprite + name label + interpolation
│   │   │   └── EventBridge.ts         # EventEmitter between React and Phaser
│   │   └── store/
│   │       └── simulation.ts          # Zustand store: agent states, event log
│   └── public/
│       └── assets/
│           ├── tilemaps/              # Tiled JSON map files
│           ├── tilesets/              # Tile sprite sheets
│           └── sprites/               # Agent character sprites
│
└── data/
    └── saves/                         # JSON snapshots of saved simulations
```

---

## Architectural Patterns

### Pattern 1: Tick-Driven Simulation with Concurrent Agent Coroutines

**What:** A central simulation engine advances a tick counter and signals all agents to run their cognition cycle. Each agent is an independent asyncio coroutine that yields at every LLM `await` call, letting other agents progress concurrently.

**When:** Multi-agent simulation where agents are loosely coupled and can run in parallel within a tick.

```python
# engine.py
class SimulationEngine:
    def __init__(self, agents: list[Agent], tick_interval: float = 5.0):
        self.agents = agents
        self.tick_interval = tick_interval
        self.tick = 0
        self.running = False

    async def run(self):
        self.running = True
        while self.running:
            self.tick += 1
            # All agents run their tick concurrently; LLM awaits yield control
            await asyncio.gather(*[agent.run_tick(self.tick) for agent in self.agents])
            await asyncio.sleep(self.tick_interval)

# agent.py
class Agent:
    async def run_tick(self, tick: int):
        percepts = await self.perceive()      # reads world grid, no LLM call
        reaction = await self.react(percepts) # LLM call — yields here
        action = await self.act(reaction)     # may include LLM call
        await self.maybe_reflect(tick)        # LLM call only if threshold met
        return action
```

### Pattern 2: Event Bus (asyncio.Queue) for Decoupled Simulation Events

**What:** Simulation events (agent moved, conversation started, user event injected) are pushed onto a session-scoped asyncio.Queue. A separate broadcaster coroutine drains the queue and sends WebSocket messages.

**When:** Prevents tight coupling between simulation logic and WebSocket transport; simulation doesn't know or care about the frontend.

```python
# ws.py
class ConnectionManager:
    def __init__(self):
        self.sessions: dict[str, asyncio.Queue] = {}
        self.connections: dict[str, WebSocket] = {}

    async def broadcaster(self, session_id: str):
        queue = self.sessions[session_id]
        ws = self.connections[session_id]
        while True:
            msg = await queue.get()
            try:
                await ws.send_json(msg)
            except WebSocketDisconnect:
                break

# simulation/events.py — simulation pushes events without knowing about WS
async def emit(session_id: str, event: dict, event_bus: dict[str, asyncio.Queue]):
    await event_bus[session_id].put(event)
```

### Pattern 3: LLM Gateway with Model Routing and Semaphore Rate Limiting

**What:** A single `llm_call(call_type, prompt, config)` function routes to cheap vs. expensive models based on call type, and uses an asyncio.Semaphore to cap simultaneous in-flight LLM requests (prevents API 429s and runaway cost).

**When:** Always — without this, 10 agents each making 10 LLM calls per tick = 100 concurrent requests, which will hit rate limits.

```python
# llm/gateway.py
import litellm
import asyncio

CALL_TYPE_MODELS = {
    "perceive":   "openai/gpt-4o-mini",    # cheap: routine classification
    "plan":       "openai/gpt-4o-mini",    # cheap: schedule generation
    "react":      "openai/gpt-4o",         # expensive: nuanced reaction
    "reflect":    "openai/gpt-4o",         # expensive: synthesis
    "converse":   "openai/gpt-4o-mini",    # cheap: dialogue turns
}

_semaphore = asyncio.Semaphore(20)  # max 20 concurrent LLM calls globally

async def llm_call(call_type: str, prompt: str, user_config: dict) -> str:
    model = CALL_TYPE_MODELS.get(call_type, "openai/gpt-4o-mini")
    # Override model from user config if set
    if override := user_config.get(f"model_{call_type}"):
        model = override
    async with _semaphore:
        response = await litellm.acompletion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            api_key=user_config["api_key"],
            api_base=user_config.get("api_base"),  # for Ollama
        )
    return response.choices[0].message.content
```

### Pattern 4: React-Phaser Bridge via EventEmitter

**What:** React owns WebSocket state and dispatches messages into the Phaser game via a shared EventEmitter ref. Phaser never opens its own WebSocket — it receives data from React.

**When:** When combining React UI (controls, panels) with Phaser canvas (rendering) — this prevents two separate WebSocket connections and keeps React as the single source of truth for server state.

```typescript
// game/EventBridge.ts
import Phaser from "phaser";
export const EventBridge = new Phaser.Events.EventEmitter();

// ws/useSimulation.ts (React hook)
ws.onmessage = (e) => {
  const msg = JSON.parse(e.data);
  if (msg.type === "agent_moved") {
    EventBridge.emit("agent_moved", msg.payload);
  } else if (msg.type === "agent_thought") {
    // update Zustand store → AgentFeed renders
    simulationStore.getState().addThought(msg.payload);
  }
};

// game/entities/AgentSprite.ts (Phaser scene)
EventBridge.on("agent_moved", ({ agent_id, x, y }) => {
  const sprite = this.agentSprites.get(agent_id);
  // Tween for smooth interpolation between current and target position
  this.tweens.add({ targets: sprite, x: x * TILE_SIZE, y: y * TILE_SIZE, duration: 800 });
});
```

### Pattern 5: Per-Agent Memory Namespace (ChromaDB)

**What:** Each agent gets an isolated ChromaDB collection or FAISS index keyed by `agent_id`. Retrieval uses a composite score: `recency × 0.5 + relevance × 3 + importance × 2`.

**When:** Agents must not share memories. Namespace isolation prevents cross-contamination and allows per-agent memory dumps for save/load.

```python
# agents/memory/store.py
import chromadb

_chroma_client = chromadb.Client()

def get_agent_collection(agent_id: str):
    return _chroma_client.get_or_create_collection(f"agent_{agent_id}")

async def add_memory(agent_id: str, content: str, importance: float, embedding: list[float]):
    col = get_agent_collection(agent_id)
    col.add(
        documents=[content],
        embeddings=[embedding],
        metadatas=[{"importance": importance, "created_at": time.time(), "last_access": time.time()}],
        ids=[str(uuid.uuid4())],
    )

# agents/memory/retrieval.py
def score_memory(meta: dict, query_embedding: list[float], doc_embedding: list[float]) -> float:
    now = time.time()
    recency = 0.99 ** ((now - meta["last_access"]) / 3600)   # exponential decay per hour
    relevance = cosine_similarity(query_embedding, doc_embedding)
    importance = meta["importance"] / 10.0
    return recency * 0.5 + relevance * 3.0 + importance * 2.0
```

---

## Data Flow

### Simulation Loop Flow

```
SimulationEngine.tick()
    │
    ├── asyncio.gather(agent.run_tick() for all agents)
    │       │
    │       ├── agent.perceive()
    │       │       Reads world grid (no LLM) → collect nearby events/agents within radius
    │       │
    │       ├── agent.react(percepts)
    │       │       LLM call (gateway → litellm → provider API)
    │       │       ← reaction decision: continue / interrupt / initiate conversation
    │       │
    │       ├── agent.act(reaction)
    │       │       Update position intent → pathfinding.next_step(from, to)
    │       │       Emit action event → event_bus.put({type: "agent_moved", ...})
    │       │       If conversation: LLM call per dialogue turn
    │       │
    │       └── agent.maybe_reflect(tick)
    │               Check poignancy threshold; if met:
    │               LLM call → generate insight → memory.add_memory(insight, ...)
    │
    └── asyncio.sleep(tick_interval)
```

### Real-time Update Flow

```
event_bus.put(event)               [Simulation Engine]
    │
    └── broadcaster coroutine wakes
            │
            └── ws.send_json(event)         [FastAPI WebSocket layer]
                    │
                    └── useSimulation hook receives message  [React]
                            │
                            ├── (visual events) EventBridge.emit(...)  → Phaser canvas
                            │       │
                            │       └── AgentSprite.tween() to new position
                            │
                            └── (log events) simulationStore.addThought(...)  → AgentFeed renders
```

### Event Injection Flow

```
User types event in EventPanel → submit
    │
    └── ws.send_json({type: "inject_event", mode: "broadcast"|"whisper", target_agent_id?, content})
            │
            └── FastAPI WebSocket receives
                    │
                    └── simulation.events.handle_injection(mode, content, target?)
                            │
                            ├── broadcast: world.broadcast_event(content) → all agents perceive at next tick
                            │
                            └── whisper: target_agent.inject_private_event(content)
                                    → agent perceives it; during next conversation, may share it organically
```

---

## Scaling Considerations

| Concern | Single simulation (5-10 agents) | 25 agents | Future: multiple sessions |
|---------|--------------------------------|-----------|--------------------------|
| **LLM concurrency** | Semaphore(20) fine | Watch 429 rate limits; use cheaper models for routine calls | Per-session semaphores or global shared limit |
| **Memory / ChromaDB** | In-process client fine | In-process fine; FAISS if ChromaDB shows memory pressure | Persistent ChromaDB server or Qdrant per-session namespace |
| **WebSocket** | Single connection per session, single FastAPI process | Same; asyncio handles thousands of connections | Redis Pub/Sub as message bus between multiple FastAPI instances |
| **Tick pacing** | 5s tick; asyncio.gather covers all agents | Tick may drift if LLM calls take >5s; cap agents or increase tick interval | Separate worker process per session via multiprocessing |
| **World state** | In-memory dict | In-memory fine | Shared state store (Redis) for multi-process scaling |

Key decisions for MVP scale (5-25 agents, single user):
- In-process ChromaDB, no external services required
- Single FastAPI process with uvicorn, no Redis needed
- asyncio.Semaphore(15-20) for global LLM rate limiting
- Tick interval 5-10 seconds; increase if LLM calls saturate

---

## Anti-Patterns

### Anti-Pattern 1: Blocking LLM Calls Inside asyncio Event Loop
**What goes wrong:** Using synchronous `litellm.completion()` instead of `litellm.acompletion()` inside an async function blocks the entire event loop — all WebSocket connections, all other agents, all broadcasts freeze until that one LLM call returns.
**Instead:** Always use async LLM clients (`litellm.acompletion`, `openai.AsyncOpenAI`). If a library has no async API, run it in a thread: `await asyncio.to_thread(sync_fn, args)`.

### Anti-Pattern 2: Serverless / Function-as-a-Service Deployment
**What goes wrong:** AWS Lambda, Vercel Functions, Cloudflare Workers have request timeouts (15s-5min) and stateless execution — incompatible with long-running WebSocket connections and the simulation tick loop.
**Instead:** Use a persistent, long-lived process: uvicorn on a VPS or container. A single DigitalOcean Droplet (4GB RAM) handles this simulation fine.

### Anti-Pattern 3: Phaser Opening Its Own WebSocket
**What goes wrong:** Phaser and React end up with separate, unsynchronized views of server state; React UI controls fight with Phaser for the connection; reconnection logic must be duplicated.
**Instead:** React owns the single WebSocket. Phaser receives data via an in-process EventEmitter (EventBridge pattern). React is the source of truth; Phaser is a dumb renderer.

### Anti-Pattern 4: Sequential Per-Agent Processing
**What goes wrong:** Running agents one-at-a-time (the reference implementation pattern) means tick time scales linearly with agent count. 10 agents × 3 LLM calls × 2s each = 60s per tick minimum.
**Instead:** `asyncio.gather()` all agent coroutines. LLM I/O awaits yield the event loop, so all agents' LLM calls can be in-flight simultaneously. Actual wall-clock tick time approaches the slowest single agent's call chain, not the sum.

### Anti-Pattern 5: Single Monolithic Agent State Object (Shared Mutable)
**What goes wrong:** Multiple coroutines reading/writing a shared agent dict causes race conditions. Python's asyncio is single-threaded, so true races require explicit await context switches — but bugs are subtle and hard to reproduce.
**Instead:** Each `Agent` object is exclusively owned by its own coroutine. Only the `SimulationEngine` reads agent public state (position, current_activity) between ticks, with no writes.

### Anti-Pattern 6: Storing Full Conversation History in Agent Memory Vector Store
**What goes wrong:** Verbatim conversation logs bloat the vector store and degrade retrieval quality. The embedding model treats low-signal conversational tokens as meaningful.
**Instead:** Extract observations from conversations ("Agent X told me about the stock market crash") and store those observations. Store verbatim text only in a relational/JSON log for display purposes.

---

## Integration Points

| Integration | Direction | Protocol | Key Concern |
|-------------|-----------|----------|-------------|
| Frontend → Backend | Bidirectional | WebSocket (JSON messages) | Message schema versioning; reconnect logic on drop |
| Backend → LLM Provider | Outbound | HTTPS REST (via litellm) | API key per session; rate limits; timeout handling |
| Agent Cognition → Memory | Internal | Function calls (Python) | Embedding cost; retrieval latency per tick |
| Simulation Engine → World | Internal | In-memory object access | No I/O; pure computation |
| Simulation → Event Bus | Internal | asyncio.Queue.put() | Non-blocking; queue backpressure if WS is slow |
| Persistence → Disk | Internal | JSON file + ChromaDB persist() | Snapshot consistency (agent state + memories must be co-serialized) |
| Phaser ↔ React | In-browser | Phaser.Events.EventEmitter | No shared React state; one-way data flow from React → Phaser |

### WebSocket Message Schema

All WebSocket messages share a common envelope:

```json
{
  "type": "agent_moved | agent_thought | agent_conversation | agent_action | inject_event | sim_tick | error",
  "session_id": "uuid",
  "tick": 42,
  "payload": { ... }
}
```

Client-to-server message types:
- `inject_event` — user sends event; payload: `{mode, content, target_agent_id?}`
- `start_sim` — start simulation; payload: `{agent_count, llm_config}`
- `pause_sim` / `resume_sim`
- `save_sim` / `load_sim` — persist/restore state

Server-to-client message types:
- `agent_moved` — payload: `{agent_id, from: {x,y}, to: {x,y}}`
- `agent_thought` — payload: `{agent_id, thought, tick}`
- `agent_conversation` — payload: `{agent_a, agent_b, turn, text}`
- `agent_action` — payload: `{agent_id, action_type, description}`
- `sim_tick` — payload: `{tick, sim_time_str, agent_summaries[]}`

---

## Build Order (Phase Implications)

Component dependencies determine build order. Each layer requires the one below it.

```
Layer 0 (foundation):
  world.py (TileGrid) + pathfinding.py
  → No external deps; pure Python data structures

Layer 1 (cognition backbone):
  llm/gateway.py (litellm wrapper + semaphore)
  agents/memory/store.py + retrieval.py (ChromaDB)
  → Requires: Layer 0 concepts; can be built standalone with unit tests

Layer 2 (agent cognition):
  agents/cognition/ (perceive → plan → react → act → reflect)
  → Requires: Layer 1 (LLM gateway + memory); Layer 0 (world for perceive)

Layer 3 (simulation loop):
  simulation/engine.py (tick loop + agent pool)
  simulation/events.py (event routing)
  → Requires: Layer 2 (agents); Layer 0 (world)

Layer 4 (API + transport):
  api/ws.py (WebSocket + connection manager + broadcaster)
  api/sessions.py (REST create/save/load)
  → Requires: Layer 3 (engine to start)

Layer 5 (frontend):
  Phaser 3 canvas (tilemap, sprites, interpolation)
  React UI shell (panels, event injection)
  WebSocket hook + EventBridge
  → Requires: Layer 4 (server protocol defined)
```

Suggested phase order for roadmap:
1. **World + Pathfinding** — pure data layer, testable offline
2. **LLM Gateway + Memory** — agent intelligence primitives
3. **Agent Cognition Loop** — single-agent think cycle, test with mock world
4. **Simulation Engine** — multi-agent tick loop, CLI or minimal API
5. **FastAPI + WebSocket** — real-time transport layer
6. **React + Phaser Frontend** — visual layer consumes the protocol
7. **Event Injection + Persistence** — complete user-facing features

---

## Sources

- Park et al., "Generative Agents: Interactive Simulacra of Human Behavior" (2023) — [ACM DL](https://dl.acm.org/doi/fullHtml/10.1145/3586183.3606763) / [arXiv:2304.03442](https://arxiv.org/abs/2304.03442) — HIGH confidence (primary source for agent architecture)
- Render.com, "Building Real-Time AI Chat: WebSockets, LLM Streaming, and Session Management" — [article](https://render.com/articles/real-time-ai-chat-websockets-infrastructure) — HIGH confidence for web service + background worker + pub-sub pattern
- FastAPI Official Docs, "WebSockets" — [fastapi.tiangolo.com](https://fastapi.tiangolo.com/advanced/websockets/) — HIGH confidence
- LiteLLM Docs — [docs.litellm.ai](https://docs.litellm.ai/docs/) — HIGH confidence for multi-provider abstraction
- Phaser.io, "Official Phaser 3 and React Template" — [phaser.io](https://phaser.io/news/2024/02/official-phaser-3-and-react-template) — MEDIUM confidence (integration confirmed, WS pattern inferred)
- Redowan's Reflections, "Limit concurrency with semaphore in Python asyncio" — [rednafi.com](https://rednafi.com/python/limit-concurrency-with-semaphore/) — HIGH confidence for semaphore rate limiting pattern
- Victor Dibia, "Integrating AutoGen Agents into Your Web Application (FastAPI + WebSockets + Queues)" — [newsletter](https://newsletter.victordibia.com/p/integrating-autogen-agents-into-your) — MEDIUM confidence for queue + broadcaster pattern
- deepwiki, "Vector Database and FAISS Integration in agent-zero" — [deepwiki.com](https://deepwiki.com/frdel/agent-zero/4.1-vector-database-and-faiss-integration) — MEDIUM confidence for per-agent namespace pattern
- Python asyncio official docs, "Coroutines and Tasks" — [python.org](https://docs.python.org/3/library/asyncio-task.html) — HIGH confidence for asyncio.gather pattern
