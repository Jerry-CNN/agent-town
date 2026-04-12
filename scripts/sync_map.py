#!/usr/bin/env python3
"""
sync_map.py — Convert a Tiled TMJ export into backend/frontend JSON files.

Usage:
    python3 scripts/sync_map.py --tmj frontend/public/assets/tilemap/town.tmj
    python3 scripts/sync_map.py --dry-run

Produces:
  - backend/data/map/town.json         (Maze config: world, size, tile_address_keys, tiles)
  - backend/data/map/buildings.json    (Building list with display_name, opens, closes, purpose)
  - backend/data/map/spawn_points.json (Agent name -> [tile_x, tile_y])
  - frontend/src/data/town.json        (Same content as backend town.json, for frontend access)

Also updates backend/data/agents/{name}.json coord field for each matched spawn point.

Per D-10: script lives in scripts/ following copy_assets.py pattern.
Per D-11: buildings.json generated from Tiled custom properties, not hand-maintained.
Per Pitfall 3: size field is [height, width].
Per Pitfall 8: collision processed first; addresses skip collision tiles.
"""

import argparse
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TILE_SIZE = 32

WORLD_NAME = "agent-town"

# Metadata object layer names — all must be present and type="objectgroup"
REQUIRED_METADATA_LAYERS = ["Sectors", "Arenas", "Collision", "Spawn Points"]

# Tile address hierarchy
TILE_ADDRESS_KEYS = ["world", "sector", "arena"]

# Script / project root
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

DEFAULT_TMJ_PATH = PROJECT_ROOT / "frontend" / "public" / "assets" / "tilemap" / "town.tmj"
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _obj_to_tile_bounds(obj: dict) -> tuple[int, int, int, int]:
    """Convert a Tiled pixel-space object to tile bounds (x1, y1, x2, y2).

    Tiled stores coords as floats in some exports (Pitfall 2).
    Always int() before // to avoid float tile indices.

    Returns:
        (x1, y1, x2, y2) in tile coordinates where x2/y2 are exclusive.
    """
    x1 = int(obj["x"]) // TILE_SIZE
    y1 = int(obj["y"]) // TILE_SIZE
    x2 = (int(obj["x"]) + int(obj["width"])) // TILE_SIZE
    y2 = (int(obj["y"]) + int(obj["height"])) // TILE_SIZE
    return x1, y1, x2, y2


def _get_property(obj: dict, name: str, default=None):
    """Get a named custom property value from a Tiled object's properties array."""
    for prop in obj.get("properties", []):
        if prop.get("name") == name:
            return prop.get("value", default)
    return default


def _get_layers_by_name(tmj: dict) -> dict:
    """Build {layer_name: layer} mapping from tmj['layers'].

    Validates that all required metadata layers exist and have type 'objectgroup'.
    Raises ValueError with a descriptive message on any violation (Pitfall 4 / T-11-02).
    """
    layers = {layer["name"]: layer for layer in tmj.get("layers", [])}

    for required in REQUIRED_METADATA_LAYERS:
        if required not in layers:
            raise ValueError(
                f"Required metadata layer '{required}' is missing from the TMJ file. "
                f"Found layers: {list(layers.keys())}"
            )
        layer_type = layers[required].get("type")
        if layer_type != "objectgroup":
            raise ValueError(
                f"Metadata layer '{required}' must have type 'objectgroup', "
                f"but found type '{layer_type}'. "
                f"Ensure this layer is an Object Layer in Tiled, not a Tile Layer."
            )

    return layers


# ---------------------------------------------------------------------------
# Public extraction functions
# ---------------------------------------------------------------------------


