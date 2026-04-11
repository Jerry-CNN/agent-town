"""Tile-map world data model and BFS pathfinding for Agent Town.

Adapted from the reference implementation:
  GenerativeAgentsCN/generative_agents/modules/maze.py

Design decisions (from 02-RESEARCH.md):
  - 3-level address hierarchy: world:sector:arena (dropped game_object level)
  - BFS with strict boundary guard (0 < c < width/height - 1) to match
    reference behaviour; border tiles are always collision
  - deque-based BFS frontier for O(1) popleft
"""

from __future__ import annotations

import json
import random
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Union

BUILDINGS_PATH = Path(__file__).parent.parent / "data" / "map" / "buildings.json"

# Hierarchical address levels for the 3-level scheme
ADDRESS_KEYS: list[str] = ["world", "sector", "arena"]


def _validate_level(level: str) -> None:
    """Raise a descriptive ValueError if *level* is not in ADDRESS_KEYS."""
    if level not in ADDRESS_KEYS:
        raise ValueError(
            f"Invalid address level {level!r}. Must be one of: {ADDRESS_KEYS}"
        )


@dataclass
class Tile:
    """Represents one grid square in the town map.

    Attributes:
        coord:     (x, y) grid position.
        address:   Hierarchical path, e.g. ["agent-town", "cafe", "seating"].
                   Always has world as the first element when loaded via Maze.
        collision: If True, the tile is impassable (walls, water, building edges).
        _events:   Runtime event store for Phase 3 agent perception. Starts empty.
    """

    coord: tuple[int, int]
    address: list[str] = field(default_factory=list)
    collision: bool = False
    _events: dict = field(default_factory=dict, repr=False)

    # ------------------------------------------------------------------
    # Address helpers
    # ------------------------------------------------------------------

    def get_address(
        self,
        level: str | None = None,
        as_list: bool = True,
    ) -> Union[list[str], str]:
        """Return address up to *level* (inclusive).

        Args:
            level:   One of ADDRESS_KEYS ("world", "sector", "arena").
                     If None or the last key, returns the full address.
            as_list: When True returns a list; when False returns a ":"-joined
                     string.

        Returns:
            Sliced address as list or string.
        """
        if level is not None:
            _validate_level(level)
        if level is None or level == ADDRESS_KEYS[-1]:
            addr = self.address
        else:
            pos = ADDRESS_KEYS.index(level) + 1
            addr = self.address[:pos]
        return addr if as_list else ":".join(addr)

    def get_addresses(self) -> list[str]:
        """Return all ancestor address strings (used to build address_tiles index).

        Example: address=["agent-town","cafe","seating"] →
            ["agent-town:cafe", "agent-town:cafe:seating"]
        Tiles with address length < 2 (empty or world-only) return [].
        """
        return [":".join(self.address[:i]) for i in range(2, len(self.address) + 1)]

    def has_address(self, level: str) -> bool:
        """True if the tile has an address component at *level*."""
        _validate_level(level)
        key_idx = ADDRESS_KEYS.index(level)
        return len(self.address) > key_idx

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_walkable(self) -> bool:
        """True when the tile is not a collision tile."""
        return not self.collision


@dataclass
class Building:
    """Sector-level metadata for a building in the town map.

    Loaded from backend/data/map/buildings.json, indexed by sector name.
    Separate from town.json (tile geometry) per D-06.

    Attributes:
        name:    Human-readable display name (e.g. "Town Cafe").
        sector:  Key matching address_tiles (e.g. "cafe" for "agent-town:cafe").
        opens:   Hour the building opens (0-23).
        closes:  Hour the building closes (0-23); 24 means midnight/never closes.
        purpose: Activity tag: "food", "finance", "social", "leisure",
                 "residential", "work", or "retail".
    """
    name: str
    sector: str
    opens: int    # hour (0-23)
    closes: int   # hour (0-23), 24 means midnight/never closes
    purpose: str  # tag: "food", "finance", "social", "leisure", "residential", "work", "retail"

    def is_open(self, sim_hour: int) -> bool:
        """Return True if the building is open at the given simulation hour.

        Handles three cases:
        - closes=24: always open (parks, homes)
        - opens < closes: standard range (e.g., 9-17)
        - opens >= closes: midnight wrap-around (e.g., 22-4)

        Args:
            sim_hour: Current simulation hour (0-23).

        Returns:
            True if the building accepts visitors at sim_hour.
        """
        if self.closes == 24:
            return True
        if self.opens < self.closes:
            return self.opens <= sim_hour < self.closes
        # Midnight wrap-around: open from opens until closes crosses midnight
        return sim_hour >= self.opens or sim_hour < self.closes


def load_buildings() -> dict[str, "Building"]:
    """Load Building metadata from buildings.json, indexed by sector name.

    Returns empty dict if buildings.json does not exist.

    Returns:
        Dict mapping sector name -> Building instance.
    """
    if not BUILDINGS_PATH.exists():
        return {}
    raw = json.loads(BUILDINGS_PATH.read_text(encoding="utf-8"))
    return {b["sector"]: Building(**b) for b in raw}


