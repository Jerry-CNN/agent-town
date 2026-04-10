---
phase: 03
slug: agent-cognition
status: verified
threats_open: 0
asvs_level: 1
created: 2026-04-10
---

# Phase 03 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| LLM response -> Pydantic model | All LLM outputs validated through instructor + Pydantic v2 | Structured JSON (schedules, actions, importance scores, conversation turns) |
| ChromaDB query -> agent memory | Memory retrieval enforces agent_id isolation | Embedding vectors + metadata (non-sensitive, fictional) |
| Tile grid -> perception result | Perception reads server-side tile data only | Agent positions, events, location context |
| Conversation text -> memory store | Free-text dialogue stored as summaries | Fictional agent dialogue (no PII, no code execution) |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-03-01 | Tampering | ImportanceScore LLM response | mitigate | Pydantic Field(ge=1, le=10) enforces range; instructor retries on validation failure; hardcoded fallback=5 on exhausted retries | closed |
| T-03-02 | Information Disclosure | Memory retrieval | mitigate | agent_id filter enforced on every ChromaDB query in retrieve_memories function signature — impossible to call without it | closed |
| T-03-03 | Denial of Service | Importance scoring LLM calls | mitigate | Skip LLM call for idle events (hardcode importance=1); max_retries=3; failsafe return 5 | closed |
| T-03-04 | Elevation of Privilege | ChromaDB collection naming | accept | Collection names use f"sim_{simulation_id}" — simulation_id is server-generated, not user-supplied in v1 | closed |
| T-03-05 | Tampering | DailySchedule LLM response | mitigate | Pydantic Field(ge=4, le=11) on wake_hour; Field(min_length=3) on activities; instructor retries | closed |
| T-03-06 | Tampering | SubTask time ranges | mitigate | Pydantic Field(ge=0, lt=1440) on start_minute; Field(ge=5, le=60) on duration_minutes | closed |
| T-03-07 | Denial of Service | Schedule generation LLM calls | accept | Only 2 LLM calls per schedule generation; max_retries=3 via complete_structured; bounded cost | closed |
| T-03-08 | Information Disclosure | Perception radius | accept | Perception reads server-side tile data only; no user-supplied input crosses this boundary | closed |
| T-03-09 | Denial of Service | Conversation loop | mitigate | Hard cap MAX_TURNS=4 via for range(MAX_TURNS) — never while True; cooldown prevents re-initiation within 60 seconds | closed |
| T-03-10 | Tampering | ConversationTurn.text | accept | Free-text dialogue is expected; content stored as memory summary, not executed. No code injection vector. | closed |
| T-03-11 | Tampering | ScheduleRevision.revised_entries | mitigate | Each revised ScheduleEntry validated by Pydantic Field constraints (start_minute 0-1439, duration 15-120 min) | closed |
| T-03-12 | Denial of Service | Memory storage after conversation | mitigate | Limited to 2 memories per conversation (one per agent); importance scoring has failsafe return 5 | closed |
| T-03-13 | Tampering | AgentAction.destination | accept | Destination string resolved via Maze.resolve_destination() which returns None for unknown sectors; caller handles None | closed |
| T-03-14 | Information Disclosure | Memory retrieval in decide_action | mitigate | retrieve_memories enforces agent_id filter; agents cannot access other agents' memories | closed |

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-07 | T-03-04 | Collection names are server-generated; no user input reaches ChromaDB naming in v1 | GSD workflow | 2026-04-10 |
| AR-08 | T-03-07 | Schedule generation bounded at 2 LLM calls with 3 retries each — trivial cost | GSD workflow | 2026-04-10 |
| AR-09 | T-03-08 | Perception is pure server-side tile-grid computation; no external input | GSD workflow | 2026-04-10 |
| AR-10 | T-03-10 | Conversation text is fictional agent dialogue stored as summaries; never executed as code | GSD workflow | 2026-04-10 |
| AR-11 | T-03-13 | AgentAction destinations validated through resolve_destination(); unknown sectors return None | GSD workflow | 2026-04-10 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-10 | 14 | 14 | 0 | GSD secure-phase |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-10
