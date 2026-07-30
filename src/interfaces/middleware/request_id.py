"""Request ID middleware for tracing."""

import uuid
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.logging.logger import get_logger

logger = get_logger("quantiquan.middleware.request_id")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to inject X-Request-ID header."""

    async def dispatch(self, request: Request, call_next):
        """Process request and inject request ID."""
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        # Bind request ID to logger context
        logger.bind(request_id=request_id)

        # Add to request state
        request.state.request_id = request_id

        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response