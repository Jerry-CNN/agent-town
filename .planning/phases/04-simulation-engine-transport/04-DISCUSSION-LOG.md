# Phase 4: Simulation Engine & Transport - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-10
**Phase:** 04-simulation-engine-transport
**Areas discussed:** Simulation tick model, WebSocket push protocol, Pause/resume behavior, Agent movement pacing

---

## Simulation Tick Model

### Tick Rate

| Option | Description | Selected |
|--------|-------------|----------|
| Every 5-10 seconds | Each agent runs perceive/decide/act per tick. Matches reference pacing. | ✓ |
| Every 2-3 seconds | Faster pacing but risk of LLM queueing with cheap models. | |
| You decide | Claude picks based on LLM latency. | |

**User's choice:** Every 5-10 seconds
**Notes:** None

### Concurrency

| Option | Description | Selected |
|--------|-------------|----------|
| All agents in parallel | asyncio.TaskGroup, fastest, highest concurrent LLM load. | ✓ |
| Batched (4 at a time) | Semaphore throttling, prevents overloading Ollama. | |
| You decide | | |

**User's choice:** All agents in parallel
**Notes:** None

---

## WebSocket Push Protocol

### Events Pushed

| Option | Description | Selected |
|--------|-------------|----------|
| All state changes | Position, activity, conversations, events. Browser reconstructs full state. | ✓ |
| Position + activity only | Minimal updates. Lower bandwidth. | |
| You decide | | |

**User's choice:** All state changes
**Notes:** None

### Initial State Sync

| Option | Description | Selected |
|--------|-------------|----------|
| Full snapshot on connect | Send all agent state on connect, then stream deltas. Handles page refresh. | ✓ |
| Stream only, no snapshot | Build state incrementally. Simpler but misses pre-connect events. | |
| You decide | | |

**User's choice:** Full snapshot on connect
**Notes:** None

---

## Pause/Resume Behavior

### Pause Mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Asyncio Event flag | Check flag before each tick. Agents finish current action, don't start new tick. | ✓ |
| Cancel running tasks | Forcefully cancel coroutines. Immediate but risks inconsistent state. | |
| You decide | | |

**User's choice:** Asyncio Event flag
**Notes:** None

---

## Agent Movement Pacing

### Movement Speed

| Option | Description | Selected |
|--------|-------------|----------|
| One tile per tick | Advance one tile each 5-10 sec tick. Frontend interpolates smooth movement. | ✓ |
| Variable speed by urgency | Faster when rushing, slower when strolling. More realistic but complex. | |
| You decide | | |

**User's choice:** One tile per tick
**Notes:** None

---

## Claude's Discretion

- Exact tick interval (5-10 sec range)
- LLM call timeout handling per tick
- WebSocket message batching strategy
- Connection pool management
- REST endpoints for pause/resume

## Deferred Ideas

- Simulation speed control (SIM-04) -- deferred to v2
- User-configurable agent count (SIM-05) -- deferred to v2
