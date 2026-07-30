"""Structured logger factory."""

import logging
import sys
from typing import Any, Optional

import structlog

from src.core.config.environment import get_environment


def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Optional logger name (typically __name__).

    Returns:
        structlog.BoundLogger: Structured logger instance.
    """
    if name is None:
        name = "quantiquan"

    # Ensure structlog is configured
    try:
        structlog.is_configured()
    except (AttributeError, ValueError):
        # Fallback: configure basic
        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso", utc=True),
                structlog.processors.JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

    logger = structlog.get_logger(name)
    return logger


def get_async_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """Get a logger that supports async context.

    This is an alias for get_logger for clarity in async code.

    Args:
        name: Optional logger name.

    Returns:
        structlog.BoundLogger: Structured logger instance.
    """
    return get_logger(name)


def log_exception(
    logger: structlog.BoundLogger,
    exc: Exception,
    message: str,
    **kwargs: Any,
) -> None:
    """Log an exception with structured context.

    Args:
        logger: The logger instance.
        exc: The exception to log.
        message: Human-readable message.
        **kwargs: Additional context to include.
    """
    logger.error(
        message,
        exception_type=exc.__class__.__name__,
        exception_message=str(exc),
        **kwargs,
        exc_info=True,
    )


def log_audit_event(
    logger: structlog.BoundLogger,
    event_type: str,
    tenant_id: str,
    finding_id: str,
    **kwargs: Any,
) -> None:
    """Log an audit event.

    Args:
        logger: The logger instance.
        event_type: Type of audit event.
        tenant_id: Tenant identifier.
        finding_id: Finding identifier.
        **kwargs: Additional audit context.
    """
    logger.info(
        "AUDIT_EVENT",
        event_type=event_type,
        tenant_id=tenant_id,
        finding_id=finding_id,
        **kwargs,
    )