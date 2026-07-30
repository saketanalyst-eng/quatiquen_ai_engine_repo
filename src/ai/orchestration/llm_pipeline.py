"""LLM pipeline that chains multiple steps."""

from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel

from src.ai.models.llm_response import LLMResponse
from src.ai.parsers.response_parser import ResponseParser
from src.ai.providers.base_provider import BaseProvider
from src.core.logging.logger import get_logger

logger = get_logger("quantiquan.ai.llm_pipeline")

T = TypeVar("T", bound=BaseModel)


class LLMPipeline:
    """Pipeline that runs a sequence of operations on an LLM response."""

    def __init__(self) -> None:
        """Initialize pipeline."""
        self.steps: List[Callable] = []

    def add_step(self, step: Callable) -> "LLMPipeline":
        """Add a step to the pipeline.

        Args:
            step: Function that takes (provider, prompt) and returns LLMResponse.

        Returns:
            LLMPipeline: Self for chaining.
        """
        self.steps.append(step)
        return self

    async def run(
        self,
        provider: BaseProvider,
        system_prompt: str,
        user_prompt: str,
        model_class: Type[T],
    ) -> Optional[T]:
        """Run the pipeline.

        Args:
            provider: LLM provider.
            system_prompt: System prompt.
            user_prompt: User prompt.
            model_class: Model class for parsing.

        Returns:
            Optional[T]: Parsed output or None.
        """
        if not self.steps:
            # Default: generate, parse
            response = await provider.generate_json(system_prompt, user_prompt)
            if not response.success:
                return None
            try:
                return ResponseParser.parse_model(response.raw_text, model_class)
            except Exception:
                return None

        # Run custom steps
        current = (provider, system_prompt, user_prompt)
        for step in self.steps:
            result = step(*current)
            if isinstance(result, tuple):
                current = result
            elif isinstance(result, LLMResponse):
                if not result.success:
                    return None
                try:
                    return ResponseParser.parse_model(result.raw_text, model_class)
                except Exception:
                    return None
            elif result is None:
                return None

        return None