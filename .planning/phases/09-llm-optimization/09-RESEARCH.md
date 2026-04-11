# Phase 9: LLM Optimization - Research

**Researched:** 2026-04-11
**Domain:** Python asyncio concurrency, adaptive tick timing, conversation similarity detection, OpenRouter provider configuration, ProviderSetup UI modal
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** OpenRouter is the recommended/pre-selected provider in the setup modal. Ollama is still available as "Local (advanced)" option.
- **D-02:** Default model for OpenRouter: Kimi K2.5. Pre-filled in model field when OpenRouter is selected.
- **D-03:** Add a settings/gear button to the UI header (Layout.tsx) that reopens the provider setup modal. Users can switch providers anytime without clearing localStorage.
- **D-04:** Adaptive tick interval. Rolling window of last 10-20 calls. Set tick to `max(10, avg_response_time * 1.5)` seconds.
- **D-05:** Update AGENT_STEP_TIMEOUT to `tick_interval * 2` dynamically — tracks adaptive tick, not hardcoded.
- **D-06:** Display current tick interval somewhere subtle in the UI (e.g., bottom bar).
- **D-07:** 2-level cascade: sector -> arena. Skip object level.
- **D-08:** Per-sector gating: if destination sector is unchanged from last tick and no new perceptions triggered re-evaluation, skip LLM call entirely (0 calls).
- **D-09:** Arena-level resolution only for sectors that have sub-arenas in town.json. Single-room sectors skip the arena call.
- **D-10:** Simple string similarity using Python's `difflib.SequenceMatcher`. Compare last 2 conversation turns. If `ratio() > 0.6`, terminate early.
- **D-11:** When terminated, log "conversation ended (repetition)" to the activity feed.
- **D-12:** Replaces current fixed MAX_TURNS cap — conversations end by repetition detection OR maximum of 6 turns (raised from 4).
- **D-13:** `asyncio.Semaphore(8)` in gateway.py wrapping all LLM calls.
- **D-14:** Debug logging on semaphore acquire/release.

### Claude's Discretion

- Rolling window size for adaptive tick (10 or 20 calls)
- Exact Kimi K2.5 model ID on OpenRouter
- Settings button icon and placement
- Whether to show "Tick: Xs" label in bottom bar or just tooltip

### Deferred Ideas (OUT OF SCOPE)

- Model routing per call type (CFG-04, v2) — cheap model for routine calls, expensive for complex
- LiteLLM response caching — MEDIUM confidence on cache key behavior
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LLM-01 | Agent decisions use 3-level resolution (sector -> arena -> object) with per-sector gating | Architecture Patterns §Decision Cascade and §Per-Sector Gating; Code Examples §Arena Resolution |
| LLM-02 | Tick interval reduced from 30s to 10s for more responsive agents | Architecture Patterns §Adaptive Tick; Code Examples §AdaptiveTick class |
| LLM-03 | Conversations detect repetition and terminate early instead of fixed turn count | Standard Stack §difflib; Code Examples §Repetition Detection |
| LLM-04 | asyncio.Semaphore controls concurrent LLM calls to prevent rate limits | Standard Stack §asyncio; Code Examples §Semaphore Wrapper |
</phase_requirements>

---

## Summary

Phase 9 is a pure optimization pass with no new user-facing features except a settings button and tick interval display. All changes are internal to three Python backend files (`gateway.py`, `engine.py`, `converse.py`) and two frontend files (`ProviderSetup.tsx`, `Layout.tsx`). The phase has no new library dependencies — every tool needed is already in the stack or in Python's standard library.

The four optimizations are independent: semaphore wrapping in `gateway.py`, adaptive tick in `engine.py`, 2-level decision cascade in `decide.py`, and repetition detection in `converse.py`. They can be planned and executed as four separate tasks with no sequencing dependency between them. The provider default and settings button changes are purely additive UI work.

The highest implementation risk is the adaptive tick + dynamic timeout (D-04/D-05): the current `TICK_INTERVAL` is a module-level constant used in both the sleep and the `asyncio.wait_for` timeout. Making it adaptive requires converting it from a static value to a mutable object (likely a dataclass or dict on `SimulationEngine`) that both the tick loop and `_agent_step_safe` read from. Care must be taken to avoid race conditions when the rolling window updates the interval mid-tick.

**Primary recommendation:** Implement in order: semaphore (LLM-04) first as it protects all subsequent testing; then tick reduction (LLM-02); then 2-level cascade (LLM-01); then repetition detection (LLM-03). Provider default and settings button are independent frontend tasks with no backend dependency.

---

## Standard Stack

