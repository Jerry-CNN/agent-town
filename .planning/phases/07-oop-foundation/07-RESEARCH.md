# Phase 7: OOP Foundation - Research

**Researched:** 2026-04-10
**Domain:** Python OOP refactoring — Agent/Building/Event class introduction, schemas package split, engine migration
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Agent class unifies AgentConfig + AgentState into one object. All fields are mutable (including identity fields like traits) to keep the door open for future trait evolution, even though v1.1 won't mutate them.
- **D-02:** Agent accesses memory via module-level calls: `store.add_memory(self.name, ...)`. The ChromaDB singleton stays in `store.py` — never moved into Agent.__init__ or wrapped in a class. This is a hard constraint from Codex pitfall analysis.
- **D-03:** Agent class lives in `backend/agents/agent.py`. Must NOT import from `engine.py` to avoid circular imports. Receives Maze and other engine dependencies via method parameters.
- **D-04:** Cognition methods on Agent (`perceive()`, `decide()`, `converse()`) delegate to existing standalone functions in `cognition/`. The functions themselves stay unchanged — Agent methods are thin wrappers that pass `self` fields as arguments.
- **D-05:** The `break` on engine.py:366 (limits conversation gating to one LLM call per tick per agent) must be preserved during the refactor. Add an explicit comment explaining why.
- **D-06:** Building properties (operating hours, purpose tag) defined in a separate `backend/data/map/buildings.json` file. Follows the existing data-driven pattern (agent configs are separate JSON files, town.json is generated map data). Do not mix building metadata into town.json.
- **D-07:** Building class lives in `backend/simulation/world.py` alongside Tile and Maze. Loaded from buildings.json at startup, indexed by sector name.
- **D-08:** Events expire by tick count (e.g., 10 ticks). Simple, deterministic, no sim-time clock needed. Configurable threshold.
- **D-09:** Broadcast events do NOT track propagation (who heard them). Only whisper events track propagation — since broadcasts reach everyone instantly, propagation tracking only matters for gossip.
- **D-10:** Event lifecycle states: created -> active -> spreading (whisper only) -> expired. Broadcast events go created -> active -> expired (skip spreading).
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

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ARCH-01 | Agent class unifies AgentConfig + AgentState into a single object with identity, runtime state, and system fields | Agent class structure mapped in Architecture Patterns; all callers in engine.py inventoried |
| ARCH-02 | Agent class has cognition methods (perceive, decide, converse, reflect) that delegate to existing functions | Existing cognition function signatures confirmed; delegation pattern documented |
| ARCH-03 | SimulationEngine uses Agent objects instead of separate config/state dicts | All `_agent_states` access points catalogued; migration path clear |
| BLD-01 | Building class with properties (name, operating hours, purpose tag) | Building class placement in world.py confirmed; buildings.json pattern documented |
| EVTS-01 | Event class tracks lifecycle (created, active, spreading, expired) | Event schema design documented; lifecycle state machine defined |
| EVTS-02 | Events track propagation — which agents heard the event and when | Propagation tracking design documented; broadcast vs whisper rules from D-09 |
| EVTS-03 | Events expire after a configurable duration | Tick-based expiry mechanism documented; default of 10 ticks recommended |
</phase_requirements>

---

## Summary

Phase 7 is a structural refactoring of the Python backend with no behavior change. The existing codebase uses two parallel data structures inside `SimulationEngine` — an `AgentConfig` Pydantic model (static identity) and an `AgentState` dataclass (runtime state) — held as separate dicts keyed by agent name. This phase introduces an `Agent` class that owns both, updates `SimulationEngine` to operate on a single `dict[str, Agent]`, adds a `Building` class to `world.py`, adds an `Event` Pydantic model to the new `schemas/events.py`, and splits the monolithic `schemas.py` (183 lines, 12 models) into domain-grouped modules.

The primary risks are: (1) ChromaDB singleton duplication if the Agent class moves `EphemeralClient()` creation — this silently wipes all agent memory; (2) circular import between `agent.py` and `engine.py` if dependency direction is violated; and (3) dual state ownership if `AgentState` fields are duplicated inside `Agent` rather than the dataclass being absorbed or replaced. All three are addressed by the existing architectural decisions (D-02, D-03, D-11).

The test suite has 178 tests currently passing (154 after excluding known pre-existing failures in health/integration endpoints). One test — `test_movement_one_tile_per_tick` — is pre-existing failed due to a movement loop architecture mismatch (movement is now handled in `_movement_loop`, not `_agent_step`). This is a pre-existing condition and not introduced by Phase 7. The refactor must preserve all currently-passing tests and must add a contract test verifying WebSocket payload byte-identity before and after.

**Primary recommendation:** Migrate state ownership to Agent class as the single source of truth. Replace `dict[str, AgentState]` with `dict[str, Agent]` in engine. Keep cognition function signatures unchanged — Agent methods extract fields and call them by value. Build in waves: schemas package first (pure rename, no logic change), then Agent class + engine migration, then Building class, then Event class.

---

## Standard Stack

