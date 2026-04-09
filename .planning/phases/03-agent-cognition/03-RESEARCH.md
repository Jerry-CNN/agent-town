# Phase 3: Agent Cognition - Research

**Researched:** 2026-04-09
**Domain:** LLM-powered agent cognition — memory stream, perception, schedule planning, decision-making, multi-turn conversation
**Confidence:** HIGH — core patterns verified from reference implementation (GenerativeAgentsCN) and existing codebase (Phases 1-2 outputs)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Memory System**
- D-01: ChromaDB for vector storage. One collection per simulation. Memories stored with metadata: agent_id, timestamp, importance score (1-10), memory type (observation/conversation/action/event).
- D-02: Retrieval scoring uses the reference paper's composite formula: recency x 0.5 + relevance x 3 + importance x 2. Relevance comes from ChromaDB vector similarity, recency is exponential decay from timestamp, importance is stored metadata.
- D-03: Importance scores assigned by LLM — each memory gets a 1-10 importance rating via an LLM call at storage time. Costs 1 extra call per memory but enables the full composite scoring.
- D-04: "Everything significant" gets stored: observations, conversations, actions taken, events perceived.
- D-05: Retrieval returns top 5-10 memories per decision query.

**Perception Model**
- D-06: Tile-based vision radius (~5 tiles, Manhattan or Euclidean distance).
- D-07: Agents perceive: other agents (name, current activity), injected events within radius, and location context (sector/arena name).

**Schedule & Planning**
- D-08: Two-level schedule: LLM generates hourly blocks, then decomposes each hour into 5-15 minute sub-tasks. 2 LLM calls per full schedule.
- D-09: Hybrid daily routines — config provides rough template, LLM expands into full hourly+sub-task schedule.
- D-10: Replanning triggers after conversations and significant events.

**Conversation System**
- D-11: Conversation trigger: proximity + LLM check.
- D-12: Conversations last 2-4 turns with natural ending, capped at ~4 turns.
- D-13: After conversation ends, each agent gets an LLM call to revise remaining daily schedule.

### Claude's Discretion
- Embedding model choice for ChromaDB (default all-MiniLM-L6-v2 is likely fine)
- Exact perception radius value (reference uses ~5 tiles — adjust for 100x100 map feel)
- Conversation initiation cooldown to prevent chat spam
- Prompt templates for each cognition call type (schedule generation, perception reaction, memory importance, conversation, schedule revision)
- How to structure the "decision" LLM call that picks an agent's next action (AGT-04)

### Deferred Ideas (OUT OF SCOPE)
- Reflection system (AGT-09) — agents form higher-level insights from accumulated memories. Deferred to v2.
- Relationship models (AGT-10) — agents track and update mental models of other agents. Deferred to v2.
- Poignancy threshold for triggering reflection — not needed without reflection system.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AGT-02 | Agents autonomously plan daily schedules and decompose into sub-tasks | Two-level schedule pattern from reference: `make_schedule()` → hourly blocks → `schedule_decompose` LLM call. Uses `AgentScratch.daily_plan` as seed. |
| AGT-03 | Agents perceive nearby events and other agents within a vision radius | Reference `percept()` reads tile grid for events within Manhattan/Euclidean radius. Existing `Maze.tile_at()` and tile `_events` dict ready for use. |
| AGT-04 | Agents make LLM-powered decisions about what to do next based on perceptions and plans | `_determine_action()` pattern from reference: sector → arena → object resolution via LLM. `complete_structured()` in gateway.py handles structured output. |
| AGT-05 | Memory stream stores experiences weighted by recency, relevance, and importance | ChromaDB collection per simulation, metadata fields: agent_id, importance, timestamp, memory_type. Composite scoring implemented in retrieval. |
| AGT-06 | Agents retrieve relevant memories when making decisions (composite scoring retrieval) | Score formula: `recency_decay^hours * 0.5 + cosine_similarity * 3 + importance/10 * 2`. Reference `AssociateRetriever._normalize()` shows exact normalization pattern. |
| AGT-07 | Agents initiate multi-turn conversations with nearby agents based on context | Reference `_chat_with()`: cooldown check → LLM decide_chat → multi-turn loop with end check. Up to 4 turns, repeat detection included. |
| AGT-08 | Conversations affect agent schedules (agents revise plans after chatting) | Reference `schedule_chat()` + `revise_schedule()`: post-conversation LLM call revises remaining daily plan. This is the emergent behavior mechanism. |
</phase_requirements>

---

## Summary

Phase 3 implements the full agent cognition loop: perception, memory, planning, decision-making, and conversation. The reference implementation (`GenerativeAgentsCN`) provides a battle-tested Python blueprint that maps closely to the decisions locked in CONTEXT.md. The translation work is primarily: (1) replacing LlamaIndex with ChromaDB (already decided), (2) replacing synchronous LLM calls with async `complete_structured()` from Phase 1, and (3) extending Phase 2's `schemas.py`, `world.py`, and `loader.py` as integration points.

The architecture follows the build order established in ARCHITECTURE.md: perception is a pure tile-grid read (no LLM), planning and decision calls go through the existing `gateway.complete_structured()`, and memory is the new ChromaDB layer to introduce. Conversation is the most LLM-heavy component (~4-8 calls per exchange) and also the most behaviorally important for AGT-08 (schedule revision).

