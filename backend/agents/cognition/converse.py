"""Multi-turn conversation system for Agent Town agents.

Implements AGT-07 (agent conversations) and AGT-08 (schedule revision after
conversations — the key mechanism for event propagation and gossip in Phase 6).

Architecture decisions implemented here:
  - D-11: Conversation trigger: proximity check + LLM decision (attempt_conversation).
  - D-12: Conversations run 2-4 turns with hard cap MAX_TURNS=4. NEVER uses `while True`.
    Uses `for turn in range(MAX_TURNS)` to bound LLM call count (T-03-09 mitigation).
  - D-13: After conversation ends, each agent gets an LLM call to revise their
    remaining daily schedule based on what was discussed.
  - T-03-09 (DoS): Hard cap MAX_TURNS=4 + COOLDOWN_SECONDS=60 prevents conversation spam.
  - T-03-11 (Tampering): ScheduleRevision entries validated by Pydantic Field constraints
    (start_minute 0-1439, duration 15-120); invalid LLM entries are rejected.
  - T-03-12 (DoS): Limited to 2 memories stored per conversation (one per agent);
    importance scoring has failsafe=5 on LLM failure.

Reference: GenerativeAgentsCN generative_agents/modules/converse.py
           GenerativeAgentsCN generative_agents/modules/agent.py (_chat_with ~line 501-568)
"""
import time
import logging

from backend.gateway import complete_structured
from backend.schemas import (
    ConversationDecision,
    ConversationTurn,
    ScheduleRevision,
    ScheduleEntry,
    AgentScratch,
)
from backend.agents.memory.store import add_memory, score_importance
from backend.agents.memory.retrieval import retrieve_memories
from backend.prompts.conversation_start import conversation_start_prompt
from backend.prompts.conversation_turn import conversation_turn_prompt
from backend.prompts.schedule_revise import schedule_revise_prompt

logger = logging.getLogger(__name__)

# D-12: Hard cap at 4 turns per conversation (T-03-09 DoS mitigation).
# Combined with COOLDOWN_SECONDS, this bounds LLM calls per agent pair per minute.
MAX_TURNS = 4

# Claude's discretion: 60 real-time seconds between same-pair conversations.
# Prevents conversation spam in the simulation loop while keeping agents social.
COOLDOWN_SECONDS = 60

# In-memory cooldown tracker: frozenset({agent_a, agent_b}) -> last conversation timestamp.
# Using frozenset ensures symmetry: ("alice", "bob") == ("bob", "alice").
_conversation_cooldowns: dict[frozenset, float] = {}


def _pair_key(agent_a: str, agent_b: str) -> frozenset:
    """Return a symmetric pair key for two agent names.

    frozenset guarantees _pair_key("alice", "bob") == _pair_key("bob", "alice").
    This prevents the same pair from having different cooldown timers based on
    which agent initiates the conversation check.

    Args:
        agent_a: First agent's name.
        agent_b: Second agent's name.

    Returns:
        frozenset of both agent names (order-independent).
    """
    return frozenset({agent_a, agent_b})


def check_cooldown(agent_a: str, agent_b: str) -> bool:
    """Check whether enough time has passed since the last conversation between two agents.

    Args:
        agent_a: First agent's name.
        agent_b: Second agent's name.

    Returns:
        True if the pair can converse (cooldown expired or no prior conversation).
        False if they conversed too recently (within COOLDOWN_SECONDS).
    """
    key = _pair_key(agent_a, agent_b)
    last_time = _conversation_cooldowns.get(key, 0)
    return (time.time() - last_time) >= COOLDOWN_SECONDS


def _record_conversation(agent_a: str, agent_b: str) -> None:
    """Record that a conversation just occurred between two agents.

    Updates the cooldown tracker so check_cooldown returns False for the next
    COOLDOWN_SECONDS seconds for this pair.

    Args:
        agent_a: First agent's name.
        agent_b: Second agent's name.
    """
    _conversation_cooldowns[_pair_key(agent_a, agent_b)] = time.time()


