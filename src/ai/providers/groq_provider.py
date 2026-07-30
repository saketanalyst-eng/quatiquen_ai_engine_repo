"""Groq LLM provider."""

import json
import time
from typing import Any, Dict, Optional

import httpx

from src.core.exceptions.ai import LLMProviderError, LLMTimeoutError
from src.core.logging.logger import get_logger

from src.ai.models.llm_response import LLMResponse
from src.ai.providers.base_provider import BaseProvider

logger = get_logger("quantiquan.ai.providers.groq")


class GroqProvider(BaseProvider):
    """Groq API provider."""

    def __init__(
        self,
        api_key: str,
        model: str = "mixtral-8x7b-32768",
        timeout_seconds: float = 10.0,
        base_url: str = "https://api.groq.com/openai/v1",
    ) -> None:
        """Initialize Groq provider.

        Args:
            api_key: Groq API key.
            model: Model name.
            timeout_seconds: Request timeout.
            base_url: API base URL.
        """
        super().__init__(model=model, timeout_seconds=timeout_seconds)
        self.api_key = api_key
        self.base_url = base_url
        self.client = None

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self.client is None:
            self.client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self.timeout_seconds,
            )
        return self.client

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 512,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate response from Groq."""
        start_time = time.perf_counter()
        error = None
        raw_text = ""
        input_tokens = 0
        output_tokens = 0
        success = False

        try:
            client = self._get_client()
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
                **kwargs,
            }
            response = await client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            raw_text = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            success = True

            logger.debug("Groq request succeeded", model=self.model, tokens=input_tokens + output_tokens)

        except httpx.TimeoutException as exc:
            error = f"Groq timeout after {self.timeout_seconds}s"
            logger.error(error, exc_info=True)
            raise LLMTimeoutError(error, timeout_seconds=self.timeout_seconds) from exc
        except httpx.HTTPStatusError as exc:
            error = f"Groq HTTP error: {exc.response.status_code} - {exc.response.text}"
            logger.error(error, exc_info=True)
            raise LLMProviderError(
                error,
                provider="groq",
                status_code=exc.response.status_code,
            ) from exc
        except Exception as exc:
            error = str(exc)
            logger.error("Groq provider error", error=error, exc_info=True)
            raise LLMProviderError(error, provider="groq") from exc
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000

        return LLMResponse(
            raw_text=raw_text,
            parsed=None,
            provider="groq",
            model=self.model,
            tokens_input=input_tokens,
            tokens_output=output_tokens,
            cost_estimate=0.0,
            duration_ms=duration_ms,
            success=success,
            error=error,
        )

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 512,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate JSON response from Groq."""
        # Ensure system prompt instructs JSON output
        sys_prompt = system_prompt + "\nOutput must be valid JSON."
        return await self.generate(
            system_prompt=sys_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    async def health_check(self) -> bool:
        """Check Groq API health."""
        try:
            # Simple models list query
            client = self._get_client()
            response = await client.get("/models")
            return response.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None