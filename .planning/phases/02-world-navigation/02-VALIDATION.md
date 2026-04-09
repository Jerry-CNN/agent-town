---
phase: 2
slug: world-navigation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-09
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-asyncio |
| **Config file** | backend/pyproject.toml |
| **Quick run command** | `cd backend && uv run pytest tests/ -x -q` |
| **Full suite command** | `cd backend && uv run pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/ -x -q`
- **After every plan wave:** Run `cd backend && uv run pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | MAP-03 | — | N/A | unit | `uv run pytest tests/test_maze.py -k test_locations` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | MAP-04 | — | N/A | unit | `uv run pytest tests/test_maze.py -k test_bfs` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | AGT-01 | — | N/A | unit | `uv run pytest tests/test_agent.py -k test_agent_data` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | MAP-04 | — | N/A | unit | `uv run pytest tests/test_maze.py -k test_no_path` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_maze.py` — stubs for MAP-03, MAP-04
- [ ] `backend/tests/test_agent.py` — stubs for AGT-01
- [ ] `backend/tests/conftest.py` — shared fixtures (if not already present)

*Existing pytest infrastructure from Phase 1 covers framework installation.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Town layout looks reasonable | MAP-03 | Visual judgment of tile coordinates | Print map grid to console, verify locations are in correct neighborhood clusters |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
