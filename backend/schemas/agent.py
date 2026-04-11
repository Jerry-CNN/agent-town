"""Agent-domain Pydantic schemas for Agent Town backend.

Contains: AgentAction, ArenaAction, AgentScratch, AgentSpatial, AgentConfig
"""
from pydantic import BaseModel, Field


class AgentAction(BaseModel):
    """Agent decision schema — used by instructor for structured LLM output in Phase 3."""
    destination: str
    activity: str
    reasoning: str


class ArenaAction(BaseModel):
    """Arena-level destination choice within a sector (D-07, Plan 09-02).

    After an agent picks a sector (e.g. "cafe"), this schema captures the
    arena-level pick (e.g. "seating" vs "kitchen"). Only used for sectors
    with multiple arenas (D-09: skip arena call for single-room sectors).
    """
    arena: str = Field(..., description="The specific area within the sector to go to")
    reasoning: str = Field(default="", description="Brief reasoning for arena choice")


class AgentScratch(BaseModel):
    """Agent personality and background -- the 'scratch pad' from the reference implementation."""
    age: int
    innate: str       # personality traits, comma-separated e.g. "warm, creative, curious"
    learned: str      # background paragraph
    lifestyle: str    # sleep/wake patterns and daily habits
    daily_plan: str   # routine template for LLM to fill in Phase 3


class AgentSpatial(BaseModel):
    """Agent's spatial knowledge -- known locations and their hierarchical structure."""
    address: dict[str, list[str]]  # named addresses e.g. {"living_area": ["agent-town", "home-alice", "bedroom"]}
    tree: dict                     # spatial knowledge tree (nested dict of known locations)


class AgentConfig(BaseModel):
    """Complete agent configuration loaded from a JSON config file.

    Schema mirrors the reference implementation's agent.json format (GenerativeAgentsCN),
    translated to English and extended with Agent Town's thematic locations.
    Consumed by Phase 3 (cognition), Phase 4 (simulation), and Phase 5 (frontend labels).
    """
    name: str
    coord: tuple[int, int]   # spawn position (x, y) on the tile grid
    currently: str            # current situation summary (seed for Phase 3 context)
    scratch: AgentScratch
    spatial: AgentSpatial