async def attempt_conversation(
    simulation_id: str,
    agent_name: str,
    agent_scratch: AgentScratch,
    other_name: str,
    other_activity: str,
    agent_current_activity: str,
    location: str,
) -> bool:
    """Decide whether an agent should initiate a conversation with another agent.

    Two-phase check (D-11):
    1. Cooldown gate: if they've talked within COOLDOWN_SECONDS, return False immediately
       without making any LLM call (T-03-09 DoS mitigation).
    2. LLM check: retrieve recent memories about the other agent and ask the LLM
       whether agent_name would realistically initiate conversation given context.

    Args:
        simulation_id:          The simulation these agents belong to.
        agent_name:             The agent considering starting the conversation.
        agent_scratch:          Initiating agent's personality data.
        other_name:             The other agent's name.
        other_activity:         What the other agent is currently doing.
        agent_current_activity: What the initiating agent is currently doing.
        location:               Where both agents are currently located.

    Returns:
        True if the agent should start a conversation; False otherwise.
    """
    # Phase 1: Check cooldown gate — no LLM call if still cooling down (T-03-09)
    if not check_cooldown(agent_name, other_name):
        logger.debug(
            "Conversation cooldown active for %s <-> %s", agent_name, other_name
        )
        return False

    # Phase 2: Retrieve recent memories about the other agent for context
    recent_memories = await retrieve_memories(
        simulation_id=simulation_id,
        agent_id=agent_name,
        query=f"conversations with {other_name}",
        top_k=3,
    )
    memory_dicts = [{"content": m.content} for m in recent_memories]

    # Phase 3: LLM decision — should they talk?
    messages = conversation_start_prompt(
        agent_name=agent_name,
        agent_traits=agent_scratch.innate,
        other_name=other_name,
        other_activity=other_activity,
        agent_current_activity=agent_current_activity,
        location=location,
        recent_memories=memory_dicts,
    )

    result: ConversationDecision = await complete_structured(
        messages=messages,
        response_model=ConversationDecision,
        fallback=ConversationDecision(should_talk=False, reasoning="LLM unavailable"),
    )

    return result.should_talk


