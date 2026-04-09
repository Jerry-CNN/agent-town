"""Unit tests for the tile-map world data model and BFS pathfinding.

TDD: Tests written first, implementation follows.
"""
import json
import random
from pathlib import Path

import pytest

from backend.simulation.world import ADDRESS_KEYS, Maze, Tile

# ---------------------------------------------------------------------------
# Helper: load the generated town map
# ---------------------------------------------------------------------------
TOWN_JSON = Path(__file__).parent.parent / "backend" / "data" / "map" / "town.json"


def load_town_maze() -> Maze:
    with open(TOWN_JSON) as f:
        return Maze(json.load(f))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# 10x10 grid fixture with:
#   - border walls (row 0, row 9, col 0, col 9)
#   - vertical wall at x=5 (rows 1-8), creating left/right disconnected halves
#   - one door opening at (5, 9) is NOT added (wall is solid — for disconnected test)
SMALL_MAP = {
    "world": "test-world",
    "tile_size": 32,
    "size": [10, 10],
    "tile_address_keys": ["world", "sector", "arena"],
    "tiles": [
        # Top border (y=0)
        *[{"coord": [x, 0], "collision": True} for x in range(10)],
        # Bottom border (y=9)
        *[{"coord": [x, 9], "collision": True} for x in range(10)],
        # Left border (x=0)
        *[{"coord": [0, y], "collision": True} for y in range(1, 9)],
        # Right border (x=9)
        *[{"coord": [9, y], "collision": True} for y in range(1, 9)],
        # Vertical wall at x=5 (splitting left from right, rows 1-8)
        *[{"coord": [5, y], "collision": True} for y in range(1, 9)],
        # Some address tiles in the left half
        {"coord": [2, 3], "address": ["left-zone", "room-a"]},
        {"coord": [3, 3], "address": ["left-zone", "room-a"]},
        # Some address tiles in the right half
        {"coord": [7, 3], "address": ["right-zone", "room-b"]},
        {"coord": [7, 4], "address": ["right-zone", "room-b"]},
    ],
}


# ---------------------------------------------------------------------------
# Task 1 Tests: Tile data model and Maze class
# ---------------------------------------------------------------------------


class TestTileCreation:
    def test_tile_defaults(self):
        """Tile created with only coord should have correct defaults."""
        tile = Tile(coord=(3, 4))
        assert tile.coord == (3, 4)
        assert tile.address == []
        assert tile.collision is False
        assert tile._events == {}

    def test_tile_with_all_fields(self):
        """Tile can be created with explicit address and collision."""
        tile = Tile(coord=(1, 2), address=["agent-town", "cafe", "seating"], collision=True)
        assert tile.coord == (1, 2)
        assert tile.address == ["agent-town", "cafe", "seating"]
        assert tile.collision is True

    def test_tile_is_walkable_property(self):
        """is_walkable returns not collision."""
        walkable = Tile(coord=(0, 0), collision=False)
        blocked = Tile(coord=(0, 0), collision=True)
        assert walkable.is_walkable is True
        assert blocked.is_walkable is False


class TestTileGetAddress:
    def setup_method(self):
        self.tile = Tile(
            coord=(5, 5),
            address=["agent-town", "cafe", "seating"],
        )

    def test_get_address_no_level_returns_full(self):
        result = self.tile.get_address(level=None, as_list=True)
        assert result == ["agent-town", "cafe", "seating"]

    def test_get_address_world_level(self):
        result = self.tile.get_address(level="world", as_list=True)
        assert result == ["agent-town"]

    def test_get_address_sector_level(self):
        result = self.tile.get_address(level="sector", as_list=True)
        assert result == ["agent-town", "cafe"]

    def test_get_address_arena_level(self):
        result = self.tile.get_address(level="arena", as_list=True)
        assert result == ["agent-town", "cafe", "seating"]

    def test_get_address_as_string(self):
        result = self.tile.get_address(level="sector", as_list=False)
        assert result == "agent-town:cafe"

    def test_get_addresses_returns_all_ancestors(self):
        addresses = self.tile.get_addresses()
        assert "agent-town:cafe" in addresses
        assert "agent-town:cafe:seating" in addresses
        assert len(addresses) == 2

    def test_get_addresses_empty_address(self):
        tile = Tile(coord=(0, 0))
        assert tile.get_addresses() == []

    def test_get_addresses_world_only(self):
        tile = Tile(coord=(0, 0), address=["agent-town"])
        assert tile.get_addresses() == []


