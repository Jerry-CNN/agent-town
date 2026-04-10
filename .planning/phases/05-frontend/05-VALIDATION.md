---
phase: 05
slug: frontend
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-10
---

# Phase 05 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest (frontend), pytest + pytest-asyncio (backend endpoint) |
| **Config file** | frontend/vitest.config.ts, pyproject.toml |
| **Quick run command** | `cd frontend && npm run test -- --run` |
| **Full suite command** | `cd frontend && npm run test -- --run && cd .. && uv run pytest -x -q` |
| **Estimated runtime** | ~8 seconds |

---

## Sampling Rate

- **After every task commit:** Run relevant test command (frontend or backend)
- **After every plan wave:** Run full suite
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 8 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-T1 | 01 | 1 | MAP-02 | unit | `cd frontend && npm run test -- --run` | TDD (self-creating) | ⬜ pending |
| 05-01-T2 | 01 | 1 | MAP-02, DSP-02 | unit | `cd frontend && npm run test -- --run` | TDD (extends) | ⬜ pending |
| 05-02-T1 | 02 | 1 | MAP-01 | unit | `uv run pytest tests/test_agents_router.py -x -q` | TDD (self-creating) | ⬜ pending |
| 05-02-T2 | 02 | 1 | MAP-01 | build | `cd frontend && npx tsc --noEmit` | N/A (type check) | ⬜ pending |
| 05-03-T1 | 03 | 2 | MAP-02, DSP-02 | build | `cd frontend && npx tsc --noEmit` | N/A (type check) | ⬜ pending |
| 05-03-T2 | 03 | 2 | MAP-02 | build | `cd frontend && npx tsc --noEmit` | N/A (type check) | ⬜ pending |
| 05-04-T1 | 04 | 2 | DSP-01 | unit | `cd frontend && npm run test -- --run` | TDD (self-creating) | ⬜ pending |
| 05-04-T2 | 04 | 2 | MAP-05 | unit | `cd frontend && npm run test -- --run` | TDD (extends) | ⬜ pending |

---

## Wave 0 Requirements

- [x] No new dependencies needed (all installed in Phase 1 scaffold)
- [x] Test files created via TDD self-creation within tasks

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Tile map looks visually correct with colored zones | MAP-01 | Visual quality | Open browser, verify colored rectangles with location labels |
| Agent sprites move smoothly via lerp | MAP-02 | Animation quality | Watch agents navigate between tiles, verify no teleporting |
| Activity feed auto-scrolls and pauses on scroll-up | DSP-01 | Interaction UX | Scroll up in feed, verify auto-scroll pauses; scroll to bottom, verify it resumes |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (resolved via TDD)
- [x] No watch-mode flags
- [x] Feedback latency < 8s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-10
