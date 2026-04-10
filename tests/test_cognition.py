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


# ---------------------------------------------------------------------------
# Task 1 (Plan 03): Action decision tests (TDD RED -- no decide module yet)
# ---------------------------------------------------------------------------


def test_action_decide_prompt_includes_agent_name():
    """action_decide_prompt includes the agent's name in the message content."""
    from backend.prompts.action_decide import action_decide_prompt

    messages = action_decide_prompt(
        agent_name="Alice",
        agent_traits="warm, creative",
        agent_lifestyle="early riser",
        current_activity="brewing coffee",
        current_location="cafe:seating",
        known_locations=["cafe", "park", "home-alice"],
        perception={"nearby_agents": [], "nearby_events": [], "location": "cafe:seating"},
        memories=[],
        current_schedule=[],
    )
    all_content = " ".join(
        m["content"] for m in messages if isinstance(m.get("content"), str)
    )
    assert "Alice" in all_content


def test_action_decide_prompt_includes_known_locations():
    """action_decide_prompt includes the list of known locations for destination choices."""
    from backend.prompts.action_decide import action_decide_prompt

    messages = action_decide_prompt(
        agent_name="Alice",
        agent_traits="warm, creative",
        agent_lifestyle="early riser",
        current_activity="brewing coffee",
        current_location="cafe:seating",
        known_locations=["cafe", "park", "home-alice", "stock-exchange"],
        perception={"nearby_agents": [], "nearby_events": [], "location": "cafe"},
        memories=[],
        current_schedule=[],
    )
    all_content = " ".join(
        m["content"] for m in messages if isinstance(m.get("content"), str)
    )
    # At least one known location must appear in the prompt
    assert any(loc in all_content for loc in ["cafe", "park", "home-alice", "stock-exchange"])


def test_action_decide_prompt_includes_perception():
    """action_decide_prompt includes perception context in the message content."""
    from backend.prompts.action_decide import action_decide_prompt

    perception = {
        "nearby_agents": [{"name": "Bob", "activity": "reading"}],
        "nearby_events": [],
        "location": "cafe:seating",
    }
    messages = action_decide_prompt(
        agent_name="Alice",
        agent_traits="warm",
        agent_lifestyle="morning person",
        current_activity="idle",
        current_location="cafe",
        known_locations=["cafe", "park"],
        perception=perception,
        memories=[],
        current_schedule=[],
    )
    all_content = " ".join(
        m["content"] for m in messages if isinstance(m.get("content"), str)
    )
    # Bob appears in nearby_agents -- should appear in prompt context
    assert "Bob" in all_content or "nearby" in all_content.lower()


def test_action_decide_prompt_includes_memories():
    """action_decide_prompt includes retrieved memories in the message content."""
    from backend.prompts.action_decide import action_decide_prompt

    memories = [{"content": "Alice enjoyed her morning walk last week"}]
    messages = action_decide_prompt(
        agent_name="Alice",
        agent_traits="warm",
        agent_lifestyle="morning person",
        current_activity="idle",
        current_location="cafe",
        known_locations=["cafe", "park"],
        perception={"nearby_agents": [], "nearby_events": [], "location": "cafe"},
        memories=memories,
        current_schedule=[],
    )
    all_content = " ".join(
        m["content"] for m in messages if isinstance(m.get("content"), str)
    )
    assert "morning walk" in all_content or "Alice" in all_content


