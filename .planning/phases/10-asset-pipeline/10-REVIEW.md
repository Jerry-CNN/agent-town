---
phase: 10-asset-pipeline
reviewed: 2026-04-11T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - frontend/index.html
  - frontend/src/components/MapCanvas.tsx
  - frontend/public/assets/agents/sprite.json
  - scripts/convert_sprite_atlas.py
  - scripts/copy_assets.py
findings:
  critical: 0
  warning: 4
  info: 4
  total: 8
status: issues_found
---

# Phase 10: Code Review Report

**Reviewed:** 2026-04-11T00:00:00Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Five files were reviewed covering the asset pipeline scripts and the core map canvas component. `frontend/index.html` is clean. The two Python scripts (`convert_sprite_atlas.py`, `copy_assets.py`) share the same structural problem: hard-coded absolute paths that tie the scripts to a single developer machine. `MapCanvas.tsx` has a React/ref cursor update bug and stale documentation. The `sprite.json` atlas contains duplicate frame coordinates that produce a silent bad walk animation.

No security vulnerabilities or data-loss risks were found.

---

## Warnings

### WR-01: Hard-coded absolute path breaks on any machine except the author's (`convert_sprite_atlas.py`)

**File:** `scripts/convert_sprite_atlas.py:45-56`
**Issue:** `SOURCE_PATH` is constructed from `Path.home() / "projects" / "GenerativeAgentsCN" / ...`. This path is valid only on the original developer's machine. Running the script on any CI runner, collaborator machine, or different home directory silently resolves to a non-existent path and the script exits with `ERROR: Source file not found` rather than being portable or configurable.
**Fix:** Accept the source path as a required CLI argument, or add an `--source` flag alongside `--output`. Fall back to the hard-coded default only when the argument is absent (and document the assumption prominently):

```python
parser.add_argument(
    "--source",
    type=Path,
    default=SOURCE_PATH,
    help="Path to the Phaser sprite.json source file "
         "(default: ~/projects/GenerativeAgentsCN/.../sprite.json)",
)
```

Then pass `args.source` to `convert()` instead of the module-level constant.

---

### WR-02: Hard-coded absolute path breaks on any machine except the author's (`copy_assets.py`)

**File:** `scripts/copy_assets.py:27-28`
**Issue:** `REFERENCE_ROOT` is constructed from `Path.home() / "projects" / "GenerativeAgentsCN" / ...`. Same portability problem as WR-01. This script is more impactful because it copies 16 tileset PNGs and 25 agent directories — a complete asset setup step that cannot run in CI without the author's exact filesystem layout.
**Fix:** Add a `--source` / `--reference` CLI argument with the hard-coded path as the default:

```python
parser.add_argument(
    "--reference",
    type=Path,
    default=REFERENCE_ROOT,
    help="Path to GenerativeAgentsCN reference repo's village/ assets directory.",
)
```

Pass `args.reference` through to `copy_tilesets()` and `copy_agents()`.

---

### WR-03: `isPanning.current` ref read in JSX style prop never triggers re-render (`MapCanvas.tsx`)

**File:** `frontend/src/components/MapCanvas.tsx:92`
**Issue:** The inline style `cursor: isPanning.current ? "grabbing" : "grab"` reads a `useRef` value. React does not re-render when a ref value changes, so the cursor style is computed once at mount and frozen — the cursor never visually changes to `"grabbing"` during a drag, defeating its purpose.

```tsx
// This expression is only evaluated at render time.
// isPanning.current mutations inside pointer handlers do NOT cause re-renders.
style={{ cursor: isPanning.current ? "grabbing" : "grab" }}
```

**Fix:** Promote panning state to `useState` so the cursor updates reactively:

```tsx
const [isPanning, setIsPanning] = useState(false);
// ...
const onPointerDown = useCallback((e: React.PointerEvent) => {
  setIsPanning(true);
  panStart.current = { x: e.clientX, y: e.clientY };
  offsetStart.current = { x: offsetX, y: offsetY };
  (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
}, [offsetX, offsetY]);

const onPointerUp = useCallback(() => {
  setIsPanning(false);
}, []);
// ...
style={{ cursor: isPanning ? "grabbing" : "grab" }}
```

Keep only the `panStart` and `offsetStart` mutable values as refs.

---

### WR-04: Walk animation frame `.003` is a duplicate of frame `.001` in every direction (`sprite.json`)

**File:** `frontend/public/assets/agents/sprite.json:39-49` (and matching blocks at lines 99-109, 159-169, 219-229)
**Issue:** For all four directions, the `.003` frame has identical `x`/`y` coordinates to the `.001` frame:

```json
"down-walk.001": { "frame": { "x": 32, "y": 0, ... } },
"down-walk.003": { "frame": { "x": 32, "y": 0, ... } }  // same pixel region
```

