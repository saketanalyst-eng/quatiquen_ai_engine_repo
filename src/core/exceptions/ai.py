
### File: src/core/exceptions/ai.py

"""AI/LLM layer exceptions.

These exceptions represent failures in the LLM provider, prompt parsing,
or AI orchestration layer. They are designed to be non-blocking for
the main scoring pipeline.
"""

from src.core.exceptions.infrastructure import InfrastructureError


class AIError(InfrastructureError):
    """Base exception for AI/LLM layer errors.

    Raised when LLM operations fail. These errors should not block
    the main scoring flow.
    """

    def __init__(self, message: str, code: str = "AI_ERROR", detail: dict = None) -> None:
        """Initialize AI error.

        Args:
            message: Human-readable error message.
            code: Error code for categorization.
            detail: Additional error context data.
        """
        super().__init__(message, code=code, detail=detail)


class LLMTimeoutError(AIError):
    """Raised when an LLM request times out."""

    def __init__(self, message: str, timeout_seconds: float = None) -> None:
        """Initialize LLM timeout error.

        Args:
            message: Error description.
            timeout_seconds: Timeout value that was exceeded.
        """
        detail = {"timeout_seconds": timeout_seconds} if timeout_seconds else {}
        super().__init__(message, code="LLM_TIMEOUT", detail=detail)


class LLMProviderError(AIError):
    """Raised when the LLM provider returns an error."""

    def __init__(self, message: str, provider: str = None, status_code: int = None) -> None:
        """Initialize LLM provider error.

        Args:
            message: Error description.
            provider: Name of the provider (groq, openai, etc.).
            status_code: HTTP status code from provider.
        """
        detail = {}
        if provider:
            detail["provider"] = provider
        if status_code:
            detail["status_code"] = status_code
        super().__init__(message, code="LLM_PROVIDER_ERROR", detail=detail)


class LLMResponseParseError(AIError):
    """Raised when the LLM response cannot be parsed."""

    def __init__(self, message: str, raw_response: str = None) -> None:
        """Initialize LLM response parse error.

        Args:
            message: Error description.
            raw_response: The raw response that failed to parse.
        """
        detail = {"raw_response": raw_response[:500]} if raw_response else {}
        super().__init__(message, code="LLM_PARSE_ERROR", detail=detail)