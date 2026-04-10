---
phase: 03-agent-cognition
plan: 03
subsystem: cognition
tags: [action-decision, conversation, cooldown, schedule-revision, tdd, pydantic, llm, async]
dependency_graph:
  requires: [03-01-memory-stream, 03-02-perception-planning]
  provides: [action-decision, conversation-system, schedule-revision]
  affects: [phase-04-simulation-loop, phase-06-event-injection]
tech_stack:
  added: []
  patterns: [tdd-red-green, response-model-aware-mocking, frozenset-symmetric-keys, bounded-loop-not-while-true]
key_files:
  created:
    - backend/agents/cognition/decide.py
    - backend/agents/cognition/converse.py
    - backend/prompts/action_decide.py
    - backend/prompts/conversation_start.py
    - backend/prompts/conversation_turn.py
    - backend/prompts/schedule_revise.py
  modified:
    - tests/test_cognition.py
decisions:
  - "frozenset pair key for conversation cooldown: _pair_key('alice','bob') == _pair_key('bob','alice') -- symmetric, order-independent"
  - "range(MAX_TURNS) hard cap instead of while True -- T-03-09 DoS prevention is a code-level constraint not just a comment"
  - "response_model-aware mocking in tests: side_effect checks kwargs['response_model'] to return ConversationTurn vs ScheduleRevision"
  - "_extract_known_locations flattens spatial.tree second-level keys (sectors) -- world name excluded as it is not a navigable destination"
  - "summary_text capped at 300 chars for memory storage -- prevents bloated ChromaDB documents from very long conversations"
metrics:
  duration_seconds: 352
  completed_date: "2026-04-10"
  tasks_completed: 2
  tasks_total: 2
  files_created: 6
  files_modified: 1
  tests_added: 17
  tests_total_after: 139
---

# Phase 03 Plan 03: Action Decision and Conversation System Summary

**One-liner:** LLM-powered action decisions from perception+memory context, bounded multi-turn conversations (MAX_TURNS=4) with 60s cooldown, and post-conversation schedule revision stored as agent memories.

## What Was Built

### Action Decision Module (`backend/agents/cognition/decide.py`)

Implements AGT-04: agents make structured LLM decisions about their next destination and activity.

`decide_action()` follows a three-step pipeline:
1. Extracts known sector names from `agent_spatial.tree` via `_extract_known_locations()` — flattens second-level dict keys (e.g., `{"agent-town": {"cafe": {}, "park": {}}}` → `["cafe", "park"]`). The LLM must choose a destination from this list.
2. Retrieves top-5 relevant memories via `retrieve_memories(top_k=5)` using the agent's current location as query context (D-05, T-03-14 — agent isolation enforced by Plan 01).
3. Calls `complete_structured(response_model=AgentAction)` with the full context prompt.

T-03-13 is accepted: destination strings are validated by `Maze.resolve_destination()` in Phase 4 (returns None for unknown sectors).

### Action Decision Prompt (`backend/prompts/action_decide.py`)

`action_decide_prompt()` builds a two-message list with:
- System: "You are deciding what {agent_name} should do next."
- User: agent persona (name, traits, lifestyle), current state (activity, location), known locations list (labeled "MUST choose destination from this list"), perception context (nearby agents with activities, nearby events), retrieved memories, remaining schedule.

### Multi-Turn Conversation System (`backend/agents/cognition/converse.py`)

Implements AGT-07 (conversations) and AGT-08 (schedule revision — the gossip propagation mechanism for Phase 6).

**Key constants:**
- `MAX_TURNS = 4` — hard cap (T-03-09 DoS mitigation)
- `COOLDOWN_SECONDS = 60` — prevents same-pair conversation spam
- `_conversation_cooldowns: dict[frozenset, float]` — symmetric pair tracking

**`attempt_conversation()`** (D-11 — proximity + LLM check):
1. Cooldown gate: `check_cooldown(agent_name, other_name)` returns False immediately if pair conversed within 60s. No LLM call made.
2. Retrieves top-3 memories about the other agent for context.
3. LLM call with `ConversationDecision` response model; returns `result.should_talk`.

**`run_conversation()`** (D-12, D-13):
- Turn loop: `for turn in range(MAX_TURNS)` — NEVER `while True`. Each round: A speaks → check end; B speaks → check end. Minimum 2 turns (end_conversation only respected after `turn >= 1`).
- After loop: records cooldown, builds 300-char-capped summary from turn text, scores importance via `score_importance()` (failsafe=5 on LLM failure, T-03-12), stores one memory per agent via `add_memory()`.
- Schedule revision: calls `complete_structured(ScheduleRevision)` for each agent with the conversation summary as context. This is the mechanism that makes gossip propagate in Phase 6 (AGT-08).

