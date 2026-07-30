"""Response parser that extracts structured data from LLM responses."""

import json
from typing import Any, Dict, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from src.core.exceptions.ai import LLMResponseParseError
from src.core.logging.logger import get_logger

logger = get_logger("quantiquan.ai.parsers.response_parser")

T = TypeVar("T", bound=BaseModel)


class ResponseParser:
    """Parser that extracts structured data from LLM responses."""

    @staticmethod
    def extract_json(raw_text: str) -> Dict[str, Any]:
        """Extract JSON from raw text, handling markdown code blocks.

        Args:
            raw_text: Raw LLM response text.

        Returns:
            Dict[str, Any]: Parsed JSON.

        Raises:
            LLMResponseParseError: If JSON extraction fails.
        """
        # Remove markdown code blocks
        text = raw_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            # Try to find JSON within the text
            import re
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            raise LLMResponseParseError(
                f"Failed to parse JSON: {exc}",
                raw_response=raw_text[:500],
            ) from exc

    @staticmethod
    def parse_model(
        raw_text: str,
        model_class: Type[T],
    ) -> T:
        """Parse raw LLM response into a Pydantic model.

        Args:
            raw_text: Raw LLM response.
            model_class: Pydantic model class.

        Returns:
            T: Parsed model instance.

        Raises:
            LLMResponseParseError: If parsing or validation fails.
        """
        try:
            data = ResponseParser.extract_json(raw_text)
            return model_class(**data)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise LLMResponseParseError(
                f"Failed to parse model: {exc}",
                raw_response=raw_text[:500],
            ) from exc