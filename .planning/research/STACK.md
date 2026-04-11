# Stack Research

**Domain:** LLM-powered agent simulation web app
**Researched:** 2026-04-10
**Milestone:** v1.1 — OOP refactoring, UI visual overhaul, LLM optimization, agent behavior fidelity
**Confidence:** HIGH for Python patterns (stdlib), HIGH for PixiJS Graphics API, MEDIUM for LiteLLM cache

> This document **supersedes** the v1.0 STACK.md and adds new capabilities for v1.1.
> The base stack (FastAPI, PixiJS, LiteLLM, ChromaDB, Zustand, etc.) is unchanged and validated.
> Sections below cover only what is NEW for v1.1 features.

---

## What Is New for v1.1

The milestone adds four capability clusters. No new external packages are required for any of them. All new features use existing dependencies, stdlib, or patterns already in the codebase.

| Cluster | What Changes | New Dependencies? |
|---------|-------------|-------------------|
| Backend OOP refactoring | `dataclasses` → richer classes with methods | None — stdlib only |
| Building wall rendering | PixiJS `Graphics.stroke()` with existing API | None — PixiJS 8.17 already installed |
| LLM call optimization | `asyncio.Semaphore` + `litellm.cache` | None — already imported |
| Reflection system | New Pydantic schemas + LLM prompt functions | None — instructor/pydantic already present |

---

## Backend OOP Refactoring

### Current State

The existing `AgentState` in `engine.py` is a `@dataclass` with raw fields (name, config, coord, path, schedule). Cognition is in standalone functions (`perceive()`, `decide_action()`, etc.) called from `engine.py`. `AgentConfig` and friends are Pydantic models in `schemas.py`.

### What the Refactor Needs

Agent class that owns both static config and runtime state, with cognition methods. Building/Location class representing map sectors with wall metadata. Event class with lifecycle (created, active, expired). This is structural reorganization — no new runtime dependencies.

### Pattern: Combine `@dataclass` for state, Pydantic for schemas

The codebase already uses both. The right split for v1.1 is:

- **Pydantic models** (`schemas.py`): LLM response shapes, WebSocket contracts, config loaded from JSON. These cross the wire or validation boundary and need Pydantic's coercion and error messages.
- **`@dataclass`** (new `agent.py`, `building.py`, `event.py`): Runtime simulation objects that hold mutable state and expose methods. Dataclasses have no import cost overhead and integrate naturally with `asyncio`.

Do NOT use `ABC` / abstract base classes. The project spec explicitly states "all agents run same code paths with personality from LLM prompts" — agent subclassing is out of scope. ABC adds ceremony with no benefit here.

Do NOT use `__slots__` on the runtime classes in v1.1. It prevents dynamic attribute addition which will cause friction during the refactor. Add slots later after the class boundaries stabilize.

**Confidence: HIGH** — stdlib dataclasses, no new dependencies, pattern already in use in `engine.py`.

### Agent Class Shape (reference)

```python
@dataclass
class Agent:
    # Static identity (from AgentConfig)
    name: str
    config: AgentConfig

    # Runtime state (mutable per tick)
    coord: tuple[int, int]
    path: list[tuple[int, int]] = field(default_factory=list)
    current_activity: str = ""
    schedule: list[ScheduleEntry] = field(default_factory=list)
    poignancy_accumulator: float = 0.0   # new: feeds reflection trigger

    # Cognition as methods (call existing standalone functions internally)
    async def step(self, engine_context: "SimulationContext") -> None: ...
    async def reflect(self) -> None: ...   # new for v1.1
```

The `poignancy_accumulator` field is the key v1.1 addition — it accumulates importance scores across observations and triggers reflection when it crosses the threshold (150 per reference implementation, configurable).

### Building Class Shape (reference)

```python
@dataclass
class Building:
    name: str             # e.g. "stock-exchange"
    sector: str           # same as name for top-level sectors
    tiles: list[tuple[int, int]]    # all tile coords inside
    wall_tiles: list[tuple[int, int]]  # perimeter tiles (collision=True)
    entry_point: tuple[int, int]    # navigable tile just outside walls
    color: int            # hex for PixiJS rendering (0xRRGGBB)
```

