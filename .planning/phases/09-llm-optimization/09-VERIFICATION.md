---
phase: 09-llm-optimization
verified: 2026-04-11T18:00:00Z
status: human_needed
score: 9/11 must-haves verified
overrides_applied: 0
gaps: []
human_verification:
  - test: "Open browser at http://localhost:5173, clear localStorage (localStorage.removeItem('agenttown_provider')), refresh — verify setup modal shows OpenRouter pre-selected AND model field shows 'openrouter/openai/gpt-4o-mini' (current default, not kimi-k2.5)"
    expected: "Modal opens with OpenRouter radio selected. Model field pre-filled. Note: backend/config.py and ProviderSetup.tsx both use 'openrouter/openai/gpt-4o-mini' not 'openrouter/moonshotai/kimi-k2.5' — verify whether this is intentional per user preference"
    why_human: "Visual check needed. Also flags a deviation from plan spec for human decision: plan required kimi-k2.5 but implementation uses gpt-4o-mini. This may be correct per user preference or may need correction."
  - test: "After setup, click 'Settings' button in header. Verify modal reopens with current config pre-populated. Click Cancel. Verify modal closes and simulation continues."
    expected: "Settings button visible in header. Modal reopens with correct pre-populated values. Cancel dismisses without disrupting simulation."
    why_human: "Visual and interactive behavior — cannot verify in a headless environment."
  - test: "Start simulation with any provider. Watch bottom bar for 'Tick: Xs' label. Confirm it shows a value and updates during simulation run."
    expected: "Tick interval label visible in bottom bar. Initial value 10. Updates after each tick based on actual LLM latency."
    why_human: "Visual/real-time behavior — requires running simulation."
  - test: "Let simulation run for 2-3 minutes. Observe activity feed for 'conversation ended (repetition)' log entries. Check backend console (LOG_LEVEL=DEBUG) for 'LLM semaphore acquired' debug messages."
    expected: "Agents act roughly every 10 seconds. At least one conversation terminates due to repetition over a sustained run. Semaphore acquire/release visible in debug logs."
    why_human: "Emergent/probabilistic behavior — requires live observation over time."
---

# Phase 9: LLM Optimization Verification Report

**Phase Goal:** Agent destination decisions use 2-level sector-arena resolution with per-sector gating; the tick interval adapts to LLM latency (minimum 10s); conversations self-terminate on detected repetition; concurrent LLM calls are bounded by a semaphore; OpenRouter with Kimi K2.5 is the default provider.
**Verified:** 2026-04-11T18:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | All LLM calls bounded to at most 8 concurrent in-flight requests | VERIFIED | `_llm_semaphore = asyncio.Semaphore(8)` in gateway.py:37; wraps entire `complete_structured()` body at line 110; 7/7 semaphore tests pass |
| 2 | Tick interval adapts to LLM latency, min 10s | VERIFIED | `get_adaptive_tick_interval(min_interval=10.0)` in gateway.py:43; `tick_interval` property on engine at line 111; cold start returns 10.0; slow provider (15s avg) returns 20.0 (clamped) |
| 3 | AGENT_STEP_TIMEOUT dynamically tracks max(tick_interval * 2, 120) | VERIFIED | engine.py:264 `timeout = max(self.tick_interval * 2, 120)` — 120s cold-start floor present |
| 4 | Per-sector gating skips decide LLM call when sector/perceptions/schedule unchanged | VERIFIED | decide.py:143 `if last_sector is not None and not new_perceptions and not schedule_changed: return None`; engine passes all three gating params at lines 416-420; 4/4 gating tests pass |
| 5 | 2-level cascade: multi-arena sectors make 2 LLM calls; single-arena make 1 | VERIFIED | `_sector_has_arenas()` in decide.py:60; arena call at lines 202-227; 2 LLM-count tests pass |
| 6 | Arena LLM result validated — unknown names fall back to arenas[0] | VERIFIED | decide.py:219 `if arena_result.arena in arenas:` with fallback; test_arena_validation tests pass |
| 7 | Conversations detect repetition (ratio > 0.6) and terminate early | VERIFIED | `_is_repetition()` using `difflib.SequenceMatcher` in converse.py:107-126; `MAX_TURNS = 6`; terminated_reason in return dict; 8/8 repetition tests pass |
| 8 | Concurrent conversations between same agent pair within one tick are prevented | VERIFIED | `self._active_conversations: set[frozenset[str]]` in engine.py:108; pair_key claim at line 351; cleared at start of tick at line 229 |
| 9 | tick_interval_update WS type registered — simulation does not crash on broadcast | VERIFIED | ws.py:41 `"tick_interval_update"` in WSMessage Literal; frontend types/index.ts:44 union includes it; engine broadcasts it after each tick |
| 10 | OpenRouter is pre-selected as default provider, Kimi K2.5 model pre-filled | PARTIAL | `AppState.provider = "openrouter"` default VERIFIED; ProviderSetup.tsx defaults to openrouter VERIFIED. BUT: `OPENROUTER_DEFAULT_MODEL = "openrouter/openai/gpt-4o-mini"` in config.py and ProviderSetup.tsx model default is `"openrouter/openai/gpt-4o-mini"` — plan required `"openrouter/moonshotai/kimi-k2.5"`. Deviation from plan spec. |
| 11 | Settings button in header reopens provider modal | VERIFIED | Layout.tsx:46 Settings button with `onOpenSettings`; App.tsx:47 wires `setShowSettings(true)`; modal renders when `showSettings === true` |