def extract_map(tmj: dict) -> dict:
    """Convert a Tiled TMJ dict into a town.json-compatible dict.

    Processing order (per Pitfall 8 / must_haves):
      1. Mark collision rectangle tiles as {collision: True}
      2. Assign sector addresses to non-collision tiles
      3. Assign arena addresses to non-collision tiles
         (arena name must contain exactly one ':' separator — Pitfall 5)

    Size field is [height, width] per Pitfall 3 / Maze.__init__ expectation.

    Args:
        tmj: Parsed Tiled TMJ JSON dict.

    Returns:
        town.json-compatible dict with keys: world, tile_size, size,
        tile_address_keys, tiles.

    Raises:
        ValueError: Missing/wrong-type metadata layers, or invalid arena name.
    """
    layers = _get_layers_by_name(tmj)

    # Map dimensions (in tiles)
    width: int = tmj["width"]
    height: int = tmj["height"]

    # Sparse tile registry: (x, y) -> tile_dict
    # Only tiles that have addresses or collision are stored (sparse format).
    tiles: dict[tuple[int, int], dict] = {}

    # ---- Step 1: Collision rectangles (processed first) --------------------
    for obj in layers["Collision"].get("objects", []):
        x1, y1, x2, y2 = _obj_to_tile_bounds(obj)
        for ty in range(y1, y2):
            for tx in range(x1, x2):
                tiles[(tx, ty)] = {"coord": [tx, ty], "collision": True}

    # ---- Step 2: Sector addresses (skip collision tiles) -------------------
    for obj in layers["Sectors"].get("objects", []):
        sector_name: str = obj["name"]
        x1, y1, x2, y2 = _obj_to_tile_bounds(obj)
        for ty in range(y1, y2):
            for tx in range(x1, x2):
                if (tx, ty) in tiles and tiles[(tx, ty)].get("collision"):
                    continue  # collision has priority
                existing = tiles.get((tx, ty), {})
                existing["coord"] = [tx, ty]
                existing["address"] = [sector_name]
                tiles[(tx, ty)] = existing

    # ---- Step 3: Arena addresses (skip collision tiles) --------------------
    for obj in layers["Arenas"].get("objects", []):
        arena_full_name: str = obj["name"]
        # Validate exactly one colon separator (Pitfall 5)
        parts = arena_full_name.split(":")
        if len(parts) != 2:
            raise ValueError(
                f"Arena name '{arena_full_name}' must contain exactly one colon "
                f"separator (format: 'sector:arena'). Got {len(parts) - 1} colons."
            )
        sector_name, arena_name = parts[0], parts[1]
        x1, y1, x2, y2 = _obj_to_tile_bounds(obj)
        for ty in range(y1, y2):
            for tx in range(x1, x2):
                if (tx, ty) in tiles and tiles[(tx, ty)].get("collision"):
                    continue  # collision has priority
                existing = tiles.get((tx, ty), {})
                existing["coord"] = [tx, ty]
                existing["address"] = [sector_name, arena_name]
                tiles[(tx, ty)] = existing

    # ---- Assemble output ---------------------------------------------------
    tiles_list = sorted(tiles.values(), key=lambda t: (t["coord"][1], t["coord"][0]))

    return {
        "world": WORLD_NAME,
        "tile_size": tmj.get("tilewidth", TILE_SIZE),
        # size is [height, width] — CRITICAL: height first (Pitfall 3)
        "size": [height, width],
        "tile_address_keys": TILE_ADDRESS_KEYS,
        "tiles": tiles_list,
    }


def extract_buildings(sector_objects: list) -> list[dict]:
    """Extract buildings.json from a list of Tiled Sectors layer objects.

    Each entry has exactly the keys required by the Building dataclass:
        name (display_name or obj name), sector (obj name),
        opens (int), closes (int), purpose (str).

    Missing custom properties receive defaults: opens=0, closes=24, purpose="general".

    Args:
        sector_objects: List of Tiled object dicts from the Sectors layer.

    Returns:
        List of building dicts compatible with buildings.json schema.
    """
    buildings = []
    for obj in sector_objects:
        sector_key = obj["name"]
        display_name = _get_property(obj, "display_name", default=sector_key)
        opens = int(_get_property(obj, "opens", default=0))
        closes = int(_get_property(obj, "closes", default=24))
        purpose = _get_property(obj, "purpose", default="general")
        buildings.append(
            {
                "name": display_name,
                "sector": sector_key,
                "opens": opens,
                "closes": closes,
                "purpose": purpose,
            }
        )
    return buildings


def extract_spawn_points(spawn_objects: list) -> dict[str, list[int]]:
    """Extract spawn points from a list of Tiled Spawn Points layer objects.

    Converts pixel coordinates to tile coordinates (divide by TILE_SIZE).
    Handles float coordinates from Tiled exports (Pitfall 2).

    Args:
        spawn_objects: List of Tiled point object dicts from the Spawn Points layer.

    Returns:
        Dict mapping agent_name -> [tile_x, tile_y].
    """
    spawn_points: dict[str, list[int]] = {}
    for obj in spawn_objects:
        agent_name = obj["name"]
        tile_x = int(obj["x"]) // TILE_SIZE
        tile_y = int(obj["y"]) // TILE_SIZE
        spawn_points[agent_name] = [tile_x, tile_y]
    return spawn_points


# ---------------------------------------------------------------------------
# main — CLI entry point
# ---------------------------------------------------------------------------


