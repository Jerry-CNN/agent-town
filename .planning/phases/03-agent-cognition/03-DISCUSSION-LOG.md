# Phase 3: Agent Cognition - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-09
**Phase:** 03-agent-cognition
**Areas discussed:** Memory system, Perception model, Schedule & planning, Conversation system

---

## Memory System

### Retrieval Scoring

| Option | Description | Selected |
|--------|-------------|----------|
| Match the reference weights | recency x 0.5 + relevance x 3 + importance x 2. Proven formula from the Generative Agents paper. | ✓ |
| Simplified: relevance only | Just ChromaDB vector similarity. Cheaper but loses temporal and emotional dimensions. | |
| Equal weights | recency x 1 + relevance x 1 + importance x 1. Balanced but doesn't match the paper. | |

**User's choice:** Match the reference weights
**Notes:** None

### Importance Scoring

| Option | Description | Selected |
|--------|-------------|----------|
| LLM scores each memory 1-10 | Reference approach: LLM rates importance when storing. 1 extra LLM call per memory. | ✓ |
| Rule-based heuristics | Conversations = high, movement = low, events = high. No LLM call. | |
| You decide | Claude picks best cost/quality tradeoff. | |

**User's choice:** LLM scores each memory 1-10
**Notes:** None

### Memory Types

| Option | Description | Selected |
|--------|-------------|----------|
| Everything significant | Observations, conversations, actions, events. Broad capture, retrieval handles relevance. | ✓ |
| Conversations + events only | Skip mundane observations. Fewer memories but agents forget routine context. | |
| You decide | Claude picks based on cost-effectiveness. | |

**User's choice:** Everything significant
**Notes:** None

### Top-K Retrieval

| Option | Description | Selected |
|--------|-------------|----------|
| Top 5-10 | Reference uses ~10. Good balance of recall and token cost. | ✓ |
| Top 3-5 | Minimal context. Saves tokens but may miss important memories. | |
| Dynamic threshold | Return all above a score threshold. More adaptive but harder to predict. | |

**User's choice:** Top 5-10
**Notes:** None

---

## Perception Model

### Vision Radius

| Option | Description | Selected |
|--------|-------------|----------|
| Tile-based radius | Perceive everything within N tiles. Reference uses ~5 tiles. Simple, predictable. | ✓ |
| Sector-based | Perceive everything in current sector. Simpler but 'sees through walls'. | |
| Hybrid: sector + nearby tiles | Most realistic but more complex. | |

**User's choice:** Tile-based radius
**Notes:** None

### Perception Content

| Option | Description | Selected |
|--------|-------------|----------|
| Agents + events + location context | Full awareness: other agents, events, spatial context. Matches reference. | ✓ |
| Agents + events only | Skip location context. | |
| You decide | Claude picks for most interesting behavior. | |

**User's choice:** Agents + events + location context
**Notes:** None

---

## Schedule & Planning

### Schedule Granularity

| Option | Description | Selected |
|--------|-------------|----------|
| Hourly blocks -> sub-tasks | LLM generates hourly plan, then decomposes into 5-15 min sub-tasks. 2 LLM calls. | ✓ |
| Hourly blocks only | Just hourly plans, no decomposition. 1 LLM call, coarser behavior. | |
| 30-minute blocks | Middle ground. Single LLM call with more entries. | |

**User's choice:** Hourly blocks -> sub-tasks
**Notes:** None

### Replanning Triggers

| Option | Description | Selected |
|--------|-------------|----------|
| After conversations + significant events | Agent revises schedule when conversation or event changes plans. Matches AGT-08. | ✓ |
| Fixed intervals | Replan every N ticks regardless. Predictable cost but less reactive. | |
| You decide | Claude picks best trigger mechanism. | |

**User's choice:** After conversations + significant events
**Notes:** None

---

## Conversation System

### Conversation Trigger

| Option | Description | Selected |
|--------|-------------|----------|
| Proximity + LLM check | When within radius, LLM decides if they'd talk based on personalities and context. | ✓ |
| Proximity + cooldown timer | Always chat when nearby with cooldown. No LLM call. Less realistic. | |
| You decide | Claude picks best balance. | |

**User's choice:** Proximity + LLM check
**Notes:** None

### Turn Count

| Option | Description | Selected |
|--------|-------------|----------|
| 2-4 turns with natural ending | LLM decides when to end, capped at ~4 turns. Each turn = 1 LLM call per agent. | ✓ |
| Fixed 2 turns | Always exactly 2 exchanges. Predictable cost. | |
| LLM decides, cap at 6 | More natural but up to 12 LLM calls per conversation. | |

**User's choice:** 2-4 turns with natural ending
**Notes:** None

### Schedule Revision After Chat

| Option | Description | Selected |
|--------|-------------|----------|
| LLM revises remaining schedule | Each agent gets LLM call to revise remaining plan based on conversation. | ✓ |
| Only revise if about an event | Skip revision for casual chat. Fewer LLM calls. | |
| You decide | Claude picks for most emergent behavior. | |

**User's choice:** LLM revises remaining schedule
**Notes:** None

---

## Claude's Discretion

- Embedding model choice for ChromaDB
- Exact perception radius value
- Conversation initiation cooldown
- Prompt templates for each cognition call type
- Decision LLM call structure (AGT-04)

## Deferred Ideas

- Reflection system (AGT-09) -- deferred to v2
- Relationship models (AGT-10) -- deferred to v2
