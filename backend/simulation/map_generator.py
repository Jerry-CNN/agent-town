"""Programmatic town map JSON generator for Agent Town.

Generates a 100x100 tile map with all thematic locations in neighbourhood
clusters.  Output is the custom backend format (sparse tile list) used by
the Maze class — NOT the standard Tiled export format (which is a Phase 5
concern).

Design decisions (from 02-RESEARCH.md, 02-CONTEXT.md):
  D-01  100x100 tile grid
  D-02  Thematic locations: stock-exchange, wedding-hall, park, homes,
         shop, cafe, office
  D-03  Neighbourhood cluster arrangement: NW=park, NE=homes (residential 1),
         middle=commercial band, SW=civic, SE=more homes (residential 2)
  D-04  32px tile size
  D-07  Programmatic generation (this file)

Pitfall-prevention:
  Pitfall 3 — coordinate deduplication: Use a dict keyed by (x,y) so the
              same coordinate can only appear once.  Collision entries take
              priority over address entries (last-write wins in priority order
              collision > address > default-walkable).
  Pitfall 4 — empty-sector guard: Post-generation assertion that each required
              sector has at least one walkable tile.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Output path for the generated JSON
_MAP_PATH = Path(__file__).parent.parent / "data" / "map" / "town.json"

# Required sectors must all have ≥1 walkable interior tile after generation
_REQUIRED_SECTORS = [
    "park",
    "cafe",
    "shop",
    "office",
    "stock-exchange",
    "wedding-hall",
    "home-alice",
    "home-bob",
    "home-carla",
    "home-henry",
    "home-isabel",
    "home-david",
    "home-emma",
    "home-frank",
    "home-grace",
    "home-james",
]


# ---------------------------------------------------------------------------
# Low-level tile builder helpers
# ---------------------------------------------------------------------------


def _add_border_walls(tiles: dict[tuple[int, int], dict]) -> None:
    """Mark all 4 border edges of the 100x100 grid as collision."""
    for x in range(100):
        tiles[(x, 0)] = {"coord": [x, 0], "collision": True}
        tiles[(x, 99)] = {"coord": [x, 99], "collision": True}
    for y in range(1, 99):
        tiles[(0, y)] = {"coord": [0, y], "collision": True}
        tiles[(99, y)] = {"coord": [99, y], "collision": True}


def _add_building(
    tiles: dict[tuple[int, int], dict],
    sector: str,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    arenas: list[tuple[str, int, int, int, int]],
    door_wall: str = "south",
    door_x: int | None = None,
    door_y: int | None = None,
) -> None:
    """Add a building: perimeter walls + addressable interior tiles.

    Args:
        tiles:     Tile accumulator dict keyed by (x, y).
        sector:    Sector name (e.g. "cafe").
        x1, y1:   Top-left corner of bounding rect (inclusive).
        x2, y2:   Bottom-right corner of bounding rect (exclusive, Python-slice style).
        arenas:    List of (arena_name, ax1, ay1, ax2, ay2) tuples.
                   Interior tiles not covered by any arena get the sector name
                   without an arena sub-division.
        door_wall: Which wall to cut a 2-tile door into ("north"|"south"|"east"|"west").
        door_x:    X coordinate for the door opening (for north/south walls).
        door_y:    Y coordinate for the door opening (for east/west walls).
    """
    # --- Building perimeter (collision) ------------------------------------
    for x in range(x1, x2):
        tiles[(x, y1)] = {"coord": [x, y1], "collision": True}
        tiles[(x, y2 - 1)] = {"coord": [x, y2 - 1], "collision": True}
    for y in range(y1, y2):
        tiles[(x1, y)] = {"coord": [x1, y], "collision": True}
        tiles[(x2 - 1, y)] = {"coord": [x2 - 1, y], "collision": True}

    # --- Door opening (overwrite perimeter collision with walkable) ---------
    cx = door_x if door_x is not None else (x1 + x2) // 2
    cy = door_y if door_y is not None else (y1 + y2) // 2

    if door_wall == "south":
        # Cut 2-tile door in the bottom wall
        for dx in range(2):
            door_coord = (cx + dx, y2 - 1)
            tiles[door_coord] = {
                "coord": list(door_coord),
                "address": [sector, "foyer"] if sector == "wedding-hall" else [sector, "entrance"],
            }
    elif door_wall == "north":
        for dx in range(2):
            door_coord = (cx + dx, y1)
            tiles[door_coord] = {
                "coord": list(door_coord),
                "address": [sector, "entrance"],
            }
    elif door_wall == "east":
        for dy in range(2):
            door_coord = (x2 - 1, cy + dy)
            tiles[door_coord] = {
                "coord": list(door_coord),
                "address": [sector, "entrance"],
            }
    elif door_wall == "west":
        for dy in range(2):
            door_coord = (x1, cy + dy)
            tiles[door_coord] = {
                "coord": list(door_coord),
                "address": [sector, "entrance"],
            }

    # --- Arena interior tiles ----------------------------------------------
    # Pre-compute which interior coords belong to which arena
    arena_map: dict[tuple[int, int], str] = {}
    for arena_name, ax1, ay1, ax2, ay2 in arenas:
        for y in range(ay1 + 1, ay2):
            for x in range(ax1 + 1, ax2):
                arena_map[(x, y)] = arena_name

    # Fill all interior coords with address entries
    for y in range(y1 + 1, y2 - 1):
        for x in range(x1 + 1, x2 - 1):
            coord = (x, y)
            if coord in tiles and tiles[coord].get("collision"):
                # Don't overwrite collision (e.g. from adjacent building)
                continue
            arena_name = arena_map.get(coord, "main")
            tiles[coord] = {
                "coord": [x, y],
                "address": [sector, arena_name],
            }


def _add_park(tiles: dict[tuple[int, int], dict]) -> None:
    """North-west quadrant: Park (open area, no perimeter walls)."""
    # Park is an open area — no building walls, just addressable tiles
    # Bounds: x=5-35, y=5-28
    zones: list[tuple[str, int, int, int, int]] = [
        ("garden", 5, 5, 26, 19),
        ("bench-area", 5, 19, 26, 28),
        ("pond", 26, 5, 35, 28),
    ]
    for arena_name, ax1, ay1, ax2, ay2 in zones:
        for y in range(ay1, ay2):
            for x in range(ax1, ax2):
                coord = (x, y)
                if coord in tiles and tiles[coord].get("collision"):
                    continue
                tiles[coord] = {
                    "coord": [x, y],
                    "address": ["park", arena_name],
                }


def _add_home(
    tiles: dict[tuple[int, int], dict],
    sector: str,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    has_kitchen: bool = False,
) -> None:
    """Convenience wrapper for residential buildings."""
    mid_y = (y1 + y2) // 2
    if has_kitchen:
        arenas = [
            ("bedroom", x1, y1, x2, mid_y),
            ("living-room", x1, mid_y, x2, y2 - 2),
            ("kitchen", x1, y2 - 3, x2, y2),
        ]
    else:
        arenas = [
            ("bedroom", x1, y1, x2, mid_y),
            ("living-room", x1, mid_y, x2, y2),
        ]
    _add_building(
        tiles, sector, x1, y1, x2, y2,
        arenas=arenas,
        door_wall="south",
        door_x=(x1 + x2) // 2,
    )


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------


def generate_town_map() -> dict[str, Any]:
    """Generate the 100x100 Agent Town map.

    Returns:
        Dict in the custom backend format:
        {
            "world": "agent-town",
            "tile_size": 32,
            "size": [100, 100],
            "tile_address_keys": ["world", "sector", "arena"],
            "tiles": [...]   # sparse list, only non-default tiles
        }

    All border tiles are collision.  Buildings have perimeter walls and
    door openings.  Road/walkway tiles between buildings are anonymous
    walkable (no address, no collision — omitted from the sparse list).
    """
    # Use dict keyed by (x,y) to prevent duplicate coordinates (pitfall 3).
    # Collision entries take priority — once a tile is collision, it stays.
    tiles: dict[tuple[int, int], dict] = {}

    # -----------------------------------------------------------------------
    # 1. Border walls
    # -----------------------------------------------------------------------
    _add_border_walls(tiles)

    # -----------------------------------------------------------------------
    # 2. North-west: Park (y=5-28, x=5-35)
    # -----------------------------------------------------------------------
    _add_park(tiles)

    # -----------------------------------------------------------------------
    # 3. North-east: Residential cluster 1 (y=5-28, x=60-95)
    #    Homes: alice, bob, carla, henry, isabel  (2 rows of homes)
    # -----------------------------------------------------------------------
    # Row 1 of NE homes (y=5–16): alice, bob
    _add_home(tiles, "home-alice", 60, 5, 75, 16, has_kitchen=True)
    _add_home(tiles, "home-bob",  77, 5, 92, 16)

    # Row 2 of NE homes (y=18–28): carla, henry, isabel
    _add_home(tiles, "home-carla",  60, 18, 71, 28)
    _add_home(tiles, "home-henry",  73, 18, 82, 28)
    _add_home(tiles, "home-isabel", 84, 18, 93, 28)

    # -----------------------------------------------------------------------
    # 4. Commercial band (y=35–52, x=5–95)
    #    cafe | shop | office | stock-exchange
    # -----------------------------------------------------------------------
    _add_building(
        tiles, "cafe", 5, 35, 25, 52,
        arenas=[
            ("seating", 5, 35, 20, 44),
            ("counter", 20, 35, 25, 44),
            ("kitchen", 5, 44, 25, 52),
        ],
        door_wall="north",
        door_x=12,
    )
    _add_building(
        tiles, "shop", 27, 35, 47, 52,
        arenas=[
            ("floor", 27, 35, 42, 47),
            ("counter", 42, 35, 47, 47),
            ("stockroom", 27, 47, 47, 52),
        ],
        door_wall="north",
        door_x=34,
    )
    _add_building(
        tiles, "office", 49, 35, 70, 52,
        arenas=[
            ("open-plan", 49, 35, 65, 47),
            ("meeting-room", 65, 35, 70, 52),
        ],
        door_wall="north",
        door_x=55,
    )
    _add_building(
        tiles, "stock-exchange", 72, 35, 95, 52,
        arenas=[
            ("trading-floor", 72, 35, 88, 52),
            ("clerk-desk", 88, 35, 95, 52),
        ],
        door_wall="north",
        door_x=79,
    )

    # -----------------------------------------------------------------------
    # 5. South-west: Civic — Wedding Hall (y=60–82, x=5–45)
    # -----------------------------------------------------------------------
    _add_building(
        tiles, "wedding-hall", 5, 60, 45, 82,
        arenas=[
            ("foyer", 5, 60, 25, 68),
            ("hall", 5, 68, 45, 76),
            ("dressing-room", 25, 60, 45, 68),
        ],
        door_wall="north",
        door_x=22,
    )

    # -----------------------------------------------------------------------
    # 6. South-east: Residential cluster 2 (y=57–98, x=48–97)
    #    Homes: david, emma, frank, grace, james
    # -----------------------------------------------------------------------
    # Row 1 (y=57–69): david, emma
    _add_home(tiles, "home-david", 48, 57, 62, 69)
    _add_home(tiles, "home-emma",  64, 57, 78, 69)

    # Row 2 (y=71–82): frank, grace
    _add_home(tiles, "home-frank",  48, 71, 62, 82)
    _add_home(tiles, "home-grace",  64, 71, 78, 82)

    # Row 3 (y=84–95): james (solo home)
    _add_home(tiles, "home-james",  48, 84, 65, 95)

    # -----------------------------------------------------------------------
    # Post-generation: validate each required sector has walkable tiles
    # -----------------------------------------------------------------------
    # Build quick sector→coords map from current tile dict for validation
    sector_coords: dict[str, list[tuple[int, int]]] = {}
    for coord, tile_def in tiles.items():
        if "address" in tile_def and not tile_def.get("collision"):
            sector = tile_def["address"][0]
            sector_coords.setdefault(sector, []).append(coord)

    for sector in _REQUIRED_SECTORS:
        count = len(sector_coords.get(sector, []))
        assert count > 0, (
            f"Sector '{sector}' has no walkable tiles — check zone bounds"
        )

    # -----------------------------------------------------------------------
    # Serialise to list (JSON cannot use tuple keys)
    # -----------------------------------------------------------------------
    tile_list = list(tiles.values())

    return {
        "world": "agent-town",
        "tile_size": 32,
        "size": [100, 100],
        "tile_address_keys": ["world", "sector", "arena"],
        "tiles": tile_list,
    }


if __name__ == "__main__":
    _MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    result = generate_town_map()
    _MAP_PATH.write_text(json.dumps(result, indent=2))
    print(f"Generated {_MAP_PATH}")
    print(f"  Tiles defined: {len(result['tiles'])}")
    print(f"  Grid size:     {result['size']}")
