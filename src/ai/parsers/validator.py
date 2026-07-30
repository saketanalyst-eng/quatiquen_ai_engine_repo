"""Validator for LLM output structure."""

import json
from typing import Any, Dict, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from src.core.exceptions.ai import LLMResponseParseError
from src.core.logging.logger import get_logger

logger = get_logger("quantiquan.ai.parsers.validator")

T = TypeVar("T", bound=BaseModel)


class Validator:
    """Validator for structured LLM outputs."""

    @staticmethod
    def validate_dict(data: Dict[str, Any], required_fields: list[str]) -> bool:
        """Check if dictionary contains required fields.

        Args:
            data: Dictionary to validate.
            required_fields: List of required field names.

        Returns:
            bool: True if all required fields present.

        Raises:
            LLMResponseParseError: If validation fails.
        """
        missing = [f for f in required_fields if f not in data]
        if missing:
            raise LLMResponseParseError(
                f"Missing required fields: {missing}",
                raw_response=str(data)[:500],
            )
        return True

    @staticmethod
    def validate_model(data: Dict[str, Any], model_class: Type[T]) -> T:
        """Validate and parse dictionary into Pydantic model.

        Args:
            data: Dictionary data.
            model_class: Pydantic model class.

        Returns:
            T: Parsed model instance.

        Raises:
            LLMResponseParseError: If validation fails.
        """
        try:
            return model_class(**data)
        except ValidationError as exc:
            raise LLMResponseParseError(
                f"Model validation failed: {exc}",
                raw_response=str(data)[:500],
            ) from exc