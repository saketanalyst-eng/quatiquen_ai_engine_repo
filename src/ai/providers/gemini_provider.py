"""Google Gemini provider."""

import json
import time
from typing import Any, Optional

import httpx

from src.core.exceptions.ai import LLMProviderError, LLMTimeoutError
from src.core.logging.logger import get_logger

from src.ai.models.llm_response import LLMResponse
from src.ai.providers.base_provider import BaseProvider

logger = get_logger("quantiquan.ai.providers.gemini")


class GeminiProvider(BaseProvider):
    """Google Gemini API provider."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash-exp",
        timeout_seconds: float = 10.0,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
    ) -> None:
        """Initialize Gemini provider.

        Args:
            api_key: Gemini API key.
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
        """Generate response from Gemini."""
        start_time = time.perf_counter()
        error = None
        raw_text = ""
        input_tokens = 0
        output_tokens = 0
        success = False

        try:
            client = self._get_client()
            # Gemini API: combine system and user into a single prompt
            combined_prompt = f"{system_prompt}\n\n{user_prompt}"
            payload = {
                "contents": [{"parts": [{"text": combined_prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                },
            }
            url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            # Gemini doesn't return token counts in this API; we estimate.
            success = True
            logger.debug("Gemini request succeeded", model=self.model)

        except httpx.TimeoutException as exc:
            error = f"Gemini timeout after {self.timeout_seconds}s"
            logger.error(error, exc_info=True)
            raise LLMTimeoutError(error, timeout_seconds=self.timeout_seconds) from exc
        except httpx.HTTPStatusError as exc:
            error = f"Gemini HTTP error: {exc.response.status_code} - {exc.response.text}"
            logger.error(error, exc_info=True)
            raise LLMProviderError(
                error,
                provider="gemini",
                status_code=exc.response.status_code,
            ) from exc
        except Exception as exc:
            error = str(exc)
            logger.error("Gemini provider error", error=error, exc_info=True)
            raise LLMProviderError(error, provider="gemini") from exc
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000

        return LLMResponse(
            raw_text=raw_text,
            parsed=None,
            provider="gemini",
            model=self.model,
            tokens_input=0,
            tokens_output=0,
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
        """Generate JSON response from Gemini."""
        sys_prompt = system_prompt + "\nOutput must be valid JSON."
        return await self.generate(
            system_prompt=sys_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    async def health_check(self) -> bool:
        """Check Gemini API health."""
        try:
            client = self._get_client()
            url = f"{self.base_url}/models?key={self.api_key}"
            response = await client.get(url)
            return response.status_code == 200
        except Exception:
            return False