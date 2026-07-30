"""Generic wrapper for LLM responses."""

from dataclasses import dataclass
from typing import Any, Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class LLMResponse(Generic[T]):
    """Wrapper for LLM responses with metadata.

    Attributes:
        raw_text: Raw text from the LLM.
        parsed: Parsed structured object (if any).
        provider: Provider used.
        model: Model used.
        tokens_input: Number of input tokens.
        tokens_output: Number of output tokens.
        cost_estimate: Estimated cost in USD.
        duration_ms: Request duration in milliseconds.
        success: Whether the request succeeded.
        error: Error message if failed.
    """

    raw_text: str
    parsed: Optional[T]
    provider: str
    model: str
    tokens_input: int
    tokens_output: int
    cost_estimate: float
    duration_ms: float
    success: bool
    error: Optional[str] = None