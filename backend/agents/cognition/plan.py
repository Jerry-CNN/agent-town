"""Two-level daily schedule generation for Agent Town agents.

Implements the two-level schedule generation pattern from the reference:
  Level 1 (generate_daily_schedule): LLM generates hourly activity blocks
  Level 2 (decompose_hour): LLM decomposes each hour into 5-15 minute sub-tasks

Total: 2 LLM calls per full schedule generation (D-08).
Schedule uses the agent's daily_plan template from AgentScratch (D-09).

Reference: GenerativeAgentsCN/generative_agents/modules/plan.py
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from backend.gateway import complete_structured
from backend.schemas import DailySchedule, ScheduleEntry, SubTask, AgentScratch
from backend.prompts.schedule_init import schedule_init_prompt
from backend.prompts.schedule_decompose import schedule_decompose_prompt


class _SubTaskList(BaseModel):
    """Wrapper model for structured LLM output: a list of sub-tasks.

    instructor requires a Pydantic model at the top level; this wraps the
    list[SubTask] so complete_structured() can parse and validate it.
    """
    subtasks: list[SubTask] = Field(min_length=1)


async def generate_daily_schedule(
    agent_name: str,
    agent_scratch: AgentScratch,
) -> list[ScheduleEntry]:
    """Generate an hourly daily schedule from the agent's personality and routine.

    LLM Call 1 of 2 in the two-level schedule pattern (D-08).

    The agent's daily_plan template is injected into the prompt (D-09, Pitfall 4):
    without it the LLM generates generic schedules that ignore the agent's
    configured routine.

    Args:
        agent_name:    Agent's name.
        agent_scratch: Agent's personality and background data.

    Returns:
        List of ScheduleEntry objects with hourly blocks, sorted by start_minute.
        Each entry's decompose list is empty — call decompose_hour() separately.
    """
    messages = schedule_init_prompt(
        agent_name=agent_name,
        agent_age=agent_scratch.age,
        agent_traits=agent_scratch.innate,
        agent_lifestyle=agent_scratch.lifestyle,
        daily_plan_template=agent_scratch.daily_plan,
    )

    daily_schedule: DailySchedule = await complete_structured(
        messages=messages,
        response_model=DailySchedule,
        fallback=DailySchedule(activities=["rest at home", "rest at home", "rest at home"], wake_hour=7),
    )

    # Convert activity list to ScheduleEntry objects.
    # Distribute activities across hours starting at wake_hour.
    entries: list[ScheduleEntry] = []
    for i, activity in enumerate(daily_schedule.activities):
        hour = daily_schedule.wake_hour + i
        start_minute = hour * 60
        # Clamp to valid range (shouldn't exceed 1439 for a reasonable schedule)
        if start_minute >= 1440:
            break
        entries.append(
            ScheduleEntry(
                start_minute=start_minute,
                duration_minutes=60,
                describe=activity,
            )
        )

    return entries


async def decompose_hour(
    agent_name: str,
    entry: ScheduleEntry,
) -> list[SubTask]:
    """Decompose an hourly schedule block into 5-15 minute sub-tasks.

    LLM Call 2 of 2 in the two-level schedule pattern (D-08).

    Args:
        agent_name: Agent's name for prompt context.
        entry:      The hourly ScheduleEntry to decompose.

    Returns:
        List of SubTask objects. Also attaches the result to entry.decompose.
    """
    messages = schedule_decompose_prompt(
        agent_name=agent_name,
        hourly_activity=entry.describe,
        duration_minutes=entry.duration_minutes,
    )

    result = await complete_structured(
        messages=messages,
        response_model=_SubTaskList,
        fallback=_SubTaskList(
            subtasks=[
                SubTask(
                    start_minute=entry.start_minute,
                    duration_minutes=entry.duration_minutes,
                    describe=entry.describe,
                )
            ]
        ),
    )

    # Handle both the case where result is already a list (mock) and where it's _SubTaskList
    if isinstance(result, list):
        subtasks = result
    else:
        subtasks = result.subtasks

    # Attach sub-tasks to the entry
    entry.decompose = subtasks

    return subtasks
