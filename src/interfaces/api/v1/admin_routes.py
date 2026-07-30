"""Admin API routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from src.core.logging.logger import get_logger
from src.interfaces.dependencies.inject import get_container

logger = get_logger("quantiquan.interfaces.admin_routes")

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/cache/clear")
async def clear_cache(container=Depends(get_container)) -> dict:
    """Clear all cache.

    Args:
        container: DI container.

    Returns:
        dict: Success message.
    """
    try:
        cache = container.get("cache")
        if cache:
            await cache.delete_pattern("*")
        logger.info("Cache cleared")
        return {"status": "success", "message": "Cache cleared"}
    except Exception as exc:
        logger.error("Cache clear failed", error=str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "cache_error", "message": "Failed to clear cache"},
        )


@router.get("/health/detailed")
async def detailed_health(container=Depends(get_container)) -> dict:
    """Detailed health check with component status.

    Args:
        container: DI container.

    Returns:
        dict: Detailed health status.
    """
    try:
        health_checker = container.get("health_checker")
        if health_checker:
            return await health_checker.health_response()
        return {"status": "healthy", "components": {}}
    except Exception as exc:
        logger.error("Health check failed", error=str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "health_error", "message": "Health check failed"},
        )