# Phase 8: Visual & Building Behavior - Research

**Researched:** 2026-04-10
**Domain:** PixiJS v8 rendering, BFS collision data, LLM prompt engineering (operating hours), simulation time tracking
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Building walls rendered as 3-4px dark stroke outlines around each sector's bounding box using PixiJS v8 `g.stroke()` after `g.fill()`. Uses existing TileMap.tsx draw pattern.
- **D-02:** Claude decides the exact stroke color and width for best contrast against sector fill colors.
- **D-03:** `map_generator.py` auto-generates wall collision tiles as the outer perimeter ring of each sector bounding box. Each building gets 1-2 designated doorway gaps (non-collision tiles on the perimeter) for entry/exit.
- **D-04:** Doorway placement is automatic — one gap per sector placed at the tile closest to the nearest road/path tile.
- **D-05:** Agent labels get semi-transparent dark background pills (rounded rect) behind white text. Always readable regardless of underlying map color.
- **D-06:** Font sizes increased: agent name 20px, activity text 16px, initial letter 16px. Sector labels increased to 28px.
- **D-07:** Activity text truncated with ellipsis if longer than ~25 characters on the map label. Full text visible in inspector panel.
- **D-08:** When an agent's LLM decide call fires, the list of available destinations in the prompt context excludes closed buildings. The agent never sees closed buildings as options.
- **D-09:** If an agent is inside a building when it closes, the agent immediately interrupts its current activity and triggers a new decide call to pick an open destination.
- **D-10:** Simulation time is tracked (hour of day) and compared against each Building's `opens`/`closes` fields to determine open/closed status.

### Claude's Discretion

- Exact stroke colors per sector (darker shade of fill color recommended)
- Doorway gap width (1 or 2 tiles)
- Background pill opacity and corner radius
- Whether sector labels also get background pills
- Simulation time advancement rate (e.g., 1 tick = 10 sim-minutes)

### Deferred Ideas (OUT OF SCOPE)

- **Full pixel-art tileset rendering** — Stardew Valley style via pixi-tiledmap + Tiled editor. Separate milestone (v1.3) after v1.1 completes.
- **Dynamic text scaling** — font size adjusts with zoom level. Nice-to-have but not Phase 8 scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BLD-02 | Buildings have wall tiles marked as collision so agents cannot walk through them | Map generator already generates perimeter collision tiles. No new tile generation needed. Cross-validation test must be re-run after any `town.json` update. |
| BLD-03 | Agents respect building operating hours when choosing destinations (closed buildings excluded from LLM context; agent re-decides from open options) | Requires simulation time tracking on `SimulationEngine` + `buildings` dict loaded in engine + filter in `decide_action()` prompt + ejection logic in `_agent_step()`. All integration points identified. |
| VIS-01 | Building walls are rendered as visible outlines on the map | PixiJS v8 `g.setStrokeStyle()` + `g.stroke()` after `g.fill()` in `TileMap.tsx` `drawMap` callback. Pre-computed `SECTOR_BOUNDS` already available. One-line addition per sector loop iteration. |
| VIS-02 | Agent name and activity text is readable at default zoom level | Font size increases (name 20px, activity 16px, letter 16px, sector labels 28px) + background pill in `AgentSprite.tsx`. Background pill requires drawing a PixiJS Graphics rounded rect behind text nodes. |
</phase_requirements>

---

## Summary

Phase 8 adds visual clarity (wall outlines, readable labels) and behavioral correctness (operating hours enforcement) to the existing simulation. It is a focused, low-risk improvement phase — all four changes build on already-working infrastructure rather than introducing new external dependencies.

The most important discovery from code analysis: **building perimeter collision tiles already exist in `town.json`**. `map_generator.py` calls `_add_building()` which marks the outer perimeter ring as `collision=True` for every sector. The current codebase has 1,216 collision tiles of which 68 are just the cafe perimeter. This means BLD-02 (wall collision) is already satisfied in the map data. The remaining work for BLD-02 is confirming that BFS respects them (it does — Pitfall 4 analysis shows the cross-validation test already verifies no agent spawns on a collision tile) and then adding the visual stroke (VIS-01) to show users that walls are there.

The operating hours system (BLD-03) requires the most new code: simulation time tracking on `SimulationEngine`, filtering closed sectors from the `decide_action()` prompt, and ejecting agents whose building closes while they are inside. The `Building` dataclass with `opens`/`closes` fields is already complete in `world.py`, and `buildings.json` is already fully populated with 16 sectors.

