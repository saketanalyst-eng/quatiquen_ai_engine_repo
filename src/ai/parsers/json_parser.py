"""JSON parser with robust extraction."""

import json
from typing import Any, Dict, Optional

from src.core.logging.logger import get_logger

logger = get_logger("quantiquan.ai.parsers.json_parser")


class JSONParser:
    """Utility for parsing JSON from LLM responses."""

    @staticmethod
    def parse(raw_text: str) -> Dict[str, Any]:
        """Parse JSON from raw text.

        Args:
            raw_text: Raw text containing JSON.

        Returns:
            Dict[str, Any]: Parsed JSON.

        Raises:
            json.JSONDecodeError: If parsing fails.
        """
        # Attempt to clean the text
        text = raw_text.strip()
        # Remove markdown code fences
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        return json.loads(text)