This replaces the current SectorBounds dict pattern used in both `world.py` and `TileMap.tsx`. The frontend receives building metadata via the simulation snapshot; the backend owns the authoritative Building objects.

---

## Building Wall Rendering (PixiJS)

### Current State

`TileMap.tsx` draws sector zones as filled rectangles with no outlines. Sector labels exist but are 13px at full map scale (3200px canvas fit into ~800px viewport → effectively ~3px at default zoom). Collision tiles are drawn as individual dark gray rects, but these are sparse border tiles, not building wall outlines.

### What Is Needed

Visible wall outlines around building sectors. Readable text labels. Both are achievable with the existing PixiJS 8.17.1 API — no new packages.

### PixiJS v8 Graphics Stroke API

Confirmed current API (verified against official docs):

```typescript
// Draw a filled rect with a stroke outline
g.rect(x, y, width, height)
  .fill({ color: 0xa8d5a2 })          // fill interior
  .stroke({ color: 0x5a8a55, width: 2 }); // draw wall outline
```

The stroke call must come AFTER fill in v8 — unlike v7 where lineStyle was set before drawing. The `stroke()` method accepts `StrokeStyle`: `{ color, width, alpha, join, cap, pixelLine }`.

For a 32px tile grid with default zoom ~0.25, a 2px stroke at world-space renders at 0.5px on screen — invisible. Use **3-4px width** for wall outlines to remain visible at default fit-to-screen zoom.

For pixel-perfect 1px lines (grid lines, not walls): `{ pixelLine: true }` keeps lines exactly 1 screen pixel regardless of zoom. This is useful for arena subdivision lines but NOT for building walls which need visible weight.

**Confidence: HIGH** — official PixiJS 8.x docs confirm this API. The current codebase already uses `g.setFillStyle()` + `g.fill()` correctly; adding `.stroke()` is additive.

### Text Readability Fix

Current agent labels are 9-13px PixiJS `pixiText` (canvas-rasterized). At the ~0.25x default scale, these render at effectively 2-3px — unreadable.

Two approaches, both using existing PixiJS capabilities:

**Option A: Increase font size and scale inverse to zoom (recommended)**
Keep `pixiText` but increase font sizes significantly (24-32px for sector labels, 18px for agent names, 14px for activity). At 0.25x zoom, 28px renders at 7px — barely readable but acceptable. This is the minimal-change path.

**Option B: BitmapText for agent labels**
`BitmapText` uses a pre-rasterized glyph atlas — better performance (no per-frame Canvas rasterization), supports MSDF fonts for crisp scaling at any zoom level. Tradeoff: requires generating a bitmap font atlas or using a pre-built one. The PixiJS 8.17 release notes confirm `BitmapText` and `Text` parity improvements.

**Recommendation: Option A for v1.1** (minimal risk, no new assets). Option B is a v1.2 optimization if text performance becomes a bottleneck with 25 agents all updating labels per frame.

For sector labels specifically: the current approach renders them at module-load time as `pixiText` objects positioned at sector centers. At 32px font size (up from 13px), these remain readable at default zoom. Since sector labels never change, there is no performance cost to increasing their size.

**Confidence: HIGH** — PixiJS docs confirm `Text` and `BitmapText` capabilities. The current code pattern (pixi `Text` via JSX) supports fontSize changes with no API change.

---

## LLM Call Optimization

### Current Architecture

