"""Unit tests for the Agent class (Phase 7, Plan 02).

TDD: Tests written first (RED), then implementation makes them pass (GREEN).
All cognition functions are mocked — no real LLM calls.

Covers:
  - Agent can be constructed from AgentConfig with all required fields accessible
  - Agent.perceive() delegates to cognition.perceive.perceive() with correct args
  - Agent.decide() delegates to cognition.decide.decide_action() with correct args
  - Agent.converse() orchestrates attempt_conversation + run_conversation correctly
  - Agent.reflect() raises NotImplementedError("Reflection is Phase 11 scope")
  - No chromadb import in the agent module (D-02)
  - No circular import between agent.py and engine.py (D-03)
"""
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_agent_config(name: str = "Alice", coord: tuple = (5, 5)):
    """Build a minimal valid AgentConfig for testing."""
    from backend.schemas import AgentConfig, AgentScratch, AgentSpatial
    return AgentConfig(
        name=name,
        coord=coord,
        currently="standing around",
        scratch=AgentScratch(
            age=30,
            innate="curious, friendly",
            learned="a town resident",
            lifestyle="wakes at 7am",
            daily_plan="morning routine, work, leisure",
        ),
        spatial=AgentSpatial(
            address={"home": ["agent-town", "home", "bedroom"]},
            tree={"agent-town": {"cafe": {}, "park": {}}},
        ),
    )


# ---------------------------------------------------------------------------
# Test 1: Field access
# ---------------------------------------------------------------------------


def test_agent_has_all_required_fields():
    """Agent can be constructed from AgentConfig and all fields are accessible.

    Matches the fields from AgentState that Agent replaces.
    """
    from backend.agents.agent import Agent
    config = _make_agent_config("Alice", (5, 5))

    agent = Agent(
        name="Alice",
        config=config,
        coord=(5, 5),
        path=[(6, 5), (7, 5)],
        current_activity="walking",
        schedule=[],
    )

    assert agent.name == "Alice"
    assert agent.config is config
    assert agent.coord == (5, 5)
    assert agent.path == [(6, 5), (7, 5)]
    assert agent.current_activity == "walking"
    assert agent.schedule == []

    # Verify mutable — can update without errors
    agent.coord = (6, 5)
    agent.path.pop(0)
    agent.current_activity = "at cafe"
    assert agent.coord == (6, 5)
    assert agent.path == [(7, 5)]
    assert agent.current_activity == "at cafe"


def test_agent_default_fields():
    """Agent can be constructed with only required fields; optional fields default correctly."""
    from backend.agents.agent import Agent
    config = _make_agent_config("Bob", (3, 3))

    agent = Agent(name="Bob", config=config, coord=(3, 3))

    assert agent.path == []
    assert agent.current_activity == ""
    assert agent.schedule == []


# ---------------------------------------------------------------------------
# Test 2: perceive() delegation
# ---------------------------------------------------------------------------


def test_agent_perceive_delegates_with_correct_args():
    """Agent.perceive(maze, all_agents) calls cognition.perceive.perceive() with
    agent_coord=self.coord and agent_name=self.name.
    """
    from backend.agents.agent import Agent
    from backend.schemas import PerceptionResult

    config = _make_agent_config("Alice", (5, 5))
    agent = Agent(name="Alice", config=config, coord=(5, 5))

    mock_result = PerceptionResult(nearby_events=[], nearby_agents=[], location="cafe")
    mock_maze = MagicMock()
    all_agents = {"Bob": {"coord": (6, 6), "current_activity": "idle"}}

    with patch("backend.agents.cognition.perceive.perceive", return_value=mock_result) as mock_perceive:
        result = agent.perceive(maze=mock_maze, all_agents=all_agents)

    mock_perceive.assert_called_once_with(
        agent_coord=(5, 5),
        agent_name="Alice",
        maze=mock_maze,
        all_agents=all_agents,
    )
    assert result is mock_result


