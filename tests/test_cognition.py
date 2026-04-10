"""Unit tests for agent cognition modules: perception and schedule planning.

TDD: Tests written first (RED), then implementation makes them pass (GREEN).
"""
import math
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


# ---------------------------------------------------------------------------
# Shared maze fixture for perception tests
# ---------------------------------------------------------------------------

SMALL_MAP_CONFIG = {
    "world": "agent-town",
    "tile_size": 32,
    "size": [30, 30],  # 30x30 grid
    "tile_address_keys": ["world", "sector", "arena"],
    "tiles": [
        # Border walls
        *[{"coord": [x, 0], "collision": True} for x in range(30)],
        *[{"coord": [x, 29], "collision": True} for x in range(30)],
        *[{"coord": [0, y], "collision": True} for y in range(1, 29)],
        *[{"coord": [29, y], "collision": True} for y in range(1, 29)],
        # Addressed interior tiles (near center)
        {"coord": [10, 10], "address": ["cafe", "seating"]},
        {"coord": [11, 10], "address": ["cafe", "seating"]},
        {"coord": [12, 12], "address": ["cafe", "counter"]},
        {"coord": [20, 20], "address": ["park", "bench"]},
    ],
}


@pytest.fixture
def small_maze():
    """A small Maze fixture for perception tests."""
    from backend.simulation.world import Maze
    return Maze(SMALL_MAP_CONFIG)


# ---------------------------------------------------------------------------
# Task 1: Perception tests (RED phase -- no perceive module yet)
# ---------------------------------------------------------------------------


def test_perceive_detects_nearby_agent(small_maze):
    """Agent at (10, 10) perceives another agent at (12, 12) — distance ~2.83 < 5."""
    from backend.agents.cognition.perceive import perceive

    all_agents = {
        "alice": {"coord": (10, 10), "current_activity": "brewing coffee"},
        "bob": {"coord": (12, 12), "current_activity": "reading newspaper"},
    }
    result = perceive(
        agent_coord=(10, 10),
        agent_name="alice",
        maze=small_maze,
        all_agents=all_agents,
        radius=5,
    )
    nearby_names = [a["name"] for a in result.nearby_agents]
    assert "bob" in nearby_names


def test_perceive_excludes_distant_agent(small_maze):
    """Agent at (10, 10) does NOT perceive agent at (20, 20) — distance ~14.1 > 5."""
    from backend.agents.cognition.perceive import perceive

    all_agents = {
        "alice": {"coord": (10, 10), "current_activity": "brewing coffee"},
        "charlie": {"coord": (20, 20), "current_activity": "walking"},
    }
    result = perceive(
        agent_coord=(10, 10),
        agent_name="alice",
        maze=small_maze,
        all_agents=all_agents,
        radius=5,
    )
    nearby_names = [a["name"] for a in result.nearby_agents]
    assert "charlie" not in nearby_names


def test_perceive_excludes_self(small_maze):
    """Agent does not perceive itself in the nearby_agents list."""
    from backend.agents.cognition.perceive import perceive

    all_agents = {
        "alice": {"coord": (10, 10), "current_activity": "brewing coffee"},
    }
    result = perceive(
        agent_coord=(10, 10),
        agent_name="alice",
        maze=small_maze,
        all_agents=all_agents,
        radius=5,
    )
    nearby_names = [a["name"] for a in result.nearby_agents]
    assert "alice" not in nearby_names


def test_perceive_detects_events_within_radius(small_maze):
    """Events stored on tiles within radius appear in nearby_events."""
    from backend.agents.cognition.perceive import perceive

    # Place an event on a tile at (11, 10) — distance 1 from (10, 10)
    tile = small_maze.tile_at((11, 10))
    tile._events["wedding_announcement"] = "There is a wedding tomorrow!"

    all_agents = {
        "alice": {"coord": (10, 10), "current_activity": "brewing coffee"},
    }
    result = perceive(
        agent_coord=(10, 10),
        agent_name="alice",
        maze=small_maze,
        all_agents=all_agents,
        radius=5,
    )
    assert len(result.nearby_events) > 0