### Core

No new packages. Phase 7 uses the installed stack exclusively.

| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| Python dataclasses (`@dataclass`) | stdlib | Agent runtime state fields | Already used for `AgentState`; project CLAUDE.md specifies "no Agent subclassing" so ABC is out |
| Pydantic v2 (`BaseModel`) | 2.12+ (installed) | Building, Event, and schema models | Already used for `AgentConfig`, `WSMessage`; `model_validator` pattern established |
| Python `__init__.py` re-exports | stdlib | `schemas/` backward-compat umbrella | Standard Python package pattern; zero new dependencies |

[VERIFIED: codebase grep] `pyproject.toml` lists `pydantic>=2.12`, `chromadb>=1.5.7` — no new installs required for Phase 7.

### Supporting (Already Installed)

| Library | Role in Phase 7 | Constraint |
|---------|-----------------|------------|
| ChromaDB | Stays in `store.py` module singleton | D-02: NEVER instantiated inside Agent class |
| pytest + pytest-asyncio | 178 tests; asyncio_mode=auto | Tests must pass; one pre-existing failure is exempt |

---

## Architecture Patterns

### Recommended Project Structure After Phase 7

```
backend/
├── schemas/                 # NEW: split from schemas.py
│   ├── __init__.py          # Re-exports all models (backward compat)
│   ├── agent.py             # AgentConfig, AgentScratch, AgentSpatial, AgentAction
│   ├── cognition.py         # DailySchedule, ScheduleEntry, SubTask, ScheduleRevision,
│   │                        #   PerceptionResult, ConversationDecision, ConversationTurn
│   ├── events.py            # Event (new), Memory, ImportanceScore
│   └── ws.py                # WSMessage, ProviderConfig, LLMTestResponse
├── agents/
│   ├── agent.py             # NEW: Agent class (unifies AgentConfig + AgentState)
│   ├── loader.py            # MODIFIED: returns list[Agent] instead of list[AgentConfig]
│   └── ...                  # cognition/ and memory/ stay unchanged
└── simulation/
    ├── engine.py            # MODIFIED: dict[str, Agent] replaces two dicts
    └── world.py             # MODIFIED: Building class added
```

Old `backend/schemas.py` is deleted after `backend/schemas/__init__.py` re-exports everything.

### Pattern 1: Agent Class — Unified State Owner

**What:** Single class owns both static identity (from `AgentConfig`) and mutable runtime state (was `AgentState`). Cognition methods are thin wrappers.

**When to use:** Always — this is the target for the entire phase.

**Design rationale:** Keeping `config: AgentConfig` as a sub-object (not flattened) avoids touching all existing code that accesses `state.config.scratch`, `state.config.spatial`, etc. Only the fields the engine accesses on every tick are promoted to the top level of Agent.

```python
# Source: CONTEXT.md D-01 + ARCHITECTURE.md recommended structure
# File: backend/agents/agent.py

from __future__ import annotations
from dataclasses import dataclass, field
from backend.schemas import AgentConfig, AgentScratch, AgentSpatial, ScheduleEntry


@dataclass
class Agent:
    """Unified agent object: identity (AgentConfig) + runtime state (was AgentState).

    D-01: All fields mutable, even identity fields.
    D-02: Memory accessed via store.py module functions, never a client here.
    D-03: No imports from simulation/engine.py — Maze passed via method params.
    """
    # --- Static identity (from AgentConfig JSON) ---
    name: str
    config: AgentConfig          # kept as sub-object, not flattened

    # --- Runtime state (was AgentState fields) ---
    coord: tuple[int, int]
    path: list[tuple[int, int]] = field(default_factory=list)
    current_activity: str = ""
    schedule: list[ScheduleEntry] = field(default_factory=list)

    # --- D-04: Cognition wrappers ---
    def perceive(self, maze, all_agents: dict) -> "PerceptionResult":
        from backend.agents.cognition.perceive import perceive as _perceive
        return _perceive(
            agent_coord=self.coord,
            agent_name=self.name,
            maze=maze,
            all_agents=all_agents,
        )

    def decide(self, simulation_id: str, perception, **kwargs):
        from backend.agents.cognition.decide import decide_action
        return decide_action(
            simulation_id=simulation_id,
            agent_name=self.name,
            agent_scratch=self.config.scratch,
            agent_spatial=self.config.spatial,
            current_activity=self.current_activity,
            perception=perception,
            current_schedule=self.schedule,
        )

    # converse() is omitted here — engine.py calls cognition functions directly
    # because conversation involves two agents and the wrapping would add no value.
```

[ASSUMED] The exact set of cognition wrappers on Agent is at Claude's discretion per CONTEXT.md. The pattern above implements perceive() and decide() as wrappers. converse() may be better left in engine.py since it takes two Agent objects.

### Pattern 2: Engine Migration — Single Dict

**What:** Replace two parallel dicts with one `dict[str, Agent]`.

**Engine callers inventoried (from codebase read of `engine.py`):**

