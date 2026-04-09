---
phase: 01-foundation
plan: "01"
subsystem: backend
tags: [fastapi, async, llm-gateway, instructor, litellm, pydantic-v2, websocket, concurrency]
dependency_graph:
  requires: []
  provides: [backend-scaffold, llm-gateway, health-endpoint, websocket-stub, async-foundation]
  affects: [01-02, 01-03, phase-03-agents]
tech_stack:
  added:
    - "fastapi>=0.135"
    - "uvicorn[standard]>=0.44"
    - "pydantic>=2.12"
    - "litellm>=1.83.0"
    - "instructor>=1.15"
    - "httpx>=0.28"
    - "pytest>=9"
    - "pytest-asyncio>=1.3"
  patterns:
    - "instructor.from_litellm(litellm.acompletion) for structured LLM output with retry"
    - "asyncio.TaskGroup for concurrent agent step execution (Python 3.11+)"
    - "httpx.ASGITransport for async FastAPI test client (httpx>=0.28)"
    - "Pydantic v2 model_validator (not @validator) for schema validation"
key_files:
  created:
    - pyproject.toml
    - backend/__init__.py
    - backend/main.py
    - backend/config.py
    - backend/schemas.py
    - backend/gateway.py
    - backend/routers/__init__.py
    - backend/routers/health.py
    - backend/routers/ws.py
    - backend/routers/llm.py
    - tests/__init__.py
    - tests/conftest.py
    - tests/test_health.py
    - tests/test_concurrency.py
    - tests/test_structured_output.py
  modified: []
decisions:
  - "Explicit retry loop in complete_structured (not relying solely on instructor max_retries) so patched tests observe retry behavior correctly"
  - "FALLBACK_AGENT_ACTION returned on all-retry failure for AgentAction — never raises (D-06 non-blocking)"
  - "T-01-02: api_key truncated to first 8 chars in log messages; never logged in full"
  - "T-01-03: retry loop bounded at max_retries=3 by default; instructor max_retries=1 per attempt"
  - "T-01-04: ProviderConfig model_validator rejects model strings not matching ollama_chat/... or openrouter/... prefix"
metrics:
  duration: "~30 minutes"
  completed_date: "2026-04-09"
  tasks_completed: 2
  files_created: 15
  files_modified: 0
  tests_added: 8
---

# Phase 1 Plan 01: FastAPI Backend Scaffold with Async LLM Gateway Summary

**One-liner:** FastAPI app with lifespan Ollama probe, async LLM gateway (Ollama + OpenRouter via instructor+LiteLLM), Pydantic v2 schemas, WebSocket ping/pong stub, and pytest suite proving concurrent execution (INF-02) and structured-output retry fallback (INF-03).

## What Was Built

### Task 1: Project manifest and FastAPI app scaffold (commit: 8b0efeb)

- `pyproject.toml`: Python project manifest with all backend dependencies pinned, including `litellm>=1.83.0` (avoids supply-chain backdoor in 1.82.7/1.82.8)
- `backend/config.py`: Module-level `AppState` dataclass singleton — `state.ollama_available`, `state.openrouter_configured`, `state.provider`, `state.api_key`, `state.model`
- `backend/schemas.py`: Four Pydantic v2 models — `AgentAction`, `WSMessage`, `ProviderConfig` (with model_validator rejecting openrouter+no api_key and validating model string prefix), `LLMTestResponse`
- `backend/main.py`: FastAPI app with lifespan hook probing Ollama at startup (3-second timeout, non-blocking on failure per D-06)
- `backend/routers/health.py`: `GET /health` returning `{"status": "ok", "provider_status": {"ollama": bool, "openrouter": bool}}`
- `backend/routers/ws.py`: WebSocket `/ws` with ping/pong loop, graceful disconnect handling
- `tests/conftest.py`: `async_client` fixture using `httpx.ASGITransport` (httpx>=0.28 API), `mock_ollama_available` fixture
- `tests/test_health.py`: 2 tests — health 200 with correct keys, health 200 when Ollama unavailable

### Task 2: Async LLM gateway, concurrency proof, structured output retry (commit: 5dc199c)

- `backend/gateway.py`: `complete_structured()` async function using `instructor.from_litellm(litellm.acompletion)` with explicit retry loop (max_retries=3), `FALLBACK_AGENT_ACTION` returned on all-retry failure, api_key never logged in full (T-01-02)
- `backend/routers/llm.py`: `POST /api/llm/test` (calls complete_structured, Pydantic validates provider config) and `POST /api/config` (updates AppState)
- `tests/test_concurrency.py`: Proves 10 async tasks complete in parallel using `asyncio.TaskGroup` — elapsed < 0.5s (not ~1.0s sequential), plus TaskGroup exception propagation test
- `tests/test_structured_output.py`: 4 tests — retry succeeds on 2nd call, fallback returned after all failures, 422 on /api/llm/test with openrouter+no key, 422 on /api/config with openrouter+no key

## Test Results

```
8 passed in 0.92s
```

All 4 test files green: test_health.py (2), test_concurrency.py (2), test_structured_output.py (4).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Explicit retry loop in complete_structured**
- **Found during:** Task 2 GREEN phase (test failure)
- **Issue:** The plan showed `max_retries=max_retries` passed to `_client.chat.completions.create`. When tests patched `_client.chat.completions.create` directly, the first exception jumped straight to our `except` block — instructor's internal retry logic only runs at the LiteLLM transport layer, not when we patch the create method. Test for "retry succeeds on second call" returned `FALLBACK_AGENT_ACTION` instead of the valid `AgentAction`.
- **Fix:** Added explicit `for attempt in range(1, max_retries + 1)` loop in `complete_structured`, passing `max_retries=1` per attempt to instructor. Each exception is caught and retried in the gateway loop.
- **Files modified:** `backend/gateway.py`
- **Commit:** 5dc199c (included in Task 2 commit)

## Known Stubs

- `backend/routers/ws.py`: WebSocket endpoint accepts connections and handles ping/pong but does not yet wire to simulation engine state. This is intentional — Phase 4 (real-time frontend) wires agent updates through this endpoint.
- `backend/main.py`: Shutdown cleanup comment is a placeholder for future resource teardown (e.g., ChromaDB, DB connections in later phases).

## Threat Surface

All threat mitigations from plan's `<threat_model>` implemented:

| Threat ID | Mitigation Applied |
|-----------|-------------------|
| T-01-02 | `gateway.py` logger.warning uses `type(exc).__name__` not exc message; api_key truncated to `key[:8]+"..."` in debug logs only |
| T-01-03 | `max_retries=3` cap enforced via explicit loop; Ollama probe uses 3-second httpx timeout |
| T-01-04 | `ProviderConfig.validate_openrouter_api_key` model_validator raises ValueError (-> 422); `validate_model_string` rejects model strings not matching `^(ollama_chat\|openrouter/).+` |

## Self-Check: PASSED

Files exist:
- pyproject.toml: FOUND
- backend/main.py: FOUND
- backend/gateway.py: FOUND
- backend/schemas.py: FOUND
- backend/routers/llm.py: FOUND
- tests/test_concurrency.py: FOUND
- tests/test_structured_output.py: FOUND

Commits exist:
- 8b0efeb (Task 1): FOUND
- 5dc199c (Task 2): FOUND
