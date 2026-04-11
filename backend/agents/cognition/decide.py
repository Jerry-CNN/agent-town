"""LLM-powered action decision for Agent Town agents.

Implements AGT-04: agents make structured LLM decisions about their next
destination and activity based on perception, memory context, and personality.

Architecture decisions:
  - D-05: Retrieves top 5 memories per decision query for context
  - D-07: Perception feeds into the decision (nearby agents, events, location)
  - D-08: Per-sector gating — skips LLM call when last_sector is unchanged AND
    no new perceptions AND schedule block has not changed (returns None)
  - D-09: 2-level cascade (sector -> arena) — only calls arena LLM for sectors
    with multiple arenas; single-arena sectors skip the arena call
  - AGT-04: Returns AgentAction | None (None = gating skip, caller keeps current action)
  - T-03-14: retrieve_memories enforces agent_id filter — agents cannot access
    other agents' memories (Plan 01 guarantee)
  - Codex P1-2/P1-6: Gating checks all three conditions (last_sector, new_perceptions,
    schedule_changed) — checking only last_sector is insufficient
  - Codex P1-5: Arena names validated against known list; unknown names fall back to
    arenas[0] with warning log to prevent path resolution failure in engine

The caller (Phase 4 simulation loop) converts AgentAction.destination to tile
coordinates via Maze.resolve_destination(action.destination).

Reference: GenerativeAgentsCN generative_agents/modules/agent.py _determine_action
"""
import logging

from backend.gateway import complete_structured
from backend.schemas import AgentAction, ArenaAction, AgentScratch, AgentSpatial, PerceptionResult
from backend.agents.memory.retrieval import retrieve_memories
from backend.prompts.action_decide import action_decide_prompt
from backend.prompts.arena_decide import arena_decide_prompt

logger = logging.getLogger(__name__)


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


def _sector_has_arenas(sector_name: str, spatial_tree: dict) -> list[str]:
    """Return list of arena names if sector has multiple arenas, else empty list.

    Looks up sector_name in the spatial tree. If the sector dict has >1 key (arenas),
    returns the arena names. Single-arena or missing sectors return empty list.

    Per D-09: skip arena call for single-room sectors to avoid unnecessary LLM overhead.

    Args:
        sector_name:   The sector to check (e.g. "cafe", "park").
        spatial_tree:  The agent's spatial knowledge tree (AgentSpatial.tree).

    Returns:
        List of arena names if the sector has >1 arenas, else [].
    """
    for _world, sectors in spatial_tree.items():
        if isinstance(sectors, dict) and sector_name in sectors:
            arenas = sectors[sector_name]
            if isinstance(arenas, dict) and len(arenas) > 1:
                return list(arenas.keys())
    return []


async def decide_action(
    simulation_id: str,
    agent_name: str,
    agent_scratch: AgentScratch,
    agent_spatial: AgentSpatial,
    current_activity: str,
    perception: PerceptionResult,
    current_schedule: list,
    open_locations: list[str] | None = None,
    last_sector: str | None = None,
    new_perceptions: bool = True,
    schedule_changed: bool = False,
) -> AgentAction | None:
    """Decide the agent's next action using LLM with perception and memory context.

    D-08: Per-sector gating — returns None (no LLM call) when ALL of:
      1. last_sector is not None (agent has a previous sector — not first tick)
      2. new_perceptions is False (no nearby agents/events/injected memories)
      3. schedule_changed is False (schedule block has not advanced since last tick)
    Caller interprets None as "keep current action" — zero LLM cost for stable ticks.

    D-09: 2-level cascade — after sector selection, calls arena LLM only for sectors
    with multiple arenas. Single-room sectors skip the arena call entirely.

    Codex P1-5: Arena name validated against known list — unknown arena falls back
    to arenas[0] with WARNING log (prevents engine path resolution failure).

    Args:
        simulation_id:     The simulation this agent belongs to.
        agent_name:        Agent's display name.
        agent_scratch:     Agent's personality and background data.
        agent_spatial:     Agent's spatial knowledge (known locations).
        current_activity:  What the agent is currently doing.
        perception:        Result of the latest perception sweep (perceive()).
        current_schedule:  Remaining schedule entries for the day.
        open_locations:    Optional filtered list of currently-open destination sectors.
                           When provided, replaces full spatial tree extraction.
                           When None, falls back to _extract_known_locations().
        last_sector:       Sector from the previous tick (None on first tick).
                           Used for D-08 gating check.
        new_perceptions:   True if there are new perceptions this tick (nearby agents,
                           nearby events, or injected memories). False means the
                           environment around the agent has not changed.
        schedule_changed:  True if the agent's current schedule block has advanced
                           (Codex P1-6: accounts for schedule-driven movement triggers).

    Returns:
        AgentAction with destination (sector or sector:arena), activity, and reasoning.
        None if gating condition met — caller should keep current action.
        If all LLM retries fail, gateway returns FALLBACK_AGENT_ACTION (destination="idle").
    """
    # D-08: Per-sector gating — skip LLM ONLY when ALL three conditions are stable:
    #   1. Agent has a known previous sector (not first tick — last_sector is not None)
    #   2. No new perceptions (no nearby agents/events/injected memories)
    #   3. Schedule block has not changed since last tick
    #
    # Codex P1-2: Checking only `last_sector is not None` is insufficient — the agent's
    # schedule may require them to move even without perceptions.
    # Codex P1-6: `had_new_perceptions` must account for schedule changes, not just
    # nearby_agents/nearby_events proximity events.
    if last_sector is not None and not new_perceptions and not schedule_changed:
        return None

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

    # Call LLM for structured AgentAction decision (sector-level)
    result: AgentAction = await complete_structured(
        messages=messages,
        response_model=AgentAction,
    )

    # D-07/D-09: Arena-level resolution for multi-arena sectors.
    # Only fires when the chosen sector has >1 arena. Single-room sectors skip this call.
    arenas = _sector_has_arenas(result.destination, agent_spatial.tree)
    if arenas:
        arena_messages = arena_decide_prompt(
            agent_name=agent_name,
            agent_traits=agent_scratch.innate,
            chosen_sector=result.destination,
            available_arenas=arenas,
            current_activity=current_activity,
        )
        arena_result: ArenaAction = await complete_structured(
            messages=arena_messages,
            response_model=ArenaAction,
            fallback=ArenaAction(arena=arenas[0], reasoning="fallback"),
        )
        # Codex P1-5: Validate arena against known list. A syntactically valid but
        # unknown arena string passes ArenaAction Pydantic validation but produces
        # a "sector:arena" path that fails resolution in engine.
        if arena_result.arena in arenas:
            result.destination = f"{result.destination}:{arena_result.arena}"
        else:
            logger.warning(
                "Agent %s LLM returned unknown arena '%s' for sector '%s' — "
                "falling back to '%s'",
                agent_name, arena_result.arena, result.destination, arenas[0],
            )
            result.destination = f"{result.destination}:{arenas[0]}"

    return result
