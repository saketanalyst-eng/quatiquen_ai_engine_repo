"""Base abstraction for LLM providers."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from src.ai.models.llm_response import LLMResponse


class BaseProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, model: str, timeout_seconds: float = 10.0) -> None:
        """Initialize provider.

        Args:
            model: Model name to use.
            timeout_seconds: Request timeout.
        """
        self.model = model
        self.timeout_seconds = timeout_seconds

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 512,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a response from the LLM.

        Args:
            system_prompt: System prompt.
            user_prompt: User prompt.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional provider-specific parameters.

        Returns:
            LLMResponse: Response wrapper with metadata.
        """
        pass

    @abstractmethod
    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 512,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a JSON response from the LLM.

        Args:
            system_prompt: System prompt.
            user_prompt: User prompt.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional provider-specific parameters.

        Returns:
            LLMResponse: Response wrapper with metadata.
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is healthy.

        Returns:
            bool: True if healthy.
        """
        pass