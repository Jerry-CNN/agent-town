"""Prompt template for the arena-level decision LLM call (D-07, D-09, Plan 09-02).

After an agent picks a sector (e.g. "cafe"), this prompt asks the LLM to pick
a specific arena within that sector (e.g. "seating" vs "kitchen" vs "counter").
Only called for sectors with multiple arenas — single-arena sectors skip this
call entirely (D-09: avoid object-level overhead for simple destinations).

Reference: GenerativeAgentsCN generative_agents/modules/agent.py _determine_action
"""


def arena_decide_prompt(
    agent_name: str,
    agent_traits: str,
    chosen_sector: str,
    available_arenas: list[str],
    current_activity: str,
) -> list[dict]:
    """Build messages for the arena-level decision LLM call.

    Args:
        agent_name:        Agent's display name.
        agent_traits:      Personality traits string (innate), e.g. "warm, creative".
        chosen_sector:     The sector the agent has already decided to go to.
        available_arenas:  List of arena names within the sector. The LLM MUST
                           choose one of these exactly.
        current_activity:  What the agent is currently doing (context for choice).

    Returns:
        A messages list: [{"role": "system", ...}, {"role": "user", ...}]
    """
    arenas_list = ", ".join(available_arenas)
    system_message = {
        "role": "system",
        "content": (
            f"You are deciding which specific area within {chosen_sector} "
            f"{agent_name} should go to. Choose from the available areas."
        ),
    }
    user_message = {
        "role": "user",
        "content": (
            f"Agent: {agent_name}\n"
            f"Personality: {agent_traits}\n"
            f"Currently doing: {current_activity}\n"
            f"Chosen destination: {chosen_sector}\n"
            f"Available areas (MUST choose one): {arenas_list}\n\n"
            f"Which specific area in {chosen_sector} should {agent_name} go to? "
            f"Provide brief reasoning."
        ),
    }
    return [system_message, user_message]
