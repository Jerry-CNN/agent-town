# Phase 2: World & Navigation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-09
**Phase:** 02-world-navigation
**Areas discussed:** Town layout & locations, Map data format, Agent cast & personalities, Pathfinding behavior, Tile size & scale, Agent spawn positions, Location metadata

---

## Town layout & locations

| Option | Description | Selected |
|--------|-------------|----------|
| Small (40x40) | Compact town, agents always near each other, good for 5-10 agents | |
| Medium (60x60) | Balanced, distinct neighborhoods but agents still cross paths | |
| Large (100x100+) | Sprawling town like reference, agents spread out, better for 15-25 agents | ✓ |

**User's choice:** Large (100x100+)
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Roadmap set as-is | Stock exchange, wedding hall, park, homes, shops, cafe, office | ✓ |
| Expanded set | Add library, gym, restaurant, church/temple, hospital, town square | |
| You decide | Claude picks locations supporting event injection use cases | |

**User's choice:** Roadmap set as-is
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Neighborhood clusters | Group related locations: residential, commercial, civic, green space | ✓ |
| Town center + outskirts | Central square with public buildings, homes and park on edges | |
| You decide | Claude designs layout for best agent movement patterns | |

**User's choice:** Neighborhood clusters
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Named areas only | Each location is a region of walkable tiles with a name | |
| Hierarchical (like ref) | Locations have sub-areas: 'Cafe > counter', 'Office > desk 3' | |
| You decide | Claude picks depth level based on Phase 3 needs | ✓ |

**User's choice:** You decide (Claude's discretion)
**Notes:** None

---

## Map data format

| Option | Description | Selected |
|--------|-------------|----------|
| Tiled JSON (Recommended) | Design in Tiled editor, export JSON, load at runtime with pixi-tiledmap | ✓ |
| Python-defined grid | Define map programmatically, locations as coordinate ranges | |
| Simple JSON config | Hand-written JSON with location bounding boxes | |

**User's choice:** Tiled JSON
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated collision layer | Separate Tiled layer marking walkable vs obstacle tiles | ✓ |
| Tile property flags | Each tile type has a 'walkable' property in tileset | |
| You decide | Claude picks based on Tiled + pixi-tiledmap support | |

**User's choice:** Dedicated collision layer
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Claude creates it | Claude generates Tiled JSON programmatically, user reviews | ✓ |
| I'll design it in Tiled | User designs town visually in Tiled editor | |
| Placeholder first | Simple programmatic placeholder, replace with Tiled map later | |

**User's choice:** Claude creates it
**Notes:** None

---

## Agent cast & personalities

| Option | Description | Selected |
|--------|-------------|----------|
| 5 agents | Minimum per AGT-01, small cast, each distinct and memorable | |
| 8-10 agents | Enough variety for group dynamics, cliques, gossip chains | ✓ |
| 15+ agents | Bustling town feel, more emergent behavior but harder to track | |

**User's choice:** 8-10 agents
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Diverse occupations | Mix of jobs: trader, baker, florist, office worker, barista | ✓ |
| Social archetypes | Characters by personality: the gossip, introvert, overachiever | |
| You decide | Claude designs cast for maximum emergent behavior | |

**User's choice:** Diverse occupations
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| JSON config files | Each agent in a JSON file (name, traits, occupation, home, routine) | ✓ |
| Python dataclass/Pydantic | Agent definitions hardcoded as Pydantic models | |
| You decide | Claude picks format best for architecture | |

**User's choice:** JSON config files
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-defined routines | Config includes full daily schedule, LLM modifies based on events | |
| LLM-generated routines | Only personality + occupation, LLM generates routine on start | |
| Hybrid | Rough template in config, LLM fills in details and adapts | ✓ |

**User's choice:** Hybrid
**Notes:** None

---

## Pathfinding behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Nearest entrance tile | Each location has entrance tiles, agent paths to closest entrance | |
| Any walkable tile in zone | Agent picks any walkable tile within location's area | ✓ |
| You decide | Claude picks based on Tiled format and movement patterns | |

**User's choice:** Any walkable tile in zone
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| 1 tile per sim step | Like reference, agents move one tile at a time | |
| Variable speed | Some agents faster based on personality/urgency | |
| You decide | Claude picks based on map size and natural feel | ✓ |

**User's choice:** You decide (Claude's discretion)
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Pure BFS (Recommended) | Shortest unweighted path, all walkable tiles equal | ✓ |
| Weighted A* | Tiles have movement costs, roads cheaper than grass | |
| You decide | Claude picks algorithm based on size and performance | |

**User's choice:** Pure BFS
**Notes:** None

---

## Tile size & scale

| Option | Description | Selected |
|--------|-------------|----------|
| 32px tiles (Recommended) | Standard pixel-art, reference uses 32px, works with pixi-tiledmap | ✓ |
| 16px tiles | More detail but 4x more tiles, may look small | |
| You decide | Claude picks based on pixi-tiledmap and tileset support | |

**User's choice:** 32px tiles
**Notes:** None

---

## Agent spawn positions

| Option | Description | Selected |
|--------|-------------|----------|
| At their home | Each agent starts at their home location | |
| At their workplace | Agents start at associated work location | |
| You decide | Claude picks for best initial experience | |

**User's choice:** Mixture of both (free text)
**Notes:** "We can have a mixture of both." — varied initial positions for a more interesting first impression.

---

## Location metadata

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal (name + tiles) | Locations are named zones, LLM infers activities from name | ✓ |
| Rich metadata | Activity types, operating hours, capacity per location | |
| You decide | Claude picks based on Phase 3 cognition needs | |

**User's choice:** Minimal (name + tiles)
**Notes:** None

---

## Claude's Discretion

- Interior room depth (hierarchical sub-areas vs flat named zones)
- Agent movement speed per simulation step

## Deferred Ideas

None — discussion stayed within phase scope
