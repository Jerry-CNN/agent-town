"""Agent-domain Pydantic schemas for Agent Town backend.

Contains: AgentAction, AgentScratch, AgentSpatial, AgentConfig
"""
from pydantic import BaseModel


class AgentAction(BaseModel):
    """Agent decision schema — used by instructor for structured LLM output in Phase 3."""
    destination: str
    activity: str
    reasoning: str


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
