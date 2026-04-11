---
phase: 9
slug: llm-optimization
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-11
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-asyncio |
| **Config file** | `backend/pyproject.toml` |
| **Quick run command** | `cd backend && python -m pytest tests/ -x -q --timeout=30` |
| **Full suite command** | `cd backend && python -m pytest tests/ -v --timeout=60` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/ -x -q --timeout=30`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -v --timeout=60`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | LLM-04 | — | Semaphore limits concurrent calls to 8 | unit (inline TDD) | `cd backend && python -m pytest tests/test_gateway_semaphore.py -v` | Created inline by task | ⬜ pending |
| 09-01-02 | 01 | 1 | LLM-02 | — | Adaptive tick tracks latency rolling window | unit (inline TDD) | `cd backend && python -m pytest tests/test_engine_adaptive.py -v` | Created inline by task | ⬜ pending |
| 09-02-01 | 02 | 1 | LLM-01 | — | 2-level cascade: sector then arena; per-sector gating skips LLM when unchanged | unit (inline TDD) | `cd backend && python -m pytest tests/test_decide_cascade.py -v` | Created inline by task | ⬜ pending |
| 09-02-02 | 02 | 1 | LLM-03 | — | Repetition detection terminates conversation | unit (inline TDD) | `cd backend && python -m pytest tests/test_converse_repetition.py -v` | Created inline by task | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Nyquist note:** All four plan tasks use `tdd="true"` with inline `<behavior>` blocks. Each task creates its own test file as part of the RED phase before writing production code. Separate Wave 0 test stubs are not needed because the inline TDD workflow produces the test files as the first action within each task.

---

## Wave 0 Requirements

No separate Wave 0 needed. All test files are created inline by their respective TDD tasks:

- `tests/test_gateway_semaphore.py` — created by Plan 01 Task 1 (inline TDD)
- `tests/test_engine_adaptive.py` — created by Plan 01 Task 2 (inline TDD)
- `tests/test_decide_cascade.py` — created by Plan 02 Task 1 (inline TDD)
- `tests/test_converse_repetition.py` — created by Plan 02 Task 2 (inline TDD)

*Existing test infrastructure covers framework setup.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Settings button opens provider modal | D-03 | UI interaction | Click gear icon in header, verify modal opens with current provider selected |
| Tick interval display in bottom bar | D-06 | Visual verification | Run simulation, check bottom bar shows "Tick: Xs" updating dynamically |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or inline TDD coverage
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Inline TDD replaces Wave 0 — test files created as first step of each task
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
