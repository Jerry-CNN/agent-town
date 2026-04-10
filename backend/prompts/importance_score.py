"""Prompt template for LLM importance scoring (D-03).

Follows the reference agent.py pattern: provide agent persona context, describe
the event, and ask for a 1-10 importance rating. Used by store.score_importance().
"""


def importance_score_prompt(
    agent_name: str,
    agent_traits: str,
    agent_lifestyle: str,
    memory_text: str,
) -> list[dict]:
    """Return a messages list for an LLM importance-scoring call.

    Args:
        agent_name:      Agent's display name (e.g. "Alice").
        agent_traits:    Comma-separated personality traits (e.g. "warm, creative, curious").
        agent_lifestyle: Brief lifestyle description (e.g. "early riser, coffee before work").
        memory_text:     The memory/event to rate.

    Returns:
        A list of message dicts suitable for litellm / instructor completion calls.

    Example output scores:
        "ate breakfast" -> 1  (mundane routine)
        "met a new friend at the park" -> 5  (moderately significant)
        "witnessed a public argument" -> 8  (emotionally charged)
        "learned their business is failing" -> 10  (life-altering)
    """
    system_message = (
        f"You are an expert at evaluating how significant events are to specific people. "
        f"You think carefully about an event's emotional, social, and practical impact on "
        f"the person's life and goals."
    )

    user_message = (
        f"You are rating the importance of an event to {agent_name}.\n\n"
        f"About {agent_name}:\n"
        f"- Personality: {agent_traits}\n"
        f"- Lifestyle: {agent_lifestyle}\n\n"
        f"Event to rate:\n"
        f'"{memory_text}"\n\n'
        f"On a scale of 1 to 10, how important is this event to {agent_name}?\n\n"
        f"1 = completely mundane (eating breakfast, walking somewhere routine)\n"
        f"5 = moderately significant (meeting an acquaintance, minor surprise)\n"
        f"10 = extremely important, life-changing (major conflict, critical news)\n\n"
        f"Respond with a JSON object containing:\n"
        f'- "score": integer 1-10\n'
        f'- "reasoning": brief one-sentence explanation\n'
    )

    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message},
    ]