# ---------------------------------------------------------------------------
# Test 3: decide() delegation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_decide_delegates_with_correct_args():
    """Agent.decide(simulation_id, perception) calls decide_action() with self.name,
    self.config.scratch, self.config.spatial, self.current_activity.
    """
    from backend.agents.agent import Agent
    from backend.schemas import AgentAction, PerceptionResult

    config = _make_agent_config("Alice", (5, 5))
    agent = Agent(name="Alice", config=config, coord=(5, 5), current_activity="working")

    mock_action = AgentAction(destination="cafe", activity="getting coffee", reasoning="want coffee")
    perception = PerceptionResult(nearby_events=[], nearby_agents=[], location="park")

    with patch("backend.agents.cognition.decide.decide_action", new_callable=AsyncMock, return_value=mock_action) as mock_decide:
        result = await agent.decide(simulation_id="sim-01", perception=perception)

    mock_decide.assert_called_once_with(
        simulation_id="sim-01",
        agent_name="Alice",
        agent_scratch=config.scratch,
        agent_spatial=config.spatial,
        current_activity="working",
        perception=perception,
        current_schedule=[],
    )
    assert result is mock_action


@pytest.mark.asyncio
async def test_agent_decide_passes_through_none():
    """Test 12 (Codex P2-7): Agent.decide() return type is AgentAction | None.

    When decide_action returns None (per-sector gating skip, D-08), Agent.decide()
    passes None through to the caller unchanged.
    """
    from backend.agents.agent import Agent
    from backend.schemas import PerceptionResult

    config = _make_agent_config("Alice", (5, 5))
    agent = Agent(name="Alice", config=config, coord=(5, 5), current_activity="working")
    perception = PerceptionResult(nearby_events=[], nearby_agents=[], location="park")

    with patch("backend.agents.cognition.decide.decide_action",
               new_callable=AsyncMock, return_value=None):
        result = await agent.decide(simulation_id="sim-01", perception=perception)

    assert result is None


# ---------------------------------------------------------------------------
# Test 4: converse() orchestration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_converse_returns_none_when_attempt_fails():
    """Agent.converse() returns None if attempt_conversation returns False."""
    from backend.agents.agent import Agent

    config_a = _make_agent_config("Alice", (5, 5))
    config_b = _make_agent_config("Bob", (6, 5))
    agent_a = Agent(name="Alice", config=config_a, coord=(5, 5))
    agent_b = Agent(name="Bob", config=config_b, coord=(6, 5))
    mock_tile = MagicMock()
    mock_tile.address = ["agent-town", "cafe"]
    mock_tile.get_address.return_value = "agent-town:cafe"
    mock_maze = MagicMock()
    mock_maze.tile_at.return_value = mock_tile

    with patch("backend.agents.cognition.converse.attempt_conversation", new_callable=AsyncMock, return_value=False) as mock_attempt, \
         patch("backend.agents.cognition.converse.run_conversation", new_callable=AsyncMock) as mock_run:

        result = await agent_a.converse(other=agent_b, maze=mock_maze, simulation_id="sim-01")

    assert result is None
    mock_attempt.assert_called_once()
    mock_run.assert_not_called()


@pytest.mark.asyncio
async def test_agent_converse_returns_result_when_attempt_succeeds():
    """Agent.converse() calls run_conversation and returns its result when attempt returns True."""
    from backend.agents.agent import Agent

    config_a = _make_agent_config("Alice", (5, 5))
    config_b = _make_agent_config("Bob", (6, 5))
    agent_a = Agent(name="Alice", config=config_a, coord=(5, 5), current_activity="reading")
    agent_b = Agent(name="Bob", config=config_b, coord=(6, 5), current_activity="idle")
    mock_tile = MagicMock()
    mock_tile.address = ["agent-town", "cafe"]
    mock_tile.get_address.return_value = "agent-town:cafe"
    mock_maze = MagicMock()
    mock_maze.tile_at.return_value = mock_tile

    mock_convo_result = {"turns": ["hi", "hello"], "summary": "they chatted"}

    with patch("backend.agents.cognition.converse.attempt_conversation", new_callable=AsyncMock, return_value=True) as mock_attempt, \
         patch("backend.agents.cognition.converse.run_conversation", new_callable=AsyncMock, return_value=mock_convo_result) as mock_run:

        result = await agent_a.converse(other=agent_b, maze=mock_maze, simulation_id="sim-01")

    assert result is mock_convo_result
    mock_attempt.assert_called_once_with(
        simulation_id="sim-01",
        agent_name="Alice",
        agent_scratch=config_a.scratch,
        other_name="Bob",
        other_activity="idle",
        agent_current_activity="reading",
        location="agent-town:cafe",
    )
    mock_run.assert_called_once_with(
        simulation_id="sim-01",
        agent_a_name="Alice",
        agent_a_scratch=config_a.scratch,
        agent_b_name="Bob",
        agent_b_scratch=config_b.scratch,
        location="agent-town:cafe",
        remaining_schedule_a=[],
        remaining_schedule_b=[],
    )


