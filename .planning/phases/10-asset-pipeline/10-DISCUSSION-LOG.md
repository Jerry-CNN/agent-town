# Phase 10: Asset Pipeline - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-11
**Phase:** 10-asset-pipeline
**Areas discussed:** Agent sprite mapping, Tileset scope, Atlas conversion, Asset organization

---

## Agent Sprite Mapping

| Option | Description | Selected |
|--------|-------------|----------|
| Pick 8, port 8 | Choose 8 visually distinct reference sprites, rename to match Agent Town agents | |
| Port all 25, assign 8 | Port all 25 reference sprites into assets; assign 8 to current agents. Leaves room to add agents later. | ✓ |
| Let me pick | User manually selects which specific reference sprites map to which agents | |

**User's choice:** Port all 25, assign 8
**Notes:** Keeps flexibility for future agent additions without re-running asset pipeline.

---

## Tileset Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Port all 16 | Maximum flexibility for map design in Phase 11. ~15MB of PNGs total. | ✓ |
| Port essentials only | Field, Village, Forest, all 5 interiors, Room_Builder, blocks. Skip Desert, Harbor, Mountains. | |
| You decide | Claude picks based on what Agent Town's buildings need | |

**User's choice:** Port all 16
**Notes:** None

---

## Atlas Conversion

| Option | Description | Selected |
|--------|-------------|----------|
| One-time script | Python script converts sprite.json once. Converted output committed to repo. | ✓ |
| Build-time tool | Vite plugin or npm script that converts on build. | |
| Manual conversion | Hand-edit the JSON to PixiJS format. | |

**User's choice:** One-time script
**Notes:** User asked about execution speed — clarified that all approaches have zero runtime cost since the converted JSON is pre-committed. One-time script chosen for simplicity and maintainability.

---

## Asset Organization

| Option | Description | Selected |
|--------|-------------|----------|
| Mirror reference structure | assets/village/tilemap/ and assets/village/agents/{name}/ | |
| Simplified flat | assets/tilesets/ and assets/agents/{name}/ | |
| You decide | Claude picks the best structure for PixiJS asset loading | ✓ |

**User's choice:** You decide (Claude's Discretion)
**Notes:** None

---

## Claude's Discretion

- Asset directory structure under frontend/public/assets/ (user deferred to Claude)
- Agent-to-sprite mapping (which of 25 reference sprites → which of 8 Agent Town agents)

## Deferred Ideas

None
