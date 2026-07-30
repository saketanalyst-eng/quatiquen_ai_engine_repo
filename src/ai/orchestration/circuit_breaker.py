"""Circuit breaker pattern for LLM calls."""

import asyncio
import time
from typing import Optional

from src.core.config.settings import get_settings
from src.core.logging.logger import get_logger

logger = get_logger("quantiquan.ai.circuit_breaker")


class CircuitBreaker:
    """Circuit breaker to prevent cascading LLM failures.

    States:
        CLOSED: Normal operation, calls go through.
        OPEN: Failure threshold exceeded, calls fail fast.
        HALF_OPEN: Trial period to test if service recovered.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: int = 30,
    ) -> None:
        """Initialize circuit breaker."""
        settings = get_settings()
        self.failure_threshold = failure_threshold or settings.circuit_breaker_failure_threshold
        self.timeout_seconds = timeout_seconds or settings.circuit_breaker_timeout_seconds

        self._state: str = "CLOSED"
        self._failure_count: int = 0
        self._last_failure_time: Optional[float] = None
        self._lock = asyncio.Lock()

    @property
    def is_open(self) -> bool:
        return self._state == "OPEN"

    @property
    def is_closed(self) -> bool:
        return self._state == "CLOSED"

    @property
    def is_half_open(self) -> bool:
        return self._state == "HALF_OPEN"

    async def record_success(self) -> None:
        async with self._lock:
            if self._state == "HALF_OPEN":
                self._state = "CLOSED"
                self._failure_count = 0
                logger.info("Circuit breaker closed (recovery successful)")
            elif self._state == "CLOSED":
                self._failure_count = 0

    async def record_failure(self) -> None:
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == "CLOSED" and self._failure_count >= self.failure_threshold:
                self._state = "OPEN"
                logger.warning("Circuit breaker opened (threshold exceeded)")
            elif self._state == "HALF_OPEN":
                self._state = "OPEN"
                logger.warning("Circuit breaker opened (recovery failed)")

    async def allow_request(self) -> bool:
        async with self._lock:
            if self._state == "CLOSED":
                return True

            if self._state == "OPEN":
                if self._last_failure_time is not None:
                    elapsed = time.time() - self._last_failure_time
                    if elapsed >= self.timeout_seconds:
                        self._state = "HALF_OPEN"
                        logger.info("Circuit breaker half-open (testing recovery)")
                        return True
                return False

            # HALF_OPEN: allow one request
            return True

    # ✅ Async context manager methods
    async def __aenter__(self):
        if not await self.allow_request():
            logger.warning("Circuit breaker blocked request")
            raise Exception("Circuit breaker is open")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            await self.record_success()
        else:
            await self.record_failure()
        return False  # Do not suppress exceptions