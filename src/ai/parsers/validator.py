"""Validator for LLM output structure and safety."""

import json
import re
from typing import Any, Dict, Type, TypeVar

from pydantic import BaseModel, ValidationError

from src.core.exceptions.ai import LLMResponseParseError
from src.core.logging.logger import get_logger

logger = get_logger("quantiquan.ai.parsers.validator")

T = TypeVar("T", bound=BaseModel)


class Validator:
    """Validator for structured LLM outputs with hallucination detection."""

    # Patterns for hallucination detection
    HALLUCINATION_PATTERNS = [
        # Unsupported dollar amounts without qualifiers
        r"\$\s*\d+[,.]?\d*\s*(million|billion|thousand|M|B|K)?",
        # Specific PCI fine amounts (often hallucinated)
        r"PCI fines? up? to? \$?\d+[,.]?\d*",
        # Specific financial loss amounts
        r"financial losses? (of|up to) \$?\d+[,.]?\d*",
    ]

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

    @staticmethod
    def detect_hallucinations(text: str) -> list[str]:
        """Detect potential hallucinations in text.

        Args:
            text: Text to scan.

        Returns:
            list[str]: List of detected hallucination patterns.
        """
        detected = []
        for pattern in Validator.HALLUCINATION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                detected.append(pattern)
        return detected

    @staticmethod
    def validate_summary(summary: Dict[str, Any]) -> bool:
        """Validate a summary dictionary for hallucinations.

        Args:
            summary: Summary dictionary with fields: business_risk, technical_risk,
                     why_scored, immediate_recommendation, expected_business_impact.

        Returns:
            bool: True if validation passes, False if hallucinations detected.
        """
        # Combine all text fields
        all_text = " ".join(str(v) for v in summary.values())

        # Check for hallucinations
        hallucinations = Validator.detect_hallucinations(all_text)

        if hallucinations:
            logger.warning(
                "Hallucinations detected in summary",
                patterns=hallucinations,
                summary_preview=all_text[:200],
            )
            return False

        # Check for unsupported claims (specific facts without context)
        # This is a basic check; more advanced checks can be added later.

        return True

    @staticmethod
    def safe_summary_fallback() -> Dict[str, str]:
        """Return a safe fallback summary when validation fails.

        Returns:
            Dict[str, str]: Safe fallback summary.
        """
        return {
            "business_risk": "This vulnerability could impact business operations. Please review the finding details for more information.",
            "technical_risk": "Technical analysis is unavailable. Please consult the finding details.",
            "why_scored": "Score is based on asset importance, vulnerability severity, exploitability, business impact, and exposure.",
            "immediate_recommendation": "Review the finding and apply appropriate remediation based on your organization's security policies.",
            "expected_business_impact": "Potential business impact depends on the specific context. Please consult your security team for assessment.",
        }