@pytest.mark.asyncio
async def test_decide_action_returns_agent_action():
    """decide_action returns an AgentAction with destination, activity, reasoning."""
    from backend.agents.cognition.decide import decide_action
    from backend.schemas import AgentAction, AgentScratch, AgentSpatial, PerceptionResult

    scratch = AgentScratch(
        age=28,
        innate="warm, creative",
        learned="Alice runs the local cafe.",
        lifestyle="Early riser.",
        daily_plan="Wake up early, open the cafe.",
    )
    spatial = AgentSpatial(
        address={"living_area": ["agent-town", "home-alice", "bedroom"]},
        tree={"agent-town": {"cafe": {}, "park": {}, "home-alice": {}}},
    )
    perception = PerceptionResult(
        nearby_agents=[{"name": "Bob", "activity": "reading"}],
        nearby_events=[],
        location="cafe:seating",
    )

    mock_action = AgentAction(
        destination="park",
        activity="taking a morning walk",
        reasoning="Alice needs a break after the morning rush.",
    )

    with patch(
        "backend.agents.cognition.decide.complete_structured",
        new_callable=AsyncMock,
        return_value=mock_action,
    ), patch(
        "backend.agents.cognition.decide.retrieve_memories",
        new_callable=AsyncMock,
        return_value=[],
    ):
        result = await decide_action(
            simulation_id="sim-test",
            agent_name="Alice",
            agent_scratch=scratch,
            agent_spatial=spatial,
            current_activity="serving coffee",
            perception=perception,
            current_schedule=[],
        )

    assert isinstance(result, AgentAction)
    assert result.destination == "park"
    assert result.activity == "taking a morning walk"


@pytest.mark.asyncio
async def test_decide_action_calls_retrieve_memories():
    """decide_action calls retrieve_memories with the correct simulation_id and agent_name."""
    from backend.agents.cognition.decide import decide_action
    from backend.schemas import AgentAction, AgentScratch, AgentSpatial, PerceptionResult

    scratch = AgentScratch(
        age=30,
        innate="organized",
        learned="Bob is a banker.",
        lifestyle="Strict routine.",
        daily_plan="Wake at 7, go to work.",
    )
    spatial = AgentSpatial(
        address={"living_area": ["agent-town", "home-bob", "bedroom"]},
        tree={"agent-town": {"bank": {}, "park": {}, "home-bob": {}}},
    )
    perception = PerceptionResult(nearby_agents=[], nearby_events=[], location="bank")

    mock_action = AgentAction(
        destination="bank",
        activity="reviewing loans",
        reasoning="Time to work.",
    )

    retrieve_mock = AsyncMock(return_value=[])

    with patch(
        "backend.agents.cognition.decide.complete_structured",
        new_callable=AsyncMock,
        return_value=mock_action,
    ), patch(
        "backend.agents.cognition.decide.retrieve_memories",
        retrieve_mock,
    ):
        await decide_action(
            simulation_id="sim-abc",
            agent_name="Bob",
            agent_scratch=scratch,
            agent_spatial=spatial,
            current_activity="idle",
            perception=perception,
            current_schedule=[],
        )

    # retrieve_memories must be called with correct simulation_id and agent_name
    retrieve_mock.assert_called_once()
    call_kwargs = retrieve_mock.call_args
    assert call_kwargs.args[0] == "sim-abc" or call_kwargs.kwargs.get("simulation_id") == "sim-abc"
    assert "Bob" in str(call_kwargs)


# ---------------------------------------------------------------------------
# Task 2 (Plan 03): Conversation system tests (TDD RED -- no converse module yet)
# ---------------------------------------------------------------------------


def test_cooldown_returns_true_initially():
    """check_cooldown returns True when no prior conversation has occurred."""
    from backend.agents.cognition.converse import check_cooldown

    # Use unique names to avoid pollution from other tests
    assert check_cooldown("zara-unique-1", "yuri-unique-1") is True


def test_cooldown_returns_false_after_record():
    """check_cooldown returns False immediately after _record_conversation."""
    from backend.agents.cognition.converse import check_cooldown, _record_conversation

    _record_conversation("pair-agent-x", "pair-agent-y")
    # Immediately after recording, cooldown has NOT expired
    assert check_cooldown("pair-agent-x", "pair-agent-y") is False


def test_pair_key_is_symmetric():
    """_pair_key("alice", "bob") == _pair_key("bob", "alice") — order doesn't matter."""
    from backend.agents.cognition.converse import _pair_key

    assert _pair_key("alice", "bob") == _pair_key("bob", "alice")


def test_conversation_start_prompt_includes_both_agent_names():
    """conversation_start_prompt includes both agent names in message content."""
    from backend.prompts.conversation_start import conversation_start_prompt

    messages = conversation_start_prompt(
        agent_name="Alice",
        agent_traits="warm, creative",
        other_name="Bob",
        other_activity="reading the newspaper",
        agent_current_activity="brewing coffee",
        location="cafe",
        recent_memories=[],
    )
    all_content = " ".join(
        m["content"] for m in messages if isinstance(m.get("content"), str)
    )
    assert "Alice" in all_content
    assert "Bob" in all_content


