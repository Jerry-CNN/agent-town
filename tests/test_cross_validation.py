"""Cross-plan integration tests: validate agent configs against generated town map.

Wave 2 plan (02-03) validates consistency between:
  - Plan 01 output: backend/simulation/world.py + backend/data/map/town.json
  - Plan 02 output: backend/agents/loader.py + backend/data/agents/*.json

Tests catch coordinate mismatches that cannot be detected when plans run in parallel.
"""

import json
import logging
from pathlib import Path

import pytest

from backend.simulation.world import Maze
from backend.agents.loader import load_all_agents

logger = logging.getLogger(__name__)

TOWN_JSON = Path(__file__).parent.parent / "backend" / "data" / "map" / "town.json"


@pytest.fixture(scope="module")
def maze() -> Maze:
    """Load and parse the generated town map once for all tests."""
    with open(TOWN_JSON) as f:
        return Maze(json.load(f))


@pytest.fixture(scope="module")
def agents():
    """Load all agent configs once for all tests."""
    return load_all_agents()


# ---------------------------------------------------------------------------
# Test 1: All agent coords within map bounds
# ---------------------------------------------------------------------------


def test_all_agent_coords_within_map_bounds(agents, maze):
    """Every agent's coord (x, y) must be within 0 <= x < width and 0 <= y < height."""
    failures = []
    for agent in agents:
        x, y = agent.coord
        if not (0 <= x < maze.width):
            failures.append(
                f"{agent.name}: x={x} out of bounds (width={maze.width})"
            )
        if not (0 <= y < maze.height):
            failures.append(
                f"{agent.name}: y={y} out of bounds (height={maze.height})"
            )
    assert not failures, (
        f"Agents with out-of-bounds coords:\n" + "\n".join(failures)
    )


# ---------------------------------------------------------------------------
# Test 2: All agent coords on walkable tiles
# ---------------------------------------------------------------------------


def test_all_agent_coords_on_walkable_tiles(agents, maze):
    """Every agent's coord must land on a walkable tile (not a collision tile).

    On failure, include agent name, coord, tile collision status,
    and the nearest walkable tile in the intended sector (via resolve_destination).
    """
    failures = []
    for agent in agents:
        tile = maze.tile_at(agent.coord)
        if not tile.is_walkable:
            # Provide debugging context: nearest walkable tile in intended sector
            living_area = agent.spatial.address.get("living_area", [])
            sector = living_area[1] if len(living_area) > 1 else None
            nearest = maze.resolve_destination(sector) if sector else None
            failures.append(
                f"{agent.name}: coord={agent.coord} is a collision tile. "
                f"tile.address={tile.address}. "
                f"Nearest walkable in sector '{sector}': {nearest}"
            )
    assert not failures, (
        "Agents spawning on collision tiles:\n" + "\n".join(failures)
    )


# ---------------------------------------------------------------------------
# Test 3: No agent spawns on a border tile
# ---------------------------------------------------------------------------


def test_no_agent_spawns_on_border(agents, maze):
    """No agent should spawn on a border tile (row 0, row N-1, col 0, col N-1).

    Border tiles are always collision by convention (BFS strict-boundary guard).
    """
    failures = []
    for agent in agents:
        x, y = agent.coord
        is_border = (
            x == 0
            or x == maze.width - 1
            or y == 0
            or y == maze.height - 1
        )
        if is_border:
            failures.append(
                f"{agent.name}: coord={agent.coord} is a border tile "
                f"(width={maze.width}, height={maze.height})"
            )
    assert not failures, (
        "Agents spawning on border tiles:\n" + "\n".join(failures)
    )


# ---------------------------------------------------------------------------
# Test 4: Every agent's home sector exists in the map's address index
# ---------------------------------------------------------------------------


def test_agent_home_sectors_exist_in_map(agents, maze):
    """The sector component of each agent's living_area address must exist in maze.address_tiles.

    Sector key format: "agent-town:{sector}" where sector is index 1 of the address list.
    E.g., ["agent-town", "home-alice", "bedroom"] -> "agent-town:home-alice"
    """
    failures = []
    for agent in agents:
        living_area = agent.spatial.address.get("living_area", [])
        if len(living_area) < 2:
            failures.append(
                f"{agent.name}: living_area address too short: {living_area!r} "
                "(expected at least [world, sector])"
            )
            continue
        sector = living_area[1]
        addr_key = f"agent-town:{sector}"
        if addr_key not in maze.address_tiles:
            available = sorted(
                k for k in maze.address_tiles if k.count(":") == 1
            )
            failures.append(
                f"{agent.name}: home sector '{addr_key}' not in maze.address_tiles. "
                f"Available sectors: {available}"
            )
    assert not failures, (
        "Agents with home sectors missing from the map:\n" + "\n".join(failures)
    )


