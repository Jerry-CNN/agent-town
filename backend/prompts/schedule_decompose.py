"""Prompt template for hourly schedule block decomposition (D-08).

LLM Call 2 of 2 in schedule generation: breaks an hourly activity block
into 5-15 minute sub-tasks that fit within the given duration.

Reference: GenerativeAgentsCN/generative_agents/modules/plan.py (schedule_decompose)
"""


def schedule_decompose_prompt(
    agent_name: str,
    hourly_activity: str,
    duration_minutes: int,
) -> list[dict]:
    """Build the messages list for decomposing one hourly block into sub-tasks.

    Args:
        agent_name:       Agent's name for context.
        hourly_activity:  Description of the hourly block to decompose.
        duration_minutes: Total duration of the hourly block in minutes.

    Returns:
        A messages list: [system_message, user_message] suitable for
        complete_structured() with a list[SubTask] response_model.
    """
    system_message = {
        "role": "system",
        "content": (
            "You are a detailed task planner. Your job is to break down high-level "
            "hourly activities into specific 5-15 minute sub-tasks that together "
            "fill the allotted time. Each sub-task should be a concrete, observable action."
        ),
    }

    user_message = {
        "role": "user",
        "content": (
            f"Break down the following activity for {agent_name} into specific sub-tasks:\n\n"
            f"Activity: {hourly_activity}\n"
            f"Total duration: {duration_minutes} minutes\n\n"
            f"Create a list of 3-5 sub-tasks that together cover the full {duration_minutes} minutes. "
            f"Each sub-task should take 5-15 minutes. "
            f"Include the start_minute (minutes from midnight) and duration_minutes for each sub-task."
        ),
    }

    return [system_message, user_message]
