"""Prompt template for the action decision LLM call.

Builds the messages list for decide_action() in backend/agents/cognition/decide.py.
Agent chooses their next destination and activity based on:
  - Personality and lifestyle
  - Current state (what they're doing, where they are)
  - Known locations they can travel to
  - Nearby agents and events from perception sweep (D-07)
  - Retrieved memories relevant to the current context (D-05)
  - Remaining schedule entries for continuity

Reference: GenerativeAgentsCN generative_agents/modules/agent.py _determine_action
"""


def action_decide_prompt(
    agent_name: str,
    agent_traits: str,
    agent_lifestyle: str,
    current_activity: str,
    current_location: str,
    known_locations: list[str],
    perception: dict,
    memories: list[dict],
    current_schedule: list[dict],
) -> list[dict]:
    """Build messages for the action decision LLM call.

    Args:
        agent_name:        Agent's display name.
        agent_traits:      Personality traits string (innate), e.g. "warm, creative".
        agent_lifestyle:   Lifestyle description (sleep/wake patterns, habits).
        current_activity:  What the agent is currently doing.
        current_location:  Current location descriptor (e.g. "cafe:seating").
        known_locations:   Flat list of sector names the agent can travel to.
                           The LLM MUST choose a destination from this list.
        perception:        Dict with keys "nearby_agents", "nearby_events", "location"
                           from the perception sweep.
        memories:          List of dicts with "content" key — retrieved memories
                           relevant to the current decision context (top 5, D-05).
        current_schedule:  Remaining schedule entries (list of dicts) for reference.

    Returns:
        A messages list: [{"role": "system", ...}, {"role": "user", ...}]
    """
    # --- Format nearby agents ---
    nearby_agents = perception.get("nearby_agents", [])
    if nearby_agents:
        agents_lines = "\n".join(
            f"  - {a.get('name', 'unknown')} is {a.get('activity', 'doing something')}"
            for a in nearby_agents
        )
        nearby_agents_str = f"Nearby agents:\n{agents_lines}"
    else:
        nearby_agents_str = "Nearby agents: none"

    # --- Format nearby events ---
    nearby_events = perception.get("nearby_events", [])
    if nearby_events:
        events_lines = "\n".join(
            f"  - {e.get('event', str(e))}" for e in nearby_events
        )
        nearby_events_str = f"Nearby events:\n{events_lines}"
    else:
        nearby_events_str = "Nearby events: none"

    # --- Format retrieved memories ---
    if memories:
        memories_lines = "\n".join(
            f"  - {m.get('content', str(m))}" for m in memories
        )
        memories_str = f"Relevant memories:\n{memories_lines}"
    else:
        memories_str = "Relevant memories: none"

    # --- Format remaining schedule ---
    if current_schedule:
        schedule_lines = "\n".join(
            f"  - {s.get('describe', str(s))}" for s in current_schedule
        )
        schedule_str = f"Remaining schedule:\n{schedule_lines}"
    else:
        schedule_str = "Remaining schedule: no entries"

    # --- Format known locations ---
    locations_list = ", ".join(known_locations) if known_locations else "no known locations"

    system_message = {
        "role": "system",
        "content": (
            f"You are deciding what {agent_name} should do next. "
            f"{agent_name} is a character in a living town simulation. "
            "Respond as a thoughtful narrator who knows this character well."
        ),
    }

    user_message = {
        "role": "user",
        "content": (
            f"Agent: {agent_name}\n"
            f"Personality traits: {agent_traits}\n"
            f"Lifestyle: {agent_lifestyle}\n\n"
            f"Current state:\n"
            f"  - Currently doing: {current_activity}\n"
            f"  - Current location: {current_location}\n\n"
            f"Known locations (MUST choose destination from this list): {locations_list}\n\n"
            f"Perception context:\n"
            f"{nearby_agents_str}\n"
            f"{nearby_events_str}\n\n"
            f"{memories_str}\n\n"
            f"{schedule_str}\n\n"
            f"Based on this context, decide what {agent_name} should do next. "
            f"Choose a destination from the known locations list and describe the activity. "
            f"Provide brief reasoning for the decision."
        ),
    }

    return [system_message, user_message]