ChromaDB is not yet installed in the project (`uv pip show chromadb` returns "not found"). This is the single new dependency to add in Wave 0. The `sentence-transformers` package and its `all-MiniLM-L6-v2` model must also be added; ChromaDB bundles the embedding function but the model downloads on first use — plan for this in CI/CD and local setup documentation.

**Primary recommendation:** Build cognition as discrete, independently testable modules under `backend/agents/cognition/` and `backend/agents/memory/`. Wire them together through the existing `complete_structured()` gateway and extend `schemas.py` with new Pydantic v2 models for every new LLM call type.

---

## Standard Stack

### Core (already installed via pyproject.toml)

| Library | Installed Version | Purpose | Status |
|---------|------------------|---------|--------|
| FastAPI | 0.135.3 | Async HTTP server | Installed |
| instructor | 1.15.1 | Structured LLM output via Pydantic | Installed |
| litellm | 1.83.4 | Multi-provider LLM abstraction | Installed |
| pydantic | 2.12.5 | Data validation / schemas | Installed |
| pytest + pytest-asyncio | 9.0.3 / 1.3.0 | Testing framework | Installed |

[VERIFIED: uv pip show — checked 2026-04-09]

### New Dependencies (must add in Wave 0)

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| chromadb | 0.6+ | Vector store for memory stream | Locked by D-01. Embedded, zero-ops, metadata filtering. Not yet in pyproject.toml. |
| sentence-transformers | 3.x | Local embedding model | Required by ChromaDB's default embedding function. `all-MiniLM-L6-v2` downloads on first use (~80MB). |

[ASSUMED: chromadb 0.6+ is current stable — verify with `npm view chromadb` equivalent: `uv pip install chromadb --dry-run` or PyPI check]

**Installation command:**
```bash
uv add chromadb sentence-transformers
```

**Version verification needed before writing plans:**
```bash
uv pip show chromadb sentence-transformers
```

---

## Architecture Patterns

### Recommended Module Structure for Phase 3

```
backend/
├── agents/
│   ├── agent.py              # Agent dataclass — extend with cognition state
│   ├── cognition/
│   │   ├── __init__.py
│   │   ├── perceive.py       # Tile-grid scan, no LLM — pure Python
│   │   ├── plan.py           # Schedule generation (2 LLM calls) + decomposition
│   │   ├── decide.py         # Action decision LLM call (AGT-04)
│   │   └── converse.py       # Multi-turn conversation + schedule revision (AGT-07/08)
│   └── memory/
│       ├── __init__.py
│       ├── store.py          # ChromaDB wrapper, per-agent collection namespace
│       └── retrieval.py      # Composite scoring: recency * 0.5 + relevance * 3 + importance * 2
├── schemas.py                # EXTEND with new Pydantic v2 models (see below)
└── prompts/                  # One .txt or .py file per LLM call type
    ├── schedule_init.py
    ├── schedule_decompose.py
    ├── importance_score.py
    ├── action_decide.py
    ├── conversation_start.py
    ├── conversation_turn.py
    ├── conversation_end_check.py
    └── schedule_revise.py
```

[VERIFIED: from reference implementation structure at GenerativeAgentsCN/generative_agents/modules/]

### Pattern 1: Perception (No LLM — Pure Grid Scan)

**What:** Read tiles within a Manhattan/Euclidean radius from `Maze.tile_at()`. Collect events stored on tiles, identify nearby agents by checking tile `_events` dicts.

**When to use:** Every cognition cycle. Perception is the cheapest step — never add LLM calls here.

**Reference implementation** (`agent.py:percept()`):
```python
# Source: GenerativeAgentsCN/generative_agents/modules/agent.py:271
def percept(self):
    scope = self.maze.get_scope(self.coord, self.percept_config)
    events, arena = {}, self.get_tile().get_address("arena")
    for tile in scope:
        if not tile.events or tile.get_address("arena") != arena:
            continue
        dist = math.dist(tile.coord, self.coord)
        for event in tile.get_events():
            if dist < events.get(event, float("inf")):
                events[event] = dist
    events = list(sorted(events.keys(), key=lambda k: events[k]))
```

**Agent Town translation:** `Maze.tile_at(coord)` and `Tile._events` dict already exist in `backend/simulation/world.py`. The Phase 3 `perceive.py` module reads from the Maze instance and returns a `PerceptionResult` Pydantic model. The Maze's `get_scope` equivalent is a radius scan over tile coords; add a helper `maze.tiles_within_radius(coord, radius)` that returns all tiles within N tiles using Chebyshev or Manhattan distance.

```python
# Proposed perceive.py signature
async def perceive(agent_coord: tuple[int, int], maze: Maze, agents: dict[str, AgentState], radius: int = 5) -> PerceptionResult:
    """No LLM call — pure tile grid read."""
    ...
```

[VERIFIED: from world.py — Tile._events dict confirmed, Maze.tile_at() confirmed]

### Pattern 2: Two-Level Schedule Generation (2 LLM Calls)

**What:** Call 1 generates hourly activity blocks ("8am: open cafe", "12pm: lunch in park"). Call 2 decomposes the *current* hourly block into 5-15 minute sub-tasks. Schedule is stored as a list of `ScheduleEntry` objects.

