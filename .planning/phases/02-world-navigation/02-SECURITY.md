---
phase: 02
slug: world-navigation
status: verified
threats_open: 0
asvs_level: 1
created: 2026-04-09
---

# Phase 02 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| JSON file -> Maze constructor | town.json loaded from disk, parsed into Python objects | Map layout data (non-sensitive, committed to git) |
| JSON file -> Pydantic model | Agent JSON configs loaded and validated through AgentConfig.model_validate() | Fictional agent personality data (non-sensitive) |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-02-01 | Tampering | backend/data/map/town.json | accept | File committed to git, not user-editable at runtime. No runtime file upload mechanism. | closed |
| T-02-02 | Denial of Service | Maze.find_path BFS | accept | BFS on 100x100 grid is O(10,000) worst case. No user-supplied input reaches BFS in Phase 2. | closed |
| T-02-03 | Information Disclosure | Agent JSON configs | accept | Fictional simulation data, no PII. Public codebase. | closed |
| T-02-04 | Tampering | backend/data/agents/*.json | accept | Files committed to git, not user-editable at runtime. Pydantic validation catches malformed data. | closed |
| T-02-05 | Information Disclosure | Agent personality text | accept | All agent data is fictional simulation content. No real PII. | closed |
| T-02-06 | Spoofing | AgentConfig.name field | accept | Agent names pre-defined in committed JSON. No user-supplied agent creation in v1. | closed |
| T-02-07 | Tampering | Agent coord values | mitigate | Cross-validation tests (tests/test_cross_validation.py) catch coords on collision tiles or out of bounds. 3 test functions verify bounds, walkability, and border exclusion. | closed |

*Status: open / closed*
*Disposition: mitigate (implementation required) / accept (documented risk) / transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-01 | T-02-01 | town.json is a build-time artifact committed to git; no runtime mutation path exists | GSD workflow | 2026-04-09 |
| AR-02 | T-02-02 | BFS worst case O(10K) is trivial; no user-controlled input reaches pathfinding in Phase 2 | GSD workflow | 2026-04-09 |
| AR-03 | T-02-03 | Agent data is entirely fictional; no PII or secrets | GSD workflow | 2026-04-09 |
| AR-04 | T-02-04 | Same as AR-01; agent configs are git-committed build artifacts with Pydantic validation | GSD workflow | 2026-04-09 |
| AR-05 | T-02-05 | Same as AR-03; fictional personality text | GSD workflow | 2026-04-09 |
| AR-06 | T-02-06 | No user-created agents in v1; names are hardcoded in committed JSON | GSD workflow | 2026-04-09 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-09 | 7 | 7 | 0 | GSD secure-phase |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-09
