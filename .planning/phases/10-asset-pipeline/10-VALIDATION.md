---
phase: 10
slug: asset-pipeline
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-12
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 4.1.4 |
| **Config file** | frontend/vitest.config.ts (Wave 0) |
| **Quick run command** | `cd frontend && npm test` |
| **Full suite command** | `cd frontend && npm test` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npm test`
- **After every plan wave:** Run `cd frontend && npm test` + manual browser spot-check
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | PIPE-01 | smoke | `python3 scripts/verify_assets.py` | ❌ W0 | ⬜ pending |
| 10-01-02 | 01 | 1 | PIPE-02 | unit | `cd frontend && npm test` | ❌ W0 | ⬜ pending |
| 10-02-01 | 02 | 1 | PIPE-03 | unit | `cd frontend && npm test` | ❌ W0 | ⬜ pending |
| 10-02-02 | 02 | 1 | PIPE-03 | manual | Browser visual check at 2x zoom | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/src/__tests__/spriteAtlas.test.ts` — covers PIPE-02 (JSON structure validation)
- [ ] `frontend/src/__tests__/scaleModeInit.test.ts` — covers PIPE-03 (scaleMode nearest assertion)
- [ ] `scripts/verify_assets.py` — smoke test for PIPE-01 (count and name-check all expected files)
- [ ] `frontend/vitest.config.ts` — configure jsdom environment

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Tile edge crispness at 2x zoom | PIPE-03 | Requires visual rendering in browser | Open app, zoom to 2x, verify tile edges are sharp not blurred |
| No 404s for tileset assets | PIPE-01 | Requires running dev server + browser | Open browser devtools Network tab, reload, confirm no 404s for assets/ |

---

## Validation Sign-Off

- [x] All tasks have automated verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
