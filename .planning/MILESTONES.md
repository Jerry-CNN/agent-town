# Milestones

## v1.1 Architecture & Polish (Shipped: 2026-04-12)

**Phases:** 5 (7, 8, 9, 9.1, 9.2) | **Plans:** 9 | **Timeline:** 2026-04-11
**Files changed:** 39 | **Lines:** +4,407 / -668

**Key accomplishments:**

- Agent/Building/Event OOP classes replace scattered dicts; schemas split into domain modules (Phase 7)
- Building wall outlines rendered on map; operating hours enforce agent re-routing when buildings close (Phase 8)
- 2-level LLM decision cascade (sector -> arena) with per-sector gating; adaptive tick interval; conversation repetition detection; semaphore concurrency control (Phase 9)
- Event lifecycle state machine wired into runtime — inject_event creates Event objects, heard_by tracks whisper propagation, expired events cleaned up; engine routes through Agent wrapper methods (Phase 9.1)
- Activity text restored on agent sprites with semi-transparent pill background; WCAG AA contrast verified on all sector backgrounds (Phase 9.2)

**Known issues:**

- Activity-location mismatch: agent activity text sometimes shows a different location than physical position (cognition bug, tracked for v1.2)
- 7 pre-existing test failures (test_health x2, test_integration x3, test_memory x1 flaky, test_movement x1)

---