class Maze:
    """Tile-map town loaded from a config dict (parsed from town.json).

    Responsibilities:
      - Build the full NxM Tile grid from a sparse tile-definition list.
      - Build reverse index: address string → set of (x, y) coordinates.
      - Provide BFS pathfinding (find_path) and destination resolution.

    Args:
        config: Dict parsed from town.json. Expected keys:
            "world"            – world name, e.g. "agent-town"
            "size"             – [height, width] (rows x cols)
            "tile_size"        – pixel size per tile (e.g. 32)
            "tile_address_keys"– address hierarchy labels
            "tiles"            – sparse list of tile definitions
    """

    def __init__(self, config: dict) -> None:
        self.world: str = config["world"]
        # size is [height, width] (rows first, matching matrix indexing)
        self.height, self.width = config["size"]
        self.tile_size: int = config["tile_size"]

        # ---- Build full grid, all tiles default walkable & empty ----------
        self.tiles: list[list[Tile]] = [
            [Tile(coord=(x, y)) for x in range(self.width)]
            for y in range(self.height)
        ]

        # ---- Apply sparse tile definitions --------------------------------
        for tile_def in config.get("tiles", []):
            x, y = tile_def["coord"]
            raw_address: list[str] = tile_def.get("address", [])
            # Prepend world name so every addressed tile has full path
            full_address: list[str] = [self.world] + raw_address if raw_address else []
            self.tiles[y][x] = Tile(
                coord=(x, y),
                address=full_address,
                collision=tile_def.get("collision", False),
            )

        # ---- Build reverse address index -----------------------------------
        # Maps "world:sector" → set((x,y)), "world:sector:arena" → set((x,y))
        self.address_tiles: dict[str, set[tuple[int, int]]] = {}
        for row in self.tiles:
            for tile in row:
                for addr_str in tile.get_addresses():
                    self.address_tiles.setdefault(addr_str, set()).add(tile.coord)

    # ------------------------------------------------------------------
    # Tile access
    # ------------------------------------------------------------------

    def tile_at(self, coord: tuple[int, int]) -> Tile:
        """Return the Tile at (x, y) coordinate."""
        x, y = coord
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError(
                f"Coordinate {coord} is out of bounds "
                f"(width={self.width}, height={self.height})"
            )
        return self.tiles[y][x]

    # ------------------------------------------------------------------
    # BFS pathfinding
    # ------------------------------------------------------------------

    def get_walkable_neighbors(
        self, coord: tuple[int, int]
    ) -> list[tuple[int, int]]:
        """Return 4-directional walkable neighbors.

        Uses strict inequality (0 < c < dimension - 1) to exclude border tiles,
        matching the reference implementation. Border tiles are expected to be
        collision tiles, so this is both a bounds guard and a walkability guard.
        """
        x, y = coord
        candidates = [
            (x - 1, y),
            (x + 1, y),
            (x, y - 1),
            (x, y + 1),
        ]
        return [
            c
            for c in candidates
            if (
                0 < c[0] < self.width - 1
                and 0 < c[1] < self.height - 1
                and not self.tiles[c[1]][c[0]].collision
            )
        ]

    def find_path(
        self,
        src: tuple[int, int],
        dst: tuple[int, int],
    ) -> list[tuple[int, int]]:
        """BFS shortest path from *src* to *dst*.

        Returns:
            List of (x, y) coordinates from src to dst (inclusive).
            Returns [src] if src == dst.
            Returns [] if dst is unreachable from src.

        Algorithm:
            BFS with a distance map (0 = unvisited).  src is marked with
            distance 1.  After BFS completes, path is reconstructed backwards
            from dst using the distance values — each step follows the neighbor
            with distance one less than the current.
        """
        if src == dst:
            return [src]

        # Distance map: 0 = unvisited, 1 = src, >1 = distance from src
        dist: list[list[int]] = [
            [0] * self.width for _ in range(self.height)
        ]
        dist[src[1]][src[0]] = 1

        frontier: deque[tuple[int, int]] = deque([src])

        while frontier:
            curr = frontier.popleft()
            if curr == dst:
                break
            for nb in self.get_walkable_neighbors(curr):
                if dist[nb[1]][nb[0]] == 0:
                    dist[nb[1]][nb[0]] = dist[curr[1]][curr[0]] + 1
                    frontier.append(nb)

        # If dst was never reached, return empty
        if dist[dst[1]][dst[0]] == 0:
            return []

        # Reconstruct path backwards from dst to src
        path: list[tuple[int, int]] = [dst]
        step = dist[dst[1]][dst[0]]
        while step > 1:
            for nb in self.get_walkable_neighbors(path[-1]):
                if dist[nb[1]][nb[0]] == step - 1:
                    path.append(nb)
                    break
            step -= 1

        return path[::-1]  # reverse to get src → dst order

    # ------------------------------------------------------------------
    # Address utilities
    # ------------------------------------------------------------------

    def get_address_tiles(
        self, address: list[str]
    ) -> set[tuple[int, int]]:
        """Return all tile coordinates for a given address list."""
        key = ":".join(address)
        return self.address_tiles.get(key, set())

    def resolve_destination(
        self, sector: str
    ) -> tuple[int, int] | None:
        """Pick a random walkable tile in the named sector.

        Args:
            sector: Sector name without world prefix, e.g. "cafe".

        Returns:
            A random walkable (x, y) coordinate within the sector, or
            None if the sector is unknown or has no walkable tiles.
        """
        key = f"{self.world}:{sector}"
        tile_coords = self.address_tiles.get(key, set())
        walkable = [c for c in tile_coords if not self.tile_at(c).collision]
        return random.choice(walkable) if walkable else None
