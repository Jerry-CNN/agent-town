"""LLM-powered action decision for Agent Town agents.

Implements AGT-04: agents make structured LLM decisions about their next
destination and activity based on perception, memory context, and personality.

Architecture decisions:
  - D-05: Retrieves top 5 memories per decision query for context
  - D-07: Perception feeds into the decision (nearby agents, events, location)
  - AGT-04: Returns AgentAction (destination, activity, reasoning) for simulation loop
  - T-03-14: retrieve_memories enforces agent_id filter — agents cannot access
    other agents' memories (Plan 01 guarantee)

The caller (Phase 4 simulation loop) converts AgentAction.destination to tile
coordinates via Maze.resolve_destination(action.destination).

Reference: GenerativeAgentsCN generative_agents/modules/agent.py _determine_action
"""
from backend.gateway import complete_structured
from backend.schemas import AgentAction, AgentScratch, AgentSpatial, PerceptionResult
from backend.agents.memory.retrieval import retrieve_memories
from backend.prompts.action_decide import action_decide_prompt


def _extract_known_locations(spatial_tree: dict) -> list[str]:
    """Flatten the top-level sector keys from the agent's spatial knowledge tree.

    The spatial.tree is a nested dict like:
        {"agent-town": {"cafe": {...}, "park": {...}, "home-alice": {...}}}

    We extract the second-level keys (sector names) as the agent's known destination list.
    The world name (first-level key, e.g. "agent-town") is excluded since it's not
    a navigable destination.

    Args:
        spatial_tree: The agent's spatial knowledge tree (AgentSpatial.tree).

    Returns:
        Flat list of sector names the agent can travel to.
    """
    locations: list[str] = []
    for _world, sectors in spatial_tree.items():
        if isinstance(sectors, dict):
            locations.extend(sectors.keys())
    return locations


async def decide_action(
    simulation_id: str,
    agent_name: str,
    agent_scratch: AgentScratch,
    agent_spatial: AgentSpatial,
    current_activity: str,
    perception: PerceptionResult,
    current_schedule: list,
    open_locations: list[str] | None = None,
) -> AgentAction:
    """Decide the agent's next action using LLM with perception and memory context.

    Retrieves relevant memories, builds a context-rich prompt with the agent's
    current perception (nearby agents, events, location) and known destination
    options, then calls the LLM for a structured AgentAction decision.

    Args:
        simulation_id:     The simulation this agent belongs to.
        agent_name:        Agent's display name.
        agent_scratch:     Agent's personality and background data.
        agent_spatial:     Agent's spatial knowledge (known locations).
        current_activity:  What the agent is currently doing.
        perception:        Result of the latest perception sweep (perceive()).
        current_schedule:  Remaining schedule entries for the day (list of ScheduleEntry
                           or compatible dicts — used as reference context only).
        open_locations:    Optional filtered list of currently-open destination sectors
                           (D-08, BLD-03). When provided, replaces the full spatial tree
                           extraction so agents only see open buildings as choices.
                           When None, falls back to _extract_known_locations() as before
                           (backward-compatible).

    Returns:
        AgentAction with destination (sector name), activity description, and reasoning.
        If all LLM retries fail, gateway returns FALLBACK_AGENT_ACTION (destination="idle").
    """
    # Use open_locations if provided (D-08: filter closed buildings from decide prompt),
    # otherwise fall back to full spatial tree (backward-compatible for existing callers).
    known_locations = (
        open_locations
        if open_locations is not None
        else _extract_known_locations(agent_spatial.tree)
    )

    # Retrieve top 5 relevant memories for decision context (D-05, T-03-14)
    memories = await retrieve_memories(
        simulation_id=simulation_id,
        agent_id=agent_name,
        query=f"{agent_name} deciding what to do: {perception.location}",
        top_k=5,
    )

    # Format memories as simple dicts for the prompt template
    memory_dicts = [{"content": m.content} for m in memories]

    # Format current schedule as simple dicts for the prompt template
    # Handle both ScheduleEntry objects and plain dicts
    schedule_dicts: list[dict] = []
    for entry in current_schedule:
        if hasattr(entry, "describe"):
            schedule_dicts.append({"describe": entry.describe})
        elif isinstance(entry, dict):
            schedule_dicts.append(entry)

    # Build perception context dict for prompt
    perception_dict = {
        "nearby_agents": perception.nearby_agents,
        "nearby_events": perception.nearby_events,
        "location": perception.location,
    }

    # Build prompt messages
    messages = action_decide_prompt(
        agent_name=agent_name,
        agent_traits=agent_scratch.innate,
        agent_lifestyle=agent_scratch.lifestyle,
        current_activity=current_activity,
        current_location=perception.location,
        known_locations=known_locations,
        perception=perception_dict,
        memories=memory_dicts,
        current_schedule=schedule_dicts,
    )

    # Call LLM for structured AgentAction decision
    result: AgentAction = await complete_structured(
        messages=messages,
        response_model=AgentAction,
    )

    return result