async def run_conversation(
    simulation_id: str,
    agent_a_name: str,
    agent_a_scratch: AgentScratch,
    agent_b_name: str,
    agent_b_scratch: AgentScratch,
    location: str,
    remaining_schedule_a: list[ScheduleEntry],
    remaining_schedule_b: list[ScheduleEntry],
) -> dict:
    """Run a full multi-turn conversation between two agents.

    Turn loop (D-12, T-03-09):
    - Iterates over `range(MAX_TURNS)` — NEVER uses `while True`.
    - Both agents speak per round. Conversation ends if either agent sets
      end_conversation=True after at least 1 full round (2 turns minimum).
    - Hard cap: MAX_TURNS rounds (2*MAX_TURNS total utterances maximum).

    After the conversation (D-13):
    - Records cooldown for this pair.
    - Stores a conversation summary as a memory for each agent (not verbatim turns).
    - Uses score_importance() with failsafe=5 to rate the memory.
    - Calls schedule revision LLM for each agent's remaining schedule.

    Args:
        simulation_id:         The simulation these agents belong to.
        agent_a_name:          First agent's name.
        agent_a_scratch:       First agent's personality data.
        agent_b_name:          Second agent's name.
        agent_b_scratch:       Second agent's personality data.
        location:              Where the conversation takes place.
        remaining_schedule_a:  Agent A's remaining daily schedule.
        remaining_schedule_b:  Agent B's remaining daily schedule.

    Returns:
        Dict with:
          - "turns": list of {"speaker": str, "text": str} dicts
          - "revised_schedule_a": list[ScheduleEntry] for agent A
          - "revised_schedule_b": list[ScheduleEntry] for agent B
          - "summary": str describing the conversation topic
    """
    conversation_log: list[dict] = []
    ended_early = False

    # --- Turn loop: range(MAX_TURNS) ensures hard cap at MAX_TURNS rounds ---
    # Each round has 2 speakers (A then B). Total utterances <= 2 * MAX_TURNS.
    for turn in range(MAX_TURNS):
        # Agent A speaks
        messages_a = conversation_turn_prompt(
            agent_name=agent_a_name,
            agent_traits=agent_a_scratch.innate,
            other_name=agent_b_name,
            conversation_so_far=conversation_log,
            turn_number=turn + 1,
            max_turns=MAX_TURNS,
        )
        turn_a: ConversationTurn = await complete_structured(
            messages=messages_a,
            response_model=ConversationTurn,
            fallback=ConversationTurn(text="...", end_conversation=True),
        )
        conversation_log.append({"speaker": agent_a_name, "text": turn_a.text})

        # End conversation if A wants to end AND at least 1 full round completed
        if turn_a.end_conversation and turn >= 1:
            ended_early = True
            break

        # Agent B speaks
        messages_b = conversation_turn_prompt(
            agent_name=agent_b_name,
            agent_traits=agent_b_scratch.innate,
            other_name=agent_a_name,
            conversation_so_far=conversation_log,
            turn_number=turn + 1,
            max_turns=MAX_TURNS,
        )
        turn_b: ConversationTurn = await complete_structured(
            messages=messages_b,
            response_model=ConversationTurn,
            fallback=ConversationTurn(text="...", end_conversation=True),
        )
        conversation_log.append({"speaker": agent_b_name, "text": turn_b.text})

        # End conversation if B wants to end AND at least 1 full round completed
        if turn_b.end_conversation and turn >= 1:
            ended_early = True
            break

    # --- Record cooldown to prevent same-pair conversation spam ---
    _record_conversation(agent_a_name, agent_b_name)

    # --- Build conversation summary (Anti-Pattern: store extracted summary, not verbatim) ---
    # Concatenate key text from turns to approximate topic
    all_text = " ".join(t["text"] for t in conversation_log)
    # Truncate to keep summary manageable
    summary_text = all_text[:300] if len(all_text) > 300 else all_text

    summary_a = f"Had a conversation with {agent_b_name} at {location}: {summary_text}"
    summary_b = f"Had a conversation with {agent_a_name} at {location}: {summary_text}"

    # --- Store conversation summary as memory for each agent (T-03-12: limited to 2 memories) ---
    importance_a = await score_importance(
        agent_name=agent_a_name,
        agent_scratch=agent_a_scratch.innate,
        memory_text=summary_a,
        agent_lifestyle=agent_a_scratch.lifestyle,
    )
    importance_b = await score_importance(
        agent_name=agent_b_name,
        agent_scratch=agent_b_scratch.innate,
        memory_text=summary_b,
        agent_lifestyle=agent_b_scratch.lifestyle,
    )

    await add_memory(
        simulation_id=simulation_id,
        agent_id=agent_a_name,
        content=summary_a,
        memory_type="conversation",
        importance=importance_a,
    )
    await add_memory(
        simulation_id=simulation_id,
        agent_id=agent_b_name,
        content=summary_b,
        memory_type="conversation",
        importance=importance_b,
    )

    # --- Schedule revision (D-10, D-13): each agent revises remaining schedule ---
    # Format remaining schedules as dicts for the prompt.
    # Only include entries with a valid "describe" field — skip malformed dicts that
    # lack it to avoid passing raw dict reprs like "{'start_minute': 720}" into the LLM.
    schedule_a_dicts = []
    for e in remaining_schedule_a:
        if hasattr(e, "describe"):
            schedule_a_dicts.append({"describe": e.describe})
        elif isinstance(e, dict) and "describe" in e:
            schedule_a_dicts.append({"describe": e["describe"]})
        # else: silently skip malformed entries without a describe field

    schedule_b_dicts = []
    for e in remaining_schedule_b:
        if hasattr(e, "describe"):
            schedule_b_dicts.append({"describe": e.describe})
        elif isinstance(e, dict) and "describe" in e:
            schedule_b_dicts.append({"describe": e["describe"]})
        # else: silently skip malformed entries without a describe field

    messages_revise_a = schedule_revise_prompt(
        agent_name=agent_a_name,
        agent_traits=agent_a_scratch.innate,
        conversation_summary=summary_text,
        remaining_schedule=schedule_a_dicts,
    )
    messages_revise_b = schedule_revise_prompt(
        agent_name=agent_b_name,
        agent_traits=agent_b_scratch.innate,
        conversation_summary=summary_text,
        remaining_schedule=schedule_b_dicts,
    )

    revision_a: ScheduleRevision = await complete_structured(
        messages=messages_revise_a,
        response_model=ScheduleRevision,
        fallback=ScheduleRevision(revised_entries=remaining_schedule_a, reason="LLM unavailable"),
    )
    revision_b: ScheduleRevision = await complete_structured(
        messages=messages_revise_b,
        response_model=ScheduleRevision,
        fallback=ScheduleRevision(revised_entries=remaining_schedule_b, reason="LLM unavailable"),
    )

    return {
        "turns": conversation_log,
        "revised_schedule_a": revision_a.revised_entries,
        "revised_schedule_b": revision_b.revised_entries,
        "summary": summary_text,
    }
