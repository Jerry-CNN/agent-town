"""Prompt template for the conversation initiation LLM check.

Asks the LLM whether agent_name should start a conversation with other_name
based on their personalities, current activities, location, and recent context.

Used by attempt_conversation() in backend/agents/cognition/converse.py.
Returns a ConversationDecision model (should_talk: bool, reasoning: str).

Reference: GenerativeAgentsCN generative_agents/modules/converse.py
"""


def conversation_start_prompt(
    agent_name: str,
    agent_traits: str,
    other_name: str,
    other_activity: str,
    agent_current_activity: str,
    location: str,
    recent_memories: list[dict],
) -> list[dict]:
    """Build messages for the conversation initiation check LLM call.

    Args:
        agent_name:              Agent considering starting the conversation.
        agent_traits:            Personality traits (innate), e.g. "warm, creative".
        other_name:              The other agent's name.
        other_activity:          What the other agent is currently doing.
        agent_current_activity:  What the initiating agent is currently doing.
        location:                Location where both agents are present.
        recent_memories:         List of dicts with "content" key — recent memories
                                 about the other agent for context.

    Returns:
        A messages list: [{"role": "system", ...}, {"role": "user", ...}]
    """
    # Format recent memories
    if recent_memories:
        memories_lines = "\n".join(
            f"  - {m.get('content', str(m))}" for m in recent_memories
        )
        memories_str = f"Recent memories about {other_name}:\n{memories_lines}"
    else:
        memories_str = f"Recent memories about {other_name}: none"

    system_message = {
        "role": "system",
        "content": (
            f"You decide whether {agent_name} would start a conversation. "
            "Answer with a clear yes or no decision and brief reasoning."
        ),
    }

    user_message = {
        "role": "user",
        "content": (
            f"Should {agent_name} ({agent_traits}) start a conversation with "
            f"{other_name} who is currently {other_activity}? "
            f"They are both at {location}. "
            f"{agent_name} is currently {agent_current_activity}.\n\n"
            f"{memories_str}\n\n"
            f"Respond with whether {agent_name} should talk to {other_name} and why. "
            "Consider their personalities, what they're doing, and the context."
        ),
    }

    return [system_message, user_message]