**Primary recommendation:** Execute in four independent sub-tasks: (1) VIS-01 wall stroke rendering, (2) VIS-02 text readability, (3) simulation time tracking + BLD-03 decide filter, (4) BLD-03 agent ejection. Sub-tasks 1 and 2 have zero backend dependencies. Sub-tasks 3 and 4 are pure Python with no LLM calls in the new code.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PixiJS | 8.x (installed) | Wall stroke, label pills rendering | `g.setStrokeStyle()` + `g.stroke()` is the canonical v8 Graphics pattern. Already used in project. |
| @pixi/react | 8.x (installed) | React-PixiJS JSX bridge | Already installed and used. `pixiGraphics draw={callback}` pattern for map layer. |
| Python dataclasses | stdlib | `Building` class holds `opens/closes` | Already implemented in `world.py`. No new imports needed. |
| asyncio | stdlib | `sim_time` tracking via tick loop | SimulationEngine already has asyncio event loop and `_tick_count`. |

No new libraries are needed for this phase. All required functionality is available through existing installed packages.

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pixi.js `TextStyle` | 8.x | Font size and color control | Existing LABEL_STYLE in TileMap.tsx — update fontSize to 28. AgentSprite.tsx text styles — increase fontSize values. |
| pixi.js `Graphics` | 8.x | Background pill behind text | Draw rounded rect before rendering Text nodes in AgentSprite. |

**Installation:** No new packages required.

---

## Architecture Patterns

### Recommended Project Structure

No new files or directories needed. Changes touch only:

```
backend/
├── simulation/
│   ├── engine.py          # Add: sim_time tracking, building hours check, agent ejection
│   └── world.py           # Already has Building class — no changes
├── data/map/
│   └── buildings.json     # Already has opens/closes — no changes
└── agents/cognition/
    └── decide.py          # Add: open_locations filter parameter
frontend/src/components/
├── TileMap.tsx             # Add: stroke after fill, sector label font size 28
└── AgentSprite.tsx         # Add: background pill Graphics, increase font sizes
```

### Pattern 1: PixiJS v8 Stroke After Fill (Wall Outlines)

**What:** After drawing each sector's filled rectangle, call `g.setStrokeStyle()` and `g.stroke()` to render a border outline using the same bounds.

**When to use:** Any time a PixiJS Graphics shape needs both a fill and an outline. The PixiJS v8 Graphics API separates fill and stroke into distinct calls — `g.fill()` and `g.stroke()` can both be called on the same shape definition.

**Example (source: PixiJS v8 official docs + FEATURES.md):**
```typescript
// Source: FEATURES.md "PixiJS Wall Rendering" section (codebase)
// Pattern: setFillStyle → rect → fill → setStrokeStyle → stroke
// Note: the rect() call does NOT need to be repeated — stroke applies
// to the last drawn shape.

// In TileMap.tsx drawMap callback, inside the SECTOR_BOUNDS loop:
for (const bounds of SECTOR_BOUNDS) {
  // 1. Filled background (existing code)
  g.setFillStyle({ color: bounds.color });
  g.rect(bounds.x, bounds.y, bounds.width, bounds.height);
  g.fill();

  // 2. Stroke outline (new code — D-01, D-02)
  // Stroke width 3px, darker shade of sector color
  g.setStrokeStyle({ color: darkenColor(bounds.color, 0.35), width: 3 });
  g.rect(bounds.x, bounds.y, bounds.width, bounds.height);
  g.stroke();
}
```

**darkenColor utility** (pure math, no library needed):
```typescript
// Source: FEATURES.md wall rendering section
function darkenColor(hex: number, factor: number): number {
  const r = Math.floor(((hex >> 16) & 0xff) * (1 - factor));
  const g = Math.floor(((hex >> 8) & 0xff) * (1 - factor));
  const b = Math.floor((hex & 0xff) * (1 - factor));
  return (r << 16) | (g << 8) | b;
}
```

**CRITICAL:** Keep the `useCallback` deps array as `[]`. `darkenColor` is a pure function called inline — no new external references. The stroke data comes from the same module-level `SECTOR_BOUNDS` constant. See Pitfall 5 (PITFALLS.md) for why adding Zustand subscriptions to this deps array causes full-map redraws on every tick.

### Pattern 2: PixiJS Background Pill Behind Text (VIS-02)

**What:** Draw a semi-transparent dark rounded rectangle behind agent name/activity text labels so they are readable on any background color.

**When to use:** Any PixiJS label that appears over a colored background with unpredictable contrast.