def test_perceive_excludes_events_outside_radius(small_maze):
    """Events on tiles beyond radius are NOT returned."""
    from backend.agents.cognition.perceive import perceive

    # Place an event far away at (20, 20) — distance ~14.1 from (10, 10)
    tile = small_maze.tile_at((20, 20))
    tile._events["distant_event"] = "Something happening far away"

    all_agents = {
        "alice": {"coord": (10, 10), "current_activity": "brewing coffee"},
    }
    result = perceive(
        agent_coord=(10, 10),
        agent_name="alice",
        maze=small_maze,
        all_agents=all_agents,
        radius=5,
    )
    # distant_event should not appear
    event_values = [e.get("event") for e in result.nearby_events]
    assert "Something happening far away" not in event_values


def test_perceive_location_field(small_maze):
    """Location field contains the current tile's address string."""
    from backend.agents.cognition.perceive import perceive

    all_agents = {
        "alice": {"coord": (10, 10), "current_activity": "brewing coffee"},
    }
    result = perceive(
        agent_coord=(10, 10),
        agent_name="alice",
        maze=small_maze,
        all_agents=all_agents,
        radius=5,
    )
    # Tile at (10, 10) has address ["agent-town", "cafe", "seating"]
    assert "cafe" in result.location


def test_perceive_nearby_agents_include_activity(small_maze):
    """nearby_agents includes name and current_activity fields."""
    from backend.agents.cognition.perceive import perceive

    all_agents = {
        "alice": {"coord": (10, 10), "current_activity": "brewing coffee"},
        "bob": {"coord": (12, 12), "current_activity": "reading newspaper"},
    }
    result = perceive(
        agent_coord=(10, 10),
        agent_name="alice",
        maze=small_maze,
        all_agents=all_agents,
        radius=5,
    )
    bob_entry = next(a for a in result.nearby_agents if a["name"] == "bob")
    assert "activity" in bob_entry
    assert bob_entry["activity"] == "reading newspaper"


def test_perceive_results_sorted_by_distance(small_maze):
    """Results are sorted by distance (closest first)."""
    from backend.agents.cognition.perceive import perceive

    all_agents = {
        "alice": {"coord": (10, 10), "current_activity": "brewing coffee"},
        "bob": {"coord": (14, 10), "current_activity": "working"},   # distance 4
        "carol": {"coord": (11, 10), "current_activity": "chatting"}, # distance 1
    }
    result = perceive(
        agent_coord=(10, 10),
        agent_name="alice",
        maze=small_maze,
        all_agents=all_agents,
        radius=5,
    )
    distances = [a["distance"] for a in result.nearby_agents]
    assert distances == sorted(distances)


def test_perceive_radius_boundary(small_maze):
    """Agent exactly at radius boundary (5.0) is included; just outside is not."""
    from backend.agents.cognition.perceive import perceive

    # Agent at exactly (15, 10) — distance 5.0 from (10, 10)
    all_agents_inside = {
        "alice": {"coord": (10, 10), "current_activity": "brewing coffee"},
        "dave": {"coord": (15, 10), "current_activity": "walking"},  # dist = 5.0
    }
    result_inside = perceive(
        agent_coord=(10, 10),
        agent_name="alice",
        maze=small_maze,
        all_agents=all_agents_inside,
        radius=5,
    )
    # Agent at exactly radius=5 should be included (distance <= radius)
    nearby_names = [a["name"] for a in result_inside.nearby_agents]
    assert "dave" in nearby_names

    # Agent at (16, 10) — distance 6.0 from (10, 10), outside radius
    all_agents_outside = {
        "alice": {"coord": (10, 10), "current_activity": "brewing coffee"},
        "eve": {"coord": (16, 10), "current_activity": "walking"},  # dist = 6.0
    }
    result_outside = perceive(
        agent_coord=(10, 10),
        agent_name="alice",
        maze=small_maze,
        all_agents=all_agents_outside,
        radius=5,
    )
    nearby_names_outside = [a["name"] for a in result_outside.nearby_agents]
    assert "eve" not in nearby_names_outside


def test_perceive_returns_perception_result_type(small_maze):
    """perceive() returns a PerceptionResult instance."""
    from backend.agents.cognition.perceive import perceive
    from backend.schemas import PerceptionResult

    all_agents = {
        "alice": {"coord": (10, 10), "current_activity": "idle"},
    }
    result = perceive(
        agent_coord=(10, 10),
        agent_name="alice",
        maze=small_maze,
        all_agents=all_agents,
        radius=5,
    )
    assert isinstance(result, PerceptionResult)


