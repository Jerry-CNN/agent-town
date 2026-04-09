---
phase: 03
slug: agent-cognition
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-09
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-asyncio |
| **Config file** | pyproject.toml (existing) |
| **Quick run command** | `uv run pytest tests/test_cognition.py tests/test_memory.py -x -q` |
| **Full suite command** | `uv run pytest -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_cognition.py tests/test_memory.py -x -q`
- **After every plan wave:** Run `uv run pytest -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-T1 | 01 | 1 | AGT-05 | — | N/A | unit | `uv run pytest tests/test_memory.py -x -q` | TDD (self-creating) | ⬜ pending |
| 03-01-T2 | 01 | 1 | AGT-06 | — | N/A | unit | `uv run pytest tests/test_memory.py -x -q` | TDD (self-creating) | ⬜ pending |
| 03-02-T1 | 02 | 2 | AGT-03 | — | N/A | unit | `uv run pytest tests/test_cognition.py -x -q -k "perceive"` | TDD (self-creating) | ⬜ pending |
| 03-02-T2 | 02 | 2 | AGT-02 | — | N/A | unit | `uv run pytest tests/test_cognition.py -x -q` | TDD (self-creating) | ⬜ pending |
| 03-03-T1 | 03 | 3 | AGT-04 | — | N/A | unit | `uv run pytest tests/test_cognition.py -x -q -k "decide"` | TDD (extends) | ⬜ pending |
| 03-03-T2 | 03 | 3 | AGT-07, AGT-08 | — | N/A | unit | `uv run pytest tests/test_cognition.py -x -q` | TDD (extends) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Note: All tasks use TDD pattern — test files are created within the task before the verify step runs. No separate Wave 0 plan needed.*

---

## Wave 0 Requirements

- [x] `chromadb` + `sentence-transformers` — installed within Plan 01 Task 1 via `uv add`
- [x] `tests/test_memory.py` — created within Plan 01 Task 1 (TDD self-creating)
- [x] `tests/test_cognition.py` — created within Plan 02 Task 1 (TDD self-creating)

*Wave 0 resolved via TDD: each task creates its test files as part of execution before verify runs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| LLM-generated schedule feels natural | AGT-02 | Subjective quality | Read generated schedule output, verify hourly blocks + sub-tasks are coherent |
| Conversation dialogue is contextual | AGT-07 | Subjective quality | Read conversation transcript, verify agents reference personality and context |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (resolved via TDD self-creation)
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-09
