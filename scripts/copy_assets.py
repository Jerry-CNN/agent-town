#!/usr/bin/env python3
"""
copy_assets.py — Copy pixel-art assets from the GenerativeAgentsCN reference repo
into the Agent Town frontend public directory.

Usage:
    python3 scripts/copy_assets.py            # Copy all assets
    python3 scripts/copy_assets.py --dry-run  # Preview without copying

Copies:
  - 16 tileset PNGs from reference tilemap/ -> frontend/public/assets/tilemap/
  - 25 agent sprite directories (texture.png + portrait.png) ->
    frontend/public/assets/agents/{name}/

The 8 active Agent Town agents map to English directory names.
The remaining 17 agents are indexed agent_09 through agent_25 (alphabetical
order of their Chinese source directory names).
"""

import shutil
import sys
import argparse
from pathlib import Path

# ── Path configuration ────────────────────────────────────────────────────────

REFERENCE_ROOT = Path.home() / "projects" / "GenerativeAgentsCN" / \
    "generative_agents" / "frontend" / "static" / "assets" / "village"

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
TARGET_TILEMAP = PROJECT_ROOT / "frontend" / "public" / "assets" / "tilemap"
TARGET_AGENTS = PROJECT_ROOT / "frontend" / "public" / "assets" / "agents"

# ── Tileset files to copy (D-02: all 16 CuteRPG tilesets) ───────────────────
# tilemap.json is intentionally excluded — it is Phaser-specific.
# Phase 11 will author a new Tiled map from scratch.

TILESET_FILES = [
    "CuteRPG_Desert_B.png",
    "CuteRPG_Desert_C.png",
    "CuteRPG_Field_B.png",
    "CuteRPG_Field_C.png",
    "CuteRPG_Forest_B.png",
    "CuteRPG_Forest_C.png",
    "CuteRPG_Harbor_C.png",
    "CuteRPG_Mountains_B.png",
    "CuteRPG_Village_B.png",
    "Room_Builder_32x32.png",
    "blocks_1.png",
    "interiors_pt1.png",
    "interiors_pt2.png",
    "interiors_pt3.png",
    "interiors_pt4.png",
    "interiors_pt5.png",
]

# ── Agent name mapping (D-01) ─────────────────────────────────────────────────
# Chinese source directory -> English target directory name
# The 8 active Agent Town agents use descriptive English names.
ACTIVE_AGENT_MAP = {
    "海莉": "alice",
    "约翰": "bob",
    "玛丽亚": "carla",
    "亚当": "david",
    "简": "emma",
    "卡洛斯": "frank",
    "阿比盖尔": "grace",
    "乔治": "henry",
}

# The 17 remaining agents are indexed agent_09 through agent_25.
# Indexed in alphabetical order of their Chinese source directory names.
# Sorted Chinese names (all 25), alphabetical:
#   01. 乔治     (-> henry, active)
#   02. 亚当     (-> david, active)
#   03. 亚瑟     -> agent_09
#   04. 伊莎贝拉  -> agent_10
#   05. 克劳斯   -> agent_11
#   06. 卡洛斯   (-> frank, active)
#   07. 卡门     -> agent_12
#   08. 埃迪     -> agent_13
#   09. 塔玛拉   -> agent_14
#   10. 山姆     -> agent_15
#   11. 山本百合子 -> agent_16
#   12. 弗朗西斯科 -> agent_17
#   13. 拉吉夫   -> agent_18
#   14. 拉托亚   -> agent_19
#   15. 梅       -> agent_20
#   16. 汤姆     -> agent_21
#   17. 沃尔夫冈  -> agent_22
#   18. 海莉     (-> alice, active)
#   19. 玛丽亚   (-> carla, active)
#   20. 瑞恩     -> agent_23
#   21. 简       (-> emma, active)
#   22. 约翰     (-> bob, active)
#   23. 詹妮弗   -> agent_24
#   24. 阿伊莎   -> agent_25
#   25. 阿比盖尔  (-> grace, active)
INDEXED_AGENT_MAP = {
    "亚瑟": "agent_09",
    "伊莎贝拉": "agent_10",
    "克劳斯": "agent_11",
    "卡门": "agent_12",
    "埃迪": "agent_13",
    "塔玛拉": "agent_14",
    "山姆": "agent_15",
    "山本百合子": "agent_16",
    "弗朗西斯科": "agent_17",
    "拉吉夫": "agent_18",
    "拉托亚": "agent_19",
    "梅": "agent_20",
    "汤姆": "agent_21",
    "沃尔夫冈": "agent_22",
    "瑞恩": "agent_23",
    "詹妮弗": "agent_24",
    "阿伊莎": "agent_25",
}

