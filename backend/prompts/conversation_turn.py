"""Prompt template for generating a single conversation turn.

Each call to complete_structured() with this prompt produces one ConversationTurn
(text: str, end_conversation: bool). The LLM responds in-character as agent_name.

Used by run_conversation() in backend/agents/cognition/converse.py for each
turn of the multi-turn dialogue (D-12: 2-4 turns, hard cap at 4).

Reference: GenerativeAgentsCN generative_agents/modules/converse.py
"""


def conversation_turn_prompt(
    agent_name: str,
    agent_traits: str,
    other_name: str,
    conversation_so_far: list[dict],
    turn_number: int,
    max_turns: int,
) -> list[dict]:
    """Build messages for a single conversation turn LLM call.

    Args:
        agent_name:           The agent whose turn it is to speak.
        agent_traits:         Personality traits (innate), e.g. "warm, creative".
        other_name:           The other agent in the conversation.
        conversation_so_far:  List of turn dicts: {"speaker": str, "text": str}.
        turn_number:          Current turn number (1-indexed).
        max_turns:            Hard cap on turns (MAX_TURNS from converse.py).

    Returns:
        A messages list: [{"role": "system", ...}, {"role": "user", ...}]
    """
    # Format conversation history
    if conversation_so_far:
        history_lines = "\n".join(
            f"{t.get('speaker', 'Unknown')}: {t.get('text', '')}"
            for t in conversation_so_far
        )
        history_str = f"Conversation so far:\n{history_lines}"
    else:
        history_str = "Conversation so far: (starting now)"

    # Provide turn context so LLM can judge whether to end naturally
    turns_remaining = max_turns - turn_number
    if turns_remaining <= 0:
        ending_hint = "This is the final turn — wrap up the conversation naturally."
    elif turn_number >= 2:
        ending_hint = (
            f"Turn {turn_number} of up to {max_turns}. "
            "You may end the conversation if it feels natural (set end_conversation=true)."
        )
    else:
        ending_hint = f"Turn {turn_number} of up to {max_turns}. The conversation has just begun."

    system_message = {
        "role": "system",
        "content": (
            f"You are {agent_name} ({agent_traits}). "
            "Respond naturally in character with one conversational turn. "
            "Keep responses brief (1-3 sentences)."
        ),
    }

    user_message = {
        "role": "user",
        "content": (
            f"You are {agent_name} talking to {other_name}.\n\n"
            f"{history_str}\n\n"
            f"{ending_hint}\n\n"
            f"What does {agent_name} say next? "
            "Set end_conversation=true if the conversation is naturally concluding."
        ),
    }

    return [system_message, user_message]