**Example (adapted from PixiJS v8 Graphics API):**
```typescript
// Source: [ASSUMED] — PixiJS v8 Graphics API pattern, not verified via Context7
// In AgentSprite.tsx, inside the pixiContainer children:

// Background pill for activity text (above circle)
// Draw as a Graphics component, sized to text bounds
// Approximate pill: width ~text_length*8px, height ~20px, alpha 0.6, dark bg
const drawActivityPill = useCallback((g: PixiGraphics) => {
  g.clear();
  g.setFillStyle({ color: 0x222222, alpha: 0.65 });
  // Centered on x=0 (anchor 0.5), positioned at y=-28 to y=-10
  g.roundRect(-60, -22, 120, 14, 4);
  g.fill();
}, []);

// Render order matters: pill first, then text on top
<pixiGraphics draw={drawActivityPill} />
<pixiText ref={activityTextRef} ... style={{ fill: 0xffffff, fontSize: 16 }} />
```

**Dynamic pill width:** The pill width should match the text length. Since text changes imperatively via `activityTextRef.current.text = newActivity`, the pill width cannot be dynamic without re-measuring. Recommended approach: use a fixed-width pill wide enough for the 25-char truncated text at 16px (approximately 140px wide). This avoids requiring a Graphics redraw on every text update.

### Pattern 3: Simulation Time Tracking (BLD-03)

**What:** Track simulation hour of day on `SimulationEngine` by incrementing a `_sim_hour` counter at a configurable rate per tick.

**When to use:** Any feature that needs to know what time it is in the simulation world (operating hours, daily schedule alignment, future time-of-day events).

**Example:**
```python
# Source: [ASSUMED] — standard pattern for simulated time, not from external docs
# In SimulationEngine.__init__:
self._sim_hour: int = 7  # simulation starts at 7am
self._sim_minute: int = 0
self._ticks_per_sim_hour: int = 6  # 1 sim-hour = 6 ticks (at 30s/tick = 3 min real time per sim-hour)

# In _tick_loop, after all agent steps complete:
self._sim_minute += 10  # 10 sim-minutes per tick
if self._sim_minute >= 60:
    self._sim_minute = 0
    self._sim_hour = (self._sim_hour + 1) % 24
```

