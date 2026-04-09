---
phase: 2
slug: world-navigation
status: draft
nyquist_compliant: true
wave_0_complete: true
wave_0_note: "Wave 0 is satisfied by inline TDD — each task writes tests first, then implements. No separate Wave 0 plan required."
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
| **Quick run command** | `cd /Users/sainobekou/projects/agent-town && uv run pytest tests/ -x -q` |
| **Full suite command** | `cd /Users/sainobekou/projects/agent-town && uv run pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd /Users/sainobekou/projects/agent-town && uv run pytest tests/ -x -q`
- **After every plan wave:** Run `cd /Users/sainobekou/projects/agent-town && uv run pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | TDD Inline | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|------------|--------|
| 02-01-01 | 01 | 1 | MAP-03 | — | N/A | unit | `uv run pytest tests/test_world.py -k test_all_required_locations` | Yes | ⬜ pending |
| 02-01-02 | 01 | 1 | MAP-04 | — | N/A | unit | `uv run pytest tests/test_world.py -k test_bfs` | Yes | ⬜ pending |
| 02-02-01 | 02 | 1 | AGT-01 | — | N/A | unit | `uv run pytest tests/test_agent_loader.py -k test_loads_minimum_agent_count` | Yes | ⬜ pending |
| 02-03-01 | 03 | 2 | MAP-03, AGT-01 | — | N/A | integration | `uv run pytest tests/test_cross_validation.py -x -v` | Yes | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Wave 0 is satisfied by inline TDD within each Wave 1 task. Both Plan 01 and Plan 02 use `tdd="true"` tasks that write tests before implementation:

- Plan 01 Task 1 creates `tests/test_world.py` (tests written first, then Tile/Maze/BFS implemented)
- Plan 01 Task 2 extends `tests/test_world.py` with BFS edge case tests
- Plan 02 Task 1 creates `tests/test_agent_loader.py` (tests written first, then schemas/loader implemented)
- Plan 03 Task 1 creates `tests/test_cross_validation.py` (Wave 2 cross-plan integration tests)

No separate Wave 0 test stub plan is needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Town layout looks reasonable | MAP-03 | Visual judgment of tile coordinates | Print map grid to console, verify locations are in correct neighborhood clusters |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or inline TDD
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covered by inline TDD (no separate MISSING references)
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
