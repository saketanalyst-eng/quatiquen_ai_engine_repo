"""Token counter for LLM inputs and outputs."""

import tiktoken

from src.core.logging.logger import get_logger

logger = get_logger("quantiquan.ai.token_counter")


class TokenCounter:
    """Counts tokens for various LLM models."""

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        """Initialize token counter.

        Args:
            model: Model name for encoding (used for estimation).
        """
        self.model = model
        try:
            self.encoder = tiktoken.encoding_for_model(model)
        except Exception:
            # Fallback to cl100k_base
            self.encoder = tiktoken.get_encoding("cl100k_base")

    def count_text(self, text: str) -> int:
        """Count tokens in a text string.

        Args:
            text: Input text.

        Returns:
            int: Number of tokens.
        """
        try:
            return len(self.encoder.encode(text))
        except Exception as exc:
            logger.warning("Token counting failed", error=str(exc))
            # Heuristic: approximately 4 characters per token
            return len(text) // 4

    def count_messages(self, messages: list[dict[str, str]]) -> int:
        """Count tokens in a list of messages.

        Args:
            messages: List of {"role": ..., "content": ...} dicts.

        Returns:
            int: Total token count.
        """
        total = 0
        for msg in messages:
            total += self.count_text(msg.get("content", ""))
        return total