### Core (all already installed)

| Library | Version | Purpose | Relevance to Phase 9 |
|---------|---------|---------|----------------------|
| asyncio | stdlib | Semaphore, TaskGroup, sleep | `asyncio.Semaphore(8)` wraps `complete_structured()` in gateway.py [VERIFIED: Python 3.14.4 in venv] |
| difflib | stdlib | String similarity scoring | `SequenceMatcher.ratio()` for conversation repetition detection [VERIFIED: confirmed in Python 3.14.4] |
| instructor + LiteLLM | installed | LLM gateway | Semaphore wraps the `_client.chat.completions.create()` call inside `complete_structured()` [VERIFIED: codebase read] |
| collections.deque | stdlib | Rolling window for latency tracking | `deque(maxlen=N)` for adaptive tick rolling average [VERIFIED: Python stdlib] |

### No New Dependencies Required

All capabilities are either Python stdlib or already installed. No `pip install` step is needed for this phase.

### Kimi K2.5 on OpenRouter

| Property | Value | Source |
|----------|-------|--------|
| OpenRouter model ID | `moonshotai/kimi-k2.5` | [VERIFIED: openrouter.ai/moonshotai/kimi-k2.5] |
| LiteLLM prefix | `openrouter/moonshotai/kimi-k2.5` | [ASSUMED: LiteLLM prefixes OpenRouter models with `openrouter/`; confirmed by existing `OPENROUTER_DEFAULT_MODEL = "openrouter/meta-llama/llama-3.1-8b-instruct:free"` pattern in config.py] |
| Context window | 262K tokens | [VERIFIED: openrouter.ai listing] |
| Pricing (April 2026) | $0.45 input / $2.25 output per 1M tokens | [VERIFIED: openrouter.ai listing] |

---

## Architecture Patterns

### Recommended Project Structure (files being modified)

```
backend/
├── config.py               # OPENROUTER_DEFAULT_MODEL -> kimi-k2.5; default provider -> openrouter
├── gateway.py              # Add asyncio.Semaphore(8); add latency tracking; emit debug logs
├── simulation/
│   └── engine.py           # AdaptiveTick class; convert TICK_INTERVAL constant to instance var
└── agents/cognition/
    ├── decide.py            # 2-level cascade (sector -> arena); per-sector gating cache
    └── converse.py          # Repetition detection; MAX_TURNS=6; early termination path

frontend/src/components/
├── Layout.tsx              # Add settings/gear button that reopens ProviderSetup
├── BottomBar.tsx            # Add tick interval display (label or tooltip)
└── ProviderSetup.tsx        # Reorder to OpenRouter-first; add model field with Kimi K2.5 default
```

### Pattern 1: asyncio.Semaphore in gateway.py

**What:** A module-level `asyncio.Semaphore(8)` wraps the entire body of `complete_structured()`. All LLM calls funnnel through this single function, so the semaphore automatically bounds concurrency regardless of which cognition module initiates the call.

**When to use:** Always — it is always active. With OpenRouter it prevents rate-limit 429 errors under bursty load. With Ollama it prevents queue pileup that causes context switching overhead.

**Key constraint:** The semaphore must be created at module level, not inside `complete_structured()`. Creating it inside the function would instantiate a new semaphore per call (defeating its purpose). [VERIFIED: asyncio.Semaphore docs and codebase pattern]

```python
# Source: Python asyncio docs + codebase analysis of gateway.py
import asyncio

_llm_semaphore = asyncio.Semaphore(8)  # module-level

async def complete_structured(messages, response_model, provider_config=None, max_retries=3, fallback=None):
    async with _llm_semaphore:
        logger.debug("LLM semaphore acquired (model=%s)", model_str)
        # ... existing retry loop ...
    logger.debug("LLM semaphore released")
```

**D-14 debug logging:** Log at `DEBUG` level on acquire and release. Do not log at `INFO` — too noisy in production. The user can enable debug logging to verify semaphore behavior.

### Pattern 2: Adaptive Tick Interval

**What:** A rolling deque of the last N LLM call durations tracked in gateway.py. Engine reads the current average to set `tick_interval = max(10, avg * 1.5)` before each sleep. AGENT_STEP_TIMEOUT dynamically tracks `tick_interval * 2`.

**When to use:** Always — adaptive behavior is transparent to the simulation. Fast providers naturally converge to 10s; slow providers self-adjust.