**Score:** 9/11 truths verified (10/11 counting the partial OpenRouter default; 1 partial on Kimi K2.5 model)

### Deferred Items

No items deferred to later phases.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/gateway.py` | asyncio.Semaphore(8), latency tracking, get_adaptive_tick_interval() | VERIFIED | All three present; `_llm_semaphore`, `_latency_window`, function all at module level |
| `backend/simulation/engine.py` | tick_interval property, adaptive timeout, gating wiring, race prevention | VERIFIED | TICK_INTERVAL constant assignment gone (only in comments); property at line 111; `_active_conversations` set; all gating params passed |
| `backend/agents/agent.py` | last_sector and had_new_perceptions fields | VERIFIED | Both fields at lines 42-43 with correct defaults |
| `backend/agents/cognition/decide.py` | _sector_has_arenas, gating params, returns AgentAction|None | VERIFIED | All present; gating at line 143; arena cascade at lines 202-227 |
| `backend/agents/cognition/converse.py` | _is_repetition, MAX_TURNS=6, terminated_reason | VERIFIED | difflib import present; MAX_TURNS=6; function at line 107; terminated_reason in return dict |
| `backend/prompts/arena_decide.py` | arena_decide_prompt function | VERIFIED | File exists with correct function signature |
| `backend/schemas/__init__.py` | ArenaAction exported | VERIFIED | Exported via schemas/agent.py, re-exported in __init__.py |
| `backend/schemas/ws.py` | tick_interval_update in Literal | VERIFIED | Line 41 |
| `backend/config.py` | provider="openrouter" default, OPENROUTER_DEFAULT_MODEL | PARTIAL | provider="openrouter" VERIFIED; OPENROUTER_DEFAULT_MODEL = "openrouter/openai/gpt-4o-mini" (not kimi-k2.5 as planned) |
| `frontend/src/components/ProviderSetup.tsx` | OpenRouter-first, model field, onClose/initialConfig props | PARTIAL | OpenRouter-first VERIFIED; onClose/initialConfig VERIFIED; model field exists but defaults to gpt-4o-mini not kimi-k2.5 |
| `frontend/src/components/Layout.tsx` | onOpenSettings prop, Settings button | VERIFIED | Both present |
| `frontend/src/components/BottomBar.tsx` | tickInterval display | VERIFIED | Reads from store, renders "Tick: {tickInterval}s" |
| `frontend/src/store/simulationStore.ts` | tickInterval: 10, setTickInterval | VERIFIED | Both present |
| `frontend/src/types/index.ts` | tick_interval_update in WSMessageType, tickInterval in SimulationStore | VERIFIED | Both present |
| `frontend/src/hooks/useWebSocket.ts` | tick_interval_update case, snapshot tick_interval extraction | VERIFIED | Both at lines 108-113 and 68-70 |
| `tests/test_gateway_semaphore.py` | 7 passing tests | VERIFIED | 7/7 pass |
| `tests/test_engine_adaptive.py` | 7 passing tests | VERIFIED | 7/7 pass |
| `tests/test_decide_cascade.py` | 11 passing tests | VERIFIED | 11/11 pass |
| `tests/test_converse_repetition.py` | 8 passing tests | VERIFIED | 8/8 pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/gateway.py` | `backend/simulation/engine.py` | `get_adaptive_tick_interval()` imported and used by `tick_interval` property | VERIFIED | engine.py:36 imports it; property at line 112 calls `get_adaptive_tick_interval(min_interval=10.0)` |
| `backend/agents/cognition/decide.py` | `backend/prompts/arena_decide.py` | `arena_decide_prompt` import | VERIFIED | decide.py:32 `from backend.prompts.arena_decide import arena_decide_prompt` |
| `backend/agents/cognition/converse.py` | `difflib` | `SequenceMatcher` for repetition detection | VERIFIED | converse.py:26 `import difflib`; used at line 126 |
| `frontend/src/components/Layout.tsx` | `frontend/src/App.tsx` | `onOpenSettings` callback triggers `setShowSettings(true)` | VERIFIED | App.tsx:47 `onOpenSettings={() => setShowSettings(true)}` |
| `frontend/src/hooks/useWebSocket.ts` | `frontend/src/store/simulationStore.ts` | `tick_interval_update` message updates `tickInterval` | VERIFIED | useWebSocket.ts:108-113 case handler calls `store.setTickInterval()` |
| `backend/simulation/engine.py` | `backend/agents/cognition/decide.py` | Passes `last_sector`, `new_perceptions`, `schedule_changed` | VERIFIED | engine.py:416-420 passes all three; handles `None` return at line 424 |
| `backend/schemas/ws.py` | `backend/simulation/engine.py` | `tick_interval_update` in Literal allows engine broadcast | VERIFIED | ws.py:41; engine broadcasts at lines 241-245 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `BottomBar.tsx` | `tickInterval` | `simulationStore.tickInterval` updated by `useWebSocket.ts` via `tick_interval_update` WS messages from engine | Yes — backend computes from real latency window | FLOWING |
| `engine.py` `tick_interval` | `get_adaptive_tick_interval()` | `gateway._latency_window` deque filled by real LLM call timings | Yes — real `time.perf_counter()` measurements | FLOWING |
| `decide.py` gating | `last_sector`, `new_perceptions`, `schedule_changed` | engine._agent_step computes and passes | Yes — computed from real agent state | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `get_adaptive_tick_interval()` returns 10.0 at cold start | `uv run python -c "from backend.gateway import get_adaptive_tick_interval; print(get_adaptive_tick_interval())"` | 10.0 | PASS |
| Adaptive tick clamps to 20s max with 15s avg latency | `uv run python -c "from backend import gateway; [gateway._latency_window.append(15.0) for _ in range(10)]; print(gateway.get_adaptive_tick_interval())"` | 20.0 | PASS |
| All 33 phase-specific tests pass | `uv run python -m pytest tests/test_gateway_semaphore.py tests/test_engine_adaptive.py tests/test_decide_cascade.py tests/test_converse_repetition.py -v` | 33 passed | PASS |
| Full backend suite (excluding known pre-existing failures) | `uv run python -m pytest tests/ -q --ignore=tests/test_health.py --ignore=tests/test_integration.py` | 278 passed, 1 pre-existing failure (test_movement_one_tile_per_tick — out of scope) | PASS |
| TypeScript compilation | `cd frontend && npx tsc --noEmit` | No errors | PASS |

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| LLM-01 | 09-02, 09-03 | Agent decisions use 3-level resolution with per-sector gating | SATISFIED | 2-level cascade (sector+arena) implemented; per-sector gating via decide.py returning None; engine wires all three gating params. Note: requirement says "3-level" but plan correctly implemented 2-level (sector+arena, skipping object level per D-07). |
| LLM-02 | 09-01, 09-03 | Tick interval reduced from 30s to 10s for more responsive agents | SATISFIED | Adaptive tick with min=10s; TICK_INTERVAL constant removed; engine uses `tick_interval` property; broadcast to frontend |
| LLM-03 | 09-02, 09-03 | Conversations detect repetition and terminate early instead of fixed turn count | SATISFIED | `_is_repetition()` via difflib; MAX_TURNS=6; terminated_reason in return; logged to activity feed via _emit_conversation |
| LLM-04 | 09-01, 09-03 | asyncio.Semaphore controls concurrent LLM calls | SATISFIED | `_llm_semaphore = asyncio.Semaphore(8)` wraps complete_structured(); concurrency test proves limiting behavior |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `backend/config.py` | 7 | `OPENROUTER_DEFAULT_MODEL = "openrouter/openai/gpt-4o-mini"` — plan specified kimi-k2.5 | Warning | Model default deviates from plan spec; affects new users' first simulation cost/quality |
| `frontend/src/components/ProviderSetup.tsx` | 20 | `"openrouter/openai/gpt-4o-mini"` model default — plan specified kimi-k2.5 | Warning | Same deviation as config.py; model field shows gpt-4o-mini not kimi-k2.5 on first open |
| `backend/gateway.py` | 111 | `logger.info("LLM call: ...")` instead of `logger.debug("LLM semaphore acquired ...")` | Info | Plan test 7 specified "LLM semaphore acquired" debug message; implementation uses "LLM call:" at INFO level. Tests were adapted to accept the actual messages. Functional equivalent — semaphore is still present and working. |
| `backend/simulation/engine.py` | 173, 204, 253 | Comments still reference `TICK_INTERVAL` (not as assignment — purely in docstrings) | Info | Not a code issue; comments reference old constant name. No runtime impact. |

