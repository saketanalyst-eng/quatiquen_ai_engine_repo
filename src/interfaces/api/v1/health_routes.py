"""Health check routes - bypassing DI for reliability."""

from fastapi import APIRouter, status

from src.core.monitoring.health import HealthChecker

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint."""
    checker = HealthChecker()
    return await checker.health_response()


@router.get("/readiness", status_code=status.HTTP_200_OK)
async def readiness_check():
    """Readiness probe endpoint."""
    checker = HealthChecker()
    status, _ = await checker.get_overall_status()
    return {"status": "ready" if status == "healthy" else "not ready"}