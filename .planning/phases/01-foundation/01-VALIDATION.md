---
phase: 1
slug: foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-09
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio (backend), vitest (frontend) |
| **Config file** | pyproject.toml (backend), vitest.config.ts (frontend) |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ && cd frontend && npm test` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run full suite
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Requirement | Test Type | Automated Command | Status |
|---------|-------------|-----------|-------------------|--------|
| 01-01 | INF-01 | integration | `curl localhost:8000/health` | pending |
| 01-02 | INF-02 | unit | `uv run pytest tests/test_concurrency.py` | pending |
| 01-03 | INF-03 | unit | `uv run pytest tests/test_structured_output.py` | pending |

---

## Wave 0 Requirements

- [ ] `tests/conftest.py` — shared fixtures (async client, mock Ollama)
- [ ] `tests/test_health.py` — FastAPI health endpoint
- [ ] `tests/test_concurrency.py` — async agent step concurrency
- [ ] `tests/test_structured_output.py` — Pydantic schema validation + retry

---
*Validation strategy for Phase 01-foundation*
*Created: 2026-04-09*
