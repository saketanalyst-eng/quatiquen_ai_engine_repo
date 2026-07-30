"""Request logging utilities for FastAPI middleware."""

import time
from typing import Any, Dict, Optional

from structlog import BoundLogger

from src.core.logging.logger import get_logger


class RequestLogger:
    """Request logger for tracking HTTP requests and responses.

    This class provides structured logging for request ingress, egress,
    and performance metrics.
    """

    def __init__(self, logger: Optional[BoundLogger] = None) -> None:
        """Initialize request logger.

        Args:
            logger: Optional logger instance. If not provided, creates a new one.
        """
        self.logger = logger or get_logger("quantiquan.request")

    def log_ingress(
        self,
        request_id: str,
        method: str,
        path: str,
        tenant_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Log incoming request.

        Args:
            request_id: Unique request identifier.
            method: HTTP method.
            path: Request path.
            tenant_id: Tenant identifier.
            client_ip: Client IP address.
            user_agent: User agent string.
            **kwargs: Additional context.
        """
        self.logger.info(
            "Request started",
            request_id=request_id,
            method=method,
            path=path,
            tenant_id=tenant_id,
            client_ip=client_ip,
            user_agent=user_agent,
            **kwargs,
        )

    def log_egress(
        self,
        request_id: str,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        tenant_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Log outgoing response.

        Args:
            request_id: Unique request identifier.
            method: HTTP method.
            path: Request path.
            status_code: HTTP response status code.
            duration_ms: Request duration in milliseconds.
            tenant_id: Tenant identifier.
            **kwargs: Additional context.
        """
        log_level = "info" if status_code < 400 else "error"

        self.logger.log(
            log_level,
            "Request completed",
            request_id=request_id,
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            tenant_id=tenant_id,
            **kwargs,
        )

    def log_error(
        self,
        request_id: str,
        method: str,
        path: str,
        error: Exception,
        tenant_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Log request error.

        Args:
            request_id: Unique request identifier.
            method: HTTP method.
            path: Request path.
            error: Exception that occurred.
            tenant_id: Tenant identifier.
            **kwargs: Additional context.
        """
        self.logger.error(
            "Request error",
            request_id=request_id,
            method=method,
            path=path,
            error_type=error.__class__.__name__,
            error_message=str(error),
            tenant_id=tenant_id,
            exc_info=True,
            **kwargs,
        )

    def bind(self, **kwargs: Any) -> BoundLogger:
        """Bind context to the underlying logger.

        Args:
            **kwargs: Key-value pairs to bind.

        Returns:
            BoundLogger: Bound logger instance.
        """
        return self.logger.bind(**kwargs)