# ---------------------------------------------------------------------------
# Test 5: reflect() raises NotImplementedError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reflect_raises_not_implemented():
    """Agent.reflect() raises NotImplementedError with message containing 'Phase 11'."""
    from backend.agents.agent import Agent

    config = _make_agent_config("Alice")
    agent = Agent(name="Alice", config=config, coord=(5, 5))

    with pytest.raises(NotImplementedError) as exc_info:
        await agent.reflect()

    assert "Phase 11" in str(exc_info.value), \
        f"Expected 'Phase 11' in NotImplementedError message, got: {exc_info.value}"


# ---------------------------------------------------------------------------
# Test 6: No chromadb import
# ---------------------------------------------------------------------------


def test_no_chromadb_import_in_agent_module():
    """agent.py does NOT import chromadb (D-02: memory via store.py module calls only).

    Checks sys.modules after importing the module to detect any chromadb import
    that was triggered by the agent module's import chain.
    """
    # Ensure the module is imported
    import backend.agents.agent  # noqa: F401

    # chromadb should NOT be present in the agent module's direct imports.
    # We check by inspecting the module source via __file__ (grep approach).
    import inspect
    import backend.agents.agent as agent_module

    source = inspect.getsource(agent_module)
    assert "import chromadb" not in source, \
        "agent.py must not import chromadb (D-02: memory only via store.py)"
    # Check that chromadb is not imported (allows docstring mentions as comments)
    import ast
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.name for alias in node.names]
            module = getattr(node, "module", "") or ""
            assert "chromadb" not in module and all("chromadb" not in n for n in names), \
                "agent.py must not import chromadb (D-02)"


# ---------------------------------------------------------------------------
# Test 7: No circular import
# ---------------------------------------------------------------------------


def test_no_circular_import_with_engine():
    """Importing Agent and SimulationEngine together does NOT raise ImportError.

    This verifies D-03: Agent class must not import from backend.simulation.engine.
    """
    # If this does not raise, the imports are clean
    from backend.agents.agent import Agent  # noqa: F401
    from backend.simulation.engine import SimulationEngine  # noqa: F401
    # If we get here without exception, circular import is not present
    assert Agent is not None
    assert SimulationEngine is not None


# ---------------------------------------------------------------------------
# Test 8: converse method exists and is async
# ---------------------------------------------------------------------------


def test_agent_has_async_converse_method():
    """Agent has an async converse method with the expected signature."""
    import asyncio
    import inspect
    from backend.agents.agent import Agent

    assert hasattr(Agent, "converse"), "Agent must have a 'converse' method"
    assert asyncio.iscoroutinefunction(Agent.converse), \
        "Agent.converse must be an async coroutine function"


# ---------------------------------------------------------------------------
# Test 9: reflect method exists and is async
# ---------------------------------------------------------------------------


def test_agent_has_async_reflect_method():
    """Agent has an async reflect method."""
    import asyncio
    from backend.agents.agent import Agent

    assert hasattr(Agent, "reflect"), "Agent must have a 'reflect' method"
    assert asyncio.iscoroutinefunction(Agent.reflect), \
        "Agent.reflect must be an async coroutine function"