**Reference implementation** (`agent.py:make_schedule()`, `memory/schedule.py`):
```python
# Source: GenerativeAgentsCN/generative_agents/modules/agent.py:181
# Call 1: schedule_init — generate high-level hourly list
init_schedule = self.completion("schedule_init", wake_up)
# Call 2: schedule_daily — map hours to activities  
schedule = self.completion("schedule_daily", wake_up, init_schedule)
# Then decompose current block
if self.schedule.decompose(plan):
    decompose_schedule = self.completion("schedule_decompose", plan, self.schedule)
```

**Agent Town translation:** Use `complete_structured()` with typed Pydantic schemas:
```python
class HourlySchedule(BaseModel):
    activities: list[str]  # ordered hourly list

class ScheduleEntry(BaseModel):
    start_minute: int   # minutes from midnight
    duration_minutes: int
    describe: str
    decompose: list[SubTask] = []

class SubTask(BaseModel):
    start_minute: int
    duration_minutes: int
    describe: str
```

[VERIFIED: from reference schedule.py — start/duration/describe fields confirmed]

### Pattern 3: Memory Storage with LLM Importance Scoring

**What:** Every stored memory gets an LLM importance rating (1-10) at write time (D-03). This rating is stored as ChromaDB metadata. At retrieval time, composite score is computed: `recency × 0.5 + relevance × 3 + importance × 2`.

**Reference implementation** (`memory/associate.py:add_node()`, `AssociateRetriever._retrieve()`):
```python
# Source: GenerativeAgentsCN/generative_agents/modules/memory/associate.py:93
# Scoring from AssociateRetriever._retrieve():
fac = self._config["recency_decay"]  # 0.995 in reference
recency_scores = self._normalize([fac**i for i in range(1, len(nodes)+1)], recency_weight)
relevance_scores = self._normalize([n.score for n in nodes], relevance_weight)
importance_scores = self._normalize([n.metadata["poignancy"] for n in nodes], importance_weight)
final_scores = {n.id_: r1 + r2 + i for n, r1, r2, i in zip(...)}
```

**Agent Town translation — ChromaDB pattern:**
```python
# Source: project ARCHITECTURE.md pattern 5
import chromadb
import time

_chroma_client = chromadb.EphemeralClient()  # or PersistentClient for save/load

def get_agent_collection(simulation_id: str, agent_id: str):
    # D-01: one collection per simulation, scoped by agent via metadata filter
    col_name = f"sim_{simulation_id}"
    return _chroma_client.get_or_create_collection(col_name)

async def add_memory(
    simulation_id: str,
    agent_id: str,
    content: str,
    memory_type: str,   # "observation" | "conversation" | "action" | "event"
    importance: int,    # 1-10, from LLM importance scoring call
):
    col = get_agent_collection(simulation_id, agent_id)
    col.add(
        documents=[content],
        metadatas=[{
            "agent_id": agent_id,
            "memory_type": memory_type,
            "importance": importance,
            "created_at": time.time(),
            "last_access": time.time(),
        }],
        ids=[str(uuid.uuid4())],
    )
```

**Retrieval — composite scoring:**
```python
def retrieve_memories(
    simulation_id: str,
    agent_id: str,
    query: str,
    top_k: int = 10,        # D-05: return top 5-10
    recency_weight: float = 0.5,
    relevance_weight: float = 3.0,
    importance_weight: float = 2.0,
    recency_decay: float = 0.995,
) -> list[Memory]:
    col = get_agent_collection(simulation_id, agent_id)
    # Query with metadata filter for this agent
    results = col.query(
        query_texts=[query],
        n_results=50,  # over-fetch, re-rank with composite score
        where={"agent_id": agent_id},
    )
    now = time.time()
    scored = []
    for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
        hours_since_access = (now - meta["last_access"]) / 3600
        recency = recency_decay ** hours_since_access
        relevance = 1.0 - dist  # ChromaDB returns L2 distance by default; use cosine
        importance = meta["importance"] / 10.0
        score = recency * recency_weight + relevance * relevance_weight + importance * importance_weight
        scored.append((score, doc, meta))
    scored.sort(reverse=True)
    return [Memory(content=doc, metadata=meta) for _, doc, meta in scored[:top_k]]
```

[VERIFIED: composite weights from CONTEXT.md D-02 and reference associate.py]

**Important ChromaDB note:** ChromaDB returns L2 distance by default. Use `cosine` distance for embedding similarity retrieval. Set at collection creation:
```python
col = client.get_or_create_collection(name, metadata={"hnsw:space": "cosine"})
```
[ASSUMED: ChromaDB 0.6 API supports `metadata={"hnsw:space": "cosine"}` — verify against official ChromaDB docs]

### Pattern 4: LLM Importance Scoring Call

**What:** Before storing a memory, make one LLM call to rate its importance 1-10.

**Pydantic schema:**
```python
class ImportanceScore(BaseModel):
    score: int = Field(ge=1, le=10, description="Importance score 1-10")
    reasoning: str  # optional, helps debugging

# Usage:
importance_result = await complete_structured(
    messages=[{"role": "user", "content": importance_prompt(memory_text, agent_name)}],
    response_model=ImportanceScore,
)
```

