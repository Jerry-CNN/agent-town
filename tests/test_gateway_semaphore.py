"""Unit tests for gateway.py asyncio.Semaphore concurrency limiting and latency tracking.

TDD RED phase — these tests FAIL before the implementation is added to gateway.py.
"""
import asyncio
import time
import pytest

from backend import gateway


# ---------------------------------------------------------------------------
# Test 1: Semaphore limits in-flight calls
# ---------------------------------------------------------------------------
async def test_semaphore_limits_concurrent_inflight(monkeypatch):
    """
    With semaphore(2) and 4 concurrent calls, at most 2 are in-flight
    simultaneously. We measure max concurrent count via a shared counter.
    """
    from backend.schemas import ProviderConfig, AgentAction

    # Temporarily replace the module-level semaphore with one that allows only 2
    monkeypatch.setattr(gateway, "_llm_semaphore", asyncio.Semaphore(2))

    in_flight = 0
    max_in_flight = 0

    async def mock_create(*args, **kwargs):
        nonlocal in_flight, max_in_flight
        in_flight += 1
        max_in_flight = max(max_in_flight, in_flight)
        await asyncio.sleep(0.05)  # hold the slot briefly to reveal queueing
        in_flight -= 1
        return AgentAction(destination="park", activity="walking", reasoning="test")

    monkeypatch.setattr(gateway._client.chat.completions, "create", mock_create)

    provider = ProviderConfig(provider="ollama")

    async def call():
        return await gateway.complete_structured(
            messages=[{"role": "user", "content": "test"}],
            response_model=AgentAction,
            provider_config=provider,
            max_retries=1,
        )

    await asyncio.gather(call(), call(), call(), call())

    assert max_in_flight <= 2, (
        f"Expected at most 2 concurrent in-flight calls (semaphore=2), "
        f"got max_in_flight={max_in_flight}"
    )


# ---------------------------------------------------------------------------
# Test 2: Successful call appends elapsed time to _latency_window
# ---------------------------------------------------------------------------
async def test_successful_call_records_latency(monkeypatch):
    """After a successful LLM call, _latency_window contains one entry with elapsed time."""
    from collections import deque
    from backend.schemas import ProviderConfig, AgentAction

    # Reset the latency window for isolation
    monkeypatch.setattr(gateway, "_latency_window", deque(maxlen=10))

    async def mock_create(*args, **kwargs):
        await asyncio.sleep(0.01)
        return AgentAction(destination="park", activity="walking", reasoning="test")

    monkeypatch.setattr(gateway._client.chat.completions, "create", mock_create)

    provider = ProviderConfig(provider="ollama")
    result = await gateway.complete_structured(
        messages=[{"role": "user", "content": "test"}],
        response_model=AgentAction,
        provider_config=provider,
        max_retries=1,
    )

    assert isinstance(result, AgentAction)
    assert len(gateway._latency_window) == 1, (
        f"Expected 1 latency entry after a successful call, "
        f"got {len(gateway._latency_window)}"
    )
    elapsed = gateway._latency_window[0]
    assert elapsed >= 0.0, "Elapsed time must be non-negative"
    # The mock sleeps 0.01s — allow a generous upper bound for CI overhead
    assert elapsed < 5.0, f"Elapsed time {elapsed:.3f}s is unreasonably large"