def test_perceive_empty_agents(small_maze):
    """Perception works correctly when there are no other agents."""
    from backend.agents.cognition.perceive import perceive

    all_agents = {
        "alice": {"coord": (10, 10), "current_activity": "brewing coffee"},
    }
    result = perceive(
        agent_coord=(10, 10),
        agent_name="alice",
        maze=small_maze,
        all_agents=all_agents,
        radius=5,
    )
    assert result.nearby_agents == []


# ---------------------------------------------------------------------------
# Task 2: Schedule generation tests (RED phase -- no plan module yet)
# ---------------------------------------------------------------------------


def test_schedule_init_prompt_includes_daily_plan():
    """schedule_init_prompt must include the daily_plan template (Pitfall 4 prevention)."""
    from backend.prompts.schedule_init import schedule_init_prompt

    messages = schedule_init_prompt(
        agent_name="Alice",
        agent_age=28,
        agent_traits="warm, creative, curious",
        agent_lifestyle="early riser, loves morning walks",
        daily_plan_template="Wake up early, walk to the cafe, serve customers.",
    )
    all_content = " ".join(
        m["content"] for m in messages if isinstance(m.get("content"), str)
    )
    assert "Wake up early" in all_content


def test_schedule_init_prompt_includes_agent_name():
    """schedule_init_prompt must include the agent name."""
    from backend.prompts.schedule_init import schedule_init_prompt

    messages = schedule_init_prompt(
        agent_name="Alice",
        agent_age=28,
        agent_traits="warm, creative, curious",
        agent_lifestyle="early riser, loves morning walks",
        daily_plan_template="Wake up early, walk to the cafe.",
    )
    all_content = " ".join(
        m["content"] for m in messages if isinstance(m.get("content"), str)
    )
    assert "Alice" in all_content


def test_schedule_init_prompt_includes_traits():
    """schedule_init_prompt must include personality traits (innate)."""
    from backend.prompts.schedule_init import schedule_init_prompt

    messages = schedule_init_prompt(
        agent_name="Alice",
        agent_age=28,
        agent_traits="warm, creative, curious",
        agent_lifestyle="early riser, loves morning walks",
        daily_plan_template="Wake up early.",
    )
    all_content = " ".join(
        m["content"] for m in messages if isinstance(m.get("content"), str)
    )
    assert "warm" in all_content or "creative" in all_content or "curious" in all_content


def test_schedule_init_prompt_returns_messages_list():
    """schedule_init_prompt returns a list of message dicts."""
    from backend.prompts.schedule_init import schedule_init_prompt

    messages = schedule_init_prompt(
        agent_name="Alice",
        agent_age=28,
        agent_traits="warm, creative",
        agent_lifestyle="morning person",
        daily_plan_template="Wake up, go to work.",
    )
    assert isinstance(messages, list)
    assert len(messages) >= 1
    for m in messages:
        assert "role" in m
        assert "content" in m


def test_schedule_decompose_prompt_includes_activity():
    """schedule_decompose_prompt must include the hourly activity being decomposed."""
    from backend.prompts.schedule_decompose import schedule_decompose_prompt

    messages = schedule_decompose_prompt(
        agent_name="Alice",
        hourly_activity="open the cafe and brew the first batch",
        duration_minutes=60,
    )
    all_content = " ".join(
        m["content"] for m in messages if isinstance(m.get("content"), str)
    )
    assert "open the cafe" in all_content or "brew the first batch" in all_content


def test_schedule_decompose_prompt_returns_messages_list():
    """schedule_decompose_prompt returns a list of message dicts."""
    from backend.prompts.schedule_decompose import schedule_decompose_prompt

    messages = schedule_decompose_prompt(
        agent_name="Alice",
        hourly_activity="morning walk in the park",
        duration_minutes=60,
    )
    assert isinstance(messages, list)
    assert len(messages) >= 1