def main(
    tmj_path: Path = DEFAULT_TMJ_PATH,
    backend_dir: Path = BACKEND_DIR,
    frontend_dir: Path = FRONTEND_DIR,
    dry_run: bool = False,
) -> None:
    """Parse a Tiled TMJ file and write output JSON files.

    In --dry-run mode, parses and validates the TMJ and prints a summary
    (sectors found, buildings, spawn points, warnings) but does NOT write
    any output files or modify agent JSONs.

    Args:
        tmj_path:    Path to the Tiled TMJ export.
        backend_dir: Project backend root (contains data/map/ and data/agents/).
        frontend_dir: Project frontend root (contains src/data/).
        dry_run:     If True, validate only — no file writes.
    """
    # --- Load and parse TMJ (T-11-01: wrap in try/except) ---
    try:
        with open(tmj_path) as f:
            tmj = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: TMJ file not found: {tmj_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(f"ERROR: TMJ file is not valid JSON: {exc}", file=sys.stderr)
        sys.exit(1)

    # Validate required keys
    for key in ("width", "height", "layers"):
        if key not in tmj:
            print(f"ERROR: TMJ file missing required key '{key}'", file=sys.stderr)
            sys.exit(1)

    # --- Extract layers ---
    try:
        layers = _get_layers_by_name(tmj)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    # --- Extract data ---
    try:
        town_json = extract_map(tmj)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    sector_objects = layers["Sectors"].get("objects", [])
    spawn_objects = layers["Spawn Points"].get("objects", [])

    buildings = extract_buildings(sector_objects)
    spawn_points = extract_spawn_points(spawn_objects)

    # --- Summary printout ---
    print(f"TMJ: {tmj_path}")
    print(f"Map size: {tmj['width']}w x {tmj['height']}h tiles")
    print(f"Sectors found ({len(sector_objects)}): {[o['name'] for o in sector_objects]}")
    print(f"Buildings generated: {len(buildings)}")
    print(f"Spawn points: {list(spawn_points.keys())}")

    collision_tiles = [t for t in town_json["tiles"] if t.get("collision")]
    print(f"Collision tiles: {len(collision_tiles)}")

    if dry_run:
        print("\nDRY RUN — no files written.")
        return

    # --- Write output files ---
    backend_map_dir = Path(backend_dir) / "data" / "map"
    backend_agents_dir = Path(backend_dir) / "data" / "agents"
    frontend_data_dir = Path(frontend_dir) / "src" / "data"

    # backend/data/map/town.json
    town_path = backend_map_dir / "town.json"
    town_path.parent.mkdir(parents=True, exist_ok=True)
    with open(town_path, "w") as f:
        json.dump(town_json, f, indent=2)
    print(f"Wrote: {town_path}")

    # backend/data/map/buildings.json
    buildings_path = backend_map_dir / "buildings.json"
    with open(buildings_path, "w") as f:
        json.dump(buildings, f, indent=2)
    print(f"Wrote: {buildings_path}")

    # backend/data/map/spawn_points.json
    spawn_path = backend_map_dir / "spawn_points.json"
    with open(spawn_path, "w") as f:
        json.dump(spawn_points, f, indent=2)
    print(f"Wrote: {spawn_path}")

    # frontend/src/data/town.json (same content as backend town.json)
    frontend_town_path = frontend_data_dir / "town.json"
    frontend_town_path.parent.mkdir(parents=True, exist_ok=True)
    with open(frontend_town_path, "w") as f:
        json.dump(town_json, f, indent=2)
    print(f"Wrote: {frontend_town_path}")

    # Update agent coord fields in backend/data/agents/{name}.json
    agents_updated = []
    agents_dir = Path(backend_agents_dir)
    if agents_dir.exists():
        for agent_name, tile_coord in spawn_points.items():
            agent_path = agents_dir / f"{agent_name}.json"
            if agent_path.exists():
                with open(agent_path) as f:
                    agent_data = json.load(f)
                agent_data["coord"] = tile_coord
                with open(agent_path, "w") as f:
                    json.dump(agent_data, f, indent=2)
                agents_updated.append(agent_name)

    if agents_updated:
        print(f"Updated agent coords: {agents_updated}")

    print("\nSync complete.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert a Tiled TMJ export into Agent Town backend/frontend JSON files."
    )
    parser.add_argument(
        "--tmj",
        type=Path,
        default=DEFAULT_TMJ_PATH,
        help=f"Path to Tiled TMJ export (default: {DEFAULT_TMJ_PATH})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and validate only; do not write output files.",
    )
    args = parser.parse_args()
    main(tmj_path=args.tmj, dry_run=args.dry_run)
