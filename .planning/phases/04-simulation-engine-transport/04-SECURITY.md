---
phase: 04
slug: simulation-engine-transport
status: verified
threats_open: 0
asvs_level: 1
created: 2026-04-10
---

# Phase 04 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| WebSocket message -> WSMessage model | Client-sent JSON validated through Pydantic model_validate_json() | Pause/resume commands, ping/pong |
| SimulationEngine -> WebSocket broadcast | Server pushes agent state to all connected clients | Agent positions, activities, conversations (non-sensitive) |
| Agent cognition -> SimulationEngine | LLM responses flow through engine tick loop | Structured Pydantic models (AgentAction, DailySchedule, etc.) |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-04-01 | Denial of Service | SimulationEngine._tick_loop | mitigate | Per-agent exception isolation in _agent_step_safe(); asyncio.wait_for timeout (2x TICK_INTERVAL) prevents indefinite hangs | closed |
| T-04-02 | Denial of Service | SimulationEngine.initialize | mitigate | generate_daily_schedule has DailySchedule fallback; TaskGroup wraps each init; single agent failure logged, not fatal | closed |
| T-04-03 | Information Disclosure | AgentState.config.scratch | accept | Single-user v1 has no multi-tenant isolation concern; personality data is fictional | closed |
| T-04-04 | Tampering | ws.py WebSocket message parsing | mitigate | WSMessage.model_validate_json() with try/except; invalid messages return type="error" | closed |
| T-04-05 | Denial of Service | ws.py pause/resume flood | accept | asyncio.Event set/clear is idempotent; rapid toggling has no meaningful cost | closed |
| T-04-06 | Denial of Service | ConnectionManager.broadcast dead connections | mitigate | Dead connections caught per-connection in try/except; removed after broadcast loop | closed |
| T-04-07 | Denial of Service | SimulationEngine via CancelledError | mitigate | sim_task.cancel() in lifespan shutdown; CancelledError re-raised for clean termination | closed |
| T-04-08 | Information Disclosure | Snapshot exposes agent state | accept | Single-user v1; all agent state is public to the user. No PII. | closed |

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-12 | T-04-03 | Single-user architecture; no multi-tenant isolation needed in v1 | GSD workflow | 2026-04-10 |
| AR-13 | T-04-05 | Event.set/clear is O(1) idempotent; no amplification vector | GSD workflow | 2026-04-10 |
| AR-14 | T-04-08 | All agent data is fictional simulation content; user is the sole observer | GSD workflow | 2026-04-10 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-10 | 8 | 8 | 0 | GSD secure-phase |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-10
