"""Unit tests for scripts/sync_map.py — TMJ-to-JSON conversion.

TDD: Tests written first, implementation follows.
All tests use the `minimal_tmj` fixture from conftest.py.
"""

import pytest

from scripts.sync_map import (
    extract_map,
    extract_buildings,
    extract_spawn_points,
)


# ---------------------------------------------------------------------------
# extract_map — town.json production
# ---------------------------------------------------------------------------


def test_extract_map_size_is_height_width(minimal_tmj):
    """size field must be [height, width] — height FIRST per Maze.__init__."""
    result = extract_map(minimal_tmj)
    assert result["size"] == [10, 10], (
        "size must be [height, width]; 10x10 map -> [10, 10]"
    )


def test_extract_map_world_name(minimal_tmj):
    """World name must be 'agent-town' (hardcoded canonical value)."""
    result = extract_map(minimal_tmj)
    assert result["world"] == "agent-town"


def test_extract_map_tile_address_keys(minimal_tmj):
    """tile_address_keys must be ['world', 'sector', 'arena']."""
    result = extract_map(minimal_tmj)
    assert result["tile_address_keys"] == ["world", "sector", "arena"]


def test_extract_map_collision_tiles_marked(minimal_tmj):
    """
    Collision rectangle at pixel (0,0) size (320,32) covers tile row y=0, x=0..9.
    Each tile in that row must appear in tiles list with collision=True.
    """
    result = extract_map(minimal_tmj)
    tiles_by_coord = {tuple(t["coord"]): t for t in result["tiles"]}

    # Top border: x=0..9, y=0
    for x in range(10):
        coord = (x, 0)
        assert coord in tiles_by_coord, f"Collision tile {coord} missing from tiles list"
        tile = tiles_by_coord[coord]
        assert tile.get("collision") is True, (
            f"Tile {coord} should have collision=True"
        )


def test_extract_map_sector_address_assigned(minimal_tmj):
    """
    Sector 'test-cafe' covers tiles x:[2,5) y:[2,5).
    Non-collision tiles in that range must have address ['test-cafe'].
    """
    result = extract_map(minimal_tmj)
    tiles_by_coord = {tuple(t["coord"]): t for t in result["tiles"]}

    # Check a tile clearly inside the sector and NOT colliding (e.g. (4, 4))
    coord = (4, 4)
    assert coord in tiles_by_coord, f"Sector tile {coord} missing"
    tile = tiles_by_coord[coord]
    assert tile.get("address") == ["test-cafe"], (
        f"Expected address ['test-cafe'] on {coord}, got {tile.get('address')}"
    )
    assert tile.get("collision") is not True, "Sector tile should not be collision"


def test_extract_map_arena_address_assigned(minimal_tmj):
    """
    Arena 'test-cafe:seating' covers tiles x:[2,4) y:[2,4).
    Non-collision tiles in that range must have address ['test-cafe', 'seating'].
    """
    result = extract_map(minimal_tmj)
    tiles_by_coord = {tuple(t["coord"]): t for t in result["tiles"]}

    # Tile at (3,3) is inside the arena rectangle and NOT a collision tile
    coord = (3, 3)
    assert coord in tiles_by_coord, f"Arena tile {coord} missing"
    tile = tiles_by_coord[coord]
    assert tile.get("address") == ["test-cafe", "seating"], (
        f"Expected arena address on {coord}, got {tile.get('address')}"
    )


def test_extract_map_collision_not_overwritten_by_arena(minimal_tmj):
    """
    Collision tiles must NOT be overwritten by arena or sector addresses.
    Top border (y=0) must remain collision-only even if a future object overlaps it.
    This test uses tile (2, 0) which is in the collision strip but NOT in the arena.
    """
    result = extract_map(minimal_tmj)
    tiles_by_coord = {tuple(t["coord"]): t for t in result["tiles"]}

    coord = (2, 0)
    assert coord in tiles_by_coord, f"Collision tile {coord} missing"
    tile = tiles_by_coord[coord]
    assert tile.get("collision") is True, f"Tile {coord} must remain collision=True"
    assert "address" not in tile or tile.get("address") is None or tile.get("address") == [], (
        f"Collision tile {coord} must not have an address; got {tile.get('address')}"
    )


# ---------------------------------------------------------------------------
# extract_buildings — buildings.json production
# ---------------------------------------------------------------------------