# ---------------------------------------------------------------------------
# Test 3: Failed calls do NOT append to _latency_window
# ---------------------------------------------------------------------------
async def test_failed_call_does_not_record_latency(monkeypatch):
    """Failed LLM calls do NOT append to _latency_window (Pitfall 6: only successful)."""
    from collections import deque
    from backend.schemas import ProviderConfig, AgentAction

    monkeypatch.setattr(gateway, "_latency_window", deque(maxlen=10))

    async def mock_create_fail(*args, **kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(gateway._client.chat.completions, "create", mock_create_fail)

    provider = ProviderConfig(provider="ollama")
    # All retries fail — returns FALLBACK_AGENT_ACTION for AgentAction response_model
    result = await gateway.complete_structured(
        messages=[{"role": "user", "content": "test"}],
        response_model=AgentAction,
        provider_config=provider,
        max_retries=2,
    )

    assert isinstance(result, AgentAction)
    assert result.destination == "idle", "Expected FALLBACK_AGENT_ACTION on all failures"
    assert len(gateway._latency_window) == 0, (
        f"Failed calls must not append to _latency_window, "
        f"got {len(gateway._latency_window)} entries"
    )


# ---------------------------------------------------------------------------
# Test 4: get_adaptive_tick_interval with empty window returns min_interval
# ---------------------------------------------------------------------------
def test_adaptive_tick_interval_empty_window_returns_min(monkeypatch):
    """get_adaptive_tick_interval() with empty window returns min_interval (10.0)."""
    from collections import deque

    monkeypatch.setattr(gateway, "_latency_window", deque(maxlen=10))

    result = gateway.get_adaptive_tick_interval()
    assert result == 10.0, f"Expected 10.0, got {result}"


# ---------------------------------------------------------------------------
# Test 5: get_adaptive_tick_interval with fast window stays at min
# ---------------------------------------------------------------------------
def test_adaptive_tick_interval_fast_window_clamps_to_min(monkeypatch):
    """get_adaptive_tick_interval() with window [3.0, 3.0, 3.0] returns max(10, 4.5)=10.0."""
    from collections import deque

    window = deque([3.0, 3.0, 3.0], maxlen=10)
    monkeypatch.setattr(gateway, "_latency_window", window)

    result = gateway.get_adaptive_tick_interval()
    expected = max(10.0, (3.0 + 3.0 + 3.0) / 3 * 1.5)  # max(10, 4.5) = 10.0
    assert result == expected, f"Expected {expected}, got {result}"
    assert result == 10.0


# ---------------------------------------------------------------------------
# Test 6: get_adaptive_tick_interval with slow window returns avg*1.5
# ---------------------------------------------------------------------------
def test_adaptive_tick_interval_slow_window_returns_scaled(monkeypatch):
    """get_adaptive_tick_interval() with window [12.0, 12.0] returns max(10, 18.0)=18.0."""
    from collections import deque

    window = deque([12.0, 12.0], maxlen=10)
    monkeypatch.setattr(gateway, "_latency_window", window)

    result = gateway.get_adaptive_tick_interval()
    expected = max(10.0, 12.0 * 1.5)  # max(10, 18.0) = 18.0
    assert result == expected, f"Expected {expected}, got {result}"
    assert result == 18.0


# ---------------------------------------------------------------------------
# Test 7: Debug log messages contain expected text on acquire/release
# ---------------------------------------------------------------------------
async def test_debug_log_messages_on_acquire_and_release(monkeypatch, caplog):
    """Debug log messages contain 'LLM semaphore acquired' on entry and 'LLM semaphore released'."""
    import logging
    from collections import deque
    from backend.schemas import ProviderConfig, AgentAction

    monkeypatch.setattr(gateway, "_latency_window", deque(maxlen=10))

    async def mock_create(*args, **kwargs):
        return AgentAction(destination="park", activity="walking", reasoning="test")

    monkeypatch.setattr(gateway._client.chat.completions, "create", mock_create)

    provider = ProviderConfig(provider="ollama")

    with caplog.at_level(logging.DEBUG, logger="backend.gateway"):
        await gateway.complete_structured(
            messages=[{"role": "user", "content": "test"}],
            response_model=AgentAction,
            provider_config=provider,
            max_retries=1,
        )

    log_text = " ".join(caplog.messages)
    assert "LLM call:" in log_text, (
        f"Expected 'LLM call:' in logs. Got: {caplog.messages}"
    )
    assert "LLM done:" in log_text, (
        f"Expected 'LLM done:' in logs. Got: {caplog.messages}"
    )
