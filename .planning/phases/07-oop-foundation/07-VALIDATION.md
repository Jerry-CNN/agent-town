---
phase: 7
slug: oop-foundation
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-10
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 + pytest-asyncio 1.3.0 |
| **Config file** | `pyproject.toml` (`asyncio_mode = "auto"`, `testpaths = ["tests"]`) |
| **Quick run command** | `.venv/bin/python -m pytest tests/test_world.py tests/test_agent_loader.py tests/test_cognition.py tests/test_memory.py -x -q` |
| **Full suite command** | `.venv/bin/python -m pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python -m pytest tests/test_world.py tests/test_agent_loader.py tests/test_cognition.py tests/test_memory.py -x -q`
- **After every plan wave:** Run `.venv/bin/python -m pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green (excluding 6 pre-existing failures in health/integration/simulation)
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | EVTS-01, EVTS-02, EVTS-03, BLD-01 | unit | `.venv/bin/python -m pytest tests/test_events.py tests/test_building.py -x -q` | ❌ W0 | ⬜ pending |
| 07-01-02 | 01 | 1 | (schema split) | smoke | `python -c "from backend.schemas import AgentConfig, WSMessage, Memory, Event"` | inline | ⬜ pending |
| 07-02-01 | 02 | 2 | ARCH-01, ARCH-02 | unit | `.venv/bin/python -m pytest tests/test_agent_class.py -x -q` | ❌ W0 | ⬜ pending |
| 07-02-02 | 02 | 2 | ARCH-03 | unit + contract | `.venv/bin/python -m pytest tests/test_simulation.py tests/test_ws_contract.py -x -q` | ✅ / ❌ W0 | ⬜ pending |
| All | - | - | All | regression | `.venv/bin/python -m pytest tests/ -q --ignore=tests/test_health.py --ignore=tests/test_integration.py` | ✅ | ⬜ pending |
| All | - | - | All | smoke | `python -c "from backend.agents.agent import Agent; from backend.simulation.engine import SimulationEngine; print('OK')"` | inline | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_agent_class.py` — Agent class fields, cognition delegation (ARCH-01, ARCH-02)
- [ ] `tests/test_events.py` — Event lifecycle, propagation tracking, expiry (EVTS-01, EVTS-02, EVTS-03)
- [ ] `tests/test_building.py` — Building class fields and town loading (BLD-01)
- [ ] `tests/test_ws_contract.py` — WS payload structure contract test

*No framework install needed — pytest already configured.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have automated verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
