---
phase: 04
slug: simulation-engine-transport
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-10
---

# Phase 04 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-asyncio |
| **Config file** | pyproject.toml (existing) |
| **Quick run command** | `uv run pytest tests/test_simulation.py -x -q` |
| **Full suite command** | `uv run pytest -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_simulation.py -x -q`
- **After every plan wave:** Run `uv run pytest -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-T1 | 01 | 1 | SIM-01 | unit | `uv run pytest tests/test_simulation.py -x -q` | TDD (self-creating) | ⬜ pending |
| 04-02-T1 | 02 | 2 | SIM-02 | unit | `uv run pytest tests/test_simulation.py -x -q` | TDD (extends) | ⬜ pending |
| 04-03-T1 | 03 | 3 | SIM-03 | unit | `uv run pytest tests/test_simulation.py -x -q` | TDD (extends) | ⬜ pending |

*Note: All tasks use TDD pattern — test files created within tasks before verify runs.*

---

## Wave 0 Requirements

- [x] No new dependencies needed (all already installed)
- [x] `tests/test_simulation.py` — created via TDD self-creation in Plan 01

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Town feels alive with agents moving | SIM-01 | Subjective quality | Watch simulation run for 30 seconds, verify agents move and change activities |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (resolved via TDD)
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-10
