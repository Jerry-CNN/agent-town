---
phase: 03
slug: agent-cognition
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| 03-01-01 | 01 | 0 | AGT-05 | — | N/A | unit | `uv run pytest tests/test_memory.py -x -q` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 1 | AGT-02 | — | N/A | unit | `uv run pytest tests/test_cognition.py -x -q` | ❌ W0 | ⬜ pending |
| 03-03-01 | 03 | 1 | AGT-03 | — | N/A | unit | `uv run pytest tests/test_cognition.py -x -q` | ❌ W0 | ⬜ pending |
| 03-04-01 | 04 | 2 | AGT-07, AGT-08 | — | N/A | unit | `uv run pytest tests/test_cognition.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `chromadb` + `sentence-transformers` — add via `uv add chromadb sentence-transformers`
- [ ] `tests/test_memory.py` — stubs for AGT-05, AGT-06 (memory storage + retrieval)
- [ ] `tests/test_cognition.py` — stubs for AGT-02, AGT-03, AGT-04, AGT-07, AGT-08

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| LLM-generated schedule feels natural | AGT-02 | Subjective quality | Read generated schedule output, verify hourly blocks + sub-tasks are coherent |
| Conversation dialogue is contextual | AGT-07 | Subjective quality | Read conversation transcript, verify agents reference personality and context |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
