"""Custom exception hierarchy for the application.

All exceptions inherit from base domain, application, infrastructure,
or AI-specific error classes to enable fine-grained error handling.
"""

from src.core.exceptions.ai import (
    AIError,
    LLMProviderError,
    LLMResponseParseError,
    LLMTimeoutError,
)
from src.core.exceptions.application import (
    ApplicationError,
    ConfigurationError,          # <-- imported from application
    PipelineInterruptionError,
    UseCaseError,
)
from src.core.exceptions.domain import (
    DomainError,
    EntityNotFoundError,
    InvalidEntityStateError,
    InvalidValueObjectError,
    ValidationError,
)
from src.core.exceptions.infrastructure import (
    CacheError,
    DatabaseError,
    ExternalServiceError,
    InfrastructureError,
)

__all__ = [
    "AIError",
    "ApplicationError",
    "CacheError",
    "ConfigurationError",
    "DatabaseError",
    "DomainError",
    "EntityNotFoundError",
    "ExternalServiceError",
    "InfrastructureError",
    "InvalidEntityStateError",
    "InvalidValueObjectError",
    "LLMProviderError",
    "LLMResponseParseError",
    "LLMTimeoutError",
    "PipelineInterruptionError",
    "UseCaseError",
    "ValidationError",
]