#!/usr/bin/env python3
"""
convert_sprite_atlas.py — Convert Phaser JSONArray sprite atlas to PixiJS ISpritesheetData format.

Usage:
    python3 scripts/convert_sprite_atlas.py                          # Write to default output path
    python3 scripts/convert_sprite_atlas.py --output path/to/out.json  # Write to custom path

Source format (Phaser JSONArray):
    {
      "frames": [
        { "filename": "down-walk.000", "frame": { "w": 32, "h": 32, "x": 0, "y": 0 }, ... },
        ...
      ],
      "meta": { ... }
    }

Target format (PixiJS ISpritesheetData):
    {
      "frames": {
        "down-walk.000": { "frame": { "x": 0, "y": 0, "w": 32, "h": 32 }, "sourceSize": { "w": 32, "h": 32 } },
        ...
      },
      "animations": {
        "down-walk": ["down-walk.000", "down-walk.001", "down-walk.002", "down-walk.003"],
        ...
      },
      "meta": {
        "image": "texture.png",
        "format": "RGBA8888",
        "size": { "w": 96, "h": 128 },
        "scale": 1
      }
    }
"""

import json
import sys
import argparse
import re
from pathlib import Path

# ── Path configuration ────────────────────────────────────────────────────────

SOURCE_PATH = (
    Path.home()
    / "projects"
    / "GenerativeAgentsCN"
    / "generative_agents"
    / "frontend"
    / "static"
    / "assets"
    / "village"
    / "agents"
    / "sprite.json"
)

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_OUTPUT = PROJECT_ROOT / "frontend" / "public" / "assets" / "agents" / "sprite.json"

# PixiJS meta constants for the shared sprite sheet
META_IMAGE = "texture.png"
META_FORMAT = "RGBA8888"
META_SIZE = {"w": 96, "h": 128}
META_SCALE = 1

# Animation directions matched from frame filenames
ANIMATION_DIRECTIONS = ["down", "left", "right", "up"]

# Pattern: direction-walk.NNN (e.g. down-walk.000)
WALK_FRAME_PATTERN = re.compile(r"^([a-z]+)-walk\.(\d{3})$")

# Pattern: direction idle (e.g. "down", "left", "right", "up")
IDLE_FRAME_PATTERN = re.compile(r"^([a-z]+)$")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert Phaser sprite atlas JSON to PixiJS ISpritesheetData format."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output path for sprite.json (default: {DEFAULT_OUTPUT})",
    )
    return parser.parse_args()


def convert(source_path: Path) -> dict:
    """Read Phaser JSONArray sprite atlas and return PixiJS ISpritesheetData dict."""
    with open(source_path, "r", encoding="utf-8") as f:
        phaser_data = json.load(f)

    phaser_frames = phaser_data["frames"]

    # ── Convert frames: array -> dict ──────────────────────────────────────
    # Phaser frame entry: { "filename": "...", "frame": { "w", "h", "x", "y" }, "anchor": {...} }
    # PixiJS frame entry: { "frame": { "x", "y", "w", "h" }, "sourceSize": { "w", "h" } }
    pixi_frames = {}
    for entry in phaser_frames:
        filename = entry["filename"]
        src_frame = entry["frame"]
        pixi_frames[filename] = {
            "frame": {
                "x": src_frame["x"],
                "y": src_frame["y"],
                "w": src_frame["w"],
                "h": src_frame["h"],
            },
            "sourceSize": {
                "w": src_frame["w"],
                "h": src_frame["h"],
            },
        }

    # ── Build animations: group walk frames by direction ──────────────────
    # Walk frames follow the pattern: {direction}-walk.{NNN}
    # We collect all matching frame names, group by direction, sort by frame number.
    walk_frames: dict[str, list[tuple[int, str]]] = {}
    for filename in pixi_frames:
        match = WALK_FRAME_PATTERN.match(filename)
        if match:
            direction = match.group(1)
            frame_num = int(match.group(2))
            walk_frames.setdefault(direction, []).append((frame_num, filename))

    animations = {}
    for direction in ANIMATION_DIRECTIONS:
        if direction in walk_frames:
            sorted_frames = sorted(walk_frames[direction], key=lambda t: t[0])
            animations[f"{direction}-walk"] = [name for _, name in sorted_frames]

    # ── Build meta ────────────────────────────────────────────────────────
    meta = {
        "image": META_IMAGE,
        "format": META_FORMAT,
        "size": META_SIZE,
        "scale": META_SCALE,
    }

    return {
        "frames": pixi_frames,
        "animations": animations,
        "meta": meta,
    }


def validate(data: dict) -> list[str]:
    """Validate the converted data. Returns list of error strings (empty = valid)."""
    errors = []

    frames = data.get("frames", {})
    if not isinstance(frames, dict):
        errors.append(f"frames must be dict, got {type(frames).__name__}")
    else:
        if len(frames) != 20:
            errors.append(f"Expected 20 frames, got {len(frames)}")
        if "down-walk.000" not in frames:
            errors.append("Missing required frame: down-walk.000")
        if "down" not in frames:
            errors.append("Missing required idle frame: down")
        if "up" not in frames:
            errors.append("Missing required idle frame: up")

    animations = data.get("animations", {})
    expected_anims = {"down-walk", "left-walk", "right-walk", "up-walk"}
    actual_anims = set(animations.keys())
    if actual_anims != expected_anims:
        errors.append(f"Wrong animation keys. Expected {expected_anims}, got {actual_anims}")
    for anim_name, frame_list in animations.items():
        if len(frame_list) != 4:
            errors.append(f"Animation {anim_name} has {len(frame_list)} frames, expected 4")

    meta = data.get("meta", {})
    if meta.get("image") != META_IMAGE:
        errors.append(f"meta.image must be '{META_IMAGE}', got '{meta.get('image')}'")
    if meta.get("size") != META_SIZE:
        errors.append(f"meta.size must be {META_SIZE}, got {meta.get('size')}")
    if meta.get("scale") != META_SCALE:
        errors.append(f"meta.scale must be {META_SCALE}, got {meta.get('scale')}")
    if meta.get("format") != META_FORMAT:
        errors.append(f"meta.format must be '{META_FORMAT}', got '{meta.get('format')}'")

    return errors


def main():
    args = parse_args()
    output_path = args.output

    if not SOURCE_PATH.exists():
        print(f"ERROR: Source file not found: {SOURCE_PATH}", file=sys.stderr)
        sys.exit(1)

    print(f"Reading source: {SOURCE_PATH}")
    pixi_data = convert(SOURCE_PATH)

    # Validate before writing
    errors = validate(pixi_data)
    if errors:
        print("ERROR: Validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(pixi_data, f, indent=2)
        f.write("\n")  # trailing newline

    print(f"Written: {output_path}")
    print(f"  frames: {len(pixi_data['frames'])} keys (dict format)")
    print(f"  animations: {list(pixi_data['animations'].keys())}")
    print(f"  meta.image: {pixi_data['meta']['image']}")
    print(f"  meta.size: {pixi_data['meta']['size']}")
    sys.exit(0)


if __name__ == "__main__":
    main()
