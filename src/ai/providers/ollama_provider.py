"""Ollama local provider."""

import json
import time
from typing import Any, Optional

import httpx

from src.core.exceptions.ai import LLMProviderError, LLMTimeoutError
from src.core.logging.logger import get_logger

from src.ai.models.llm_response import LLMResponse
from src.ai.providers.base_provider import BaseProvider

logger = get_logger("quantiquan.ai.providers.ollama")


class OllamaProvider(BaseProvider):
    """Ollama local LLM provider."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2",
        timeout_seconds: float = 30.0,
    ) -> None:
        """Initialize Ollama provider.

        Args:
            base_url: Ollama API base URL.
            model: Model name.
            timeout_seconds: Request timeout (longer for local).
        """
        super().__init__(model=model, timeout_seconds=timeout_seconds)
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
        """Generate response from Ollama."""
        start_time = time.perf_counter()
        error = None
        raw_text = ""
        input_tokens = 0
        output_tokens = 0
        success = False

        try:
            client = self._get_client()
            # Ollama uses a different API: /api/generate
            payload = {
                "model": self.model,
                "prompt": f"{system_prompt}\n\n{user_prompt}",
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            }
            response = await client.post("/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
            raw_text = data.get("response", "")
            # Ollama returns token counts in some versions
            input_tokens = data.get("prompt_eval_count", 0)
            output_tokens = data.get("eval_count", 0)
            success = True
            logger.debug("Ollama request succeeded", model=self.model)

        except httpx.TimeoutException as exc:
            error = f"Ollama timeout after {self.timeout_seconds}s"
            logger.error(error, exc_info=True)
            raise LLMTimeoutError(error, timeout_seconds=self.timeout_seconds) from exc
        except httpx.HTTPStatusError as exc:
            error = f"Ollama HTTP error: {exc.response.status_code} - {exc.response.text}"
            logger.error(error, exc_info=True)
            raise LLMProviderError(
                error,
                provider="ollama",
                status_code=exc.response.status_code,
            ) from exc
        except Exception as exc:
            error = str(exc)
            logger.error("Ollama provider error", error=error, exc_info=True)
            raise LLMProviderError(error, provider="ollama") from exc
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000

        return LLMResponse(
            raw_text=raw_text,
            parsed=None,
            provider="ollama",
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
        """Generate JSON response from Ollama."""
        sys_prompt = system_prompt + "\nOutput must be valid JSON."
        return await self.generate(
            system_prompt=sys_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    async def health_check(self) -> bool:
        """Check Ollama API health."""
        try:
            client = self._get_client()
            response = await client.get("/api/tags")
            return response.status_code == 200
        except Exception:
            return False