| Code location | Currently accesses | After refactor |
|---------------|-------------------|----------------|
| `_movement_loop()` line ~199 | `state.path`, `state.coord` | `agent.path`, `agent.coord` |
| `_agent_step()` line ~276 | `state.config`, `state.coord`, `state.path`, `state.schedule`, `state.current_activity` | `agent.config`, `agent.coord`, etc. |
| `_emit_agent_update()` line ~413 | `state.coord`, `state.current_activity` | `agent.coord`, `agent.current_activity` |
| `inject_event()` line ~476 | `state.path` | `agent.path` |
| `get_snapshot()` line ~508 | `state.coord`, `state.current_activity` | `agent.coord`, `agent.current_activity` |
| `initialize()` line ~137 | creates `AgentState(...)` objects | creates `Agent(...)` objects |

Field names are preserved identically. The engine renaming is a mechanical field-accessor update.

**The `_configs` list is eliminated** — `SimulationEngine._configs` currently holds the pre-initialization list of `AgentConfig` objects. After the refactor, `loader.py` can return `list[Agent]` directly (with runtime fields zeroed out), eliminating `_configs`.

```python
# engine.py after migration
class SimulationEngine:
    def __init__(self, maze, agents: list[Agent], simulation_id: str, ...):
        self._agents: dict[str, Agent] = {}   # renamed from _agent_states
        self._agent_configs: list[Agent] = agents  # pre-init list

    async def initialize(self) -> None:
        await reset_simulation(self.simulation_id)
        for agent in self._agent_configs:
            agent.coord = agent.config.coord       # set from JSON
            agent.current_activity = agent.config.currently
            self._agents[agent.name] = agent
        # ... schedule generation unchanged
```

### Pattern 3: Building Class

**What:** Thin dataclass in `world.py` holding sector metadata loaded from `buildings.json`.

**Why `world.py`:** Building class logically belongs with `Tile` and `Maze` — it describes the physical world. The decision is locked (D-07).

```python
# Source: CONTEXT.md D-06, D-07
# File: backend/simulation/world.py (addition, not replacement)

from dataclasses import dataclass
from typing import Literal

@dataclass
class Building:
    """Sector-level metadata for a building in the town map.

    Loaded from backend/data/map/buildings.json, indexed by sector name.
    Separate from town.json (tile geometry) per D-06.
    """
    name: str                              # display name, e.g. "The Cozy Cafe"
    sector: str                            # key in town.json, e.g. "cafe"
    opens: int                             # hour (0-23), e.g. 7
    closes: int                            # hour (0-23), e.g. 22
    purpose: str                           # tag, e.g. "food", "finance", "social"
```

**buildings.json format (to create):**

```json
[
  {"sector": "cafe", "name": "The Cozy Cafe", "opens": 7, "closes": 22, "purpose": "food"},
  {"sector": "stock-exchange", "name": "Stock Exchange", "opens": 9, "closes": 17, "purpose": "finance"},
  {"sector": "wedding-hall", "name": "Wedding Hall", "opens": 10, "closes": 23, "purpose": "social"},
  {"sector": "park", "name": "Town Park", "opens": 0, "closes": 24, "purpose": "leisure"},
  {"sector": "home-alice", "name": "Alice's Home", "opens": 0, "closes": 24, "purpose": "residential"},
  {"sector": "home-bob", "name": "Bob's Home", "opens": 0, "closes": 24, "purpose": "residential"},
  {"sector": "home-carla", "name": "Carla's Home", "opens": 0, "closes": 24, "purpose": "residential"}
]
```

[ASSUMED] The sector list is inferred from the town.json address data. The actual sectors should be verified against `Maze.address_tiles` keys at runtime.

### Pattern 4: Event Class and Lifecycle

**What:** Pydantic model in `schemas/events.py` tracking lifecycle state and (for whispers) propagation.

**Lifecycle state machine (D-10):**

```
Broadcast: created -> active -> expired
Whisper:   created -> active -> spreading -> expired
```

```python
# Source: CONTEXT.md D-08, D-09, D-10
# File: backend/schemas/events.py

from typing import Literal
from pydantic import BaseModel, Field

EVENT_EXPIRY_TICKS: int = 10  # D-08: configurable; Claude's discretion default

class Event(BaseModel):
    """Injected event with lifecycle tracking.

    D-09: Broadcasts do not track propagation (heard_by is always empty).
    D-10: State machine: created -> active -> [spreading (whisper)] -> expired.
    D-08: Expiry by tick count, not wall clock time.
    """
    text: str
    mode: Literal["broadcast", "whisper"]
    target: str | None = None          # whisper target agent name; None for broadcast
    status: Literal["created", "active", "spreading", "expired"] = "created"
    created_tick: int = 0
    expires_after_ticks: int = EVENT_EXPIRY_TICKS
    heard_by: list[str] = Field(default_factory=list)  # whisper only (D-09)

    def is_expired(self, current_tick: int) -> bool:
        return current_tick - self.created_tick >= self.expires_after_ticks

    def tick(self, current_tick: int) -> None:
        """Advance lifecycle state based on current tick."""
        if self.is_expired(current_tick):
            self.status = "expired"
        elif self.mode == "whisper" and self.status == "active":
            self.status = "spreading"
```