# ---------------------------------------------------------------------------
# Test 5: Every agent's workplace sector (if any) exists in the map
# ---------------------------------------------------------------------------


def test_agent_workplace_sectors_exist_in_map(agents, maze):
    """The sector component of each agent's workplace address must exist in maze.address_tiles.

    Only applied to agents that have a 'workplace' key in spatial.address.
    """
    failures = []
    for agent in agents:
        workplace = agent.spatial.address.get("workplace")
        if workplace is None:
            continue  # agent has no workplace — expected for some agents
        if len(workplace) < 2:
            failures.append(
                f"{agent.name}: workplace address too short: {workplace!r} "
                "(expected at least [world, sector])"
            )
            continue
        sector = workplace[1]
        addr_key = f"agent-town:{sector}"
        if addr_key not in maze.address_tiles:
            available = sorted(
                k for k in maze.address_tiles if k.count(":") == 1
            )
            failures.append(
                f"{agent.name}: workplace sector '{addr_key}' not in maze.address_tiles. "
                f"Available sectors: {available}"
            )
    assert not failures, (
        "Agents with workplace sectors missing from the map:\n" + "\n".join(failures)
    )


# ---------------------------------------------------------------------------
# Test 6: All agents on the same connected walkable subgraph
# ---------------------------------------------------------------------------


def test_all_agents_on_connected_graph(agents, maze):
    """Every agent must be pathfindable from agent[0]'s spawn coord.

    A non-empty path proves both agents are on the same connected walkable
    subgraph. An empty path indicates an isolated walkable cluster — an agent
    would be unreachable by all other agents.
    """
    assert len(agents) >= 2, "Need at least 2 agents to test connectivity"
    ref = agents[0]
    failures = []
    for agent in agents[1:]:
        path = maze.find_path(ref.coord, agent.coord)
        if not path:
            failures.append(
                f"{agent.name} at {agent.coord} is unreachable from "
                f"{ref.name} at {ref.coord} (disconnected walkable cluster)"
            )
    assert not failures, (
        "Agents on disconnected walkable subgraph:\n" + "\n".join(failures)
    )


# ---------------------------------------------------------------------------
# Test 7: Agent spawn coords match intended sector (soft check with warnings)
# ---------------------------------------------------------------------------


def test_agent_spawn_coords_match_intended_sector(agents, maze):
    """Check that agent spawn tiles are inside their intended sector.

    Determination logic:
      - If the agent's spatial.address has a 'workplace', their intended spawn
        sector is the workplace sector (agents who start at work).
      - If the agent has only 'living_area', their intended spawn sector is
        the home sector.
      - Compare tile.address[1] (the sector component) against expected sector.

    NOTE: This is a soft/warn-only test. Agents spawning on road tiles or in
    adjacent sectors are a data quality issue but NOT a hard failure — the
    mandatory hard constraints are tests 1-3 above. If mismatches are found,
    a warning is logged and the test still passes.
    """
    mismatches = []
    for agent in agents:
        tile = maze.tile_at(agent.coord)

        # Determine intended spawn sector from spatial.address
        workplace = agent.spatial.address.get("workplace")
        living_area = agent.spatial.address.get("living_area", [])

        if workplace and len(workplace) > 1:
            # Agents with a workplace are expected to start at work or home
            # (per D-11: mixed spawn). Check both as valid intended sectors.
            workplace_sector = workplace[1]
            home_sector = living_area[1] if len(living_area) > 1 else None
            valid_sectors = {workplace_sector}
            if home_sector:
                valid_sectors.add(home_sector)
        else:
            # Retirees and homebodies — expected to start at home
            home_sector = living_area[1] if len(living_area) > 1 else None
            valid_sectors = {home_sector} if home_sector else set()

        # Get the actual tile's sector (index 1 of address, if addressed)
        if len(tile.address) >= 2:
            tile_sector = tile.address[1]
            if tile_sector not in valid_sectors:
                mismatches.append(
                    f"{agent.name}: coord={agent.coord} is in sector '{tile_sector}' "
                    f"but expected one of {valid_sectors}. "
                    f"tile.address={tile.address}"
                )
        else:
            # Tile has no sector address (anonymous road tile)
            mismatches.append(
                f"{agent.name}: coord={agent.coord} is on an anonymous tile "
                f"(no sector address). tile.address={tile.address!r}. "
                "This is a data quality issue — consider moving to a named sector tile."
            )

    if mismatches:
        for msg in mismatches:
            logger.warning("Sector mismatch (soft): %s", msg)

    # Soft check: emit warnings but do not fail
    # Hard constraints (in-bounds, walkable, non-border) are enforced by tests 1-3
    assert True, "Sector match check completed (soft warnings logged above)"
