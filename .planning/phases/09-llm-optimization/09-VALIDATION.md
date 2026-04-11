---
phase: 9
slug: llm-optimization
status: draft
nyquist_compliant: false
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
| 09-01-01 | 01 | 1 | LLM-04 | — | Semaphore limits concurrent calls to 8 | unit | `cd backend && python -m pytest tests/test_gateway.py -k semaphore -v` | ❌ W0 | ⬜ pending |
| 09-01-02 | 01 | 1 | LLM-02 | — | Adaptive tick tracks latency rolling window | unit | `cd backend && python -m pytest tests/test_engine.py -k adaptive -v` | ❌ W0 | ⬜ pending |
| 09-02-01 | 02 | 1 | LLM-01 | — | 2-level cascade: sector then arena | unit | `cd backend && python -m pytest tests/test_decide.py -k cascade -v` | ❌ W0 | ⬜ pending |
| 09-02-02 | 02 | 1 | LLM-01 | — | Per-sector gating skips LLM when unchanged | unit | `cd backend && python -m pytest tests/test_decide.py -k gating -v` | ❌ W0 | ⬜ pending |
| 09-03-01 | 03 | 1 | LLM-03 | — | Repetition detection terminates conversation | unit | `cd backend && python -m pytest tests/test_converse.py -k repetition -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_gateway.py` — semaphore concurrency stubs for LLM-04
- [ ] `tests/test_engine.py` — adaptive tick interval stubs for LLM-02
- [ ] `tests/test_decide.py` — cascade + gating stubs for LLM-01
- [ ] `tests/test_converse.py` — repetition detection stubs for LLM-03

*Existing test infrastructure covers framework setup.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Settings button opens provider modal | D-03 | UI interaction | Click gear icon in header, verify modal opens with current provider selected |
| Tick interval display in bottom bar | D-06 | Visual verification | Run simulation, check bottom bar shows "Tick: Xs" updating dynamically |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
