"""Core cross-cutting concerns module.

This module provides configuration, constants, exceptions, logging, security,
monitoring, caching, and dependency injection facilities that are used across
all layers of the application. It has zero dependencies on domain, application,
engine, AI, infrastructure, or interface layers.
"""

from src.core.config import settings
from src.core.logging import logger

__all__ = [
    "settings",
    "logger",
]