class TestMazeLoadsSmallMap:
    def setup_method(self):
        self.maze = Maze(SMALL_MAP)

    def test_maze_dimensions(self):
        assert self.maze.height == 10
        assert self.maze.width == 10

    def test_maze_world_attribute(self):
        assert self.maze.world == "test-world"

    def test_maze_tile_at(self):
        tile = self.maze.tile_at((5, 5))
        assert tile.coord == (5, 5)

    def test_border_top_is_collision(self):
        for x in range(10):
            assert self.maze.tile_at((x, 0)).collision is True

    def test_border_bottom_is_collision(self):
        for x in range(10):
            assert self.maze.tile_at((x, 9)).collision is True

    def test_border_left_is_collision(self):
        for y in range(10):
            assert self.maze.tile_at((0, y)).collision is True

    def test_border_right_is_collision(self):
        for y in range(10):
            assert self.maze.tile_at((9, y)).collision is True

    def test_vertical_wall_is_collision(self):
        for y in range(1, 9):
            assert self.maze.tile_at((5, y)).collision is True

    def test_interior_tile_is_walkable(self):
        # x=2, y=2 should be walkable (no explicit entry)
        tile = self.maze.tile_at((2, 2))
        assert tile.collision is False

    def test_address_tile_indexed(self):
        # left-zone:room-a should be indexed
        assert "test-world:left-zone" in self.maze.address_tiles
        coords = self.maze.address_tiles["test-world:left-zone"]
        assert (2, 3) in coords

    def test_address_tiles_world_prefix_prepended(self):
        tile = self.maze.tile_at((2, 3))
        assert tile.address[0] == "test-world"
        assert "left-zone" in tile.address


# ---------------------------------------------------------------------------
# Task 1 Tests: Generated town.json map
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def town_maze():
    """Load the generated town.json and return a Maze instance."""
    return load_town_maze()


class TestTownJsonStructure:
    def test_generate_town_map_structure(self):
        """generate_town_map() returns dict with all required top-level keys."""
        from backend.simulation.map_generator import generate_town_map

        result = generate_town_map()
        assert "world" in result
        assert "tile_size" in result
        assert "size" in result
        assert "tile_address_keys" in result
        assert "tiles" in result

    def test_town_json_world(self, town_maze):
        assert town_maze.world == "agent-town"

    def test_town_json_size(self, town_maze):
        assert town_maze.height == 100
        assert town_maze.width == 100

    def test_town_json_tile_size(self):
        with open(TOWN_JSON) as f:
            data = json.load(f)
        assert data["tile_size"] == 32

    def test_no_duplicate_coords_in_town_json(self):
        """No two tile entries share the same coord (pitfall 3 guard)."""
        with open(TOWN_JSON) as f:
            data = json.load(f)
        coords = [tuple(t["coord"]) for t in data["tiles"]]
        assert len(coords) == len(set(coords)), "Duplicate coordinates found in town.json"


