"""Tile-grid perception scan for Agent Town agents.

Pure Python, zero LLM calls. Agents perceive nearby agents and events
within a configurable tile-radius by scanning the Maze tile grid.

Design decisions:
  - D-06: Tile-based vision radius (~5 tiles, Euclidean distance)
  - D-07: Perceives other agents (name, current activity), events within radius,
    and location context (sector/arena name of current tile)
  - Anti-Pattern 1 (03-RESEARCH.md): Perception must NOT make LLM calls --
    it is a cheap, frequent operation that feeds into decision-making.

Reference: GenerativeAgentsCN/generative_agents/modules/perceive.py
"""
import math
from backend.simulation.world import Maze
from backend.schemas import PerceptionResult

# Maximum number of events to return (reference att_bandwidth limit)
_MAX_EVENTS = 10


def perceive(
    agent_coord: tuple[int, int],
    agent_name: str,
    maze: Maze,
    all_agents: dict[str, dict],
    radius: int = 5,
) -> PerceptionResult:
    """Scan the tile grid within *radius* tiles and return a PerceptionResult.

    Args:
        agent_coord:  (x, y) position of the perceiving agent on the tile grid.
        agent_name:   Name of the perceiving agent (for self-exclusion).
        maze:         The Maze instance providing tile data.
        all_agents:   Dict mapping agent_name -> dict with keys:
                      - "coord": tuple[int, int] -- agent's tile position
                      - "current_activity": str -- what the agent is doing
                      This decouples perception from any specific AgentState class.
        radius:       Maximum Euclidean distance (in tiles) to scan. Default 5.

    Returns:
        PerceptionResult with:
          - nearby_agents: agents within radius (excluding self), sorted by distance
          - nearby_events: events on tiles within radius, sorted by distance, capped at 10
          - location: address string of the current tile
    """
    ax, ay = agent_coord
    nearby_events: list[dict] = []
    nearby_agents: list[dict] = []

    # Scan square bounding box then filter by Euclidean distance
    for ty in range(ay - radius, ay + radius + 1):
        for tx in range(ax - radius, ax + radius + 1):
            # Compute Euclidean distance
            dist = math.sqrt((tx - ax) ** 2 + (ty - ay) ** 2)
            if dist > radius:
                continue

            # Fetch tile -- skip out-of-bounds coordinates
            try:
                tile = maze.tile_at((tx, ty))
            except IndexError:
                continue

            # Collect events from this tile
            for event_key, event_data in tile._events.items():
                nearby_events.append({
                    "distance": dist,
                    "event": event_data,
                    "key": event_key,
                })

            # Check if any agent is at this tile position
            for name, agent_info in all_agents.items():
                if name == agent_name:
                    continue  # self-exclusion
                if agent_info["coord"] == (tx, ty):
                    nearby_agents.append({
                        "name": name,
                        "activity": agent_info["current_activity"],
                        "distance": dist,
                    })

    # Sort by distance ascending (closest first)
    nearby_events.sort(key=lambda e: e["distance"])
    nearby_agents.sort(key=lambda a: a["distance"])

    # Cap events at bandwidth limit
    nearby_events = nearby_events[:_MAX_EVENTS]

    # Get location string from current tile's address
    try:
        current_tile = maze.tile_at(agent_coord)
        location = current_tile.get_address(as_list=False)
    except IndexError:
        location = ""

    return PerceptionResult(
        nearby_events=nearby_events,
        nearby_agents=nearby_agents,
        location=location,
    )