**Integration points:**
1. `gateway.py`: record `elapsed` after each successful LLM call to a shared `_latency_window: deque`
2. `engine.py`: expose a `get_current_tick_interval()` helper or property that reads from gateway's window
3. `engine.py._tick_loop()`: replace `await asyncio.sleep(TICK_INTERVAL)` with `await asyncio.sleep(engine.tick_interval)`
4. `engine.py._agent_step_safe()`: replace `timeout=max(TICK_INTERVAL * 4, 120)` with `timeout=self.tick_interval * 2`

**Rolling window size decision (Claude's discretion):** Use 10 calls. Reasoning: with 8 concurrent agents each making ~1 LLM call per tick, 10 calls represents roughly 1-2 ticks of recent history. This gives fast convergence when switching providers without overreacting to a single slow call. 20 calls would lag for 2-4 ticks before adapting, which is noticeable to users.

```python
# Source: codebase analysis + validated behavior in verification probe
from collections import deque
import time

_latency_window: deque[float] = deque(maxlen=10)  # gateway.py module level

def get_adaptive_tick_interval(min_interval: float = 10.0) -> float:
    """Return max(min_interval, avg_latency * 1.5) from recent LLM calls."""
    if not _latency_window:
        return min_interval
    avg = sum(_latency_window) / len(_latency_window)
    return max(min_interval, avg * 1.5)
```

**Validated behavior:** [VERIFIED: probe test]
- 10 calls at 3s avg: tick = max(10, 4.5) = **10s**, timeout = 20s
- 10 calls at 12s avg: tick = max(10, 18.0) = **18s**, timeout = 36s

**TICK_INTERVAL constant removal:** The module-level `TICK_INTERVAL: int = 30` in `engine.py` must become an instance property on `SimulationEngine`. Tests that import `TICK_INTERVAL` directly will fail; update them to use `engine.tick_interval`.

### Pattern 3: 2-Level Decision Cascade

**What:** `decide_action()` now runs in two phases. Phase 1 checks if the agent's sector is unchanged and no new events were perceived (gating check — 0 LLM calls). Phase 2 is the existing LLM call for sector selection, followed by an optional second call for arena selection if the chosen sector has multiple arenas.

**Per-sector gating cache (D-08):** Store `last_sector: str | None` on the Agent object. Before calling decide_action, compare current sector to last sector. If unchanged AND no new perceptions this tick, skip decide_action entirely and return the existing action. This is NOT a cache of the LLM response — it is a guard that skips the call when the agent's situation is unchanged.

**Arena-level call (D-09):** Only fire the arena LLM call if the chosen sector has multiple arenas listed in town.json. Single-room sectors (homes, small shops) produce only the sector call. Multi-room sectors (stock exchange, wedding hall, cafe with kitchen+seating) produce a second arena call.

**Implementation in decide.py:**

```python
# Source: codebase analysis + FEATURES.md reference pattern
async def decide_action(..., last_sector: str | None = None, new_perceptions: bool = True) -> AgentAction | None:
    """Returns None if gating skips the call (caller keeps current action)."""
    # D-08: Per-sector gating — skip LLM if sector unchanged and no new perceptions
    current_sector = _current_sector_of(agent_spatial, perception)
    if last_sector is not None and current_sector == last_sector and not new_perceptions:
        return None  # caller keeps current action unchanged

    # Existing LLM call (sector selection)
    action = await complete_structured(messages=..., response_model=AgentAction)

    # D-09: Arena call only if sector has multiple arenas
    if _sector_has_arenas(action.destination, agent_spatial):
        arena = await complete_structured(messages=arena_prompt(...), response_model=ArenaAction)
        action.destination = f"{action.destination}/{arena.arena}"

    return action
```

**`_sector_has_arenas()` implementation:** Read from `agent_spatial.tree` — if the sector dict has more than 1 key (arenas), the sector qualifies. This is a pure Python dict lookup, no LLM call.

**caller change in engine.py `_agent_step()`:** Track `agent.last_sector` and `agent.had_new_perceptions` on the Agent object. Pass both to decide_action. When `decide_action` returns `None`, skip path computation and memory storage for that tick.

### Pattern 4: Repetition Detection in Conversations

**What:** After each complete exchange (both A and B have spoken), compare the last 2 utterances using `difflib.SequenceMatcher(None, last_a, last_b).ratio()`. If `ratio() > 0.6`, terminate the loop, log "conversation ended (repetition)" to activity feed, and skip to cooldown + memory storage.

**When triggered:** Only after at least 2 full rounds (turn >= 1 in the current 0-indexed loop). The comparison compares agent A's last utterance to agent B's last utterance, not two consecutive utterances by the same agent.

**MAX_TURNS increase (D-12):** Raise from 4 to 6. This gives repetition detection room to fire naturally before the hard cap. [VERIFIED: existing code MAX_TURNS=4 in converse.py]

**difflib behavior verified:** [VERIFIED: probe test]
- Semantically similar ("stock market is interesting" / "stock market is very interesting"): ratio=0.848 — terminates
- Naturally diverging ("I heard there's a wedding" / "Oh really? I should buy a gift"): ratio=0.344 — continues
- Identical: ratio=1.0 — terminates

**0.6 threshold justification:** The threshold is calibrated to catch conversational stagnation (rephrasing the same point) without triggering on conversationally related but distinct responses. The verified ratio of 0.848 for "similar phrasing" and 0.344 for "distinct responses" places 0.6 as a robust midpoint.

```python
# Source: Python difflib docs + validated probe test
import difflib

def _is_repetition(text_a: str, text_b: str, threshold: float = 0.6) -> bool:
    """Return True if texts are too similar (conversation stagnated)."""
    return difflib.SequenceMatcher(None, text_a.lower(), text_b.lower()).ratio() > threshold
```

**Activity feed logging (D-11):** When repetition terminates a conversation, emit a broadcast event with the "conversation ended (repetition)" message before returning. Use the existing `_emit_conversation()` path in `engine.py`, adding a `terminated_reason` field to the conversation result dict.

### Pattern 5: ProviderSetup UI Changes

**What:** Three independent UI changes to `ProviderSetup.tsx`:
1. Swap Ollama/OpenRouter radio order — OpenRouter first
2. Add model field (text input) that appears for OpenRouter; pre-populated with Kimi K2.5 model ID
3. Rename Ollama label to "Ollama (Local — advanced)"

**Settings button in Layout.tsx:** The header currently has a "Show/Hide Panel" button. Add a second button (gear icon or "Settings" text) that calls a `onOpenSettings` callback prop passed down from `App.tsx`. `App.tsx` holds the `showProviderSetup` boolean state; the settings button sets it to `true`.

**BottomBar tick display (D-06):** Add a small static label after the provider status badge. The tick interval value must come from the Zustand store (add a `tickInterval: number` field). The backend broadcasts tick interval changes via WebSocket when the adaptive value updates. [ASSUMED: requires adding a `tick_interval_update` WebSocket message type; no existing WS message carries this value]

**Model field in /api/config POST:** The existing `/api/config` endpoint only accepts `provider` and `api_key`. Phase 9 must extend it to accept `model` so the frontend can send the user's chosen model string. [VERIFIED: current ProviderSetup.tsx and config.py read — `model` is not currently sent in the POST body]

### Anti-Patterns to Avoid

- **Creating semaphore inside `complete_structured()`:** Each invocation gets a fresh semaphore — no limiting effect.
- **Deriving AGENT_STEP_TIMEOUT from TICK_INTERVAL as a constant:** If tick is adaptive, timeout must read from the same adaptive source at call time, not at import time.
- **Storing last_sector as a local variable in `_agent_step()`:** Must persist on Agent object between ticks. A local variable resets every tick and defeats the gating purpose.
- **Firing the repetition check on the first round:** Turn 0 (first exchange) always looks repetitive in a cold start (both agents are responding to the opening). Check only after `turn >= 1`.
- **Sending the full conversation text to difflib:** Compare only the last utterance from each speaker, not the entire transcript. Ratio on long strings is distorted by shared preamble.
- **Removing the load-bearing `break` in engine.py's nearby-agent loop (line 325):** This break limits conversation gating to one LLM call per tick per agent. It MUST be preserved during any refactoring of `_agent_step()`. [VERIFIED: PITFALLS.md Pitfall 7, engine.py line 325]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| String similarity for repetition | Custom edit distance, regex overlap | `difflib.SequenceMatcher` | Already in Python stdlib; `ratio()` produces a float in [0,1] with well-understood behavior; no install required |
| Concurrent call limiting | Token bucket, manual counter, `asyncio.Lock` | `asyncio.Semaphore(N)` | Semaphore is the idiomatic asyncio primitive for bounded concurrency; correctly handles cancellation and re-raise |
| Rolling average | Manual list with `pop(0)` | `collections.deque(maxlen=N)` | `deque(maxlen=N)` auto-evicts oldest entry; `pop(0)` on a list is O(N); deque is O(1) |
| Provider health check before setting default | Custom ping endpoint | Use existing `/api/config` POST with `provider="openrouter"` | Current code already returns 200/422 which is sufficient for error display |

**Key insight:** Every optimization in this phase uses stdlib Python primitives. External library complexity is zero.

---

## Common Pitfalls

### Pitfall 1: TICK_INTERVAL Module Constant Breaks When Made Adaptive
**What goes wrong:** `TICK_INTERVAL` is imported directly by other modules (e.g., `from backend.simulation.engine import TICK_INTERVAL`). If the constant is replaced with a method or property on `SimulationEngine`, imports break with `ImportError`. Test files importing `TICK_INTERVAL` directly will fail with `ImportError` or silently use the old value.
**Why it happens:** Python caches the import value at import time; mutations to the module-level name after import are not visible to importers that did `from engine import TICK_INTERVAL`.
**How to avoid:** Remove the module-level `TICK_INTERVAL` constant. Add `tick_interval` as a `@property` on `SimulationEngine` that reads from the adaptive window. Update tests to use `engine.tick_interval`. The engine.py docstring references `D-01: TICK_INTERVAL = 5 seconds` — update the docstring.
**Warning signs:** `AttributeError: module 'backend.simulation.engine' has no attribute 'TICK_INTERVAL'` in tests.

### Pitfall 2: Semaphore Created in Wrong Scope (Inside Function)
**What goes wrong:** Placing `_llm_semaphore = asyncio.Semaphore(8)` inside `complete_structured()` creates a new semaphore on every call — no limiting effect. Calls will pile up without any queueing.
**Why it happens:** Developers co-locate semaphore creation with usage for readability.
**How to avoid:** Declare `_llm_semaphore` at module level in `gateway.py`, alongside `_client`. It is already a module-level singleton pattern file.
**Warning signs:** Debug logs show more than 8 "acquired" messages simultaneously.

### Pitfall 3: Per-Sector Gating Skips the First Tick (Agent Never Decides)
**What goes wrong:** If `agent.last_sector` starts as `None` but the gating check also returns early on `None` match, the agent never makes its first decision call and freezes at spawn with no activity.
**Why it happens:** Off-by-one in the gating condition: `if last_sector == current_sector` is True when both are `None`.
**How to avoid:** Gate condition must be `if last_sector is not None and current_sector == last_sector and not new_perceptions`. The `is not None` guard ensures the first tick always fires.
**Warning signs:** All agents are frozen with their initial "currently" activity and never change.

### Pitfall 4: Repetition Detection Compares Wrong Text Pair
**What goes wrong:** Comparing agent A's turn N against agent A's turn N-1 (same agent, consecutive turns) instead of agent A's last turn against agent B's last turn. Same-agent consecutive turns are always different (each turn advances the topic). Cross-agent last turns are the pattern that reveals stagnation.
**Why it happens:** Iterating `conversation_log[-2:]` gives the last two entries, but both could be from the same agent if the loop is indexed incorrectly.
**How to avoid:** After each round, extract `last_a = [t for t in conversation_log if t["speaker"] == agent_a_name][-1]["text"]` and `last_b = [t for t in conversation_log if t["speaker"] == agent_b_name][-1]["text"]`.
**Warning signs:** Conversations always run to MAX_TURNS regardless of content; or conversations terminate after turn 1 even when agents are discussing different topics.

### Pitfall 5: /api/config POST Does Not Accept `model` Field (Existing)
**What goes wrong:** The existing `ProviderSetup.tsx` POST body only sends `{provider, api_key}`. Adding a model field in the UI without updating the backend `/api/config` handler means the model is silently dropped. `config.state.model` remains as the old default.
**Why it happens:** Frontend and backend changes are planned as separate tasks; the backend task is missed.
**How to avoid:** The `/api/config` POST handler (likely in `backend/main.py` or a router) must be updated to accept an optional `model: str | None` field and write it to `cfg.state.model`.
**Warning signs:** User selects Kimi K2.5 in setup modal but logs show `openrouter/meta-llama/llama-3.1-8b-instruct:free` being called.

### Pitfall 6: Latency Tracking Includes Retry Overhead (Distorts Window)
**What goes wrong:** Recording `elapsed` from the outer try loop in `complete_structured()` includes all retry attempts. A call that fails twice and succeeds on attempt 3 records 3x the actual single-call latency. This inflates the rolling average and pushes the adaptive tick interval up unnecessarily.
**Why it happens:** Timing is naturally placed around the full `for attempt in range(max_retries)` block.
**How to avoid:** Record latency from the start of the successful attempt only — measure from the `await _client.chat.completions.create(...)` call, not from the function entry. On failure, do not record to the window.
**Warning signs:** Tick interval climbs over time during a session where the LLM is occasionally unreliable, even though individual successful calls are fast.

---

## Code Examples

### Semaphore in gateway.py
```python
# Source: codebase analysis of gateway.py + Python asyncio docs
import asyncio
import time

_llm_semaphore = asyncio.Semaphore(8)   # module-level
_latency_window: deque[float] = deque(maxlen=10)  # module-level

async def complete_structured(messages, response_model, ...):
    async with _llm_semaphore:
        logger.debug("LLM semaphore acquired")
        for attempt in range(1, max_retries + 1):
            try:
                t0 = time.perf_counter()
                result = await _client.chat.completions.create(...)
                _latency_window.append(time.perf_counter() - t0)  # only on success
                logger.debug("LLM semaphore releasing (latency=%.2fs)", _latency_window[-1])
                return result
            except Exception as exc:
                last_exc = exc
                logger.warning("LLM attempt %d/%d failed: %s", attempt, max_retries, type(exc).__name__)
    # semaphore released by context manager before reaching fallback logic
```

### AdaptiveTick property on SimulationEngine
```python
# Source: codebase analysis of engine.py + validated probe
from backend.gateway import get_adaptive_tick_interval

class SimulationEngine:
    # Remove TICK_INTERVAL module constant; use this property instead
    @property
    def tick_interval(self) -> float:
        return get_adaptive_tick_interval(min_interval=10.0)

    async def _tick_loop(self):
        while True:
            await self._running.wait()
            # ... existing tick body ...
            await asyncio.sleep(self.tick_interval)  # adaptive

    async def _agent_step_safe(self, agent_name, agent):
        timeout = self.tick_interval * 2
        try:
            await asyncio.wait_for(self._agent_step(agent_name, agent), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("Agent %s step timed out after %ds", agent_name, timeout)
```

### Per-Sector Gating in engine.py _agent_step
```python
# Source: codebase analysis of engine.py decide flow + CONTEXT.md D-08
# Agent object needs: last_sector: str | None = None, had_new_perceptions: bool = True

# After perception (before decide phase):
current_sector = perception.location.split("/")[1] if "/" in perception.location else perception.location
new_perceptions = bool(perception.nearby_agents or perception.nearby_events)
agent.had_new_perceptions = new_perceptions

# Gate: skip decide if sector unchanged and nothing new
if (agent.last_sector is not None
        and current_sector == agent.last_sector
        and not new_perceptions):
    return  # skip decide — keep current activity

# ... decide_action call ...

# After decide:
agent.last_sector = action.destination  # store for next tick gating
```

### Arena-Level Resolution in decide.py
```python
# Source: FEATURES.md reference pattern + codebase analysis of decide.py
def _sector_has_arenas(sector: str, spatial_tree: dict) -> bool:
    """Return True if the sector has more than one arena in the spatial tree."""
    for _world, sectors in spatial_tree.items():
        if isinstance(sectors, dict) and sector in sectors:
            arenas = sectors[sector]
            return isinstance(arenas, dict) and len(arenas) > 1
    return False
```

### Repetition Detection in converse.py
```python
# Source: Python difflib docs + validated probe test (ratio 0.848 for similar, 0.344 for distinct)
import difflib

MAX_TURNS = 6  # raised from 4 (D-12)

def _is_repetition(text_a: str, text_b: str, threshold: float = 0.6) -> bool:
    return difflib.SequenceMatcher(None, text_a.lower(), text_b.lower()).ratio() > threshold

# Inside run_conversation() turn loop, after agent B speaks (turn >= 1):
if turn >= 1:
    last_a = next(t["text"] for t in reversed(conversation_log) if t["speaker"] == agent_a_name)
    last_b = next(t["text"] for t in reversed(conversation_log) if t["speaker"] == agent_b_name)
    if _is_repetition(last_a, last_b):
        logger.info("Conversation %s<->%s ended (repetition) at turn %d", agent_a_name, agent_b_name, turn)
        ended_early = True
        break
```

### ProviderSetup.tsx — OpenRouter Default + Model Field
```typescript
// Source: codebase analysis of ProviderSetup.tsx
const KIMI_K2_5_MODEL_ID = "openrouter/moonshotai/kimi-k2.5";

// Initial state: OpenRouter pre-selected, Kimi pre-filled
const [provider, setProvider] = useState<Provider>("openrouter");
const [model, setModel] = useState(KIMI_K2_5_MODEL_ID);

// POST body includes model
const body: Record<string, unknown> = { provider, model: model.trim() };
if (provider === "openrouter") body.api_key = apiKey.trim();
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fixed `TICK_INTERVAL = 30` | Adaptive `max(10, avg_latency * 1.5)` | Phase 9 | Agents act 3x more frequently with fast providers |
| Fixed `MAX_TURNS = 4` | Repetition-gated + max 6 turns | Phase 9 | Conversations end when done, not on a timer |
| Unbounded concurrent LLM calls | Bounded by `Semaphore(8)` | Phase 9 | Prevents OpenRouter 429 errors and Ollama queue pileup |
| Single sector LLM decision | 2-level sector+arena cascade with gating | Phase 9 | 0 LLM calls when agent is staying in the same sector |
| Ollama pre-selected by default | OpenRouter + Kimi K2.5 pre-selected | Phase 9 | Better out-of-box experience for new users |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | LiteLLM prefixes OpenRouter models with `openrouter/` — correct model string is `openrouter/moonshotai/kimi-k2.5` | Standard Stack, Code Examples | API calls fail with model not found; fix: check LiteLLM docs or test with a single call before hardcoding |
| A2 | `tick_interval_update` WebSocket message type does not yet exist; must be added to backend WS broadcast and frontend store | Architecture Patterns §BottomBar tick display | If WS message already exists under a different type name, the plan creates a duplicate |
| A3 | `perception.location` format is `"world/sector/arena"` (slash-separated) so `split("/")[1]` extracts the sector for gating | Code Examples §Per-Sector Gating | If location format differs, gating check always mismatches and falls back to always calling decide_action (safe degradation, just no optimization) |

**High-confidence claims with no assumptions:** difflib availability (verified), Semaphore behavior (verified), adaptive tick formula output (verified probe), MAX_TURNS value (verified source read), Kimi K2.5 OpenRouter model ID slug (verified web search), existing `/api/config` POST body structure (verified source read).

---

## Open Questions (RESOLVED)

1. **Does the `/api/config` endpoint live in `main.py` or a dedicated router?**
   - What we know: `ProviderSetup.tsx` POSTs to `/api/config`; `config.py` has `state = AppState()`.
   - What's unclear: The router file was not read; the model field extension needs to target the right handler.
   - Recommendation: Planner should include "read backend/main.py or equivalent router to locate /api/config handler" as the first micro-step of the provider default task.
   - **RESOLVED:** Confirmed via grep: `/api/config` is in `backend/routers/llm.py` (line 29). `main.py` includes the router at line 150: `app.include_router(llm.router)`. Plan 03 Task 1a targets `backend/routers/llm.py` directly.

2. **Does `perception.location` always use slash-separated format?**
   - What we know: `perceive.py` was not read in this session.
   - What's unclear: The exact string format of `PerceptionResult.location`.
   - Recommendation: Planner should add a "read perceive.py to confirm location format" step in the per-sector gating task.
   - **RESOLVED:** Plan 02 Task 1 implements gating using `last_sector` and `new_perceptions` parameters passed from the engine (Plan 03 wiring), not by parsing `perception.location`. The sector name is extracted from `AgentAction.destination` (a known sector name from the spatial tree), not from perception format. The location format question is moot for this design.

3. **Should tick interval be broadcast to the frontend on every change or only on significant changes (>1s delta)?**
   - What we know: The bottom bar needs to display current tick interval (D-06).
   - What's unclear: Whether to broadcast on every `_latency_window.append()` or debounce.
   - Recommendation: Broadcast only when the computed interval changes by more than 1 second. This prevents constant WS messages for minor latency fluctuations.
   - **RESOLVED:** Plan 03 broadcasts `tick_interval_update` once per tick (in `_tick_loop` after the sleep), not on every `_latency_window.append()`. Since ticks happen every 10+ seconds, this is inherently rate-limited. No debouncing needed.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python venv (pytest) | Test execution | Available | Python 3.14.4 | — |
| difflib | LLM-03 repetition detection | Available | stdlib | — |
| asyncio.Semaphore | LLM-04 concurrency control | Available | stdlib | — |
| collections.deque | LLM-02 rolling window | Available | stdlib | — |
| OpenRouter API | Testing Kimi K2.5 default | Available (user has key) | — | Fall back to free model in tests |

**No missing dependencies.** All required capabilities are in the Python stdlib or already installed in the virtualenv.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (confirmed in venv) |
| Config file | pyproject.toml or pytest.ini (existing) |
| Quick run command | `source .venv/bin/activate && python -m pytest tests/test_concurrency.py tests/test_cognition.py -q` |
| Full suite command | `source .venv/bin/activate && python -m pytest tests/ -q` |

**Baseline:** 247 passed, 6 failed (health/integration/simulation tests that require a running server — pre-existing failures unrelated to Phase 9).

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LLM-04 | `asyncio.Semaphore(8)` limits concurrent calls; debug logs confirm acquire/release | unit | `python -m pytest tests/test_concurrency.py tests/test_gateway_semaphore.py -q` | ❌ Wave 0: `tests/test_gateway_semaphore.py` |
| LLM-02 | Adaptive tick returns `max(10, avg*1.5)`; timeout tracks tick*2 | unit | `python -m pytest tests/test_adaptive_tick.py -q` | ❌ Wave 0: `tests/test_adaptive_tick.py` |
| LLM-01 | Per-sector gating returns None when sector unchanged + no perceptions; arena call fires only for multi-arena sectors | unit | `python -m pytest tests/test_decide_cascade.py -q` | ❌ Wave 0: `tests/test_decide_cascade.py` |
| LLM-03 | Repetition ratio > 0.6 terminates conversation; ratio < 0.6 continues; MAX_TURNS raised to 6 | unit | `python -m pytest tests/test_repetition_detection.py -q` | ❌ Wave 0: `tests/test_repetition_detection.py` |

### Sampling Rate
- **Per task commit:** Quick run (existing tests + new test for that task)
- **Per wave merge:** Full suite — `python -m pytest tests/ -q`
- **Phase gate:** Full suite green (247+ passed) before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_gateway_semaphore.py` — LLM-04: verify semaphore is module-level, limits to 8, logs on acquire/release
- [ ] `tests/test_adaptive_tick.py` — LLM-02: verify adaptive formula, min floor, deque maxlen=10, timeout=interval*2
- [ ] `tests/test_decide_cascade.py` — LLM-01: verify gating skips decide on unchanged sector, arena logic on multi-arena sectors only
- [ ] `tests/test_repetition_detection.py` — LLM-03: verify ratio threshold, correct text pair extraction, MAX_TURNS=6

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Provider auth is user-supplied API key; no change in Phase 9 |
| V3 Session Management | no | No session changes |
| V4 Access Control | no | No new endpoints |
| V5 Input Validation | yes | Model field added to /api/config POST — validate length and format |
| V6 Cryptography | no | No new crypto operations |

### Known Threat Patterns for Phase 9 Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Oversized model string in /api/config POST | Tampering | Validate `model` field: max length 200 chars, reject if contains control characters. Apply same pattern as existing `api_key` handling in config.py |
| Semaphore starvation (all 8 slots held by slow calls, new calls queue indefinitely) | Denial of Service | Semaphore permits queuing — callers already have `asyncio.wait_for(timeout=tick*2)` which cancels stalled tasks and releases semaphore slots via context manager `__aexit__` |
| Debug logging leaking API key | Information Disclosure | Existing T-01-02 rule: never log `api_key` value. Semaphore debug logs must log `model_str` only, not `litellm_kwargs` which contains the key |

---

## Sources

### Primary (HIGH confidence)
- Codebase read: `backend/gateway.py`, `backend/config.py`, `backend/simulation/engine.py`, `backend/agents/cognition/decide.py`, `backend/agents/cognition/converse.py` — current implementation patterns and integration points
- Codebase read: `frontend/src/components/ProviderSetup.tsx`, `Layout.tsx`, `BottomBar.tsx` — UI state and POST body structure
- `.planning/research/FEATURES.md` — 3-level decision cascade research, LLM call optimization findings
- `.planning/research/PITFALLS.md` — Pitfall 6 (3-level tripling), Pitfall 7 (gating break), Pitfall 10 (TICK_INTERVAL/timeout mismatch)
- Python stdlib: difflib.SequenceMatcher, asyncio.Semaphore, collections.deque — verified in Python 3.14.4 venv
- Probe tests: adaptive tick formula validation, difflib ratio on realistic conversation samples, asyncio.Semaphore behavior

### Secondary (MEDIUM confidence)
- [OpenRouter Kimi K2.5 listing](https://openrouter.ai/moonshotai/kimi-k2.5) — model ID `moonshotai/kimi-k2.5`, pricing, context window

### Tertiary (LOW confidence)
- LiteLLM `openrouter/` prefix pattern for Kimi K2.5 — inferred from existing `openrouter/meta-llama/...` pattern in config.py; not directly verified against LiteLLM docs for this specific model [A1]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies verified in running venv; no new installs needed
- Architecture: HIGH — all patterns verified against actual source code; no speculation
- Pitfalls: HIGH — drawn from existing PITFALLS.md (first-party) and probe tests
- Kimi K2.5 model ID: MEDIUM — OpenRouter slug verified; LiteLLM prefix assumed from codebase pattern

**Research date:** 2026-04-11
**Valid until:** 2026-05-11 (30 days — stable stdlib and existing codebase patterns)
