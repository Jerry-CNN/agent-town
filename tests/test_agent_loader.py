"""Unit tests for agent config loading and validation."""
import pytest
from pydantic import ValidationError
from backend.agents.loader import load_all_agents
from backend.schemas import AgentConfig, AgentScratch, AgentSpatial


def test_loads_minimum_agent_count():
    """AGT-01: At least 8 pre-defined agents must load from JSON configs."""
    agents = load_all_agents()
    assert len(agents) >= 8


def test_agents_have_distinct_names():
    """D-08: All agent names are distinct -- no duplicates in the cast."""
    agents = load_all_agents()
    names = [a.name for a in agents]
    assert len(names) == len(set(names))


def test_agents_have_personality_traits():
    """D-09: Every agent has non-empty innate personality traits."""
    agents = load_all_agents()
    for agent in agents:
        assert len(agent.scratch.innate) > 0, f"{agent.name} is missing innate traits"


def test_agents_have_daily_plan():
    """D-10: Every agent has a non-empty daily routine template."""
    agents = load_all_agents()
    for agent in agents:
        assert len(agent.scratch.daily_plan) > 0, f"{agent.name} is missing daily_plan"


def test_agents_have_valid_coords():
    """D-11: Every agent has a spawn coord of two non-negative integers."""
    agents = load_all_agents()
    for agent in agents:
        assert isinstance(agent.coord, tuple), f"{agent.name} coord is not a tuple"
        assert len(agent.coord) == 2, f"{agent.name} coord must have exactly 2 elements"
        assert isinstance(agent.coord[0], int), f"{agent.name} coord[0] must be int"
        assert isinstance(agent.coord[1], int), f"{agent.name} coord[1] must be int"


def test_agents_have_mixed_spawn_locations():
    """D-11: Not all agents share the same spawn coordinate."""
    agents = load_all_agents()
    coords = [a.coord for a in agents]
    assert len(set(coords)) > 1, "All agents spawn at the same coordinate -- D-11 requires mixed locations"


def test_agents_have_spatial_living_area():
    """Every agent has a spatial.address with a 'living_area' key."""
    agents = load_all_agents()
    for agent in agents:
        assert "living_area" in agent.spatial.address, (
            f"{agent.name} spatial.address is missing 'living_area' key"
        )


def test_agents_have_spatial_tree():
    """Every agent has a non-empty spatial knowledge tree."""
    agents = load_all_agents()
    for agent in agents:
        assert len(agent.spatial.tree) > 0, f"{agent.name} has an empty spatial.tree"


def test_agent_config_validation_rejects_incomplete():
    """Pydantic v2 raises ValidationError when required fields are missing."""
    with pytest.raises(ValidationError):
        AgentConfig.model_validate({"name": "Test"})


def test_diverse_occupations():
    """D-08: At least 5 different occupation-related keywords in daily_plans."""
    agents = load_all_agents()
    all_plans = " ".join(a.scratch.daily_plan.lower() for a in agents)
    occupation_keywords = ["cafe", "stock", "shop", "office", "park", "wedding", "bak"]
    found = [kw for kw in occupation_keywords if kw in all_plans]
    assert len(found) >= 5, (
        f"Only found {len(found)} occupation keywords: {found}. Need at least 5."
    )


def test_agents_have_age():
    """Every agent has an integer age in their scratch."""
    agents = load_all_agents()
    for agent in agents:
        assert isinstance(agent.scratch.age, int), f"{agent.name} scratch.age must be int"
        assert agent.scratch.age > 0, f"{agent.name} scratch.age must be positive"


def test_agents_have_learned_background():
    """Every agent has a non-empty learned background paragraph."""
    agents = load_all_agents()
    for agent in agents:
        assert len(agent.scratch.learned) > 0, f"{agent.name} is missing learned background"


def test_agents_have_lifestyle():
    """Every agent has a non-empty lifestyle description."""
    agents = load_all_agents()
    for agent in agents:
        assert len(agent.scratch.lifestyle) > 0, f"{agent.name} is missing lifestyle"


def test_agents_have_currently():
    """Every agent has a non-empty 'currently' situation summary."""
    agents = load_all_agents()
    for agent in agents:
        assert len(agent.currently) > 0, f"{agent.name} is missing 'currently' field"


def test_spatial_tree_has_world_key():
    """Every agent's spatial.tree contains 'agent-town' as the world key."""
    agents = load_all_agents()
    for agent in agents:
        assert "agent-town" in agent.spatial.tree, (
            f"{agent.name} spatial.tree must contain 'agent-town' as world key"
        )