**Where Event objects live:** `SimulationEngine` holds an `active_events: list[Event]` that is pruned each tick. Events in this list are what the perception system reads from `tile._events`. The existing `inject_event()` call path (stores to ChromaDB as `memory_type="event"`) is preserved alongside this new tracking object.

### Pattern 5: schemas/ Package — Backward Compatibility

**What:** Split `schemas.py` into 4 domain files + `__init__.py` that re-exports everything.

**Critical constraint:** Every existing import in the codebase must continue working without modification. The entire codebase currently uses `from backend.schemas import X` — these must still resolve after the split.

**Inventory of current schemas.py models and their target file:**

| Model | Target file | Currently imported by |
|-------|-------------|----------------------|
| `AgentAction` | `schemas/agent.py` | `decide.py`, `engine.py` |
| `AgentScratch` | `schemas/agent.py` | `converse.py`, `decide.py`, `plan.py`, `store.py`, `engine.py` |
| `AgentSpatial` | `schemas/agent.py` | `decide.py` |
| `AgentConfig` | `schemas/agent.py` | `loader.py`, `engine.py`, test files |
| `WSMessage` | `schemas/ws.py` | `routers/ws.py`, test files |
| `ProviderConfig` | `schemas/ws.py` | `routers/llm.py` |
| `LLMTestResponse` | `schemas/ws.py` | `routers/llm.py` |
| `SubTask` | `schemas/cognition.py` | `plan.py` |
| `ScheduleEntry` | `schemas/cognition.py` | `engine.py`, `converse.py`, `plan.py`, test files |
| `DailySchedule` | `schemas/cognition.py` | `plan.py` |
| `ImportanceScore` | `schemas/events.py` | `store.py` |
| `ConversationDecision` | `schemas/cognition.py` | `converse.py` |
| `ConversationTurn` | `schemas/cognition.py` | `converse.py` |
| `ScheduleRevision` | `schemas/cognition.py` | `converse.py` |
| `PerceptionResult` | `schemas/cognition.py` | `perceive.py`, `decide.py`, `engine.py`, test files |
| `Memory` | `schemas/events.py` | `retrieval.py` |
| `Event` (NEW) | `schemas/events.py` | `engine.py` (new usage) |

**`schemas/__init__.py` pattern:**

```python
# Source: Python stdlib module pattern
# File: backend/schemas/__init__.py

from backend.schemas.agent import AgentConfig, AgentScratch, AgentSpatial, AgentAction
from backend.schemas.cognition import (
    DailySchedule, ScheduleEntry, SubTask, ScheduleRevision,
    PerceptionResult, ConversationDecision, ConversationTurn,
)
from backend.schemas.events import Event, Memory, ImportanceScore
from backend.schemas.ws import WSMessage, ProviderConfig, LLMTestResponse

__all__ = [
    "AgentConfig", "AgentScratch", "AgentSpatial", "AgentAction",
    "DailySchedule", "ScheduleEntry", "SubTask", "ScheduleRevision",
    "PerceptionResult", "ConversationDecision", "ConversationTurn",
    "Event", "Memory", "ImportanceScore",
    "WSMessage", "ProviderConfig", "LLMTestResponse",
]
```

### Anti-Patterns to Avoid

- **Flattening AgentConfig into Agent:** All 12+ fields of `AgentConfig` scattered onto `Agent` — then `loader.py`, `converse.py`, `decide.py`, test helpers, and schemas all break. Keep `Agent.config: AgentConfig` as a sub-object.
- **Cascade-refactoring cognition function signatures:** Changing `perceive(agent_coord, agent_name, maze, all_agents)` to `perceive(agent: Agent, maze)` breaks 11 test assertions in `test_cognition.py` and invalidates the D-04 constraint.
- **Moving `_chroma_client` into Agent.__init__:** Creates a second `EphemeralClient()` per agent; agents lose all memories silently.
- **Importing from `engine.py` in `agent.py`:** `engine.py` imports `Agent`; if `agent.py` imports anything from `engine.py`, Python raises `ImportError` at startup.
- **Keeping `_agent_states` dict after adding `Agent` class:** Creates dual state ownership — `engine._agent_states[name].coord` and `agent.coord` drift silently. Choose one owner.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Backward-compatible re-exports | Custom import shim or __getattr__ magic | Standard `__init__.py` with explicit imports | Explicit re-exports are grep-able, IDE-friendly, and work with mypy/pyright |
| Circular import breaking | TYPE_CHECKING guards or lazy imports | Dependency direction enforcement (schemas -> agents -> engine) | TYPE_CHECKING guards hide the bug at runtime; proper layering eliminates it |
| Tick-based expiry | Time-based expiry with datetime comparison | `created_tick: int` + `expires_after_ticks: int` | Deterministic, testable, no clock drift; matches D-08 decision |

---

## Runtime State Inventory

