---
phase: "10"
plan: "01"
subsystem: asset-pipeline
tags: [assets, tilemap, sprites, pixijs, python-scripts]
dependency_graph:
  requires: []
  provides:
    - "16 CuteRPG tileset PNGs in frontend/public/assets/tilemap/"
    - "25 agent sprite directories (texture.png + portrait.png) in frontend/public/assets/agents/"
    - "PixiJS ISpritesheetData sprite.json in frontend/public/assets/agents/"
    - "scripts/copy_assets.py — reusable idempotent asset copy script"
    - "scripts/convert_sprite_atlas.py — Phaser-to-PixiJS atlas conversion script"
  affects:
    - "Phase 11 (map design) — depends on tileset PNGs being in place"
    - "Phase 12 (tile rendering) — depends on tileset PNGs for PixiJS texture loading"
    - "Phase 13 (animated sprites) — depends on sprite.json and agent texture.png files"
tech_stack:
  added: []
  patterns:
    - "Phaser JSONArray to PixiJS ISpritesheetData frame dict conversion"
    - "Chinese-to-English agent name mapping (8 active + 17 indexed)"
    - "shutil.copy2 for asset pipeline scripts"
key_files:
  created:
    - scripts/copy_assets.py
    - scripts/convert_sprite_atlas.py
    - frontend/public/assets/agents/sprite.json
    - frontend/public/assets/tilemap/ (16 PNG files)
    - frontend/public/assets/agents/ (25 directories x 2 files)
  modified: []
decisions:
  - "8 active agents get English names (alice/bob/carla/david/emma/frank/grace/henry); 17 inactive get agent_09..agent_25 to avoid URL encoding issues with Chinese characters"
  - "tilemap.json excluded from copy — it is Phaser-specific; Phase 11 will author a new Tiled map"
  - "sprite.json meta.image set to 'texture.png' (relative path) so PixiJS resolves it relative to JSON URL"
metrics:
  duration_minutes: 15
  completed_date: "2026-04-12"
  tasks_completed: 2
  tasks_total: 2
  files_created: 69
  files_modified: 0
---

# Phase 10 Plan 01: Asset Pipeline Summary

**One-liner:** Port all 16 CuteRPG tileset PNGs and 25 agent sprite sheets from the GenerativeAgentsCN reference repo, and convert the Phaser JSONArray sprite atlas to PixiJS ISpritesheetData format via reusable Python scripts.

## What Was Built

**Task 1 — Copy tilesets and agent sprites**

Created `scripts/copy_assets.py` using stdlib only (`shutil`, `pathlib`). The script:
- Copies 16 CuteRPG tileset PNGs to `frontend/public/assets/tilemap/`
- Copies 25 agent sprite directories (texture.png + portrait.png) to `frontend/public/assets/agents/`
- Maps 8 active Agent Town agents from Chinese source names to English directory names
- Indexes remaining 17 agents as `agent_09`..`agent_25` in alphabetical order of Chinese source names
- Supports `--dry-run` flag, prints a summary, exits 1 on missing source files
- Excludes `tilemap.json` (Phaser-specific; Phase 11 will author a new Tiled map)

**Task 2 — Convert Phaser sprite atlas to PixiJS format**

Created `scripts/convert_sprite_atlas.py` using stdlib only (`json`, `pathlib`, `re`). The script:
- Reads `~/projects/GenerativeAgentsCN/.../agents/sprite.json` (Phaser JSONArray format)
- Converts `frames` from array to dict keyed by filename, normalizing coordinate order to x/y/w/h
- Builds `animations` dict by grouping direction-walk frames (4 frames each: 000-003)
- Sets `meta.image = "texture.png"`, `meta.format = "RGBA8888"`, `meta.size = {w: 96, h: 128}`, `meta.scale = 1`
- Validates output before writing (frame count, animation keys, meta values)
- Writes to `frontend/public/assets/agents/sprite.json` with indent=2

## Commits

| Task | Commit | Files |
|------|--------|-------|
| 1 — Copy assets | 4c9b603 | scripts/copy_assets.py + 66 asset files |
| 2 — Convert atlas | 73360e8 | scripts/convert_sprite_atlas.py + frontend/public/assets/agents/sprite.json |

## Verification Results

All plan verification checks pass:
- `ls frontend/public/assets/tilemap/*.png | wc -l` → 16
- `ls -d frontend/public/assets/agents/*/  | wc -l` → 25
- sprite.json validation: frames dict with 20 keys, 4 animations (4 frames each), meta.image = "texture.png" → PASS
- `python3 scripts/copy_assets.py --dry-run` → exit 0
- `python3 scripts/convert_sprite_atlas.py` → exit 0

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All asset files are real pixel-art graphics from the reference repo. sprite.json is fully generated from the source atlas with no placeholder values.

## Threat Flags

None. Assets are intentionally public pixel-art graphics (no PII, no secrets). All file operations are local filesystem only, from a trusted local reference repo.

## Self-Check: PASSED

Files verified present:
- `scripts/copy_assets.py` — FOUND
- `scripts/convert_sprite_atlas.py` — FOUND
- `frontend/public/assets/agents/sprite.json` — FOUND
- `frontend/public/assets/tilemap/CuteRPG_Field_B.png` — FOUND
- `frontend/public/assets/agents/alice/texture.png` — FOUND

Commits verified present:
- `4c9b603` — FOUND
- `73360e8` — FOUND