**Prompt template pattern** (from reference `scratch.py:prompt_poignancy_event()`):
- Provide agent persona (name, innate traits, lifestyle from `AgentScratch`)
- Describe the event/observation
- Ask: "On a scale of 1-10, how emotionally or practically significant is this for {agent_name}?"
- Failsafe: return random int 1-10 if parse fails

[VERIFIED: from GenerativeAgentsCN/generative_agents/modules/prompt/scratch.py:45-58]

### Pattern 5: Action Decision Call (AGT-04)

**What:** Given perception context and retrieved memories, ask the LLM to pick the agent's next action (destination + activity). This is the "react" step.

**Reference implementation** (`agent.py:_determine_action()`): hierarchical location resolution — sector → arena → object. Each level is an LLM call if the agent doesn't already know the location from spatial memory.

**Agent Town simplification** (Claude's discretion): Use `AgentSpatial.tree` to constrain the LLM choices to known locations. Single LLM call returns a `AgentAction` (destination: str, activity: str, reasoning: str) — the schema already exists in `schemas.py`.

```python
# Existing schema in backend/schemas.py
class AgentAction(BaseModel):
    destination: str  # sector name — Maze.resolve_destination() converts to tile
    activity: str
    reasoning: str
```

`Maze.resolve_destination(sector)` already exists and converts a sector name to walkable tile coords. The LLM just needs to pick a sector name from the agent's known locations.

[VERIFIED: AgentAction schema confirmed in backend/schemas.py; Maze.resolve_destination() confirmed in backend/simulation/world.py]

### Pattern 6: Multi-Turn Conversation (AGT-07/08)

**What:** When two agents are within perception radius, an LLM "should they talk?" check runs. If yes, 2-4 turns of dialogue ensue. After conversation, each agent calls LLM to revise remaining schedule.

**Reference implementation** (`agent.py:_chat_with()`):
```python
# Source: GenerativeAgentsCN/generative_agents/modules/agent.py:501
# Cooldown: skip if chatted within 60 minutes
chats = self.associate.retrieve_chats(other.name)
if chats and delta < 60:
    return False

# LLM decide whether to chat
if not self.completion("decide_chat", self, other, focus, chats):
    return False

# Multi-turn loop with repeat detection and topic-end check
for i in range(self.chat_iter):  # chat_iter = 4 in reference
    text = self.completion("generate_chat", ...)
    if i > 0:
        end = self.completion("decide_chat_terminate", ...)
        if end: break
    chats.append(...)
```

**Pydantic schemas needed:**
```python
class ConversationDecision(BaseModel):
    should_talk: bool
    reasoning: str

class ConversationTurn(BaseModel):
    text: str  # what this agent says
    end_conversation: bool = False

class ScheduleRevision(BaseModel):
    revised_remaining: list[SubTask]
    reason: str
```

**Cooldown (Claude's discretion):** Set per-agent cooldown of 60 real-time seconds or 60 simulated minutes between conversations with the same partner. Store last conversation timestamp per agent pair in-memory (not in ChromaDB).

**Memory storage after conversation:** Store a *summary* of the conversation as a single memory (not each turn verbatim). Anti-Pattern 6 from ARCHITECTURE.md: "Store observations extracted from conversations, not verbatim logs."

[VERIFIED: conversation loop structure from agent.py; anti-pattern from ARCHITECTURE.md]

### Anti-Patterns to Avoid

- **Calling LLM during perception:** Perception must be a pure tile-grid read. LLM calls in perception block the event loop during tick pre-processing.
- **Storing verbatim conversation turns:** Store extracted observations ("Alice told me about the wedding tomorrow") not full dialogue. Prevents embedding quality degradation.
- **Synchronous ChromaDB calls inside async functions:** ChromaDB's Python client is synchronous. Wrap with `asyncio.to_thread()` for all ChromaDB operations inside async FastAPI routes.
- **Global ChromaDB client shared across agents without agent_id filter:** All agents share one ChromaDB collection (D-01), so every query MUST include `where={"agent_id": agent_id}`.
- **Forgetting the conversation cooldown:** Without it, two proximate agents will initiate a new conversation every tick (~every 5 seconds), burning LLM budget.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Structured LLM output | Custom JSON parser with regex | `instructor` + Pydantic v2 | Already in the project. Handles retries, validation errors, and provider differences. |
| Vector similarity search | Manual cosine similarity over list of embeddings | ChromaDB with cosine space | Handles HNSW indexing, metadata filtering, persistence. Cosine sim over 1000+ memories is slow in pure Python. |
| Text embedding generation | Hand-calling LLM embedding API per memory | ChromaDB's default `all-MiniLM-L6-v2` embedding function | Runs locally, no API key, <50ms per embed, consistent across reads/writes. |
| Memory retrieval ranking | Re-implementing normalize + weight formula from scratch | The composite scoring pattern from reference (verified against paper) | Formula is subtle — normalization across unequal vector lengths must be done correctly or retrieval degrades. |
| Async rate limiting | Per-call sleep() or token bucket | `asyncio.Semaphore` already used in gateway | A Semaphore wrapper already exists conceptually in the project architecture. |

**Key insight:** The reference implementation (GenerativeAgentsCN) hand-rolls much of this because it predates ChromaDB/instructor maturity. Agent Town should not repeat those choices — each adds testing surface and failure modes.

---

## Common Pitfalls

### Pitfall 1: ChromaDB Sync Client Blocking Async Event Loop

**What goes wrong:** ChromaDB's Python client is synchronous. Calling `collection.add()`, `collection.query()`, or `client.get_or_create_collection()` directly inside an `async def` function blocks the uvicorn event loop. With 8 agents each adding memories per tick, this serializes all agent updates.

**Why it happens:** ChromaDB 0.6's primary client is synchronous. An `asyncio`-native client exists (experimental in 0.6+) but may have incomplete coverage.

**How to avoid:**
```python
# Correct: wrap synchronous ChromaDB calls with asyncio.to_thread()
async def add_memory_async(col, documents, metadatas, ids):
    await asyncio.to_thread(col.add, documents=documents, metadatas=metadatas, ids=ids)

# Also wrap queries:
async def query_async(col, query_texts, n_results, where):
    return await asyncio.to_thread(col.query, query_texts=query_texts, n_results=n_results, where=where)
```

**Warning signs:** `/health` endpoint responds slowly during agent step execution; step time grows linearly with agent count even with async gather.

[VERIFIED: pattern from PITFALLS.md Pitfall 6; ChromaDB sync nature from STACK.md]

### Pitfall 2: Missing agent_id Filter on ChromaDB Queries

**What goes wrong:** D-01 uses one ChromaDB collection per simulation (not per agent). If the `where={"agent_id": agent_id}` filter is omitted from queries, all agents receive each other's memories. Agents behave as if they share a hive mind.

**How to avoid:** Enforce the `agent_id` filter at the retrieval module boundary. Make it impossible to query without it — build the filter into the `retrieve_memories()` function signature.

**Warning signs:** Agents referencing events they could not have perceived; schedule revisions affecting the wrong agent.

[VERIFIED: ChromaDB metadata filtering pattern — standard ChromaDB usage]

### Pitfall 3: Conversation Loop Without Termination Guard

**What goes wrong:** The LLM "end conversation" check can return False indefinitely if the topic is interesting. Without a hard cap (D-12: max 4 turns), two agents lock into an infinite dialogue loop consuming LLM budget and blocking both agents from acting.

**How to avoid:** Implement the cap as a `for i in range(MAX_TURNS)` loop — never a `while True`. The reference uses `chat_iter = 4`. After the loop exits (cap reached), always proceed to schedule revision.

**Warning signs:** Two specific agents frozen in place with conversation type for many minutes; LLM call count per tick growing unexpectedly.

[VERIFIED: from reference agent.py:533-568 — loop structure is bounded by chat_iter]

### Pitfall 4: Schedule Not Seeded from AgentScratch.daily_plan

**What goes wrong:** LLM generates wildly out-of-character schedules (a barista schedules stock trading at 5am) because the agent's daily_plan template from the config was not included in the schedule generation prompt.

**How to avoid:** Always inject `agent.scratch.daily_plan` into the schedule generation prompt as the "routine template" that the LLM must build from. The `AgentScratch.daily_plan` field exists in all 8 agent JSON configs (verified: alice.json, bob.json etc.) and provides the grounding.

**Warning signs:** Agents whose schedules look generic and unrelated to their personality or occupation.

[VERIFIED: AgentScratch.daily_plan confirmed in backend/schemas.py and alice.json]

### Pitfall 5: Importance Scoring LLM Call on Every Memory (Cost Control)

**What goes wrong:** With D-03 requiring LLM importance scoring per memory, and D-04 storing "everything significant," importance scoring can fire many times per tick per agent. Each call is cheap (short prompt) but adds up: 8 agents × 5 perceptions × 1 importance call = 40 extra LLM calls per tick.

**How to avoid:**
- Use the cheapest available model for importance scoring (same model as schedule decomposition).
- Batch perception: collect all perceived events first, then score importance in parallel with `asyncio.gather()`.
- Add a pre-filter before importance scoring: skip events where the subject is "idle" (reference skips these — `poignancy = 1` hardcoded for idle events, no LLM call).
- Failsafe: if importance scoring call fails, default to importance = 5 rather than retrying.

[VERIFIED: from reference agent.py:631-656 — idle events get poignancy=1 hardcoded]

### Pitfall 6: Embedding Model Download Blocking First Run

**What goes wrong:** `sentence-transformers` downloads the `all-MiniLM-L6-v2` model (~80MB) on first use. In CI or on a fresh machine, this causes the first test run to time out or appear to hang.

**How to avoid:** Add a pre-warm step in the lifespan handler (`backend/main.py`) that initializes ChromaDB and triggers model download before the FastAPI app starts accepting requests. Surface this as a startup log message: "Warming up embedding model..."

**Warning signs:** First test run in CI takes 5+ minutes; subsequent runs are fast.

[ASSUMED: Model download size of ~80MB — from STACK.md which cited sentence-transformers docs]

---

## Code Examples

### ChromaDB Memory Store (verified pattern)

```python
# backend/agents/memory/store.py
import asyncio
import time
import uuid
import chromadb

# Source: project ARCHITECTURE.md Pattern 5 + reference associate.py + D-01
_chroma_client = chromadb.EphemeralClient()  # use PersistentClient for save/load

def _get_collection(simulation_id: str) -> chromadb.Collection:
    """One collection per simulation (D-01). Agents scoped via agent_id metadata."""
    return _chroma_client.get_or_create_collection(
        f"sim_{simulation_id}",
        metadata={"hnsw:space": "cosine"},  # cosine distance for relevance scoring
    )

async def add_memory_async(
    simulation_id: str,
    agent_id: str,
    content: str,
    memory_type: str,
    importance: int,
) -> None:
    col = _get_collection(simulation_id)
    now = time.time()
    await asyncio.to_thread(
        col.add,
        documents=[content],
        metadatas=[{
            "agent_id": agent_id,
            "memory_type": memory_type,
            "importance": importance,
            "created_at": now,
            "last_access": now,
        }],
        ids=[str(uuid.uuid4())],
    )
```

### Composite Retrieval Scoring

```python
# backend/agents/memory/retrieval.py
# Source: GenerativeAgentsCN/modules/memory/associate.py:83-120 + ARCHITECTURE.md
import asyncio
import time

async def retrieve_memories(
    simulation_id: str,
    agent_id: str,
    query: str,
    top_k: int = 10,
    recency_decay: float = 0.995,
) -> list[dict]:
    from backend.agents.memory.store import _get_collection
    col = _get_collection(simulation_id)
    
    # Over-fetch for re-ranking (ChromaDB returns by vector distance)
    results = await asyncio.to_thread(
        col.query,
        query_texts=[query],
        n_results=min(50, top_k * 5),
        where={"agent_id": agent_id},  # REQUIRED — prevents cross-agent contamination
    )
    
    now = time.time()
    scored = []
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]
    
    for doc, meta, dist in zip(documents, metadatas, distances):
        hours_since_access = (now - meta["last_access"]) / 3600
        recency = recency_decay ** hours_since_access
        relevance = 1.0 - dist   # cosine distance: 0=identical, 1=orthogonal
        importance = meta["importance"] / 10.0
        
        score = recency * 0.5 + relevance * 3.0 + importance * 2.0
        scored.append((score, doc, meta))
    
    scored.sort(reverse=True)
    return [{"content": doc, "meta": meta} for _, doc, meta in scored[:top_k]]
```

### Perception Radius Scan

```python
# backend/agents/cognition/perceive.py
# Source: GenerativeAgentsCN/modules/agent.py:271 — translated to Agent Town's Maze API
import math
from backend.simulation.world import Maze, Tile

def perceive(
    agent_coord: tuple[int, int],
    agent_name: str,
    maze: Maze,
    all_agents: dict[str, "AgentState"],
    radius: int = 5,
) -> dict:
    """Pure tile-grid scan — NO LLM calls. Returns perception dict."""
    x0, y0 = agent_coord
    nearby_events = []
    nearby_agents = []
    
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            tx, ty = x0 + dx, y0 + dy
            dist = math.sqrt(dx**2 + dy**2)  # Euclidean — matches reference
            if dist > radius:
                continue
            try:
                tile = maze.tile_at((tx, ty))
            except IndexError:
                continue
            
            # Collect tile events (injected world events stored on tiles)
            for event_key, event_data in tile._events.items():
                nearby_events.append({"distance": dist, "event": event_data})
            
            # Collect nearby agents
            for name, agent_state in all_agents.items():
                if name == agent_name:
                    continue
                if agent_state.coord == (tx, ty):
                    nearby_agents.append({
                        "name": name,
                        "activity": agent_state.current_activity,
                        "distance": dist,
                    })
    
    # Sort by distance (closest first)
    nearby_events.sort(key=lambda e: e["distance"])
    nearby_agents.sort(key=lambda a: a["distance"])
    
    current_tile = maze.tile_at(agent_coord)
    location_context = current_tile.get_address(as_list=False)  # "agent-town:cafe:counter"
    
    return {
        "nearby_events": nearby_events[:10],   # cap at 10 (reference: att_bandwidth)
        "nearby_agents": nearby_agents,
        "location": location_context,
    }
```

### Pydantic v2 Schemas to Add to schemas.py

```python
# Source: verified against existing schemas.py patterns + reference implementation
from pydantic import BaseModel, Field
from typing import Literal

class SubTask(BaseModel):
    """One 5-15 minute sub-task within an hourly schedule block."""
    start_minute: int = Field(ge=0, lt=1440, description="Minutes from midnight")
    duration_minutes: int = Field(ge=5, le=60)
    describe: str

class ScheduleEntry(BaseModel):
    """One hourly block in the agent's daily schedule."""
    start_minute: int = Field(ge=0, lt=1440)
    duration_minutes: int = Field(ge=15, le=120)
    describe: str
    decompose: list[SubTask] = []

class DailySchedule(BaseModel):
    """LLM response for schedule_init call — list of hourly activities."""
    activities: list[str] = Field(min_length=3)
    wake_hour: int = Field(ge=4, le=11)

class ImportanceScore(BaseModel):
    """LLM response for memory importance scoring (D-03)."""
    score: int = Field(ge=1, le=10)
    reasoning: str = ""

class ConversationDecision(BaseModel):
    """LLM response for conversation initiation check (D-11)."""
    should_talk: bool
    reasoning: str

class ConversationTurn(BaseModel):
    """LLM response for one dialogue turn."""
    text: str
    end_conversation: bool = False

class ScheduleRevision(BaseModel):
    """LLM response for post-conversation schedule revision (D-13)."""
    revised_entries: list[ScheduleEntry]
    reason: str

class Memory(BaseModel):
    """A retrieved memory entry from ChromaDB."""
    content: str
    agent_id: str
    memory_type: Literal["observation", "conversation", "action", "event"]
    importance: int
    created_at: float
    last_access: float
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LlamaIndex vector store | ChromaDB embedded client | Project decision (see CONTEXT.md D-01) | Lower RAM overhead, metadata filtering, no extra server. ChromaDB 0.6+ is production-stable. |
| Synchronous LLM calls (reference implementation) | `litellm.acompletion` via `instructor` | Phase 1 decision | All agents run concurrently; event loop stays unblocked. |
| Prompt-level JSON enforcement (reference) | `instructor.from_litellm()` structured output | Phase 1 decision | Automatic retry on validation error; consistent schema across providers. |
| LlamaIndex `AssociateRetriever` custom class | Pure Python composite scoring after ChromaDB query | Phase 3 (this phase) | Same math, simpler dependency tree. |
| Per-agent ChromaDB collection | One collection per simulation with agent_id metadata filter | D-01 decision | Simpler collection management; still fully isolated per agent via metadata. |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | ChromaDB 0.6+ supports `metadata={"hnsw:space": "cosine"}` at collection creation | Code Examples | If API is different, cosine distance must be set differently or default L2 distance requires formula adjustment |
| A2 | `sentence-transformers` all-MiniLM-L6-v2 model download is ~80MB | Pitfall 6 | If larger, CI timeout may need longer; if different download mechanism, pre-warm strategy needs adjustment |
| A3 | ChromaDB 0.6+ `where` metadata filter works with nested query and agent_id string equality | Memory Store pattern | If syntax is different (e.g., requires `$eq` operator), queries return wrong results silently |
| A4 | `asyncio.to_thread()` is safe for all ChromaDB operations (add, query, get_or_create_collection) | Pitfall 1 / Code Examples | If ChromaDB has thread safety issues, need alternative approach (dedicated thread pool executor) |

**If these assumptions are wrong:** verify against official ChromaDB 0.6 docs at https://docs.trychroma.com/reference/py-collection before finalizing plans.

---

## Open Questions (RESOLVED)

1. **ChromaDB async client status in 0.6+** — RESOLVED: Use `asyncio.to_thread()` wrapping for safety. Plans implement this in 03-01 Task 1 step 4. The sync client wrapped with to_thread is the proven pattern.

2. **Conversation cooldown unit — simulated time vs. real time** — RESOLVED: Use real-time seconds (`COOLDOWN_SECONDS = 60`). Plans implement this in 03-03 Task 2. Phase 4 can introduce simulated time tracking later.

3. **Event storage format on Tile._events** — RESOLVED: perceive.py reads the existing `_events` dict directly as-is. No separate TileEvent Pydantic model needed for Phase 3. The dict format is Claude's discretion per CONTEXT.md.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | Runtime | ✓ | 3.14.2 | — |
| FastAPI | HTTP server | ✓ | 0.135.3 | — |
| instructor | Structured LLM output | ✓ | 1.15.1 | — |
| litellm | LLM provider abstraction | ✓ | 1.83.4 | — |
| pydantic v2 | Data validation | ✓ | 2.12.5 | — |
| pytest + pytest-asyncio | Testing | ✓ | 9.0.3 / 1.3.0 | — |
| chromadb | Vector memory store | ✗ | — | Must install: `uv add chromadb` |
| sentence-transformers | Embedding model | ✗ | — | Must install: `uv add sentence-transformers` |
| Ollama | Local LLM (dev/test) | UNKNOWN | — | OpenRouter API key |

[VERIFIED: package versions via `uv pip show` on 2026-04-09]

**Missing dependencies with no fallback:**
- `chromadb` — blocks AGT-05 and AGT-06. Must be installed in Wave 0.
- `sentence-transformers` — required by ChromaDB's default embedding function. Must be installed with chromadb.

**Missing dependencies with fallback:**
- Ollama local LLM — tests that require actual LLM calls can be mocked. Phase 3 tests should mock `complete_structured()` for unit tests; integration tests requiring a live LLM can be skipped in CI via pytest marks.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-asyncio 1.3.0 |
| Config file | `pyproject.toml` (`asyncio_mode = "auto"`, `testpaths = ["tests"]`) |
| Quick run command | `uv run pytest tests/test_cognition.py -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AGT-02 | Schedule generation produces hourly + sub-task entries | unit | `uv run pytest tests/test_cognition.py::test_schedule_generation -x` | ❌ Wave 0 |
| AGT-02 | Schedule decomposition fires for non-sleep blocks | unit | `uv run pytest tests/test_cognition.py::test_schedule_decompose -x` | ❌ Wave 0 |
| AGT-03 | Perception radius returns events within N tiles, excludes beyond | unit | `uv run pytest tests/test_cognition.py::test_perception_radius -x` | ❌ Wave 0 |
| AGT-03 | Perception returns nearby agent name and activity | unit | `uv run pytest tests/test_cognition.py::test_perception_agents -x` | ❌ Wave 0 |
| AGT-04 | LLM decision call returns AgentAction without parse errors | unit (mocked) | `uv run pytest tests/test_cognition.py::test_action_decision -x` | ❌ Wave 0 |
| AGT-05 | Memory stored with correct metadata fields | unit | `uv run pytest tests/test_memory.py::test_add_memory_metadata -x` | ❌ Wave 0 |
| AGT-05 | 10 memories stored → retrieval returns top-k only | unit | `uv run pytest tests/test_memory.py::test_memory_topk -x` | ❌ Wave 0 |
| AGT-06 | Composite scoring ranks recency + relevance + importance correctly | unit | `uv run pytest tests/test_memory.py::test_composite_scoring -x` | ❌ Wave 0 |
| AGT-07 | Two agents within radius → conversation trigger | integration | `uv run pytest tests/test_cognition.py::test_conversation_trigger -x` | ❌ Wave 0 |
| AGT-07 | Conversation produces at least 2 turns | integration (mocked LLM) | `uv run pytest tests/test_cognition.py::test_conversation_turns -x` | ❌ Wave 0 |
| AGT-08 | Post-conversation schedule revision fires for both agents | integration (mocked LLM) | `uv run pytest tests/test_cognition.py::test_schedule_revision_after_chat -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_cognition.py tests/test_memory.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_cognition.py` — covers AGT-02, AGT-03, AGT-04, AGT-07, AGT-08
- [ ] `tests/test_memory.py` — covers AGT-05, AGT-06
- [ ] `uv add chromadb sentence-transformers` — ChromaDB not yet installed
- [ ] `tests/conftest.py` update — add `mock_complete_structured` fixture for LLM-free cognition tests
- [ ] Pre-warm embedding model in test setup (or mock ChromaDB in tests that don't need real vector search)

*(Existing test infrastructure: 86 tests covering Phases 1-2. No cognition or memory tests exist yet.)*

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Phase 3 is backend-only; no auth surface |
| V3 Session Management | No | Memory store scoped by simulation_id; cleanup handled in Phase 4 |
| V4 Access Control | No | Single-user architecture |
| V5 Input Validation | Yes | All LLM responses validated through Pydantic v2 schemas via `instructor`; importance scores clamped to 1-10 with `Field(ge=1, le=10)` |
| V6 Cryptography | No | No secrets or cryptographic operations in Phase 3 |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| LLM prompt injection via injected event content stored in memory | Tampering | Content stored verbatim in ChromaDB but only used as retrieval context, not executed. No eval/exec of memory content. |
| Memory exhaustion via rapid event injection | Denial of Service | Cap per-agent memory count (e.g., 500 entries) with oldest eviction. Phase 6 event injection rate-limiting applies. |
| API key leakage in LLM call logs | Information Disclosure | `gateway.py` already masks API key in logs (`key_hint = api_key[:8] + "..."`) — verified in Phase 1. Ensure importance scoring calls also go through `complete_structured()`. |

---

## Sources

### Primary (HIGH confidence)
- `GenerativeAgentsCN/generative_agents/modules/agent.py` — schedule planning, perception, conversation loop, importance scoring patterns. Read directly in this session.
- `GenerativeAgentsCN/generative_agents/modules/memory/associate.py` — composite scoring formula, normalization weights, retrieval pattern. Read directly.
- `GenerativeAgentsCN/generative_agents/modules/memory/schedule.py` — ScheduleEntry data structure, decompose logic. Read directly.
- `backend/gateway.py` — `complete_structured()` signature and retry behavior. Read directly.
- `backend/schemas.py` — existing Pydantic v2 models to extend. Read directly.
- `backend/simulation/world.py` — `Maze.tile_at()`, `Tile._events`, `Maze.resolve_destination()`. Read directly.
- `.planning/research/ARCHITECTURE.md` — Pattern 5 (per-agent memory namespace), anti-patterns. Read directly.
- `.planning/research/PITFALLS.md` — Pitfall 6 (sync calls in async), memory bounds, conversation loop. Read directly.

### Secondary (MEDIUM confidence)
- `.planning/research/STACK.md` — ChromaDB, sentence-transformers versions and rationale.
- `GenerativeAgentsCN/generative_agents/modules/prompt/scratch.py` — Prompt template structure and failsafe pattern. Read directly.

### Tertiary (LOW confidence — needs verification against official docs)
- ChromaDB 0.6 cosine distance configuration (`hnsw:space`: "cosine") — assumed from prior versions; verify at https://docs.trychroma.com
- `asyncio.to_thread()` thread-safety for ChromaDB operations — assumed safe based on ChromaDB docs; verify if issues arise
- sentence-transformers model download size (~80MB) — cited from STACK.md training knowledge

---

## Metadata

**Confidence breakdown:**
- Standard stack (chromadb + existing): HIGH — existing packages verified via uv pip show; chromadb version ASSUMED until installed
- Architecture patterns: HIGH — directly derived from verified reference implementation + existing codebase
- ChromaDB API details: MEDIUM — patterns from prior research; specific 0.6 API may differ on cosine distance config
- Pitfalls: HIGH — cross-verified from reference codebase, project PITFALLS.md, and prior research

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (stable libraries; ChromaDB 0.6 API stable)
