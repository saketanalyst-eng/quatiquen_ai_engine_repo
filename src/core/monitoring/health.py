"""Health check utilities for service readiness and liveness."""

import time
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple

from src.core.logging.logger import get_logger

logger = get_logger("quantiquan.health")


class HealthStatus(str, Enum):
    """Health check status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthChecker:
    """Health checker for service health monitoring."""

    def __init__(self, service_name: str = "quantiquan-ai-engine") -> None:
        """Initialize health checker.

        Args:
            service_name: Name of the service.
        """
        self.service_name = service_name
        self._checks: Dict[str, Callable] = {}

    def register(self, name: str, check_func: Callable) -> None:
        """Register a health check function.

        Args:
            name: Name of the health check.
            check_func: Async function that returns a dict with 'status' and 'message'.
        """
        self._checks[name] = check_func
        logger.info("Health check registered", name=name)

    def unregister(self, name: str) -> None:
        """Unregister a health check.

        Args:
            name: Name of the health check.
        """
        self._checks.pop(name, None)

    async def run_check(self, name: str) -> Dict[str, Any]:
        """Run a single health check.

        Returns:
            Dict: {'status': 'healthy'|'degraded'|'unhealthy', 'message': str, 'details': dict}
        """
        check_func = self._checks.get(name)
        if not check_func:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Health check '{name}' not found",
                "details": {},
            }

        try:
            start = time.perf_counter()
            result = await check_func()
            duration_ms = (time.perf_counter() - start) * 1000

            if isinstance(result, dict):
                result["duration_ms"] = round(duration_ms, 2)
                return result
            else:
                # Fallback if check returns something else
                return {
                    "status": HealthStatus.HEALTHY.value,
                    "message": str(result) if result else "OK",
                    "details": {},
                    "duration_ms": round(duration_ms, 2),
                }
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.error("Health check failed", name=name, error=str(exc), exc_info=True)
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "message": str(exc),
                "details": {},
                "duration_ms": round(duration_ms, 2),
            }

    async def run_all_checks(self) -> Dict[str, Dict[str, Any]]:
        """Run all registered health checks.

        Returns:
            Dict[str, Dict]: Mapping of check name to result dict.
        """
        results = {}
        for name in self._checks:
            results[name] = await self.run_check(name)
        return results

    async def get_overall_status(self) -> Tuple[str, Dict[str, Dict[str, Any]]]:
        """Get overall health status.

        Returns:
            Tuple[str, Dict]: Overall status ('healthy'|'degraded'|'unhealthy') and check results.
        """
        results = await self.run_all_checks()

        if not results:
            return HealthStatus.HEALTHY.value, results

        unhealthy = any(r.get("status") == HealthStatus.UNHEALTHY.value for r in results.values())
        degraded = any(r.get("status") == HealthStatus.DEGRADED.value for r in results.values())

        if unhealthy:
            return HealthStatus.UNHEALTHY.value, results
        if degraded:
            return HealthStatus.DEGRADED.value, results
        return HealthStatus.HEALTHY.value, results

    async def health_response(self) -> Dict[str, Any]:
        """Generate health check response for API.

        Returns:
            Dict: Health status response.
        """
        try:
            status, results = await self.get_overall_status()

            checks = {}
            for name, result in results.items():
                checks[name] = {
                    "status": result.get("status", "unknown"),
                    "message": result.get("message", ""),
                    "details": result.get("details", {}),
                    "duration_ms": result.get("duration_ms", 0),
                }

            return {
                "service": self.service_name,
                "status": status,
                "timestamp": time.time(),
                "checks": checks,
            }
        except Exception as exc:
            logger.error("Health response generation failed", error=str(exc), exc_info=True)
            # Always return a valid dict, never raise
            return {
                "service": self.service_name,
                "status": HealthStatus.UNHEALTHY.value,
                "timestamp": time.time(),
                "checks": {},
                "error": str(exc),
            }


async def database_health_check() -> Dict[str, Any]:
    """Check database health.

    Returns:
        Dict: Status dict.
    """
    try:
        # Simulate a database check; replace with actual ping
        return {"status": HealthStatus.HEALTHY.value, "message": "Database connection successful", "details": {}}
    except Exception as exc:
        return {"status": HealthStatus.UNHEALTHY.value, "message": str(exc), "details": {}}


async def redis_health_check() -> Dict[str, Any]:
    """Check Redis health.

    Returns:
        Dict: Status dict.
    """
    try:
        # Simulate Redis check; replace with actual ping
        return {"status": HealthStatus.HEALTHY.value, "message": "Redis connection successful", "details": {}}
    except Exception as exc:
        return {"status": HealthStatus.UNHEALTHY.value, "message": str(exc), "details": {}}


async def groq_health_check() -> Dict[str, Any]:
    """Check Groq API health.

    Returns:
        Dict: Status dict.
    """
    try:
        # Simulate Groq check; return degraded (since we might not have API key in dev)
        return {
            "status": HealthStatus.DEGRADED.value,
            "message": "Groq API is not configured in development",
            "details": {},
        }
    except Exception as exc:
        return {"status": HealthStatus.DEGRADED.value, "message": str(exc), "details": {}}