> This is a pure in-process refactor. No external services store the refactored names.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | ChromaDB `EphemeralClient` — in-memory only, starts fresh each run via `reset_simulation()` | None — data is ephemeral and re-created each startup |
| Live service config | None — simulation runs as a single FastAPI process, no external services affected by class renaming | None |
| OS-registered state | None — no Task Scheduler, pm2, or launchd entries | None |
| Secrets/env vars | None — phase touches no env var names | None |
| Build artifacts | `.venv/` cached bytecode (`.pyc` files) — will be auto-invalidated by Python on first import after rename | None — Python handles this automatically |

**Conclusion:** This is a pure Python import-graph refactor. The only "state" at risk is the ChromaDB singleton, which is protected by D-02 and verified by the existing `MemoryStore = None` sentinel in `store.py`.

---

## Common Pitfalls

### Pitfall 1: ChromaDB Singleton Duplication (CRITICAL)

**What goes wrong:** If `Agent.__init__` calls `chromadb.EphemeralClient()` — even indirectly — a second in-memory database is created. Agents appear to work but have empty memory on every query. No error is raised.

**Why it happens:** OOP instinct is to own resources inside the class. The ChromaDB client looks like a resource Agent "should" own.

**How to avoid:** `Agent` class has ZERO chromadb imports. It calls `store.add_memory(self.name, ...)` and `store.retrieve_memories(self.name, ...)` — pure function calls into the module-level singleton.

**Verification test:**
```python
import backend.agents.memory.store as store
client_before = id(store._chroma_client)
from backend.agents.agent import Agent
# Create multiple Agent instances
client_after = id(store._chroma_client)
assert client_before == client_after, "Singleton must not be recreated"
```

**Warning signs:** `col.count()` returns 0 for an agent that should have memories; `store._chroma_client is not store._chroma_client` evaluates True.

[VERIFIED: codebase read] Current `store.py` line 28: `_chroma_client = chromadb.EphemeralClient()` is module-level. Line 174: `MemoryStore = None` sentinel. Design is already correct.

### Pitfall 2: Circular Import Agent <-> Engine

**What goes wrong:** `engine.py` imports `Agent`; if `agent.py` imports `Maze` from `simulation/world.py` (not `engine.py` — but still a simulation module), the import chain is `engine -> agent -> simulation.world -> (ok, no cycle)`. However, if `agent.py` imports anything from `engine.py`, startup fails with `ImportError: cannot import name 'Agent' from partially initialized module 'backend.agents.agent'`.

**How to avoid:** `agent.py` import list must contain ONLY `backend.schemas.*` and `backend.agents.cognition.*` and `backend.agents.memory.*`. Never `backend.simulation.*` at module level. Pass `maze` as a method parameter.

**Verification command (add to CI):**
```bash
python -c "from backend.agents.agent import Agent; from backend.simulation.engine import SimulationEngine; print('OK')"
```

[VERIFIED: PITFALLS.md, ARCHITECTURE.md] Both sources confirm this as the #2 OOP refactor risk with the same mitigation.

### Pitfall 3: Dual State Ownership (State Drift)

**What goes wrong:** `engine._agent_states` dict keeps `AgentState` objects while a new `Agent` class has its own `.coord`, `.path`, etc. The movement loop mutates `AgentState.coord`; the `Agent.perceive()` method reads `self.coord` — two different values.

**How to avoid:** The refactor eliminates `AgentState` entirely. `SimulationEngine._agents: dict[str, Agent]` replaces `SimulationEngine._agent_states: dict[str, AgentState]`. One object, one owner.

**Verification test:** After refactor, `engine._agents["Alice"].coord` and `engine.get_snapshot()["agents"][0]["coord"]` must return the same value after any mutation.

### Pitfall 4: Test Breakage from AgentState Import

**What goes wrong:** `test_simulation.py` and `test_event_injection.py` both import `AgentState` directly:
```python
from backend.simulation.engine import AgentState
```
After the refactor, `AgentState` no longer exists in `engine.py`. These tests will fail with `ImportError`.

**How to avoid:** Either (a) keep `AgentState` as a deprecated alias in `engine.py` that points to `Agent` for one release, or (b) update all test imports to use `Agent` from `backend.agents.agent`. Option (b) is cleaner. The test files that need updating:
- `tests/test_simulation.py` — 7 occurrences of `AgentState` construction
- `tests/test_event_injection.py` — 8 occurrences of `AgentState` construction
- `tests/test_concurrency.py` — likely uses `AgentState`

[VERIFIED: codebase read] `test_simulation.py` line 87: `from backend.simulation.engine import AgentState`. This import will break and must be updated in the same wave as the engine migration.

### Pitfall 5: Pre-Existing Test Failure Misidentified as Regression

**What goes wrong:** `test_movement_one_tile_per_tick` in `test_simulation.py` is already failing (1 pre-existing failure confirmed). After Phase 7 changes, this test still fails — but it was failing before, so it is NOT a Phase 7 regression.

**How to avoid:** Document the pre-existing failure before starting. The success criterion for Phase 7 is that no NEW test failures are introduced, not that all 178 tests pass.