**Sim-time advancement rate (Claude's discretion):** With `TICK_INTERVAL = 30` seconds, 1 tick = 10 sim-minutes gives a 24-hour sim day in 72 real minutes. This is a reasonable default — buildings like the stock exchange (open 9-17) close after ~24 real minutes of simulation time. Adjustable via `_ticks_per_sim_minute` constant if needed.

**is_open() helper on Building:**
```python
# Add to world.py Building dataclass
def is_open(self, sim_hour: int) -> bool:
    """Return True if the building is open at the given simulation hour."""
    if self.closes == 24:
        return True  # 24-hour venue (park, homes)
    if self.opens < self.closes:
        return self.opens <= sim_hour < self.closes
    # Handles midnight wrap-around (e.g., opens=22, closes=4)
    return sim_hour >= self.opens or sim_hour < self.closes
```

### Pattern 4: Operating Hours Filter in decide_action (BLD-03)

**What:** Before calling `action_decide_prompt`, filter `known_locations` to exclude sectors whose corresponding building is currently closed.

**When to use:** Every `decide_action()` call in the engine tick.

**Example:**
```python
# Source: [ASSUMED] — standard filtering pattern
# In engine._agent_step(), before calling decide_action():
open_locations = [
    loc for loc in _extract_known_locations(config.spatial.tree)
    if self._is_location_open(loc)
]
# Then pass open_locations instead of known_locations to decide_action

def _is_location_open(self, sector: str) -> bool:
    """Return True if sector has no Building entry (unknown = open) or is currently open."""
    building = self._buildings.get(sector)
    if building is None:
        return True  # sectors without operating hours data are always accessible
    return building.is_open(self._sim_hour)
```

**CRITICAL:** Load `self._buildings` from `load_buildings()` in `SimulationEngine.__init__()`, not lazily per tick. `load_buildings()` reads from disk — calling it per agent per tick would add 8×N disk reads per tick.

### Pattern 5: Agent Ejection on Building Close (BLD-03, D-09)

**What:** Every tick, check if any agent's current position is inside a building that just closed. If so, interrupt the current activity and trigger a decide call.

**When to use:** In the tick loop, after `_sim_hour` advances, before running agent steps.

**Example:**
```python
# Source: [ASSUMED]
# In SimulationEngine._tick_loop(), after sim_hour increments:
if hour_changed:
    await self._eject_agents_from_closed_buildings()

async def _eject_agents_from_closed_buildings(self) -> None:
    for name, agent in self._agents.items():
        tile = self.maze.tile_at(agent.coord)
        if len(tile.address) < 2:
            continue  # road tile, not in a building
        sector = tile.address[1]  # e.g., "stock-exchange"
        building = self._buildings.get(sector)
        if building and not building.is_open(self._sim_hour):
            # Clear path so agent re-decides next tick
            agent.path = []
            agent.current_activity = "leaving (building closed)"
            await self._emit_agent_update(name, agent)
            logger.info("%s ejected from closed %s", name, sector)
```

**Implementation note:** The ejection does not need to fire an LLM decide call immediately. Clearing `agent.path = []` is sufficient — on the next tick, `_agent_step()` will call `decide_action()` normally because the path is empty. The agent gets a new decide call with the closed building already filtered from `open_locations`.

### Anti-Patterns to Avoid

- **Adding Zustand state for wall tile data:** Wall tile positions are static — never route them through the store. Pre-compute at module load (see Pitfall 5 in PITFALLS.md).
- **Calling `load_buildings()` per agent per tick:** This reads `buildings.json` from disk. Load once in `__init__`.
- **Redrawing Graphics for pill width on every text change:** Activity text changes every tick. The pill draw callback must use a fixed width, not measure text length, to avoid triggering a Graphics redraw per frame.
- **Blocking the tick loop for ejection LLM calls:** Ejection is path-clear + activity-string update only. No LLM call at ejection time — the LLM call happens naturally on the next tick via the standard `decide_action()` flow.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Darken a hex color | Color math from scratch | Simple bit-shift arithmetic | RGB channels are independent — 2 lines of math per channel, no library needed |
| Rounded rect for pill | Manual curve approximation | `g.roundRect(x, y, w, h, radius)` | PixiJS v8 Graphics has `roundRect()` built in [VERIFIED: PITFALLS.md PixiJS v8 Graphics API reference] |
| Background pill width matching text | Re-measure text each frame | Fixed-width pill for max expected chars | Text measurement in PixiJS requires `text.width` which accesses the renderer — safe only in useTick, not in draw callbacks |
| Is-open time logic | Custom calendar math | Simple hour comparison on Building | The `is_open()` helper is 5 lines. All buildings in this simulation use simple 0-24 ranges — midnight wrap-around is the only edge case. |

**Key insight:** Every "utility" in this phase is 2-5 lines of Python or TypeScript. No utility library additions are needed.

---

## Runtime State Inventory

> Phase 8 is not a rename/refactor/migration phase. However, sim_time is new runtime state introduced in this phase.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | ChromaDB memories contain no building hours references | None — no migration needed |
| Live service config | None — buildings.json and town.json are static files | None |
| OS-registered state | None | None |
| Secrets/env vars | None | None |
| Build artifacts | `town.json` — collision tiles already generated by map_generator.py (1216 collision tiles verified) | No regeneration needed; existing file is correct |

**sim_time is in-memory only** (new field `_sim_hour` on SimulationEngine). It resets to 7 on every server restart. This is acceptable for v1.1 — sim time does not need to persist across restarts (users will observe the simulation advancing from 7am each session).

---

## Common Pitfalls

### Pitfall 1: wall stroke triggers drawMap re-execution on every tick (from PITFALLS.md, Pitfall 5)

**What goes wrong:** If wall/stroke data is referenced from a Zustand store subscription inside `drawMap`, adding that subscription to the `useCallback` deps array causes the entire map (3200x3200px) to be redrawn on every WebSocket tick (every 500ms). Canvas flickers and FPS drops.

**Why it happens:** Developers route stroke color/width config through a store alongside dynamic agent state, then subscribe to it in the draw callback.

**How to avoid:** Stroke parameters are constants — compute `SECTOR_STROKE_COLORS` from `SECTOR_COLORS` at module load time using `darkenColor()`. Pass into `drawMap` via module-level constant, not via props or store. Keep deps array `[]`.

**Warning signs:** React DevTools Profiler shows `drawMap` running more than once.

---

### Pitfall 2: Agent spawns inside a building perimeter after any town.json regeneration (from PITFALLS.md, Pitfall 4)

**What goes wrong:** Building perimeter collision tiles already exist in `town.json` (verified: 68 tiles for the cafe alone). Agent spawn coordinates are in separate `agents/*.json` config files. If `town.json` is regenerated with different sector bounds, agent spawn coordinates may land on new collision tiles. The agent's BFS returns `[]` every tick — the agent freezes silently.

**Why it happens:** Map coordinates and agent coordinates are defined in separate files with no runtime cross-check at startup.

**How to avoid:** Re-run `pytest tests/test_cross_validation.py` after every `town.json` regeneration. Test 2 (`test_all_agent_coords_on_walkable_tiles`) is the key guard — it explicitly checks `maze.tile_at(agent.coord).is_walkable`. This test currently passes (17 passed, 0 failed as of this research).

**Warning signs:** Agent visible at spawn but never moves; BFS returns `[]` for that agent.

---

### Pitfall 3: Background pill width is too narrow for 25-char truncated text

**What goes wrong:** The activity text label is truncated to 25 characters (`MAX_ACTIVITY_LEN = 30` in current code, decision D-07 sets target at 25). If the pill background is sized for a shorter text, the text overflows visually — light-colored text on a light map tile is unreadable at the right edge.

**Why it happens:** Pill width was set based on estimated character width for one sample text, not the worst-case 25-character string.

**How to avoid:** At 16px font, the widest 25 characters (capital W, M characters) can be approximately 16px × 0.7 ≈ 11.2px each, so 25 chars ≈ 280px max. Use a pill width of 180px for typical text (covers most activities) with the ellipsis already in place. If exact fit is needed, measure `activityTextRef.current.width` once after the first text assignment in `useEffect`, then update the pill Graphics. Do not re-measure on every frame.

---

### Pitfall 4: Simulation time tracks real seconds instead of simulation hours, making buildings close too slowly or instantly

**What goes wrong:** If `_sim_hour` is derived directly from `time.time()` / 3600 (real hours since epoch), the simulation starts at the current real-world hour and advances in real time — a building that closes at 17:00 stays closed until 5pm real time, making testing impossible and behavior unpredictable for users in different timezones.

**Why it happens:** Using real time is simpler to implement than maintaining a separate sim-clock, and initial implementations often take this shortcut.

**How to avoid:** Maintain `_sim_hour` and `_sim_minute` as integer fields on `SimulationEngine`. Increment by a fixed amount per tick (e.g., 10 sim-minutes per tick). Start at 7 (7:00am) on every `initialize()`. This gives full control over simulation pacing and makes behavior testable without waiting for real-world hours.

---

### Pitfall 5: Ejection fires every tick for closed buildings, not just on the hour boundary

**What goes wrong:** If `_eject_agents_from_closed_buildings()` is called on every tick (not just when `_sim_hour` changes), and the ejection logic clears `agent.path = []`, agents near a closed building are ejected and re-routed every tick, never settling into a new destination. The `decide_action()` fires every tick for those agents, tripling LLM call count.

**Why it happens:** The tick loop calls `_eject_agents_from_closed_buildings()` unconditionally at the start of each tick, even though building hours only change on whole-hour boundaries.

**How to avoid:** Track `_last_ejection_check_hour: int = -1` on `SimulationEngine`. Only run ejection when `_sim_hour != _last_ejection_check_hour`. Update `_last_ejection_check_hour = _sim_hour` after running the check.

---

## Code Examples

### VIS-01: Stroke after fill in TileMap.tsx (complete modified sector loop)

```typescript
// Source: PixiJS v8 Graphics API — setStrokeStyle/stroke is the v8 pattern
// In the drawMap callback, replaces the existing sector zone loop:
for (const bounds of SECTOR_BOUNDS) {
  // Floor fill (existing)
  g.setFillStyle({ color: bounds.color });
  g.rect(bounds.x, bounds.y, bounds.width, bounds.height);
  g.fill();

  // Wall stroke outline (new — VIS-01)
  g.setStrokeStyle({ color: darkenColor(bounds.color, 0.35), width: 3 });
  g.rect(bounds.x, bounds.y, bounds.width, bounds.height);
  g.stroke();
}
```

### VIS-02: Sector label font size (TileMap.tsx)

```typescript
// Source: existing TileMap.tsx LABEL_STYLE — increase fontSize to 28 (D-06)
const LABEL_STYLE = new TextStyle({
  fontFamily: "Inter, system-ui, sans-serif",
  fontSize: 28,   // was 13
  fontWeight: "700",
  fill: 0x222222,
  align: "center",
  stroke: { color: 0xffffff, width: 3 },  // white halo improves readability on all backgrounds
});
```

### VIS-02: Agent name/activity font sizes and pill (AgentSprite.tsx)

```typescript
// Source: existing AgentSprite.tsx — update all fontSize values
// Agent name: 20px (was 10)
// Activity: 16px (was 9)
// Initial letter: 16px (was 12)

// New stable pill draw callback for activity text:
const drawActivityPill = useCallback((g: PixiGraphics) => {
  g.clear();
  g.setFillStyle({ color: 0x111111, alpha: 0.65 });
  g.roundRect(-90, -24, 180, 18, 5);
  g.fill();
}, []);

// New stable pill draw callback for name text:
const drawNamePill = useCallback((g: PixiGraphics) => {
  g.clear();
  g.setFillStyle({ color: 0x111111, alpha: 0.65 });
  g.roundRect(-60, 14, 120, 18, 5);
  g.fill();
}, []);
```

### BLD-03: is_open() helper in world.py

```python
# Add to Building dataclass in world.py
def is_open(self, sim_hour: int) -> bool:
    """Return True if the building is open at the given simulation hour.

    Supports wrap-around hours (e.g., opens=22, closes=4).
    24-hour venues (closes=24) are always open.
    """
    if self.closes == 24:
        return True
    if self.opens <= self.closes:
        return self.opens <= sim_hour < self.closes
    # Wrap-around: e.g., bar open 22-04
    return sim_hour >= self.opens or sim_hour < self.closes
```

### BLD-03: Filter in engine._agent_step() (decide call site)

```python
# Source: [ASSUMED] — integration of Building.is_open() into existing decide_action call
# In engine.py _agent_step(), replace the existing decide_action call:

# Filter known locations to open-only (D-08)
all_locations = _extract_known_locations_from_spatial(config.spatial.tree)
open_locations = [
    loc for loc in all_locations
    if self._is_location_open(loc)
]

action = await decide_action(
    simulation_id=self.simulation_id,
    agent_name=agent_name,
    agent_scratch=config.scratch,
    agent_spatial=config.spatial,
    current_activity=agent.current_activity,
    perception=perception,
    current_schedule=agent.schedule,
    open_locations=open_locations,   # new parameter
)
```

Note: `decide_action()` and `action_decide_prompt()` need a new `open_locations` parameter. The existing `_extract_known_locations(spatial_tree)` in `decide.py` is replaced by the pre-filtered list from the engine. Alternatively, pass `open_locations` as an override — see Open Questions.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PixiJS v7 `g.lineStyle(width, color)` | PixiJS v8 `g.setStrokeStyle({ color, width })` + `g.stroke()` | v8 launch (2024) | Old API removed in v8 — use new pattern only |
| `g.drawRect()` | `g.rect()` + `g.fill()` | v8 launch (2024) | Old API removed in v8 |
| `g.drawRoundedRect()` | `g.roundRect()` + `g.fill()` | v8 launch (2024) | Old API removed in v8 |

**Deprecated/outdated:**
- PixiJS v7 Graphics API (`lineStyle`, `drawRect`, `beginFill`): Removed in v8. All existing TileMap.tsx and AgentSprite.tsx code already uses v8 API — no migration needed.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Background pill draw callback using `useCallback` with no deps is stable and does not cause re-renders | Architecture Patterns, Pattern 2 | Pill re-renders on every frame — FPS drop. Mitigation: verify with React DevTools Profiler after implementation. |
| A2 | Fixed-width pill (180px for activity, 120px for name) covers truncated text at 16px font | Code Examples, VIS-02 | Text overflows pill horizontally. Mitigation: measure `textRef.current.width` in useEffect once and set pill width, or use a wider fixed value (200px). |
| A3 | Simulation time starting at 7 (7am) is appropriate — all public sectors are open at 7am | Architecture Patterns, Pattern 3 | Agent picks a closed destination on first decide call. Mitigation: check earliest `opens` value across buildings.json — earliest is 7am (Cafe opens at 7). Starting at 8am or 9am is safer. |
| A4 | `g.setStrokeStyle().stroke()` can be called after `g.fill()` on the same rect in PixiJS v8 — the rect definition is not consumed by `g.fill()` | Code Examples, VIS-01 | Wall stroke not rendered or wrong shape. Mitigation: verify in isolation with a test render before integrating into full map draw. The PixiJS v8 Graphics API docs confirm this pattern. |
| A5 | `_extract_known_locations(spatial_tree)` is safe to call in engine.py directly (it's currently in decide.py) | Architecture Patterns, Pattern 4 | ImportError if the function is not importable from engine.py. Mitigation: move the function to a shared utility or duplicate the 10-line function in engine.py. |
| A6 | Simulation starts at `_sim_hour = 7` — no agents are initialized inside a closed building | Architecture Patterns, Pattern 3 | Ejection logic fires on first tick for agents inside a building that is not yet open at 7am (e.g., cafe opens at 7 — exact boundary). Mitigation: start at 8 or start ejection checks at tick 2. |

---

## Open Questions

1. **Where should `open_locations` filtering happen — in `engine.py` or in `decide.py`?**
   - What we know: `decide.py` currently calls `_extract_known_locations(agent_spatial.tree)` internally. The engine does not currently override the location list.
   - What's unclear: Adding the filter in `engine.py` and passing `open_locations` as a new parameter to `decide_action()` is cleaner (single source of truth, easier to test). But it requires changing the `decide_action()` signature and the `action_decide_prompt()` signature.
   - Recommendation: Add `open_locations: list[str] | None = None` to `decide_action()`. If provided, use it; if None, fall back to `_extract_known_locations()`. This preserves backward compatibility.

2. **Does `_extract_known_locations()` need to remain in `decide.py` or should it move?**
   - What we know: It is currently a module-private function in `decide.py`. Engine needs the same logic to pre-filter.
   - What's unclear: Importing from `decide.py` in `engine.py` may create undesirable coupling.
   - Recommendation: Move `_extract_known_locations()` to `world.py` or a new `backend/simulation/time_utils.py` file so both `decide.py` and `engine.py` can import it without coupling.

3. **Should sector labels also get background pills (Claude's discretion)?**
   - What we know: Sector labels at 28px are currently dark text on sector fill colors — good contrast on pastel backgrounds but poor on the road background (warm gray) at label edges.
   - What's unclear: Whether the label ever renders over the road background (depends on sector size vs. label width).
   - Recommendation: Add a white text stroke (halo) to sector labels (`stroke: { color: 0xffffff, width: 3 }`) instead of a pill. This is simpler than adding a Graphics layer for each of the 16 sector labels.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | asyncio.TaskGroup, dataclass syntax | Yes | 3.14 (detected via .venv) | — |
| PixiJS v8 Graphics API | VIS-01 stroke rendering | Yes | 8.x (installed in frontend) | — |
| @pixi/react v8 | pixiGraphics/pixiText JSX | Yes | 8.x (installed) | — |
| pytest + pytest-asyncio | Backend unit tests | Yes | Installed (.venv confirmed) | — |
| vitest | Frontend unit tests | Yes | v4.1.4 (confirmed via test run) | — |

No missing dependencies. Current test suites pass: 17 backend tests pass, 40 frontend tests pass.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Backend framework | pytest 9.x + pytest-asyncio 1.3 |
| Backend config | `pyproject.toml` `[tool.pytest.ini_options]`, testpaths=["tests"] |
| Frontend framework | Vitest 4.1.4 |
| Frontend config | `frontend/vitest.config.ts` |
| Quick backend run | `cd /path/to/agent-town && .venv/bin/python -m pytest tests/ -x -q` |
| Full backend suite | `.venv/bin/python -m pytest tests/ -v` |
| Quick frontend run | `npm run test --prefix frontend` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BLD-02 | Agent spawn coords are on walkable tiles after wall generation | integration | `.venv/bin/python -m pytest tests/test_cross_validation.py -x -q` | Yes (test_all_agent_coords_on_walkable_tiles) |
| BLD-02 | All agents on connected walkable subgraph (no isolated clusters) | integration | `.venv/bin/python -m pytest tests/test_cross_validation.py::test_all_agents_on_connected_graph -x -q` | Yes |
| BLD-03 | Building.is_open() returns correct bool for given hour | unit | `.venv/bin/python -m pytest tests/test_building.py -x -q` | Partial — test_building.py exists but has no is_open() test yet. Wave 0 gap. |
| BLD-03 | Closed buildings excluded from open_locations list | unit | `.venv/bin/python -m pytest tests/test_operating_hours.py -x -q` | No — Wave 0 gap |
| BLD-03 | Agent ejection when building closes mid-simulation | unit | `.venv/bin/python -m pytest tests/test_operating_hours.py::test_agent_ejected_on_close -x -q` | No — Wave 0 gap |
| VIS-01 | Wall stroke is drawn in drawMap callback (no deps array change) | manual-only | React DevTools Profiler: drawMap renders once | N/A — visual verification |
| VIS-02 | Font sizes match D-06 spec (20px name, 16px activity, 28px sector) | manual-only | Visual inspection at default zoom | N/A — visual verification |

### Sampling Rate
- **Per task commit:** `.venv/bin/python -m pytest tests/ -x -q` (backend) + `npm run test --prefix frontend` (frontend)
- **Per wave merge:** Full suite — both backends and frontend
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_operating_hours.py` — covers BLD-03: `Building.is_open()` for various hours, open_locations filter, ejection behavior. Needs mock `SimulationEngine` with controlled `_sim_hour`.
- [ ] Add `test_is_open_midnight_wrap` to `tests/test_building.py` — edge case where `opens > closes` (e.g., a future venue open 22-04).

*(Existing `tests/test_cross_validation.py` already covers BLD-02 walkability — no new file needed for that requirement.)*

---

## Security Domain

No authentication, session management, or access control is involved in Phase 8. The changes are:
- Frontend rendering (no user input processed)
- Backend in-memory state update (`_sim_hour` integer)
- LLM prompt filtering (reduces prompt size — no expansion of attack surface)

**V5 Input Validation:** The `sim_hour` value is derived from an internal counter, not from user input. No validation boundary needed. The `open_locations` list is derived from `buildings.json` (a controlled static file) and `agent_spatial.tree` (LLM-populated but filtered to known keys). No injection risk.

---

## Sources

### Primary (HIGH confidence)
- `/Users/sainobekou/projects/agent-town/frontend/src/components/TileMap.tsx` — verified existing drawMap pattern, sector loop, deps array, SECTOR_BOUNDS structure
- `/Users/sainobekou/projects/agent-town/frontend/src/components/AgentSprite.tsx` — verified current font sizes (10px name, 9px activity, 12px letter), draw callback pattern, useCallback([color]) pattern
- `/Users/sainobekou/projects/agent-town/frontend/src/components/MapCanvas.tsx` — verified auto-scale approach and container structure
- `/Users/sainobekou/projects/agent-town/backend/simulation/world.py` — verified Building dataclass fields (name, sector, opens, closes, purpose), load_buildings() function
- `/Users/sainobekou/projects/agent-town/backend/simulation/map_generator.py` — verified `_add_building()` generates perimeter collision tiles + doorway gaps
- `/Users/sainobekou/projects/agent-town/backend/simulation/engine.py` — verified `_tick_count` field, `_agents` dict, `_agent_step()` control flow, inject_event pattern
- `/Users/sainobekou/projects/agent-town/backend/agents/cognition/decide.py` — verified `_extract_known_locations()`, `decide_action()` signature, prompt call site
- `/Users/sainobekou/projects/agent-town/backend/prompts/action_decide.py` — verified `known_locations` parameter flows into LLM prompt
- `/Users/sainobekou/projects/agent-town/backend/data/map/buildings.json` — verified 16 sectors with opens/closes values; cafe opens=7, stock-exchange opens=9, closes=17
- `/Users/sainobekou/projects/agent-town/.planning/research/PITFALLS.md` — verified Pitfall 4 (collision tile spawn), Pitfall 5 (drawMap re-render), Integration Gotchas table
- `/Users/sainobekou/projects/agent-town/.planning/research/FEATURES.md` — verified PixiJS v8 stroke pattern (`g.setStrokeStyle({ color, width })`), wall rendering approach, darkenColor utility concept
- Map tile count verification via Python runtime: 4845 total tiles, 1216 collision tiles, 68 cafe perimeter tiles. All 17 backend tests pass, all 40 frontend tests pass.

### Secondary (MEDIUM confidence)
- `CLAUDE.md` stack table — PixiJS 8.17+, @pixi/react 8+, confirmed as installed stack
- `CONTEXT.md` decisions D-01 through D-10 — locked user decisions, copied verbatim

### Tertiary (LOW confidence)
- [ASSUMED] PixiJS v8 `g.roundRect()` accepts `(x, y, w, h, radius)` signature — verified as part of the v8 Graphics API in PITFALLS.md source citation but not confirmed via Context7 in this session
- [ASSUMED] Simulation time starting at hour 7 (7am) — inferred from `schedule_init.py` `wake_hour` range (ge=4, le=11), not from explicit project documentation

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified installed and in use
- Architecture patterns: HIGH for PixiJS stroke (codebase evidence + FEATURES.md), MEDIUM for sim-time tracking (standard pattern, not externally verified)
- Pitfalls: HIGH — directly sourced from codebase analysis and existing PITFALLS.md
- Operating hours behavior: HIGH — Building class fully implemented, integration points clearly identified

**Research date:** 2026-04-10
**Valid until:** 2026-05-10 (PixiJS v8 API is stable; Python stdlib patterns are stable)
