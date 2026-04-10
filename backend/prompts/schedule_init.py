"""Prompt template for daily schedule initialization (D-08, D-09).

LLM Call 1 of 2 in schedule generation: generates hourly activity blocks
from an agent's personality and daily_plan template.

CRITICAL (Pitfall 4): The agent's daily_plan template MUST be injected into
the prompt. Without it, the LLM generates generic schedules that ignore the
agent's configured routine, breaking D-09 (hybrid routines from config).

Reference: GenerativeAgentsCN/generative_agents/modules/plan.py (make_schedule)
"""


def schedule_init_prompt(
    agent_name: str,
    agent_age: int,
    agent_traits: str,
    agent_lifestyle: str,
    daily_plan_template: str,
) -> list[dict]:
    """Build the messages list for initial daily schedule generation.

    Args:
        agent_name:           Agent's name (used for pronoun context).
        agent_age:            Agent's age in years.
        agent_traits:         Comma-separated personality traits (from AgentScratch.innate).
        agent_lifestyle:      Lifestyle description (from AgentScratch.lifestyle).
        daily_plan_template:  Routine template string (from AgentScratch.daily_plan).
                              MUST be included — this seeds the agent's schedule.

    Returns:
        A messages list: [system_message, user_message] suitable for
        complete_structured() with DailySchedule as response_model.
    """
    system_message = {
        "role": "system",
        "content": (
            "You are a schedule planner for generative AI agents in a simulated town. "
            "Your task is to create realistic, detailed daily schedules based on an agent's "
            "personality, lifestyle, and established daily routine template. "
            "Generate schedules that feel authentic to the agent's character."
        ),
    }

    user_message = {
        "role": "user",
        "content": (
            f"Create a detailed daily schedule for {agent_name}, a {agent_age}-year-old "
            f"with the following personality traits: {agent_traits}.\n\n"
            f"Lifestyle and habits: {agent_lifestyle}\n\n"
            f"Daily routine template (this is {agent_name}'s established routine -- "
            f"the schedule should follow this pattern):\n{daily_plan_template}\n\n"
            f"Generate a list of activities for each hour {agent_name} is awake, "
            f"following their routine template. Include specific activities that reflect "
            f"their personality and daily patterns. Also specify what hour they wake up."
        ),
    }

    return [system_message, user_message]
