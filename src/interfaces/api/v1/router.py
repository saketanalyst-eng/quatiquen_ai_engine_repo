"""V1 API router aggregation."""

from fastapi import APIRouter

from src.interfaces.api.v1.admin_routes import router as admin_router
from src.interfaces.api.v1.health_routes import router as health_router
from src.interfaces.api.v1.risk_routes import router as risk_router

router = APIRouter(prefix="/api/v1")

router.include_router(health_router, tags=["health"])
router.include_router(risk_router, tags=["risk"])
router.include_router(admin_router, tags=["admin"])