### Human Verification Required

#### 1. Kimi K2.5 Default Model Confirmation

**Test:** Check current model default vs plan spec:
- `backend/config.py`: `OPENROUTER_DEFAULT_MODEL = "openrouter/openai/gpt-4o-mini"` (NOT kimi-k2.5)
- `frontend/src/components/ProviderSetup.tsx` line 20: model default `"openrouter/openai/gpt-4o-mini"` (NOT kimi-k2.5)

**Expected per plan:** Both should show `"openrouter/moonshotai/kimi-k2.5"` (the roadmap success criteria and 09-03-PLAN both specified kimi-k2.5 explicitly as D-01/D-02).

**Why human:** This is a product decision — the user memory note says "user wants OpenRouter as default" which is implemented correctly, but Kimi K2.5 as the specific model was specified in the plan AND the roadmap goal. The deviation could be intentional (user changed their mind after writing the plan) or a missed implementation detail. The developer needs to decide whether to update the defaults to kimi-k2.5 or accept gpt-4o-mini.

#### 2. Visual Provider Setup Flow

**Test:** Clear localStorage in browser console (`localStorage.removeItem("agenttown_provider")`), refresh page.
**Expected:** Provider setup modal opens with OpenRouter radio pre-selected. Model field visible and pre-populated. Ollama labeled "Ollama (Local -- advanced)".
**Why human:** Visual rendering and form state cannot be verified programmatically.

