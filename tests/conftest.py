"""Shared pytest fixtures for Agent Town backend tests."""
import pytest
import httpx
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def async_client():
    """AsyncClient fixture using ASGI transport (httpx >= 0.28)."""
    from backend.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
def mock_ollama_available(monkeypatch):
    """Monkeypatches state.ollama_available = True for tests that need it."""
    import backend.config as cfg
    monkeypatch.setattr(cfg.state, "ollama_available", True)
    return cfg.state


# ---------------------------------------------------------------------------
# Minimal TMJ fixture for sync_map.py tests
# ---------------------------------------------------------------------------

def _make_obj(obj_id, name, x, y, width, height, obj_type="rectangle", props=None):
    """Helper to create a Tiled object dict (pixel coordinates)."""
    obj = {
        "id": obj_id,
        "name": name,
        "type": "",
        "x": float(x),
        "y": float(y),
        "width": float(width),
        "height": float(height),
        "rotation": 0.0,
        "visible": True,
    }
    if obj_type == "point":
        obj["point"] = True
        obj.pop("width", None)
        obj.pop("height", None)
    if props:
        obj["properties"] = props
    return obj


@pytest.fixture
def minimal_tmj():
    """
    A minimal 10x10 Tiled TMJ dict with all 14 layers (10 visual + 4 metadata).

    Coordinate conventions (pixel space, tilewidth/tileheight = 32):
      - Sector "test-cafe": pixel (64,64) size (128,96)
            -> tiles x:[2,5) y:[2,5)  i.e. 3 cols x 3 rows
      - Arena "test-cafe:seating": pixel (64,64) size (64,64)
            -> tiles x:[2,4) y:[2,4)  i.e. 2 cols x 2 rows
      - Collision strip: pixel (0,0) size (320,32)
            -> tiles x:[0,10) y:[0,1)  (full top row, 10 tiles)
      - Spawn point "alice": pixel (96,96) -> tile (3,3)

    Note: collision top row covers y=0 only.
    The sector and arena rectangles start at y=2 (pixel 64), so they do
    NOT overlap with the collision strip at y=0.
    """
    visual_layers = [
        {
            "id": i,
            "name": name,
            "type": "tilelayer",
            "width": 10,
            "height": 10,
            "x": 0,
            "y": 0,
            "opacity": 1,
            "visible": True,
            "data": [0] * 100,  # empty tile data
        }
        for i, name in enumerate(
            [
                "Bottom Ground",
                "Exterior Ground",
                "Exterior Decoration L1",
                "Exterior Decoration L2",
                "Interior Ground",
                "Wall",
                "Interior Furniture L1",
                "Interior Furniture L2",
                "Foreground L1",
                "Foreground L2",
            ],
            start=1,
        )
    ]

    sectors_layer = {
        "id": 11,
        "name": "Sectors",
        "type": "objectgroup",
        "x": 0,
        "y": 0,
        "opacity": 1,
        "visible": False,
        "objects": [
            _make_obj(
                101,
                "test-cafe",
                64.0, 64.0, 128.0, 96.0,
                props=[
                    {"name": "display_name", "type": "string", "value": "Test Cafe"},
                    {"name": "opens",        "type": "int",    "value": 7},
                    {"name": "closes",       "type": "int",    "value": 22},
                    {"name": "purpose",      "type": "string", "value": "food"},
                ],
            )
        ],
    }

    arenas_layer = {
        "id": 12,
        "name": "Arenas",
        "type": "objectgroup",
        "x": 0,
        "y": 0,
        "opacity": 1,
        "visible": False,
        "objects": [
            _make_obj(201, "test-cafe:seating", 64.0, 64.0, 64.0, 64.0),
        ],
    }

    collision_layer = {
        "id": 13,
        "name": "Collision",
        "type": "objectgroup",
        "x": 0,
        "y": 0,
        "opacity": 1,
        "visible": False,
        "objects": [
            # Top border: pixel (0,0) size (320,32) -> tile row y=0, x=0..9
            _make_obj(301, "border-top", 0.0, 0.0, 320.0, 32.0),
        ],
    }

    spawn_layer = {
        "id": 14,
        "name": "Spawn Points",
        "type": "objectgroup",
        "x": 0,
        "y": 0,
        "opacity": 1,
        "visible": False,
        "objects": [
            # pixel (96,96) -> tile (3,3)
            _make_obj(401, "alice", 96.0, 96.0, 0.0, 0.0, obj_type="point"),
        ],
    }

    return {
        "version": "1.10",
        "tiledversion": "1.10.2",
        "orientation": "orthogonal",
        "renderorder": "right-down",
        "width": 10,
        "height": 10,
        "tilewidth": 32,
        "tileheight": 32,
        "infinite": False,
        "tilesets": [],
        "layers": visual_layers + [sectors_layer, arenas_layer, collision_layer, spawn_layer],
    }
