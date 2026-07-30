"""Logging middleware for request/response logging."""

import time
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.logging.logger import get_logger
from src.core.logging.request_logger import RequestLogger

logger = get_logger("quantiquan.middleware.logging")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests and responses."""

    def __init__(self, app, skip_paths: Optional[list[str]] = None):
        """Initialize middleware.

        Args:
            app: ASGI app.
            skip_paths: Paths to skip logging.
        """
        super().__init__(app)
        self.skip_paths = skip_paths or ["/health", "/readiness", "/metrics"]
        self.request_logger = RequestLogger(logger)

    async def dispatch(self, request: Request, call_next):
        """Process request and log details."""
        # Skip logging for certain paths
        if request.url.path in self.skip_paths:
            return await call_next(request)

        start_time = time.perf_counter()
        request_id = request.state.request_id if hasattr(request.state, "request_id") else None

        # Log ingress
        self.request_logger.log_ingress(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            tenant_id=request.headers.get("X-Tenant-ID"),
        )

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log egress
            self.request_logger.log_egress(
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                tenant_id=request.headers.get("X-Tenant-ID"),
            )

            return response
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.request_logger.log_error(
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                error=exc,
                tenant_id=request.headers.get("X-Tenant-ID"),
                duration_ms=duration_ms,
            )
            raise