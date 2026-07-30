"""Infrastructure layer exceptions.

These exceptions represent failures in external dependencies such as
databases, caches, message queues, or external API clients.
"""


class InfrastructureError(Exception):
    """Base exception for infrastructure layer errors.

    Raised when external dependencies fail or low-level operations
    encounter errors.
    """

    def __init__(self, message: str, code: str = "INFRASTRUCTURE_ERROR", detail: dict = None) -> None:
        """Initialize infrastructure error.

        Args:
            message: Human-readable error message.
            code: Error code for categorization.
            detail: Additional error context data.
        """
        self.message = message
        self.code = code
        self.detail = detail or {}
        super().__init__(message)


class DatabaseError(InfrastructureError):
    """Raised when database operations fail."""

    def __init__(self, message: str, operation: str = None, cause: Exception = None) -> None:
        """Initialize database error.

        Args:
            message: Error description.
            operation: Database operation that failed.
            cause: Original exception.
        """
        detail = {"operation": operation} if operation else {}
        if cause:
            detail["cause"] = str(cause)
        super().__init__(message, code="DATABASE_ERROR", detail=detail)


class CacheError(InfrastructureError):
    """Raised when cache operations fail."""

    def __init__(self, message: str, key: str = None, operation: str = None) -> None:
        """Initialize cache error.

        Args:
            message: Error description.
            key: Cache key that caused the error.
            operation: Cache operation that failed.
        """
        detail = {}
        if key:
            detail["key"] = key
        if operation:
            detail["operation"] = operation
        super().__init__(message, code="CACHE_ERROR", detail=detail)


class ExternalServiceError(InfrastructureError):
    """Raised when external API calls fail."""

    def __init__(self, message: str, service: str = None, status_code: int = None, cause: Exception = None) -> None:
        """Initialize external service error.

        Args:
            message: Error description.
            service: Name of the external service.
            status_code: HTTP status code if applicable.
            cause: Original exception.
        """
        detail = {}
        if service:
            detail["service"] = service
        if status_code:
            detail["status_code"] = status_code
        if cause:
            detail["cause"] = str(cause)
        super().__init__(message, code="EXTERNAL_SERVICE_ERROR", detail=detail)