class TestTownRequiredLocations:
    REQUIRED_SECTORS = [
        "park",
        "cafe",
        "shop",
        "office",
        "stock-exchange",
        "wedding-hall",
        "home-alice",
        "home-bob",
        "home-carla",
    ]

    def test_all_required_locations_exist(self, town_maze):
        """All 7+ required sectors must be indexed in address_tiles."""
        for sector in self.REQUIRED_SECTORS:
            key = f"agent-town:{sector}"
            assert key in town_maze.address_tiles, f"Missing required sector: {key}"

    def test_border_tiles_collision_top(self, town_maze):
        for x in range(100):
            assert town_maze.tile_at((x, 0)).collision is True, f"Top border ({x},0) not collision"

    def test_border_tiles_collision_bottom(self, town_maze):
        for x in range(100):
            assert town_maze.tile_at((x, 99)).collision is True, f"Bottom border ({x},99) not collision"

    def test_border_tiles_collision_left(self, town_maze):
        for y in range(100):
            assert town_maze.tile_at((0, y)).collision is True, f"Left border (0,{y}) not collision"

    def test_border_tiles_collision_right(self, town_maze):
        for y in range(100):
            assert town_maze.tile_at((99, y)).collision is True, f"Right border (99,{y}) not collision"

    def test_every_sector_has_walkable_tiles(self, town_maze):
        """Every required sector must have at least 1 walkable tile (pitfall 4 guard)."""
        for sector in self.REQUIRED_SECTORS:
            key = f"agent-town:{sector}"
            coords = town_maze.address_tiles.get(key, set())
            walkable = [c for c in coords if not town_maze.tile_at(c).collision]
            assert len(walkable) > 0, f"Sector '{sector}' has no walkable tiles"


class TestResolveDestination:
    def test_resolve_destination_valid(self, town_maze):
        """resolve_destination('cafe') returns a non-None walkable coord."""
        coord = town_maze.resolve_destination("cafe")
        assert coord is not None
        tile = town_maze.tile_at(coord)
        assert tile.collision is False

    def test_resolve_destination_stock_exchange(self, town_maze):
        coord = town_maze.resolve_destination("stock-exchange")
        assert coord is not None
        assert town_maze.tile_at(coord).collision is False

    def test_resolve_destination_park(self, town_maze):
        coord = town_maze.resolve_destination("park")
        assert coord is not None
        assert town_maze.tile_at(coord).collision is False

    def test_resolve_destination_wedding_hall(self, town_maze):
        coord = town_maze.resolve_destination("wedding-hall")
        assert coord is not None
        assert town_maze.tile_at(coord).collision is False

    def test_resolve_destination_invalid(self, town_maze):
        """resolve_destination('nonexistent-place') returns None."""
        result = town_maze.resolve_destination("nonexistent-place")
        assert result is None


# ---------------------------------------------------------------------------
# Task 2 Tests: BFS pathfinding edge cases
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def small_maze():
    return Maze(SMALL_MAP)


class TestBFSSmallMap:
    def test_bfs_same_start_and_goal(self, small_maze):
        """find_path(src, dst) returns [src] when src == dst."""
        result = small_maze.find_path((2, 2), (2, 2))
        assert result == [(2, 2)]

    def test_bfs_finds_path_small_map(self, small_maze):
        """BFS finds a path between two walkable tiles in the left half."""
        path = small_maze.find_path((1, 1), (4, 8))
        assert len(path) > 0
        assert path[0] == (1, 1)
        assert path[-1] == (4, 8)

    def test_bfs_returns_empty_when_disconnected(self, small_maze):
        """BFS returns [] when start and goal are on opposite sides of a wall."""
        # Left side (1,5) → Right side (7,5) — wall at x=5 separates them
        result = small_maze.find_path((1, 5), (7, 5))
        assert result == []

    def test_bfs_path_steps_are_adjacent(self, small_maze):
        """Each step in a path has Manhattan distance 1 from the previous."""
        path = small_maze.find_path((1, 1), (4, 7))
        assert len(path) > 0
        for i in range(len(path) - 1):
            a, b = path[i], path[i + 1]
            manhattan = abs(a[0] - b[0]) + abs(a[1] - b[1])
            assert manhattan == 1, f"Non-adjacent steps: {a} -> {b}"

    def test_bfs_path_avoids_collision_tiles(self, small_maze):
        """No step in the path lands on a collision tile."""
        path = small_maze.find_path((1, 1), (4, 7))
        assert len(path) > 0
        for step in path:
            assert small_maze.tile_at(step).collision is False, f"Path step {step} is collision"


