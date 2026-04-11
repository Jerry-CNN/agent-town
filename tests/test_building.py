"""Unit tests for Building dataclass and load_buildings() function.

Tests cover (BLD-01):
  - Test 1: Building dataclass has all required fields
  - Test 2: load_buildings() returns dict[str, Building] keyed by sector name
  - Test 3: load_buildings() loads all entries from buildings.json
  - Test 4: load_buildings() returns empty dict when buildings.json does not exist
  - Test 5: Each buildings.json sector matches a key in town.json address_tiles
  - Test 6: Building with opens=0, closes=24 represents 24-hour venue
"""
import json
from dataclasses import fields
from pathlib import Path
from unittest.mock import patch

import pytest

TOWN_JSON = Path(__file__).parent.parent / "backend" / "data" / "map" / "town.json"
BUILDINGS_JSON = Path(__file__).parent.parent / "backend" / "data" / "map" / "buildings.json"


# ---------------------------------------------------------------------------
# Test 1: Building dataclass fields
# ---------------------------------------------------------------------------

class TestBuildingDataclass:
    def test_building_has_required_fields(self):
        """Test 1: Building dataclass has fields: name, sector, opens, closes, purpose."""
        from backend.simulation.world import Building
        field_names = {f.name for f in fields(Building)}
        assert "name" in field_names
        assert "sector" in field_names
        assert "opens" in field_names
        assert "closes" in field_names
        assert "purpose" in field_names

    def test_building_field_types(self):
        """Building fields have correct types: str, str, int, int, str."""
        from backend.simulation.world import Building
        building = Building(name="Town Cafe", sector="cafe", opens=7, closes=22, purpose="food")
        assert isinstance(building.name, str)
        assert isinstance(building.sector, str)
        assert isinstance(building.opens, int)
        assert isinstance(building.closes, int)
        assert isinstance(building.purpose, str)


# ---------------------------------------------------------------------------
# Test 2: load_buildings() return type
# ---------------------------------------------------------------------------

class TestLoadBuildingsReturnType:
    def test_load_buildings_returns_dict(self):
        """Test 2: load_buildings() returns dict[str, Building] keyed by sector name."""
        from backend.simulation.world import Building, load_buildings
        result = load_buildings()
        assert isinstance(result, dict)
        for key, value in result.items():
            assert isinstance(key, str), f"Key should be str, got {type(key)}"
            assert isinstance(value, Building), f"Value should be Building, got {type(value)}"

    def test_load_buildings_keyed_by_sector(self):
        """load_buildings() keys match the sector field of each Building."""
        from backend.simulation.world import load_buildings
        result = load_buildings()
        for key, building in result.items():
            assert key == building.sector, f"Key {key!r} != sector {building.sector!r}"


# ---------------------------------------------------------------------------
# Test 3: load_buildings() loads all entries from buildings.json
# ---------------------------------------------------------------------------

class TestLoadBuildingsEntries:
    def test_load_buildings_count_matches_json(self):
        """Test 3: load_buildings() loads all entries from buildings.json."""
        from backend.simulation.world import load_buildings
        result = load_buildings()
        with open(BUILDINGS_JSON) as f:
            raw = json.load(f)
        assert len(result) == len(raw), (
            f"Expected {len(raw)} buildings, got {len(result)}"
        )

    def test_load_buildings_has_at_least_five(self):
        """buildings.json contains at least 5 building entries."""
        from backend.simulation.world import load_buildings
        result = load_buildings()
        assert len(result) >= 5, f"Expected at least 5 buildings, got {len(result)}"


# ---------------------------------------------------------------------------
# Test 4: load_buildings() returns empty dict when buildings.json does not exist
# ---------------------------------------------------------------------------

class TestLoadBuildingsMissingFile:
    def test_missing_file_returns_empty_dict(self):
        """Test 4: load_buildings() returns empty dict when buildings.json does not exist."""
        from backend.simulation import world as world_mod
        nonexistent = Path("/tmp/does_not_exist_buildings.json")
        with patch.object(world_mod, "BUILDINGS_PATH", nonexistent):
            result = world_mod.load_buildings()
        assert result == {}


# ---------------------------------------------------------------------------
# Test 5: Cross-validation — buildings.json sectors match address_tiles in Maze
# ---------------------------------------------------------------------------

class TestCrossValidation:
    def test_building_sectors_exist_in_maze(self):
        """Test 5: Each building sector in buildings.json matches a sector key in town.json address_tiles."""
        from backend.simulation.world import Maze, load_buildings
        with open(TOWN_JSON) as f:
            maze = Maze(json.load(f))
        buildings = load_buildings()
        for sector, building in buildings.items():
            key = f"agent-town:{sector}"
            assert key in maze.address_tiles, (
                f"buildings.json sector {sector!r} not found in maze.address_tiles (key: {key!r})"
            )


# ---------------------------------------------------------------------------
# Test 6: 24-hour venue (opens=0, closes=24)
# ---------------------------------------------------------------------------

class TestTwentyFourHourVenue:
    def test_building_opens_0_closes_24(self):
        """Test 6: Building with opens=0, closes=24 represents 24-hour venue."""
        from backend.simulation.world import Building
        venue = Building(name="Central Park", sector="park", opens=0, closes=24, purpose="leisure")
        assert venue.opens == 0
        assert venue.closes == 24

    def test_park_building_is_24_hours(self):
        """Park in buildings.json should be 24-hour (opens=0, closes=24)."""
        from backend.simulation.world import load_buildings
        buildings = load_buildings()
        if "park" in buildings:
            park = buildings["park"]
            assert park.opens == 0
            assert park.closes == 24
