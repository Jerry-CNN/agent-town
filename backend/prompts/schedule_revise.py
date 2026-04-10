"""Prompt template for post-conversation schedule revision.

After a conversation ends, each agent may want to adjust their remaining
daily schedule based on what was discussed (D-10, D-13).

Returns a ScheduleRevision model (revised_entries: list[ScheduleEntry], reason: str).
The caller (run_conversation in converse.py) replaces the remaining schedule
with revised_entries if the LLM determines changes are warranted.

Reference: GenerativeAgentsCN generative_agents/modules/converse.py (post-chat revision)
"""


def schedule_revise_prompt(
    agent_name: str,
    agent_traits: str,
    conversation_summary: str,
    remaining_schedule: list[dict],
) -> list[dict]:
    """Build messages for the post-conversation schedule revision LLM call.

    Args:
        agent_name:            Agent whose schedule should be revised.
        agent_traits:          Personality traits (innate), e.g. "warm, creative".
        conversation_summary:  Summary of what was discussed in the conversation.
        remaining_schedule:    List of dicts representing remaining schedule entries
                               (e.g., [{"describe": "Visit park", "start_minute": 720}]).

    Returns:
        A messages list: [{"role": "system", ...}, {"role": "user", ...}]
    """
    # Format remaining schedule
    if remaining_schedule:
        schedule_lines = "\n".join(
            f"  - {s.get('describe', str(s))}" for s in remaining_schedule
        )
        schedule_str = f"Remaining schedule:\n{schedule_lines}"
    else:
        schedule_str = "Remaining schedule: no entries remaining"

    system_message = {
        "role": "system",
        "content": (
            f"You are revising {agent_name}'s remaining daily schedule "
            "based on a conversation they just had. "
            "Only revise if the conversation warrants a meaningful change."
        ),
    }

    user_message = {
        "role": "user",
        "content": (
            f"Agent: {agent_name} ({agent_traits})\n\n"
            f"The conversation was about: {conversation_summary}\n\n"
            f"{schedule_str}\n\n"
            f"After this conversation, {agent_name} may want to adjust their remaining schedule. "
            "Revise the schedule if the conversation warrants meaningful changes "
            "(e.g., learning about an event, making plans with someone, or changing priorities). "
            "If no changes are needed, return the schedule as-is. "
            "Provide brief reasoning for any changes."
        ),
    }

    return [system_message, user_message]
