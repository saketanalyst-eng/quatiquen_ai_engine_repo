"""Unit tests for circuit breaker."""

import pytest
from src.ai.orchestration.circuit_breaker import CircuitBreaker


@pytest.mark.asyncio
async def test_circuit_breaker_closed() -> None:
    """Test circuit breaker starts closed."""
    cb = CircuitBreaker(failure_threshold=2, timeout_seconds=1)
    assert cb.is_closed
    assert await cb.allow_request() is True


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_failures() -> None:
    """Test circuit breaker opens after threshold failures."""
    cb = CircuitBreaker(failure_threshold=2, timeout_seconds=1)

    # First failure
    await cb.record_failure()
    assert cb.is_closed  # still closed
    assert cb._failure_count == 1

    # Second failure
    await cb.record_failure()
    assert cb.is_open
    assert cb._failure_count == 2

    # Third attempt blocked
    assert await cb.allow_request() is False


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_after_timeout() -> None:
    """Test circuit breaker transitions to half-open after timeout."""
    cb = CircuitBreaker(failure_threshold=1, timeout_seconds=1)
    await cb.record_failure()
    assert cb.is_open

    # Simulate timeout by waiting
    import asyncio
    await asyncio.sleep(1.1)

    # Should now allow one request
    assert await cb.allow_request() is True
    assert cb.is_half_open

    # Record success -> closes
    await cb.record_success()
    assert cb.is_closed
    assert cb._failure_count == 0


@pytest.mark.asyncio
async def test_circuit_breaker_context_manager() -> None:
    """Test using circuit breaker as context manager."""
    cb = CircuitBreaker(failure_threshold=1, timeout_seconds=1)

    # Normal success
    async with cb:
        pass
    assert cb.is_closed
    assert cb._failure_count == 0

    # Failure
    with pytest.raises(ValueError):
        async with cb:
            raise ValueError("test error")
    assert cb.is_open