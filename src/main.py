"""FastAPI application entry point."""
import os
import contextlib
from typing import AsyncGenerator, Optional

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from src.core.config.settings import get_settings
from src.core.di.container import get_container
from src.core.logging.logger import get_logger
from src.core.logging.request_logger import RequestLogger
from src.core.monitoring.health import HealthChecker
from src.interfaces.api.v1.router import router as v1_router
from src.interfaces.middleware.exception_handler import setup_exception_handlers
from src.interfaces.middleware.logging import LoggingMiddleware
from src.interfaces.middleware.request_id import RequestIDMiddleware

logger = get_logger("quantiquan.main")
request_logger = RequestLogger(logger)


def create_app() -> FastAPI:
    """Create FastAPI application.

    Returns:
        FastAPI: Configured FastAPI application.
    """
    settings = get_settings()

    app = FastAPI(
        title="QUANTIQUAN AI Engine",
        version=settings.app_version,
        description="Security Decision Intelligence Platform - Risk Scoring & AI Summaries",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Trusted host middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"] if settings.debug else settings.allowed_origins,
    )

    # Request ID middleware
    #app.add_middleware(RequestIDMiddleware)

    # Logging middleware
    #app.add_middleware(LoggingMiddleware)

    # Register routers
    app.include_router(v1_router)

    # Set up exception handlers
    setup_exception_handlers(app)

    # Set up lifecycle events
    @app.on_event("startup")
    async def startup_event() -> None:
        """Application startup event."""
        logger.info(
            "Starting QUANTIQUAN AI Engine",
            version=settings.app_version,
            environment=settings.environment,
        )
        # Initialize DI container
        container = get_container()
        container.initialize()
        logger.info("DI container initialized")

        # Setup health checks
        try:
            # Use the type, not a string
            health_checker = container.get(HealthChecker)
            if health_checker:
                # Register health checks
                from src.core.monitoring.health import database_health_check, groq_health_check, redis_health_check
                health_checker.register("database", database_health_check)
                health_checker.register("redis", redis_health_check)
                health_checker.register("groq", groq_health_check)
                logger.info("Health checks registered")
        except Exception as exc:
            logger.warning("Failed to register health checks", error=str(exc))

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        """Application shutdown event."""
        logger.info("Shutting down QUANTIQUAN AI Engine")
        # Clean up resources
        try:
            container = get_container()
            # Close any connections
        except Exception as exc:
            logger.warning("Error during shutdown", error=str(exc))

    return app


def cli() -> None:
    """CLI entry point for running the application."""
    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=int(os.environ.get("port",8000)),
        reload=settings.debug,
        log_level="info",
    )


app = create_app()


if __name__ == "__main__":
    cli()