def test_schedule_revise_prompt_includes_conversation_summary():
    """schedule_revise_prompt includes the conversation summary in message content."""
    from backend.prompts.schedule_revise import schedule_revise_prompt

    summary = "Discussed the upcoming wedding at the town hall"
    messages = schedule_revise_prompt(
        agent_name="Alice",
        agent_traits="warm",
        conversation_summary=summary,
        remaining_schedule=[],
    )
    all_content = " ".join(
        m["content"] for m in messages if isinstance(m.get("content"), str)
    )
    assert "wedding" in all_content or "town hall" in all_content or "Discussed" in all_content


@pytest.mark.asyncio
async def test_attempt_conversation_respects_cooldown():
    """attempt_conversation returns False when agents chatted within the cooldown period."""
    from backend.agents.cognition.converse import attempt_conversation, _record_conversation
    from backend.schemas import AgentScratch

    scratch = AgentScratch(
        age=28,
        innate="warm",
        learned="Alice is friendly.",
        lifestyle="morning person",
        daily_plan="Open cafe.",
    )

    # Record a recent conversation — this sets the cooldown
    _record_conversation("alice-cooldown-test", "bob-cooldown-test")

    # attempt_conversation should return False immediately (no LLM call needed)
    result = await attempt_conversation(
        simulation_id="sim-test",
        agent_name="alice-cooldown-test",
        agent_scratch=scratch,
        other_name="bob-cooldown-test",
        other_activity="reading",
        agent_current_activity="brewing coffee",
        location="cafe",
    )
    assert result is False


@pytest.mark.asyncio
async def test_attempt_conversation_calls_llm_when_cooldown_allows():
    """attempt_conversation calls LLM when cooldown allows and returns ConversationDecision.should_talk."""
    from backend.agents.cognition.converse import attempt_conversation
    from backend.schemas import AgentScratch, ConversationDecision

    scratch = AgentScratch(
        age=28,
        innate="warm",
        learned="Alice is friendly.",
        lifestyle="morning person",
        daily_plan="Open cafe.",
    )

    mock_decision = ConversationDecision(should_talk=True, reasoning="They are old friends.")

    with patch(
        "backend.agents.cognition.converse.complete_structured",
        new_callable=AsyncMock,
        return_value=mock_decision,
    ), patch(
        "backend.agents.cognition.converse.retrieve_memories",
        new_callable=AsyncMock,
        return_value=[],
    ):
        result = await attempt_conversation(
            simulation_id="sim-fresh",
            agent_name="fresh-alice",
            agent_scratch=scratch,
            other_name="fresh-bob",
            other_activity="walking",
            agent_current_activity="idle",
            location="park",
        )

    assert result is True


@pytest.mark.asyncio
async def test_run_conversation_produces_turns():
    """run_conversation produces at least 2 turns (minimum D-12 requirement)."""
    from backend.agents.cognition.converse import run_conversation
    from backend.schemas import AgentScratch, ConversationTurn, ScheduleRevision, ScheduleEntry

    scratch_a = AgentScratch(
        age=28, innate="warm", learned="Alice runs the cafe.",
        lifestyle="morning person", daily_plan="Open cafe."
    )
    scratch_b = AgentScratch(
        age=30, innate="organized", learned="Bob is a banker.",
        lifestyle="strict routine", daily_plan="Go to work."
    )

    mock_turn = ConversationTurn(text="Hello there!", end_conversation=False)
    mock_turn_end = ConversationTurn(text="Goodbye!", end_conversation=True)
    mock_revision = ScheduleRevision(
        revised_entries=[
            ScheduleEntry(start_minute=600, duration_minutes=60, describe="Visit park after chat")
        ],
        reason="Decided to relax after conversation",
    )

    call_count = 0
    def turn_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        # Return end_conversation=True on 4th+ call (to cap at 2 full exchanges)
        if call_count >= 4:
            return ConversationTurn(text="Nice talking to you!", end_conversation=True)
        return ConversationTurn(text=f"Turn {call_count}", end_conversation=False)

    with patch(
        "backend.agents.cognition.converse.complete_structured",
        new_callable=AsyncMock,
        side_effect=turn_side_effect,
    ), patch(
        "backend.agents.cognition.converse.add_memory",
        new_callable=AsyncMock,
    ), patch(
        "backend.agents.cognition.converse.score_importance",
        new_callable=AsyncMock,
        return_value=5,
    ), patch(
        "backend.agents.cognition.converse.retrieve_memories",
        new_callable=AsyncMock,
        return_value=[],
    ):
        result = await run_conversation(
            simulation_id="sim-test",
            agent_a_name="Alice",
            agent_a_scratch=scratch_a,
            agent_b_name="Bob",
            agent_b_scratch=scratch_b,
            location="cafe",
            remaining_schedule_a=[],
            remaining_schedule_b=[],
        )

    assert "turns" in result
    assert len(result["turns"]) >= 2


