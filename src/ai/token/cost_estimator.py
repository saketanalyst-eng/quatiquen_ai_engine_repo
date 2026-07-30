"""Cost estimator for LLM API usage."""

from typing import Optional

from src.core.logging.logger import get_logger

logger = get_logger("quantiquan.ai.cost_estimator")


class CostEstimator:
    """Estimates cost for LLM calls based on tokens.

    Pricing per 1K tokens (approximate, may change):
        Groq: $0.00015 / 1K input, $0.0003 / 1K output (Mixtral)
        OpenAI GPT-4o-mini: $0.00015 / 1K input, $0.0006 / 1K output
        Gemini: free tier or variable
        Ollama: free (local)
    """

    PRICING = {
        "groq": {"input": 0.00015, "output": 0.0003},
        "openai": {"input": 0.00015, "output": 0.0006},
        "gemini": {"input": 0.0, "output": 0.0},
        "ollama": {"input": 0.0, "output": 0.0},
    }

    @classmethod
    def estimate_cost(
        cls,
        provider: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Estimate cost in USD.

        Args:
            provider: Provider name (groq, openai, gemini, ollama).
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.

        Returns:
            float: Estimated cost in USD.
        """
        pricing = cls.PRICING.get(provider.lower(), {"input": 0.0, "output": 0.0})
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        return input_cost + output_cost