@pytest.mark.asyncio
async def test_generate_daily_schedule_returns_schedule_entries():
    """generate_daily_schedule returns a list of ScheduleEntry objects."""
    from backend.agents.cognition.plan import generate_daily_schedule
    from backend.schemas import AgentScratch, DailySchedule, ScheduleEntry

    mock_schedule = DailySchedule(
        activities=[
            "Wake up and get ready for the day",
            "Walk to the cafe and open up",
            "Serve morning customers",
            "Take a break at the park",
            "Return to cafe for afternoon shift",
            "Close cafe and head home",
        ],
        wake_hour=6,
    )

    scratch = AgentScratch(
        age=28,
        innate="warm, creative, curious",
        learned="Alice runs the local cafe and loves her community.",
        lifestyle="Early riser, loves morning walks before work.",
        daily_plan="Wake up early, walk to the cafe, open up and brew the first batch.",
    )

    with patch(
        "backend.agents.cognition.plan.complete_structured",
        new_callable=AsyncMock,
        return_value=mock_schedule,
    ):
        entries = await generate_daily_schedule("Alice", scratch)

    assert isinstance(entries, list)
    assert len(entries) > 0
    for entry in entries:
        assert isinstance(entry, ScheduleEntry)
        assert 0 <= entry.start_minute < 1440
        assert entry.describe


@pytest.mark.asyncio
async def test_generate_daily_schedule_uses_wake_hour():
    """generate_daily_schedule uses wake_hour from DailySchedule to set start times."""
    from backend.agents.cognition.plan import generate_daily_schedule
    from backend.schemas import AgentScratch, DailySchedule

    mock_schedule = DailySchedule(
        activities=["Wake up and stretch", "Eat breakfast", "Head to work"],
        wake_hour=7,
    )

    scratch = AgentScratch(
        age=30,
        innate="organized, punctual",
        learned="Bob is a banker.",
        lifestyle="Strict morning routine.",
        daily_plan="Wake at 7, breakfast, commute.",
    )

    with patch(
        "backend.agents.cognition.plan.complete_structured",
        new_callable=AsyncMock,
        return_value=mock_schedule,
    ):
        entries = await generate_daily_schedule("Bob", scratch)

    # First entry should start at wake_hour * 60
    assert entries[0].start_minute == 7 * 60


@pytest.mark.asyncio
async def test_decompose_hour_returns_subtasks():
    """decompose_hour returns a list of SubTask objects."""
    from backend.agents.cognition.plan import decompose_hour
    from backend.schemas import ScheduleEntry, SubTask

    mock_entry = ScheduleEntry(
        start_minute=360,  # 6am
        duration_minutes=60,
        describe="Open the cafe and brew the first batch",
    )

    # Mock response with a list of SubTask objects
    from backend.schemas import DailySchedule

    class SubTaskList(list):
        pass

    mock_subtasks = [
        SubTask(start_minute=360, duration_minutes=10, describe="Unlock the door and turn on lights"),
        SubTask(start_minute=370, duration_minutes=15, describe="Grind beans and prepare espresso machine"),
        SubTask(start_minute=385, duration_minutes=15, describe="Brew first batch of coffee"),
        SubTask(start_minute=400, duration_minutes=20, describe="Set up pastry display and check inventory"),
    ]

    with patch(
        "backend.agents.cognition.plan.complete_structured",
        new_callable=AsyncMock,
        return_value=mock_subtasks,
    ):
        subtasks = await decompose_hour("Alice", mock_entry)

    assert isinstance(subtasks, list)
    assert len(subtasks) > 0
    for st in subtasks:
        assert isinstance(st, SubTask)


@pytest.mark.asyncio
async def test_decompose_hour_subtask_durations():
    """SubTask durations from decompose_hour are within valid range (5-60 minutes)."""
    from backend.agents.cognition.plan import decompose_hour
    from backend.schemas import ScheduleEntry, SubTask

    mock_entry = ScheduleEntry(
        start_minute=480,  # 8am
        duration_minutes=60,
        describe="Serve morning customers",
    )

    mock_subtasks = [
        SubTask(start_minute=480, duration_minutes=20, describe="Take initial orders"),
        SubTask(start_minute=500, duration_minutes=20, describe="Serve drinks and food"),
        SubTask(start_minute=520, duration_minutes=20, describe="Handle payment and cleanup"),
    ]

    with patch(
        "backend.agents.cognition.plan.complete_structured",
        new_callable=AsyncMock,
        return_value=mock_subtasks,
    ):
        subtasks = await decompose_hour("Alice", mock_entry)

    for st in subtasks:
        assert 5 <= st.duration_minutes <= 60
