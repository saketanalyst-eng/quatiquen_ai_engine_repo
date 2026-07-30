
### File: src/core/exceptions/application.py

"""Application layer exceptions.

These exceptions represent use case orchestration failures, pipeline
interruptions, or application-level business rule violations.
"""

from src.core.exceptions.domain import DomainError


class ApplicationError(Exception):
    """Base exception for application layer errors.

    Raised when use case orchestration fails or application-level
    constraints are violated.
    """

    def __init__(self, message: str, code: str = "APPLICATION_ERROR", detail: dict = None) -> None:
        """Initialize application error.

        Args:
            message: Human-readable error message.
            code: Error code for categorization.
            detail: Additional error context data.
        """
        self.message = message
        self.code = code
        self.detail = detail or {}
        super().__init__(message)


class UseCaseError(ApplicationError):
    """Raised when a use case execution fails."""

    def __init__(self, message: str, use_case: str = None, cause: Exception = None) -> None:
        """Initialize use case error.

        Args:
            message: Error description.
            use_case: Name of the failing use case.
            cause: Original exception that caused the failure.
        """
        detail = {"use_case": use_case} if use_case else {}
        if cause:
            detail["cause"] = str(cause)
        super().__init__(message, code="USE_CASE_ERROR", detail=detail)


class PipelineInterruptionError(ApplicationError):
    """Raised when the scoring pipeline is interrupted."""

    def __init__(self, message: str, stage: str = None, finding_id: str = None) -> None:
        """Initialize pipeline interruption error.

        Args:
            message: Error description.
            stage: Pipeline stage that failed.
            finding_id: ID of the finding being processed.
        """
        detail = {}
        if stage:
            detail["stage"] = stage
        if finding_id:
            detail["finding_id"] = finding_id
        super().__init__(message, code="PIPELINE_INTERRUPTION", detail=detail)


class ConfigurationError(ApplicationError):
    """Raised when application configuration is invalid."""

    def __init__(self, message: str, config_key: str = None) -> None:
        """Initialize configuration error.

        Args:
            message: Error description.
            config_key: The configuration key that is invalid.
        """
        detail = {"config_key": config_key} if config_key else {}
        super().__init__(message, code="CONFIGURATION_ERROR", detail=detail)