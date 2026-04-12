# Phase 11: Town Map Design & Backend Sync - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-12
**Phase:** 11-town-map-design-backend-sync
**Areas discussed:** Map dimensions & layout, Building interiors, Tiled layer structure, Backend sync script, Map authoring workflow, Reachability validation, Building operating hours

---

## Map Dimensions & Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Keep 100x100 | Same grid, avoids backend changes | |
| Expand to 140x100 | Match reference, more room for detail | ✓ |
| You decide | Claude picks | |

**Map size choice:** Expand to 140x100

| Option | Description | Selected |
|--------|-------------|----------|
| 8 homes | One per active agent | |
| 10 homes | Keep current count | |
| You decide | Claude picks based on space | ✓ |

**Homes:** Claude's discretion (at least 8)

| Option | Description | Selected |
|--------|-------------|----------|
| Central road style | Main road, commercial along it, homes outskirts | ✓ |
| Town square style | Central open area, buildings in ring | |
| You decide | | |

**Layout:** Central road style

---

## Building Interiors

| Option | Description | Selected |
|--------|-------------|----------|
| Adapt closest tiles | Use generic furniture for specialized buildings | |
| Source new assets | User finds additional tilesets for stock exchange, wedding hall | ✓ |
| Mix both | Adapt what works, flag gaps | |

**Asset approach:** Source new assets for specialized buildings

| Option | Description | Selected |
|--------|-------------|----------|
| Reference-level | Every room has furniture, decorations, floor patterns | ✓ |
| Functional minimum | Floor, walls, 2-3 furniture items | |
| You decide | | |

**Detail level:** Reference-level

---

## Tiled Layer Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Object layers | Rectangles with name properties for zones | ✓ |
| Tile properties | Dedicated tile layers with per-tile properties | |
| You decide | | |

**Metadata encoding:** Object layers (faster to author, easier to extract, standard Tiled approach)

**Spawn points:** Yes, in Tiled as point objects on a Spawn Points layer
**Visual layers:** Match reference (10 layers)

---

## Backend Sync Script

**Extraction scope:** All four options selected — tile grid + sectors, building metadata, spawn points, frontend map copy
**Language:** Python (runs offline, consistent with existing scripts)

---

## Map Authoring Workflow

| Option | Description | Selected |
|--------|-------------|----------|
| Claude generates TMJ | Programmatic generation, no Tiled editor | |
| Manual in Tiled editor | User designs, full visual control | ✓ |
| Hybrid | Claude generates base, user refines | |

**Authoring:** Manual in Tiled editor. Human dependency on critical path.

---

## Reachability Validation

| Option | Description | Selected |
|--------|-------------|----------|
| Automated BFS in sync script | Sync script runs BFS, fails on unreachable sectors | |
| Separate validation script | Standalone validate_map.py | ✓ |
| You decide | | |

**Validation:** Separate scripts/validate_map.py

---

## Building Operating Hours

| Option | Description | Selected |
|--------|-------------|----------|
| Stay in buildings.json | Behavioral config separate from spatial data | |
| Move to Tiled properties | Single source of truth for everything building-related | ✓ |
| You decide | | |

**Operating hours:** Move into Tiled as custom object properties

---

## Claude's Discretion

- Number of homes (at least 8)
- Specific building placement within central-road layout
- Path/terrain details
- Agent-to-spawn-point assignment

## Deferred Ideas

None
