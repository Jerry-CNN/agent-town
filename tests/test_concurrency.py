"""Concurrency proof: 10 async tasks complete in parallel, not sequentially."""
import asyncio
import time
import pytest


async def test_ten_tasks_run_concurrently():
    """
    INF-02: 10 simulated agent steps run in parallel.
    Each step sleeps 0.1s. If sequential: ~1.0s. If parallel: ~0.1s.
    Assertion: total elapsed < 0.5s proves concurrent execution.
    """
    results: list[float] = []

    async def agent_step(step_id: int) -> float:
        await asyncio.sleep(0.1)
        timestamp = time.perf_counter()
        results.append(timestamp)
        return timestamp

    start = time.perf_counter()
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(agent_step(i)) for i in range(10)]
    end = time.perf_counter()

    elapsed = end - start
    assert elapsed < 0.5, (
        f"10 tasks took {elapsed:.3f}s — expected < 0.5s (concurrent). "
        f"Sequential execution would take ~1.0s."
    )
    assert len(results) == 10, "All 10 tasks should have recorded timestamps"


async def test_task_group_raises_on_exception():
    """TaskGroup propagates exceptions correctly (structured concurrency)."""
    async def failing_task():
        await asyncio.sleep(0.01)
        raise ValueError("task failed")

    with pytest.raises(ExceptionGroup):
        async with asyncio.TaskGroup() as tg:
            tg.create_task(failing_task())