def test_extract_buildings_extracts_properties(minimal_tmj):
    """Sector with full custom properties -> all fields populated correctly."""
    layers = {layer["name"]: layer for layer in minimal_tmj["layers"]}
    sector_objects = layers["Sectors"]["objects"]
    buildings = extract_buildings(sector_objects)

    assert len(buildings) == 1
    b = buildings[0]
    assert b["name"] == "Test Cafe", f"display_name should be name; got {b['name']}"
    assert b["sector"] == "test-cafe"
    assert b["opens"] == 7
    assert b["closes"] == 22
    assert b["purpose"] == "food"


def test_extract_buildings_defaults_when_properties_missing(minimal_tmj):
    """Sector object with no custom properties gets defaults: opens=0, closes=24, purpose='general'."""
    bare_obj = {
        "id": 999,
        "name": "bare-sector",
        "type": "",
        "x": 0.0, "y": 0.0,
        "width": 64.0, "height": 64.0,
        "rotation": 0.0,
        "visible": True,
        # No "properties" key
    }
    buildings = extract_buildings([bare_obj])
    assert len(buildings) == 1
    b = buildings[0]
    assert b["sector"] == "bare-sector"
    assert b["name"] == "bare-sector", "Fallback name should be obj name"
    assert b["opens"] == 0
    assert b["closes"] == 24
    assert b["purpose"] == "general"


# ---------------------------------------------------------------------------
# extract_spawn_points — spawn_points.json production
# ---------------------------------------------------------------------------


def test_extract_spawn_points_pixel_to_tile(minimal_tmj):
    """Spawn point at pixel (96, 96) must convert to tile (3, 3)."""
    layers = {layer["name"]: layer for layer in minimal_tmj["layers"]}
    spawn_objects = layers["Spawn Points"]["objects"]
    spawn_points = extract_spawn_points(spawn_objects)

    assert "alice" in spawn_points
    assert spawn_points["alice"] == [3, 3], (
        f"Expected [3, 3] but got {spawn_points['alice']}"
    )


def test_extract_spawn_points_float_coords():
    """Float pixel coordinates are correctly converted to integer tile coords."""
    obj = {
        "id": 1,
        "name": "bob",
        "type": "",
        "x": 160.5,
        "y": 96.0,
        "point": True,
        "rotation": 0.0,
        "visible": True,
    }
    result = extract_spawn_points([obj])
    # 160.5 // 32 = 5.0 -> int 5; 96.0 // 32 = 3.0 -> int 3
    assert result["bob"] == [5, 3]


# ---------------------------------------------------------------------------
# Validation / error handling
# ---------------------------------------------------------------------------


def test_extract_map_raises_on_missing_required_layer(minimal_tmj):
    """sync_map raises ValueError when a required metadata layer is missing."""
    # Remove the "Sectors" layer from the TMJ
    minimal_tmj["layers"] = [
        l for l in minimal_tmj["layers"] if l["name"] != "Sectors"
    ]
    with pytest.raises(ValueError, match="Sectors"):
        extract_map(minimal_tmj)


def test_extract_map_raises_on_wrong_layer_type(minimal_tmj):
    """sync_map raises ValueError when a metadata layer has wrong type (tilelayer instead of objectgroup)."""
    for layer in minimal_tmj["layers"]:
        if layer["name"] == "Collision":
            layer["type"] = "tilelayer"
            layer["data"] = [0] * 100
            break
    with pytest.raises(ValueError, match="objectgroup"):
        extract_map(minimal_tmj)


def test_extract_map_raises_on_arena_name_without_colon(minimal_tmj):
    """Arena object name without colon separator raises ValueError."""
    for layer in minimal_tmj["layers"]:
        if layer["name"] == "Arenas":
            layer["objects"][0]["name"] = "no-colon-arena"
            break
    with pytest.raises(ValueError, match="colon"):
        extract_map(minimal_tmj)


def test_extract_map_float_coords_handled(minimal_tmj):
    """Float coordinates in Tiled objects are correctly converted to int tile coords."""
    # Modify the collision object to use float coords (Pitfall 2)
    for layer in minimal_tmj["layers"]:
        if layer["name"] == "Collision":
            layer["objects"][0]["x"] = 0.0
            layer["objects"][0]["y"] = 0.0
            layer["objects"][0]["width"] = 320.0
            layer["objects"][0]["height"] = 32.0
            break

    # Should not raise; collision tiles should still be marked correctly
    result = extract_map(minimal_tmj)
    tiles_by_coord = {tuple(t["coord"]): t for t in result["tiles"]}
    assert tiles_by_coord.get((0, 0), {}).get("collision") is True