@pytest.mark.asyncio
async def test_run_conversation_caps_at_max_turns():
    """run_conversation never exceeds MAX_TURNS (4) turns."""
    from backend.agents.cognition.converse import run_conversation, MAX_TURNS
    from backend.schemas import AgentScratch, ConversationTurn

    scratch = AgentScratch(
        age=28, innate="warm", learned="Alice runs the cafe.",
        lifestyle="morning person", daily_plan="Open cafe."
    )

    # Always return end_conversation=False to force max turns
    mock_turn = ConversationTurn(text="Keep talking!", end_conversation=False)

    with patch(
        "backend.agents.cognition.converse.complete_structured",
        new_callable=AsyncMock,
        return_value=mock_turn,
    ), patch(
        "backend.agents.cognition.converse.add_memory",
        new_callable=AsyncMock,
    ), patch(
        "backend.agents.cognition.converse.score_importance",
        new_callable=AsyncMock,
        return_value=5,
    ), patch(
        "backend.agents.cognition.converse.retrieve_memories",
        new_callable=AsyncMock,
        return_value=[],
    ):
        result = await run_conversation(
            simulation_id="sim-cap",
            agent_a_name="Alice",
            agent_a_scratch=scratch,
            agent_b_name="Bob",
            agent_b_scratch=scratch,
            location="cafe",
            remaining_schedule_a=[],
            remaining_schedule_b=[],
        )

    # Total turns = 2 speakers * MAX_TURNS rounds max
    assert len(result["turns"]) <= MAX_TURNS * 2


@pytest.mark.asyncio
async def test_run_conversation_calls_add_memory_for_both_agents():
    """run_conversation calls add_memory for both agents after conversation ends."""
    from backend.agents.cognition.converse import run_conversation
    from backend.schemas import AgentScratch, ConversationTurn

    scratch = AgentScratch(
        age=28, innate="warm", learned="Alice runs the cafe.",
        lifestyle="morning person", daily_plan="Open cafe."
    )

    mock_turn = ConversationTurn(text="Hello!", end_conversation=True)

    add_memory_mock = AsyncMock()

    with patch(
        "backend.agents.cognition.converse.complete_structured",
        new_callable=AsyncMock,
        return_value=mock_turn,
    ), patch(
        "backend.agents.cognition.converse.add_memory",
        add_memory_mock,
    ), patch(
        "backend.agents.cognition.converse.score_importance",
        new_callable=AsyncMock,
        return_value=7,
    ), patch(
        "backend.agents.cognition.converse.retrieve_memories",
        new_callable=AsyncMock,
        return_value=[],
    ):
        await run_conversation(
            simulation_id="sim-mem",
            agent_a_name="Alice",
            agent_a_scratch=scratch,
            agent_b_name="Bob",
            agent_b_scratch=scratch,
            location="park",
            remaining_schedule_a=[],
            remaining_schedule_b=[],
        )

    # add_memory must have been called at least twice (once per agent)
    assert add_memory_mock.call_count >= 2

    # Both Alice and Bob should have memories stored
    all_calls_args = [str(c) for c in add_memory_mock.call_args_list]
    combined = " ".join(all_calls_args)
    assert "Alice" in combined
    assert "Bob" in combined