`gateway.py` uses `instructor.from_litellm(litellm.acompletion)` with a global `_client`. All calls go through `complete_structured()`. The simulation engine calls one LLM function per agent per tick sequentially within `asyncio.TaskGroup` (all agents run concurrently, but each agent's LLM calls are sequential within `_agent_step()`).

The current `decide_action()` makes a single flat decision: "go to sector X, do activity Y." The reference implementation uses 3-level resolution: sector → arena → object. This milestone adds that.

### 3-Level Decision Resolution

The pattern from `GenerativeAgentsCN/modules/agent.py` `_determine_action()`:

1. **Sector decision** — which top-level zone to go to (stock-exchange, park, etc.)
2. **Arena decision** — which sub-area within that sector (trading floor vs. lobby)
3. **Object decision** — which specific object in that arena (terminal, seat, door)

Each level is a separate LLM call only if there is ambiguity. If a sector has one arena, skip the arena call. If an arena has one object, skip the object call. This "short-circuit on single option" pattern can eliminate 1-2 LLM calls per tick for simple scenarios.

These are three separate `complete_structured()` calls using existing infrastructure. No new libraries needed. New Pydantic schemas required: `SectorDecision`, `ArenaDecision`, `ObjectDecision` — all trivial one-field models.

**Confidence: HIGH** — directly adapted from reference implementation, all existing tools.

### Conversation Gating

Current `attempt_conversation()` already makes an LLM call to decide `ConversationDecision.should_talk`. The gap is conversation termination: the reference implementation checks `end_conversation` in each `ConversationTurn`, but also has an explicit repetition detector — if an agent produces nearly identical text to a prior turn, end early without another LLM call.

Simple Python implementation using token overlap (no new library):

```python
def _is_repetitive(turn: str, history: list[str], threshold: float = 0.7) -> bool:
    """Return True if >70% of turn tokens appear in the most recent prior turn."""
    if not history:
        return False
    turn_tokens = set(turn.lower().split())
    prev_tokens = set(history[-1].lower().split())
    if not turn_tokens:
        return False
    overlap = len(turn_tokens & prev_tokens) / len(turn_tokens)
    return overlap >= threshold
```

This avoids an extra LLM call (poignancy scoring, repetition check). **Confidence: HIGH.**

### `asyncio.Semaphore` for LLM Concurrency

Already documented in v1.0 STACK.md and the existing code. The simulation has `asyncio.TaskGroup` running all agents concurrently but no global cap on simultaneous LLM calls. At 25 agents each making 3-5 LLM calls per tick, this can hit API rate limits.

Add a module-level semaphore in `gateway.py`:

```python
_LLM_SEMAPHORE = asyncio.Semaphore(8)  # max 8 concurrent LLM calls across all agents

async def complete_structured(...) -> T:
    async with _LLM_SEMAPHORE:
        # existing retry logic
```

8 concurrent calls is the right default for OpenRouter's free tier (10 RPM limit). For Ollama, reduce to 2-3 since local models serialize anyway. Make this configurable via an env var rather than hardcoding.

**Confidence: HIGH** — `asyncio.Semaphore` is stdlib, no new dependencies.

### LiteLLM In-Memory Cache

LiteLLM ships with a built-in cache system (`litellm.cache = Cache()`). The cache key is the model name + message content hash. For agent simulation, this is useful for **schedule generation** (same agent + same day → identical LLM call at re-init) but NOT for per-tick decisions (messages include perception data which changes every tick).

Enable selectively, only for slow expensive calls:

```python
from litellm.caching.caching import Cache
litellm.cache = Cache()  # in-memory, no infrastructure

# In generate_daily_schedule():
result = await complete_structured(..., caching=True)   # cache this

# In decide_action():
result = await complete_structured(..., caching=False)  # never cache decisions
```

Cost/benefit: schedule generation is ~2 LLM calls per agent per sim init. With 10 agents, this is 20 calls saved per restart. Small gain but zero risk.

**Confidence: MEDIUM** — LiteLLM cache docs confirm the API pattern. Cache key details (whether messages are hashed including system prompt) were not independently verified. Test before relying on this.

---

## Reflection System

### What It Is

From the Generative Agents paper and reference implementation: agents accumulate "poignancy" (emotional weight) as they observe events and have conversations. When the accumulator crosses a threshold (~150 in the reference), the agent runs a reflection pass — an LLM call that synthesizes recent high-importance memories into abstract "thoughts" stored back into the memory stream.

### Implementation Components

All of this fits within existing infrastructure:

**1. Poignancy accumulation (no LLM)**
The `add_memory()` call already takes an `importance` parameter (1-10). The reflection system needs to sum these into a per-agent counter. Add `poignancy_accumulator: float = 0.0` to the Agent class (or `AgentState` dataclass in v1.0 code). Increment on every `add_memory()` call.

**2. Importance scoring LLM call (already in `schemas.py`)**
`ImportanceScore` schema already exists. The reference calls `score_importance()` for every new observation. Currently, the codebase hardcodes `importance=3` for routine actions and `importance=8` for injected events. The reflection system needs actual LLM-scored importance for the accumulator to be meaningful.

Add `score_importance()` to the cognition layer — one new LLM call per memory added. This is expensive (~1 LLM call per observation, per agent, per tick). Mitigation: score only observations from perception (other agents, events), not routine action memories. Injected events keep hardcoded importance=8.

**3. Reflection trigger (no LLM)**
```python
POIGNANCY_THRESHOLD = 150  # from reference implementation

async def maybe_reflect(agent: Agent, sim_id: str) -> None:
    if agent.poignancy_accumulator < POIGNANCY_THRESHOLD:
        return
    await reflect(agent, sim_id)
    agent.poignancy_accumulator = 0.0
```

**4. Reflection LLM calls (2-3 calls per reflection)**
Based on reference `agent.reflect()`:
- Call 1: "What are the 3 most important questions based on these memories?" (focus identification)
- Call 2: For each focus question, retrieve related memories and synthesize insights
- Call 3 (optional): Summarize recent conversations into relationship/planning thoughts

New Pydantic schemas needed:
- `ReflectionFocus(questions: list[str])` — output of Call 1
- `ReflectionInsight(insight: str, evidence_ids: list[str])` — output of Call 2

Both are simple instructor calls using `complete_structured()`. No new dependencies.

**5. Storing reflections as thoughts**
Reflections are stored in ChromaDB with `memory_type="thought"` (the existing `Memory` schema already has this). The `thought` type is retrieved in future memory queries automatically through existing `retrieve_memories()`.

Wait — the current `Memory` schema only allows `Literal["observation", "conversation", "action", "event"]`. Add `"thought"` to this union for v1.1.

**Confidence: HIGH** — all components use existing tools. The only risk is LLM call volume: reflection adds 2-3 extra calls when triggered. With 10 agents and frequent events, this could add 20-30 LLM calls per reflection cycle. Mitigation: run reflection asynchronously (don't block the tick loop), log when it fires, start with a higher threshold if costs are a concern.

---

## Relationship Tracking

The PROJECT.md v1.1 targets mention "relationship tracking" in the agent behavior fidelity cluster. The reference implementation stores per-agent relationship data in the `associate` memory module, retrieved during conversation decisions to determine rapport.

For v1.1, this can be approximated with existing ChromaDB memory storage: conversation memories already include both agent names. Relationship strength is retrievable by querying memories that mention both agents. No new data structure needed — the existing memory stream is sufficient for relationship context in prompts.

A dedicated relationship store (e.g., a dict `relationships: dict[str, dict[str, float]]` on the Agent class) is premature optimization for v1.1. Add it only if prompts show that retrieved memories don't provide enough relationship context.

**Confidence: MEDIUM** — this is an approximation of the reference's approach, not a direct port. Validate with actual prompt outputs before investing in a dedicated structure.

---

## No New Dependencies Required

Explicit confirmation that no `uv add` / `npm install` calls are needed for v1.1:

| Feature | Implementation | Dependency |
|---------|---------------|------------|
| Agent/Building/Event OOP classes | stdlib `@dataclass` | None |
| Building wall outlines | `Graphics.stroke()` | PixiJS 8.17 (installed) |
| Readable text labels | Increase `fontSize` on existing `pixiText` | PixiJS 8.17 (installed) |
| 3-level LLM decisions | New prompt functions + Pydantic schemas | instructor (installed) |
| Conversation gating (repetition) | Token overlap in Python | None |
| LLM concurrency cap | `asyncio.Semaphore` | None (stdlib) |
| LiteLLM in-memory cache | `litellm.caching.caching.Cache` | LiteLLM (installed) |
| Reflection system | New prompts + schemas | instructor + pydantic (installed) |
| Importance scoring | New `score_importance()` cognition call | instructor (installed) |
| Memory type "thought" | Extend `Memory` Literal in schemas.py | None |

---

## What NOT to Add

| Avoid | Why |
|-------|-----|
| `aiometer` / `aiolimiter` | `asyncio.Semaphore` in gateway.py handles all concurrency limiting without additional dependencies |
| `abc.ABC` base classes for agents | All agents run identical code paths; ABC enforces subclass contracts that are explicitly out of scope |
| Redis for LiteLLM caching | Single-user simulation; in-memory cache is sufficient and zero-ops |
| Sprite sheet / texture atlas | Agent circles are drawn as PixiJS Graphics, not sprites; no texture assets needed for v1.1 |
| `BitmapText` | Worth evaluating only if 25-agent text updates cause frame drops; not needed upfront |
| `pixi-tilemap` / `pixi-tiledmap` | Town map is currently hand-coded JSON; no Tiled editor files exist; importing a tile loader adds complexity without benefit until map authoring moves to Tiled |
| PydanticAI / LangGraph | These frameworks impose architectures that conflict with the paper's agent design; all reflection/planning logic stays as direct `complete_structured()` calls |

---

## Version Compatibility (v1.1 Specific)

| Pair | Note |
|------|------|
| PixiJS 8.17 `Graphics.stroke()` | The `stroke()` call must follow `fill()` in v8. The old v7 pattern `lineStyle()` before drawing is removed. Current code uses `setFillStyle()` + `fill()` correctly; add `.stroke()` after each `.fill()` call. |
| `litellm.caching.caching.Cache` import path | The cache module path changed in LiteLLM 1.60+ from `litellm.cache` to `litellm.caching.caching`. The 1.83+ versions installed use the new path. |
| `Memory` Pydantic `Literal` extension | Adding `"thought"` to the `memory_type` Literal breaks existing ChromaDB documents that lack this type. Existing records are unaffected — ChromaDB metadata is stored as strings and not re-validated. Only new writes use the updated model. |
| `asyncio.Semaphore` in async context | The semaphore must be created inside the async context (inside the FastAPI lifespan or app startup), not at module-import time, to avoid "no running event loop" errors. |

---

## Sources

- PixiJS v8 Graphics API — stroke/fill method order: https://pixijs.com/8.x/guides/components/scene-objects/graphics
- PixiJS v8 performance tips — Graphics objects fastest when not modified constantly; BitmapText for dynamic text: https://pixijs.com/8.x/guides/concepts/performance-tips
- PixiJS v8 BitmapText — pre-rasterized glyph atlas, MSDF support: https://pixijs.com/8.x/guides/components/scene-objects/text/bitmap
- PixiJS StrokeStyle interface — width, color, alpha, join, pixelLine: https://pixijs.download/dev/docs/scene.StrokeStyle.html
- LiteLLM in-memory cache setup: https://docs.litellm.ai/docs/caching/local_caching
- LiteLLM batch completion (async note): https://docs.litellm.ai/docs/completion/batching
- asyncio.Semaphore for LLM rate limiting: https://python.useinstructor.com/blog/2023/11/13/learn-async/
- Reference reflection implementation: GenerativeAgentsCN/generative_agents/modules/agent.py lines 335-383
- Reference 3-level action determination: GenerativeAgentsCN/generative_agents/modules/agent.py lines 419-457
- Python dataclasses stdlib docs: https://docs.python.org/3/library/dataclasses.html
- PixiJS v8.17 release (Text/BitmapText parity): https://pixijs.com/blog/8.16.0

---

*Stack research for: Agent Town v1.1 — OOP refactoring, UI polish, LLM optimization, reflection system*
*Researched: 2026-04-10*
