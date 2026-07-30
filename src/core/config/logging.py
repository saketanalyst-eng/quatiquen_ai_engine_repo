"""Structured logging configuration using structlog."""

import logging
import sys
from typing import Dict, Optional

import structlog
from structlog.processors import (
    StackInfoRenderer,
    TimeStamper,
    UnicodeDecoder,
    format_exc_info,
)

from src.core.config.environment import get_environment


def configure_structlog(
    level: str = "INFO",
    json_output: Optional[bool] = None,
    log_file: Optional[str] = None,
) -> None:
    """Configure structlog for structured JSON logging.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_output: Force JSON output. If None, auto-detects based on environment.
        log_file: Optional file path to write logs to. If None, writes to stdout.
    """
    if json_output is None:
        env = get_environment()
        json_output = env.is_production_like

    # Configure standard logging
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(level=log_level, stream=sys.stdout)

    # Define timestamp processor
    timestamp = TimeStamper(fmt="iso", utc=True)

    # Shared processors
    shared_processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        StackInfoRenderer(),
        format_exc_info,
        timestamp,
        structlog.processors.StackInfoRenderer(),
    ]

    if json_output:
        # JSON output for production/staging
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(serializer=lambda obj, **kwargs: __import__("json").dumps(obj, default=str)),
        ]
        renderer = structlog.processors.JSONRenderer()
    else:
        # Pretty console output for development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.plain_traceback,
            )
        ]
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Set up logging handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        root_logger.addHandler(file_handler)
    else:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(log_level)
        if json_output:
            stream_handler.setFormatter(logging.Formatter("%(message)s"))
        root_logger.addHandler(stream_handler)


def get_logger_config() -> Dict[str, str]:
    """Get logger configuration for third-party libraries.

    Returns:
        Dict[str, str]: Logger level overrides for third-party packages.
    """
    return {
        "uvicorn": "WARNING",
        "uvicorn.access": "WARNING",
        "uvicorn.error": "ERROR",
        "sqlalchemy.engine": "WARNING",
        "aioredis": "WARNING",
        "httpx": "WARNING",
        "httpcore": "WARNING",
    }