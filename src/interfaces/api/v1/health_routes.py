"""Health check routes."""

from fastapi import APIRouter, Depends, status

from src.core.monitoring.health import HealthChecker
from src.interfaces.dependencies.inject import get_health_checker

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(checker: HealthChecker = Depends(get_health_checker)):
    """Health check endpoint."""
    return await checker.health_response()


@router.get("/readiness", status_code=status.HTTP_200_OK)
async def readiness_check(checker: HealthChecker = Depends(get_health_checker)):
    """Readiness probe endpoint."""
    overall_status, _ = await checker.get_overall_status()
    return {"status": "ready" if overall_status == "healthy" else "not ready"}