The walk cycle is therefore 0 → 1 → 2 → 1 (ping-pong), not 0 → 1 → 2 → 3 (four distinct frames). If the source atlas actually has a fourth distinct frame at x=96 this is a conversion error. If the ping-pong pattern is intentional (a valid 3-frame cycle expressed as 4 entries), that should be documented and the `convert_sprite_atlas.py` validation should explicitly confirm the duplicate is expected rather than treating it as a silent data property.

**Fix (if fourth frame exists in source):** Verify the source atlas columns. The texture is 96px wide × 128px tall with 32px tiles, yielding exactly 3 columns (x=0, 32, 64). There is no column at x=96, so the ping-pong pattern is the only possibility given the current texture. Document this explicitly in `sprite.json` meta or in a comment in `convert_sprite_atlas.py` so future maintainers do not mistake it for a bug.

---

## Info

### IN-01: File docstring claims mouse-wheel zoom is supported — feature is absent (`MapCanvas.tsx`)

**File:** `frontend/src/components/MapCanvas.tsx:5`
**Issue:** The component docstring states "Supports mouse-wheel zoom and click-drag pan for map navigation." No `onWheel` handler exists anywhere in the file. The zoom is fixed at `FIXED_SCALE = 0.45` and cannot be changed by the user.
**Fix:** Either remove the zoom claim from the docstring, or add a `// TODO: wheel zoom deferred` comment referencing the relevant roadmap item. Stale documentation misleads future contributors.

---

### IN-02: `validate()` hard-codes frame count 20 as a magic number (`convert_sprite_atlas.py`)

**File:** `scripts/convert_sprite_atlas.py:158`
**Issue:** `if len(frames) != 20:` is correct for the current atlas (16 walk frames + 4 idle = 20) but gives no indication of where 20 comes from. If any direction gains a fifth frame, the validator fails with an opaque message.
**Fix:** Derive the expected count from constants at the top of the file rather than using a bare literal:

```python
EXPECTED_DIRECTIONS = len(ANIMATION_DIRECTIONS)          # 4
EXPECTED_WALK_FRAMES_PER_DIRECTION = 4
EXPECTED_IDLE_FRAMES = EXPECTED_DIRECTIONS               # one per direction
EXPECTED_TOTAL_FRAMES = (
    EXPECTED_DIRECTIONS * EXPECTED_WALK_FRAMES_PER_DIRECTION
    + EXPECTED_IDLE_FRAMES
)  # = 20

# In validate():
if len(frames) != EXPECTED_TOTAL_FRAMES:
    errors.append(f"Expected {EXPECTED_TOTAL_FRAMES} frames, got {len(frames)}")
```

---

### IN-03: No exception handling around `json.load()` for the source file (`convert_sprite_atlas.py`)

**File:** `scripts/convert_sprite_atlas.py:93-94`
**Issue:** If the source `sprite.json` is malformed JSON, `json.load()` raises `json.JSONDecodeError` with a Python traceback rather than a clean error message. The script already handles the "file not found" case gracefully (line 194); malformed JSON deserves the same treatment.
**Fix:**

```python
try:
    phaser_data = json.load(f)
except json.JSONDecodeError as exc:
    print(f"ERROR: Source file is not valid JSON: {exc}", file=sys.stderr)
    sys.exit(1)
```

Also add a `KeyError` guard around `phaser_data["frames"]` at line 96 since a valid-JSON but structurally wrong file will produce an equally unhelpful traceback.

---

### IN-04: Dry-run summary file count expression is logically inverted and confusing (`copy_assets.py`)

**File:** `scripts/copy_assets.py:231`
**Issue:** The expression `agent_files if not dry_run else agent_dirs * 2` reads backwards. During dry-run `agent_files` is 0 (no files were copied), so the condition falls to `agent_dirs * 2`. During a real run the condition evaluates `agent_files` (the actual count). The intent is correct but the condition is inverted relative to natural reading order (`if not dry_run` means "if this is NOT a dry run, show actual count").
**Fix:** Swap the operands and rename the guard for clarity:

```python
estimated_or_actual = agent_files if not dry_run else agent_dirs * 2
print(f"[dry-run] Would copy: {tileset_count} tileset files, "
      f"{agent_dirs} agent directories (~{estimated_or_actual} files total)")
```

Or simply print the two messages unconditionally and keep them consistent:

```python
if dry_run:
    print(f"[dry-run] Would copy: {tileset_count} tileset files, "
          f"{agent_dirs} agent directories (~{agent_dirs * 2} files estimated)")
else:
    print(f"Copied {tileset_count} tileset files, "
          f"{agent_dirs} agent directories ({agent_files} files total)")
```

---

_Reviewed: 2026-04-11T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
