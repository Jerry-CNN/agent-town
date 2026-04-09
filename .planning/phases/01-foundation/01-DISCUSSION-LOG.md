# Phase 1: Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-09
**Phase:** 01-foundation
**Areas discussed:** Config experience, Cost display, Error handling UX, App shell layout

---

## Config Experience

| Option | Description | Selected |
|--------|-------------|----------|
| Blocking setup screen | Full-page setup wizard before anything else loads | |
| Inline first-run prompt | Main app loads with a banner asking to configure | |
| Settings drawer | App loads normally, settings via gear icon | |

**User's choice:** "Move API key config to v2. In v1, use free tier models."
**Follow-up:** User chose Ollama local-only for v1. Default model: Llama 3.1 8B. Auto-detect what's available.
**Notes:** This significantly simplifies Phase 1 — no provider selection UI, no API key management. CFG-01, CFG-02, CFG-03 all deferred to v2.

---

## Cost Display

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, token counter | Show tokens used per step and running total | |
| Defer to v2 | Skip cost/token display entirely in v1 | ✓ |
| Minimal indicator | Just show "thinking..." indicator | |

**User's choice:** Defer to v2
**Notes:** With Ollama being free/local, cost display has less urgency.

---

## Error Handling UX

| Option | Description | Selected |
|--------|-------------|----------|
| Toast notifications | Small pop-up messages that auto-dismiss | |
| Activity feed errors | Errors inline in the activity feed | |
| You decide | Claude picks best approach | ✓ |

**User's choice:** You decide
**Notes:** Claude has discretion on error communication approach.

---

## App Shell Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Map-dominant | Tile map takes most of screen, feed in collapsible sidebar | ✓ |
| Split view | Map on left, feed + controls on right, equal emphasis | |
| You decide | Claude picks best layout | |

**User's choice:** Map-dominant layout

**Follow-up: Inspector panel location**

| Option | Description | Selected |
|--------|-------------|----------|
| Replace feed sidebar | Inspector takes over right sidebar | ✓ |
| Overlay/modal | Floating panel over the map | |
| Expandable sidebar | Sidebar splits — feed on top, inspector on bottom | |

**User's choice:** Replace feed sidebar

---

## Claude's Discretion

- Error handling UX approach (D-06)

## Deferred Ideas

- API key configuration and provider selection UI (v2)
- Token counting and cost estimation (v2)
- Model routing per call type (v2)