#### 3. Settings Button Functionality

**Test:** After completing provider setup, locate "Settings" button in header bar. Click it. Verify modal reopens with current config pre-filled. Click Cancel. Verify simulation state unchanged.
**Expected:** Settings button visible. Modal reopens with correct values. Cancel closes modal without disrupting simulation.
**Why human:** Interactive DOM behavior requires browser testing.

#### 4. Tick Interval Live Display

**Test:** Start simulation. Watch bottom bar for "Tick: Xs" label. Observe for 2-3 ticks.
**Expected:** Label starts at "Tick: 10s". May adapt upward based on LLM latency. Confirms WebSocket tick_interval_update messages are flowing and BottomBar is reactive.
**Why human:** Requires live running simulation with WebSocket connection.

#### 5. Repetition Detection Observability

**Test:** Run simulation for 3-5 minutes. Watch activity feed for "(repetition)" termination entries. Set `LOG_LEVEL=DEBUG` on backend to confirm "LLM semaphore" logging.
**Expected:** At least one conversation in an extended run terminates due to repetition. Debug logs show semaphore acquire/release behavior (logged as "LLM call:" and "LLM done:" at INFO level).
**Why human:** Probabilistic/emergent behavior over time; requires live observation.

---

## Gaps Summary

No blocking gaps identified. All 4 requirement IDs (LLM-01 through LLM-04) are substantively implemented with passing tests.

The one notable deviation — model default is `gpt-4o-mini` instead of the plan-specified `kimi-k2.5` — is flagged for human decision. It does not break any functionality; it only affects which model new users get by default. All structural wiring (OpenRouter as default provider, model field in setup modal, model persisted to Zustand/localStorage, sent to /api/config) is correctly implemented regardless of the specific default model value.

The 5 human verification items above cover visual/interactive/behavioral behaviors that require a running browser+backend environment to confirm.

---

*Verified: 2026-04-11T18:00:00Z*
*Verifier: Claude (gsd-verifier)*