**Pre-existing failures (confirmed by running `pytest` before Phase 7 begins):**
- `test_simulation.py::test_movement_one_tile_per_tick` — architecture mismatch: test calls `_agent_step()` and expects coord update, but movement is now handled by `_movement_loop()`.
- `test_health.py::test_health_returns_200_with_correct_keys` — unrelated to Phase 7 domain.
- `test_health.py::test_health_returns_200_when_ollama_unavailable` — unrelated.
- `test_integration.py::test_health_check_returns_200` — unrelated.
- `test_integration.py::test_config_ollama_returns_configured` — unrelated.
- `test_integration.py::test_config_openrouter_returns_configured` — unrelated.

### Pitfall 6: `schemas/__init__.py` Creates Import Cycles Within the Package

**What goes wrong:** If `schemas/agent.py` imports from `schemas/cognition.py` (e.g., to type-hint a ScheduleEntry in AgentConfig), and `schemas/cognition.py` imports from `schemas/agent.py`, a circular import exists within the package.

**How to avoid:** Domain files in `schemas/` MUST NOT import from each other. `schemas/__init__.py` is the only file that imports from all of them. If cross-domain typing is needed, use string literals for forward references (`"ScheduleEntry"` instead of `ScheduleEntry`).

[VERIFIED: codebase read] Current `schemas.py` has no circular dependencies within its own models. The split preserves this.

### Pitfall 7: `break` on engine.py:366 Removed During Refactor

**What goes wrong:** The `break` after the conversation gate check is the only thing that limits conversation gating to one LLM call per tick per agent. Removing it during the agent step refactor silently multiplies LLM costs by the number of nearby agents.

**How to avoid (D-05):** After migrating `_agent_step()` to use `Agent` objects, locate the `break` at line 366 (or its equivalent after rename) and add an explicit comment:
```python
# LOAD-BEARING BREAK (D-05): Only attempt one conversation gate check per tick.
# Removing this break multiplies LLM calls by the number of nearby agents.
break
```

[VERIFIED: codebase read] `engine.py` line 366: `break` exists and is in the correct location.

---

## Code Examples

### Schema Split — Complete `schemas/__init__.py`

```python
# Source: Python stdlib re-export pattern (D-11)
# File: backend/schemas/__init__.py

"""Backward-compatible umbrella import for the schemas package.

All models are importable from `backend.schemas` exactly as before:
    from backend.schemas import AgentConfig, WSMessage, PerceptionResult

Domain-specific imports also work:
    from backend.schemas.agent import AgentConfig
    from backend.schemas.events import Event
"""

from backend.schemas.agent import AgentConfig, AgentScratch, AgentSpatial, AgentAction
from backend.schemas.cognition import (
    DailySchedule,
    ScheduleEntry,
    SubTask,
    ScheduleRevision,
    PerceptionResult,
    ConversationDecision,
    ConversationTurn,
)
from backend.schemas.events import Event, Memory, ImportanceScore
from backend.schemas.ws import WSMessage, ProviderConfig, LLMTestResponse

__all__ = [
    # agent
    "AgentConfig", "AgentScratch", "AgentSpatial", "AgentAction",
    # cognition
    "DailySchedule", "ScheduleEntry", "SubTask", "ScheduleRevision",
    "PerceptionResult", "ConversationDecision", "ConversationTurn",
    # events
    "Event", "Memory", "ImportanceScore",
    # ws
    "WSMessage", "ProviderConfig", "LLMTestResponse",
]
```

### Engine Migration — Before / After diff for `_agent_step`

```python
# BEFORE (engine.py _agent_step signature)
async def _agent_step(self, agent_name: str, state: AgentState) -> None:
    config = state.config
    all_agents_view = {
        name: {"coord": s.coord, "current_activity": s.current_activity}
        for name, s in self._agent_states.items()
    }
    perception = perceive(agent_coord=state.coord, ...)
    if state.path: return
    ...

# AFTER (engine.py _agent_step signature — field names unchanged)
async def _agent_step(self, agent_name: str, agent: Agent) -> None:
    config = agent.config
    all_agents_view = {
        name: {"coord": a.coord, "current_activity": a.current_activity}
        for name, a in self._agents.items()
    }
    perception = perceive(agent_coord=agent.coord, ...)
    if agent.path: return
    ...
```

### WebSocket Contract Test (required by success criteria)

```python
# Source: Phase 7 success criterion 6 — byte-identical WS payloads
# File: tests/test_ws_contract.py (new test file)

def _capture_snapshot(engine) -> dict:
    """Capture the snapshot payload structure for comparison."""
    snapshot = engine.get_snapshot()
    # Normalize to check structural identity (not exact bytes — timestamps vary)
    agents = sorted(snapshot["agents"], key=lambda a: a["name"])
    return {
        "agent_names": [a["name"] for a in agents],
        "agent_coord_types": [type(a["coord"]).__name__ for a in agents],
        "simulation_status": snapshot["simulation_status"],
        "has_tick_count": "tick_count" in snapshot,
    }

def test_ws_payload_structure_preserved_after_oop_refactor():
    """WebSocket snapshot payload has identical structure before and after Agent refactor."""
    from backend.simulation.engine import SimulationEngine
    from backend.agents.agent import Agent
    from backend.simulation.world import Maze

    # The snapshot structure this test captures becomes the contract.
    # Run this before and after the refactor; both must produce identical results.
    maze = Maze(SMALL_MAP_CONFIG)
    # ... setup and verify snapshot structure matches pre-refactor baseline
```

