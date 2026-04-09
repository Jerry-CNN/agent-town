---
phase: 01-foundation
plan: "03"
subsystem: ui+integration
tags: [react, typescript, provider-setup, zustand, localStorage, testing-library, integration-tests, websocket]
dependency_graph:
  requires: [01-01, 01-02]
  provides:
    - ProviderSetup modal (first-visit provider selection + OpenRouter API key flow)
    - OllamaStatusBanner (non-blocking amber banner when Ollama unavailable)
    - App.tsx localStorage re-hydration with schema validation (T-03-03)
    - End-to-end integration test suite (6 tests covering full stack)
    - _resolve_model default routing test (D-02 verification)
  affects:
    - Phase 1 checkpoint (human-verify gate)
    - Phase 5 (ProviderSetup will be extended for Settings panel)
tech_stack:
  added:
    - "@testing-library/react@16 (render + fireEvent + screen + waitFor)"
    - "@vitejs/plugin-react added to vitest.config.ts for JSX transform in tests"
  patterns:
    - "ProviderSetup.test.tsx: @testing-library/react with fireEvent for user interaction simulation"
    - "T-03-03: localStorage JSON.parse wrapped in try/catch with schema validation before trusting"
    - "Integration tests reuse async_client fixture from conftest.py"
    - "WebSocket integration test uses Starlette TestClient (synchronous) not AsyncClient"
key_files:
  created:
    - frontend/src/components/ProviderSetup.tsx
    - frontend/src/components/OllamaStatusBanner.tsx
    - frontend/src/tests/providerSetup.test.tsx
    - tests/test_integration.py
  modified:
    - frontend/src/App.tsx
    - frontend/vitest.config.ts
    - tests/test_structured_output.py
decisions:
  - "Test file uses .tsx extension (not .ts) — required for JSX transform via @vitejs/plugin-react in vitest"
  - "vitest.config.ts updated to include @vitejs/plugin-react plugin for JSX in test environment"
  - "T-03-03: localStorage re-hydration in App.tsx uses try/catch + provider field presence check"
  - "OllamaStatusBanner reads providerConfig from Zustand store (not props) to check provider===ollama"
metrics:
  duration: "~3 minutes"
  completed_date: "2026-04-09"
  tasks_completed: 2
  files_created: 4
  files_modified: 3
  tests_added: 7
---

# Phase 1 Plan 03: Provider Config UI + Integration Tests Summary

**One-liner:** First-visit ProviderSetup modal (Ollama/OpenRouter radio + conditional API key), OllamaStatusBanner, localStorage re-hydration with schema validation, and 6-test end-to-end integration suite covering health, config, 422 validation, WebSocket ping-pong, and concurrency subprocess.

## What Was Built

### Task 1: ProviderSetup modal, OllamaStatusBanner, App.tsx wiring (commit: 7d24693)

- `frontend/src/components/ProviderSetup.tsx`: Full-screen overlay modal with Ollama/OpenRouter radio buttons (Ollama pre-selected), conditional API key password input (only when OpenRouter selected), Continue button disabled until key non-empty for OpenRouter, fetch to POST /api/config on submit, setProviderConfig to Zustand store, localStorage persistence with `agenttown_provider` key
- `frontend/src/components/OllamaStatusBanner.tsx`: Fixed amber banner (background: #b45309) when provider=ollama AND ollamaAvailable=false, dismissible via × button, reads providerConfig from Zustand
- `frontend/src/App.tsx`: localStorage re-hydration on mount (T-03-03: try/catch + schema validation), conditional `<ProviderSetup />` when providerConfig===null, /api/health probe on mount to set ollamaAvailable state, `<OllamaStatusBanner>` wired to ollamaAvailable
- `frontend/vitest.config.ts`: Added @vitejs/plugin-react for JSX transform in test environment
- `frontend/src/tests/providerSetup.test.tsx`: 6 tests covering all behaviors per plan spec

### Task 2: End-to-end integration test suite (commit: 2bde8c9)

- `tests/test_integration.py`: 6 tests — health 200, ollama config + subsequent health, openrouter config + health shows openrouter=true, 422 on missing key, WebSocket ping-pong (Starlette TestClient), concurrency suite subprocess
- `tests/test_structured_output.py`: Added `test_resolve_model_returns_ollama_defaults` verifying D-02 default model routing without real LLM call

## Test Results

```
Frontend: 11 passed (5 store + 6 providerSetup)
Backend:  15 passed (2 concurrency + 2 health + 6 integration + 5 structured_output)
Total: 26 tests passing
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Test file required .tsx extension for JSX**
- **Found during:** Task 1 GREEN phase (test runner error)
- **Issue:** The plan specified `frontend/src/tests/providerSetup.test.ts` (`.ts`). Tests use JSX (`<ProviderSetup />`), which requires `.tsx` extension AND the React plugin in the vitest config. Without both, Vite's import analysis rejected the JSX syntax at transform time.
- **Fix:** Renamed file to `providerSetup.test.tsx` and added `@vitejs/plugin-react` to `vitest.config.ts`.
- **Files modified:** `frontend/vitest.config.ts`, test file renamed to `.tsx`
- **Commit:** 7d24693

**2. [Rule 1 - Bug] Initial test wrote component as plain function call**
- **Found during:** Task 1 first test run
- **Issue:** Original RED-phase test called `render(ProviderSetup({}))` directly (treating it as a factory function). This triggered "Invalid hook call" since hooks cannot be called outside React's render cycle.
- **Fix:** Rewrote tests to use JSX via `render(<ProviderSetup />)` with proper `@testing-library/react` patterns.
- **Files modified:** `frontend/src/tests/providerSetup.test.tsx`
- **Commit:** 7d24693 (included in GREEN phase commit)

## Known Stubs

These are carry-overs from Plan 02 (documented there) — not introduced by this plan:

| Stub | File | Reason |
|------|------|--------|
| PixiJS canvas placeholder rectangle | `frontend/src/components/MapCanvas.tsx` | Phase 5 replaces with tile map |
| Inspector placeholder | `frontend/src/components/Layout.tsx` | Phase 5 implements AgentInspector |
| Disabled event input | `frontend/src/components/BottomBar.tsx` | Phase 6 wires event injection |

No new stubs introduced by this plan.

## Threat Mitigations Applied

All T-03-xx mitigations from the plan's threat model are implemented:

| Threat ID | Mitigation Applied |
|-----------|-------------------|
| T-03-01 | API key stored in localStorage — single-user local app tradeoff, documented as accepted |
| T-03-02 | No CSRF concern — single-user localhost, no session cookies |
| T-03-03 | `App.tsx` wraps `JSON.parse(localStorage.getItem("agenttown_provider"))` in try/catch; checks `provider` field presence and value before calling `setProviderConfig` |
| T-03-04 | `OllamaStatusBanner` shows generic message only; API key never mentioned in banner |

## Checkpoint: Awaiting Human Verification

Task 3 is `type="checkpoint:human-verify"` — execution stopped here for human sign-off on the complete Phase 1 stack.

**What to verify:** See Task 3 `<how-to-verify>` block in 01-03-PLAN.md for exact steps.

## Self-Check: PASSED

Files exist:
- frontend/src/components/ProviderSetup.tsx: FOUND
- frontend/src/components/OllamaStatusBanner.tsx: FOUND
- frontend/src/App.tsx: FOUND (modified)
- frontend/src/tests/providerSetup.test.tsx: FOUND
- tests/test_integration.py: FOUND
- tests/test_structured_output.py: FOUND (modified)

Commits exist:
- 7d24693 (Task 1): FOUND
- 2bde8c9 (Task 2): FOUND
