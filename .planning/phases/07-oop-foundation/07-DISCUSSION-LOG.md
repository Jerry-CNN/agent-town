# Phase 7: OOP Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-10
**Phase:** 07-oop-foundation
**Areas discussed:** Agent class design, Building data source, Event lifecycle rules, Schema split strategy

---

## Agent Class Design

### Immutability

| Option | Description | Selected |
|--------|-------------|----------|
| Identity immutable | name, traits, occupation frozen at load. Only runtime state changes. | |
| All mutable | Traits could evolve over time. More complex but keeps door open. | ✓ |
| You decide | Claude picks the approach | |

**User's choice:** All mutable
**Notes:** Keeps the door open for future trait evolution even though v1.1 won't mutate identity fields.

### Memory Access

| Option | Description | Selected |
|--------|-------------|----------|
| Module-level calls | Agent calls store.add_memory(self.name, ...). Memory store stays singleton. | ✓ |
| Injected interface | Agent receives MemoryInterface in __init__. Cleaner OOP but adds indirection. | |
| You decide | Claude picks based on pitfall analysis | |

**User's choice:** Module-level calls
**Notes:** Safest approach per Codex review — avoids ChromaDB singleton duplication risk.

---

## Building Data Source

| Option | Description | Selected |
|--------|-------------|----------|
| Separate buildings.json | New file in backend/data/map/ mapping sector names to properties | ✓ |
| Inline in town.json | Add buildings section to existing town.json | |
| Hardcoded in Python | Define as Python dict in config module | |
| You decide | Claude picks | |

**User's choice:** You decide (+ ask Codex)
**Notes:** Both Claude and Codex (GPT-5.4) agreed on separate buildings.json. Codex reasoning: stable domain entities use standalone JSON (like agent configs), while town.json is generated/derived data — mixing would blur source vs derived. Option 3 rejected because config.py is for runtime settings, not canonical content data.

---

## Event Lifecycle Rules

### Expiry

| Option | Description | Selected |
|--------|-------------|----------|
| By tick count | Expires after N ticks. Simple, deterministic. | ✓ |
| By sim time | Expires after N minutes of simulation time. Needs sim-time clock. | |
| Never expire | Events stay active until simulation ends. | |
| You decide | Claude picks based on reference implementation | |

**User's choice:** You decide
**Notes:** Claude chose tick-based expiry — simplest, deterministic, no sim-time clock needed.

### Broadcast Propagation

| Option | Description | Selected |
|--------|-------------|----------|
| Track all hearers | Broadcast records which agents perceived it and when | |
| Skip for broadcasts | Only whisper events track propagation | ✓ |
| You decide | Claude picks the simpler approach | |

**User's choice:** Skip for broadcasts
**Notes:** Propagation tracking only matters for gossip (whisper). Broadcasts reach everyone instantly.

---

## Schema Split Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| By domain | agent.py, cognition.py, events.py, ws.py | ✓ |
| Keep flat | Keep one schemas.py — 182 lines isn't that big | |
| You decide | Claude picks | |

**User's choice:** By domain
**Notes:** Domain split with __init__.py re-exports for backward compatibility.

---

## Claude's Discretion

- Event expiry tick count
- Internal Agent field naming conventions
- Exact method signatures for Agent cognition wrappers

## Deferred Ideas

None — discussion stayed within phase scope