class TestBFSFullTownMap:
    def test_full_town_cafe_to_stock_exchange(self, town_maze):
        """BFS path from cafe to stock-exchange is non-empty (tests road connectivity)."""
        cafe_coord = town_maze.resolve_destination("cafe")
        exchange_coord = town_maze.resolve_destination("stock-exchange")
        assert cafe_coord is not None
        assert exchange_coord is not None
        path = town_maze.find_path(cafe_coord, exchange_coord)
        assert len(path) > 0, "No path found from cafe to stock-exchange"

    def test_full_town_all_homes_reachable_from_cafe(self, town_maze):
        """All home sectors are reachable from cafe (proves road network connectivity)."""
        cafe_coord = town_maze.resolve_destination("cafe")
        assert cafe_coord is not None

        home_sectors = [
            key.split(":")[1]
            for key in town_maze.address_tiles
            if key.startswith("agent-town:home-")
            and key.count(":") == 1
        ]
        assert len(home_sectors) >= 3, "Expected at least 3 home sectors"

        for sector in home_sectors:
            home_coord = town_maze.resolve_destination(sector)
            assert home_coord is not None, f"resolve_destination('{sector}') returned None"
            path = town_maze.find_path(cafe_coord, home_coord)
            assert len(path) > 0, f"No path from cafe to {sector}"

    def test_full_town_all_sectors_reachable_from_each_other(self, town_maze):
        """Every required sector is reachable from every other sector."""
        required_sectors = [
            "park", "cafe", "shop", "office", "stock-exchange", "wedding-hall",
            "home-alice", "home-bob", "home-carla",
        ]
        # Pick one coord per sector
        sector_coords = {}
        for sector in required_sectors:
            coord = town_maze.resolve_destination(sector)
            assert coord is not None, f"resolve_destination('{sector}') returned None"
            sector_coords[sector] = coord

        # Verify all pairs are mutually reachable
        sectors = list(sector_coords.keys())
        for i, src_sector in enumerate(sectors):
            for dst_sector in sectors[i + 1:]:
                src = sector_coords[src_sector]
                dst = sector_coords[dst_sector]
                path = town_maze.find_path(src, dst)
                assert len(path) > 0, (
                    f"No path from {src_sector} {src} to {dst_sector} {dst}"
                )

    def test_bfs_path_steps_adjacent_full_map(self, town_maze):
        """Path steps on full map are all adjacent (Manhattan distance 1)."""
        src = town_maze.resolve_destination("cafe")
        dst = town_maze.resolve_destination("park")
        assert src is not None and dst is not None
        path = town_maze.find_path(src, dst)
        assert len(path) > 0
        for i in range(len(path) - 1):
            a, b = path[i], path[i + 1]
            assert abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1

    def test_bfs_path_avoids_collision_full_map(self, town_maze):
        """No path step lands on a collision tile in full map traversal."""
        src = town_maze.resolve_destination("cafe")
        dst = town_maze.resolve_destination("wedding-hall")
        assert src is not None and dst is not None
        path = town_maze.find_path(src, dst)
        assert len(path) > 0
        for step in path:
            assert not town_maze.tile_at(step).collision, f"Collision tile in path: {step}"

    def test_bfs_north_to_south(self, town_maze):
        """BFS can find a path from north (park) to south (wedding-hall) of the map."""
        north_coord = town_maze.resolve_destination("park")
        south_coord = town_maze.resolve_destination("wedding-hall")
        assert north_coord is not None
        assert south_coord is not None
        path = town_maze.find_path(north_coord, south_coord)
        assert len(path) > 0, "No path found from park (north) to wedding-hall (south)"