# Combined mapping: all 25 Chinese source names -> English target names
ALL_AGENT_MAP = {**ACTIVE_AGENT_MAP, **INDEXED_AGENT_MAP}

# Agent sprite files to copy from each source directory
AGENT_FILES = ["texture.png", "portrait.png"]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Copy pixel-art assets from GenerativeAgentsCN reference repo."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be copied without actually copying.",
    )
    return parser.parse_args()


def copy_tilesets(dry_run: bool) -> tuple[int, list[str]]:
    """Copy all 16 tileset PNGs. Returns (count_copied, missing_files)."""
    src_dir = REFERENCE_ROOT / "tilemap"
    copied = 0
    missing = []

    for filename in TILESET_FILES:
        src = src_dir / filename
        dst = TARGET_TILEMAP / filename

        if not src.exists():
            missing.append(str(src))
            print(f"  MISSING: {src}")
            continue

        if dry_run:
            print(f"  [dry-run] Would copy: {src} -> {dst}")
        else:
            TARGET_TILEMAP.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"  Copied: {filename}")
        copied += 1

    return copied, missing


def copy_agents(dry_run: bool) -> tuple[int, int, list[str]]:
    """Copy all 25 agent sprite directories. Returns (dir_count, file_count, missing)."""
    src_root = REFERENCE_ROOT / "agents"
    dirs_copied = 0
    files_copied = 0
    missing = []

    for chinese_name, english_name in sorted(ALL_AGENT_MAP.items()):
        src_dir = src_root / chinese_name
        dst_dir = TARGET_AGENTS / english_name

        agent_missing = []
        for filename in AGENT_FILES:
            src = src_dir / filename
            if not src.exists():
                agent_missing.append(str(src))
                missing.append(str(src))

        if agent_missing:
            print(f"  MISSING files for {chinese_name} ({english_name}): {agent_missing}")
            continue

        if dry_run:
            for filename in AGENT_FILES:
                src = src_dir / filename
                dst = dst_dir / filename
                print(f"  [dry-run] Would copy: {src} -> {dst}")
        else:
            dst_dir.mkdir(parents=True, exist_ok=True)
            for filename in AGENT_FILES:
                src = src_dir / filename
                dst = dst_dir / filename
                shutil.copy2(src, dst)
                files_copied += 1
            print(f"  Copied agent: {chinese_name} -> {english_name}/")

        dirs_copied += 1

    return dirs_copied, files_copied, missing


def main():
    args = parse_args()
    dry_run = args.dry_run

    if dry_run:
        print("DRY RUN — no files will be copied\n")

    print(f"Source: {REFERENCE_ROOT}")
    print(f"Target tilemap: {TARGET_TILEMAP}")
    print(f"Target agents:  {TARGET_AGENTS}\n")

    # ── Tilesets ──────────────────────────────────────────────────────────────
    print("=== Copying tilesets ===")
    tileset_count, tileset_missing = copy_tilesets(dry_run)
    print()

    # ── Agents ────────────────────────────────────────────────────────────────
    print("=== Copying agent sprites ===")
    agent_dirs, agent_files, agent_missing = copy_agents(dry_run)
    print()

    # ── Summary ───────────────────────────────────────────────────────────────
    all_missing = tileset_missing + agent_missing
    if dry_run:
        print(f"[dry-run] Would copy: {tileset_count} tileset files, "
              f"{agent_dirs} agent directories ({agent_files if not dry_run else agent_dirs * 2} files total)")
    else:
        print(f"Copied {tileset_count} tileset files, "
              f"{agent_dirs} agent directories ({agent_files} files total)")

    if all_missing:
        print(f"\nERROR: {len(all_missing)} source file(s) missing:")
        for f in all_missing:
            print(f"  - {f}")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