### Building Class Loading

```python
# Source: CONTEXT.md D-06, D-07
# File: backend/simulation/world.py (addition)

import json
from pathlib import Path

BUILDINGS_PATH = Path(__file__).parent.parent / "data" / "map" / "buildings.json"

def load_buildings() -> dict[str, "Building"]:
    """Load Building metadata from buildings.json, indexed by sector name.

    Returns:
        Dict of sector -> Building for O(1) lookup by sector name.
    """
    if not BUILDINGS_PATH.exists():
        return {}
    raw = json.loads(BUILDINGS_PATH.read_text(encoding="utf-8"))
    return {b["sector"]: Building(**b) for b in raw}
```

---

## State of the Art

| Old Pattern | Phase 7 Pattern | Reason |
|-------------|-----------------|--------|
| `AgentConfig` (Pydantic, static) + `AgentState` (dataclass, mutable) as parallel dicts | Single `Agent` dataclass owning both | Eliminates dual state ownership (Pitfall 3) |
| Flat `schemas.py` (183 lines, 12 models) | Domain-grouped `schemas/` package with backward-compat `__init__.py` | Standard Python package growth pattern; no behavior change |
| Building metadata embedded in tile address strings only | `Building` dataclass in `world.py` + `buildings.json` | Adds metadata (hours, purpose) without polluting town.json |
| No Event lifecycle tracking (events go straight to ChromaDB as `memory_type="event"`) | `Event` Pydantic model with status field + tick-based expiry | Enables future perception filtering by event status |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `loader.py` should return `list[Agent]` after refactor | Architecture Patterns (Pattern 2) | Planner may choose to keep `loader.py` returning `list[AgentConfig]` and have engine construct `Agent` objects — both approaches work; the plan should pick one |
| A2 | Exact sector list for `buildings.json` inferred from town.json at runtime | Pattern 3 / Building Class | Buildings.json might need sectors not visible from the alice.json spatial tree; planner should verify against `Maze.address_tiles.keys()` |
| A3 | `converse()` wrapper on Agent is omitted (conversation stays in engine.py calling cognition functions directly) | Pattern 1 | If planner decides `Agent.converse()` is needed, its signature must accept `other: Agent` which is fine since Agent doesn't import engine |
| A4 | Pre-existing test failures (5 in health/integration + 1 in simulation) are excluded from Phase 7 success gate | Common Pitfalls / Pitfall 5 | If any of these are considered "must fix" by user, Phase 7 scope expands |

---

## Open Questions (RESOLVED)

1. **Should `loader.py` return `list[Agent]` or stay as `list[AgentConfig]`?**
   - RESOLVED: Keep `loader.py` returning `list[AgentConfig]`. Engine's `initialize()` constructs `Agent` objects. Isolates the migration to one file.

2. **Does the Event class need a `tile_coord` field to integrate with `Tile._events`?**
   - RESOLVED: Phase 7 adds the `Event` model only. Wiring into `Tile._events` is a behavior change and belongs in v1.2 PCPT requirements. Success criterion 4 only requires the `status` field.

---

## Environment Availability

This phase has no external dependencies beyond what is already installed.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | `Agent` dataclass, `asyncio.TaskGroup` | Yes | 3.14 (checked via venv) | — |
| Pydantic v2 | `Event`, `Building` models | Yes | 2.12+ (pyproject.toml) | — |
| pytest + pytest-asyncio | 178 tests | Yes | pytest 9.x, asyncio 1.3+ | — |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-asyncio 1.3.0 |
| Config file | `pyproject.toml` (`asyncio_mode = "auto"`, `testpaths = ["tests"]`) |
| Quick run command | `.venv/bin/python -m pytest tests/test_world.py tests/test_agent_loader.py tests/test_cognition.py -x -q` |
| Full suite command | `.venv/bin/python -m pytest tests/ -q` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ARCH-01 | Agent class has name, config, coord, path, current_activity, schedule fields | unit | `.venv/bin/python -m pytest tests/test_agent_class.py -x -q` | ❌ Wave 0 |
| ARCH-02 | Agent.perceive() calls cognition perceive() function with correct args | unit | `.venv/bin/python -m pytest tests/test_agent_class.py::test_agent_perceive_delegates -x -q` | ❌ Wave 0 |
| ARCH-03 | SimulationEngine._agents is dict[str, Agent] after initialize() | unit | `.venv/bin/python -m pytest tests/test_simulation.py -x -q` | ✅ (needs update for AgentState -> Agent) |
| BLD-01 | Building dataclass has name, sector, opens, closes, purpose fields | unit | `.venv/bin/python -m pytest tests/test_building.py -x -q` | ❌ Wave 0 |
| EVTS-01 | Event.status transitions through created/active/spreading/expired | unit | `.venv/bin/python -m pytest tests/test_events.py::test_event_lifecycle -x -q` | ❌ Wave 0 |
| EVTS-02 | Whisper Event.heard_by accumulates agent names; broadcast Event.heard_by stays empty | unit | `.venv/bin/python -m pytest tests/test_events.py::test_event_propagation -x -q` | ❌ Wave 0 |
| EVTS-03 | Event.is_expired() returns True after expires_after_ticks ticks | unit | `.venv/bin/python -m pytest tests/test_events.py::test_event_expiry -x -q` | ❌ Wave 0 |
| All | WebSocket payload structure byte-identical before/after refactor | contract | `.venv/bin/python -m pytest tests/test_ws_contract.py -x -q` | ❌ Wave 0 |
| All | Existing tests pass (no regressions) | regression | `.venv/bin/python -m pytest tests/ -q --ignore=tests/test_health.py --ignore=tests/test_integration.py` | ✅ |
| All | No circular import between agent.py and engine.py | smoke | `python -c "from backend.agents.agent import Agent; from backend.simulation.engine import SimulationEngine; print('OK')"` | inline |