Returns: `{"turns": [...], "revised_schedule_a": [...], "revised_schedule_b": [...], "summary": str}`

### Prompt Templates

| File | Purpose |
|------|---------|
| `conversation_start.py` | Should {agent_name} talk to {other_name}? Both names, traits, activities, memories included. |
| `conversation_turn.py` | In-character turn response. Provides turn number and max_turns context so LLM can judge natural endings. |
| `schedule_revise.py` | Should {agent_name} revise remaining schedule after conversation? Includes full summary and remaining entries. |

### Test Suite (`tests/test_cognition.py`)

17 new tests added (37 total cognition tests):

**Action decision (6 tests):**
- prompt includes agent name
- prompt includes known locations
- prompt includes perception context (nearby agents)
- prompt includes retrieved memories
- decide_action returns AgentAction (mocked LLM + retrieve_memories)
- decide_action calls retrieve_memories with correct simulation_id and agent_name

**Conversation system (11 tests):**
- check_cooldown returns True initially
- check_cooldown returns False after _record_conversation
- _pair_key is symmetric (alice-bob == bob-alice)
- conversation_start_prompt includes both agent names
- schedule_revise_prompt includes conversation summary
- attempt_conversation returns False during cooldown
- attempt_conversation calls LLM when cooldown allows, returns should_talk
- run_conversation produces at least 2 turns
- run_conversation caps at MAX_TURNS * 2 utterances
- run_conversation calls add_memory for both agents
- Both Alice and Bob have memories stored (agent name verified in call args)

## Test Results

```
uv run pytest tests/test_cognition.py -x -q  →  37 passed
uv run pytest tests/test_memory.py -x -q     →  16 passed
uv run pytest -x -q                          →  139 passed (no regressions)
```

## Commits

| Hash | Message |
|------|---------|
| `e0434bc` | test(03-03): add failing tests for action decision and conversation system (TDD RED) |
| `1ea177b` | feat(03-03): LLM-powered action decision module with memory and perception context |
| `cc14a58` | feat(03-03): multi-turn conversation system with cooldown and schedule revision |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test side_effect returned wrong type for schedule revision calls**
- **Found during:** Task 2 GREEN phase
- **Issue:** Tests mocked `complete_structured` with `return_value=ConversationTurn(...)` for the entire test, but `run_conversation` also calls `complete_structured(response_model=ScheduleRevision)` for post-conversation schedule revision. The mock returned a `ConversationTurn` when a `ScheduleRevision` was expected, causing `AttributeError: 'ConversationTurn' object has no attribute 'revised_entries'`.
- **Fix:** Changed mock `return_value` to `side_effect` functions that check `kwargs.get("response_model")` and return the appropriate type (`ScheduleRevision` vs `ConversationTurn`).
- **Files modified:** `tests/test_cognition.py`
- **Commit:** `cc14a58`

## Known Stubs

None. All functionality is fully implemented and tested.

## Threat Flags

No new security surface beyond what was declared in the plan's threat model. All STRIDE mitigations implemented:
- T-03-09: `MAX_TURNS = 4` with `for turn in range(MAX_TURNS)` — confirmed bounded loop, not `while True`
- T-03-10: Conversation text stored as extracted summary (300-char cap), not verbatim turns
- T-03-11: `ScheduleRevision` uses Pydantic-validated `ScheduleEntry` (Field constraints from Plan 01 schemas)
- T-03-12: Exactly 2 `add_memory` calls per conversation (one per agent); `score_importance` returns 5 on failure
- T-03-13: `AgentAction.destination` resolved by `Maze.resolve_destination()` in Phase 4 (None on unknown)
- T-03-14: `retrieve_memories` enforces `agent_id` filter (Plan 01 guarantee), verified by test

## Self-Check: PASSED

| Item | Status |
|------|--------|
| backend/agents/cognition/decide.py | FOUND |
| backend/agents/cognition/converse.py | FOUND |
| backend/prompts/action_decide.py | FOUND |
| backend/prompts/conversation_start.py | FOUND |
| backend/prompts/conversation_turn.py | FOUND |
| backend/prompts/schedule_revise.py | FOUND |
| 03-03-SUMMARY.md | FOUND |
| Commit e0434bc (test RED) | FOUND |
| Commit 1ea177b (feat decide) | FOUND |
| Commit cc14a58 (feat converse) | FOUND |
| 37 cognition tests pass | PASS |
| 139 total tests pass | PASS |
| MAX_TURNS = 4 in converse.py | PASS |
| range(MAX_TURNS) loop (not while True) | PASS |
| COOLDOWN_SECONDS = 60 in converse.py | PASS |
| add_memory called for both agents | PASS |
| ScheduleRevision called after conversation | PASS |
