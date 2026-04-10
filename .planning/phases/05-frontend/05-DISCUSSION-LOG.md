# Phase 5: Frontend - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.

**Date:** 2026-04-10
**Phase:** 05-frontend
**Areas discussed:** Map rendering & camera, Agent sprites & movement, Activity feed & inspector, Visual style & polish

---

## Map Rendering & Camera

### Tile Art Style
| Option | Description | Selected |
|--------|-------------|----------|
| Colored rectangles with labels | Simple colored tiles with text overlays. Fast to implement. | ✓ |
| Pixel art tileset | Pre-made sprites. More visually appealing but requires assets. | |
| You decide | | |

### Camera/Scrolling
| Option | Description | Selected |
|--------|-------------|----------|
| Click-drag + scroll zoom | Standard map interaction. Most intuitive. | ✓ |
| Arrow keys + fixed zoom | Keyboard-based. Simpler but less natural. | |
| You decide | | |

---

## Agent Sprites & Movement

### Visual Representation
| Option | Description | Selected |
|--------|-------------|----------|
| Colored circles with initials | Unique color per agent, initial letter inside. | ✓ |
| Simple emoji avatars | Unique emoji per agent. Fun but inconsistent cross-platform. | |
| You decide | | |

### Movement Animation
| Option | Description | Selected |
|--------|-------------|----------|
| Smooth lerp interpolation | Agents slide between tiles over tick interval. Looks alive. | ✓ |
| Instant teleport | Snap to new position. Simpler but jerky. | |
| You decide | | |

---

## Activity Feed & Inspector

### Feed Behavior
| Option | Description | Selected |
|--------|-------------|----------|
| Auto-scrolling log, latest at bottom | Auto-scroll pauses when user scrolls up. | ✓ |
| Reverse chronological | Latest at top. No auto-scroll needed. | |
| You decide | | |

### Inspector Content
| Option | Description | Selected |
|--------|-------------|----------|
| Full profile + recent memories | Name, occupation, traits, activity, location, last 5 memories. | ✓ |
| Minimal: name + activity | Just current state. Less cluttered but incomplete. | |
| You decide | | |

---

## Visual Style & Polish

### Aesthetic
| Option | Description | Selected |
|--------|-------------|----------|
| Clean & minimal with soft colors | Light map, dark sidebar, sans-serif. Professional. | ✓ |
| Retro pixel art feel | Chunky pixels, 8-bit palette. More playful. | |
| You decide | | |

---

## Claude's Discretion
- Color palette, font family, zoom levels, feed density, minimap, label rendering approach

## Deferred Ideas
- Pixel art sprites (v2), speech bubbles (DSP-04), memory timeline (DSP-05), relationship graph (DSP-06), dark mode