### Sampling Rate

- **Per task commit:** `.venv/bin/python -m pytest tests/test_world.py tests/test_agent_loader.py tests/test_cognition.py tests/test_memory.py -x -q`
- **Per wave merge:** `.venv/bin/python -m pytest tests/ -q` (all 178 tests; pre-existing failures documented above are exempt)
- **Phase gate:** Full suite green (excluding pre-existing failures) + WS contract test green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_agent_class.py` — covers ARCH-01, ARCH-02 (Agent class field existence and cognition delegation)
- [ ] `tests/test_building.py` — covers BLD-01 (Building dataclass fields, buildings.json loading)
- [ ] `tests/test_events.py` — covers EVTS-01, EVTS-02, EVTS-03 (Event lifecycle, propagation, expiry)
- [ ] `tests/test_ws_contract.py` — covers success criterion 6 (WS payload byte-identity before/after)
- [ ] Update `tests/test_simulation.py` — replace `AgentState` imports with `Agent` imports (7 occurrences)
- [ ] Update `tests/test_event_injection.py` — replace `AgentState` imports with `Agent` imports (8 occurrences)

---

## Security Domain

> `security_enforcement` is not explicitly set to false in config.json — treated as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Phase 7 is internal refactoring only |
| V3 Session Management | No | No session changes |
| V4 Access Control | No | No new endpoints or permissions |
| V5 Input Validation | Yes (minor) | `Event.text` should carry forward the 500-char truncation already in `engine.inject_event()` |
| V6 Cryptography | No | No crypto changes |

### Known Threat Patterns for this Refactor

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| ChromaDB memory poisoning via agent_id collision | Tampering | Preserve existing `where={"agent_id": agent_id}` filter on all queries — unchanged by refactor |
| Event text overflow in new Event model | Tampering | `Event.text` should validate `max_length=500` via Pydantic `Field(max_length=500)` to match existing `text[:500]` truncation in `inject_event()` |

---

## Sources

### Primary (HIGH confidence)

- Direct codebase read: `backend/simulation/engine.py` (520 lines) — complete `AgentState` dataclass, all `_agent_states` access points catalogued
- Direct codebase read: `backend/schemas.py` (183 lines) — complete model inventory for split
- Direct codebase read: `backend/agents/memory/store.py` — ChromaDB singleton pattern confirmed
- Direct codebase read: `tests/test_simulation.py` (847 lines) — all `AgentState` import locations confirmed
- Direct codebase read: `.planning/research/PITFALLS.md` — 10 pitfalls with line-number-level specificity
- Direct codebase read: `.planning/research/ARCHITECTURE.md` — complete integration point map
- Direct codebase read: `.planning/phases/07-oop-foundation/07-CONTEXT.md` — locked decisions
- Pytest run: `178 tests collected`, `1 failed (pre-existing)` confirmed baseline

### Secondary (MEDIUM confidence)

- `.planning/research/SUMMARY.md` — Phase ordering rationale and confidence assessment
- `GenerativeAgentsCN/generative_agents/modules/agent.py` — reference Agent class structure (inspected first 80 lines)

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — No new packages; all patterns verified against installed codebase
- Architecture: HIGH — Full codebase read; all `_agent_states` access points catalogued; test file import locations confirmed
- Pitfalls: HIGH — 5 of 7 pitfalls verified at line numbers from direct code reads; 2 are patterns from PITFALLS.md which was itself derived from direct code analysis
- Test plan: HIGH — 178 tests collected and run; pre-existing failure count confirmed; Wave 0 gaps are specific and actionable

**Research date:** 2026-04-10
**Valid until:** 2026-05-10 (stable Python/Pydantic ecosystem; no new dependencies)
