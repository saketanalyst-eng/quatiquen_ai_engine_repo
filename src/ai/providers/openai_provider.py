"""OpenAI provider."""

import json
import time
from typing import Any, Optional

import openai

from src.core.exceptions.ai import LLMProviderError, LLMTimeoutError
from src.core.logging.logger import get_logger

from src.ai.models.llm_response import LLMResponse
from src.ai.providers.base_provider import BaseProvider

logger = get_logger("quantiquan.ai.providers.openai")


class OpenAIProvider(BaseProvider):
    """OpenAI API provider."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        timeout_seconds: float = 10.0,
        base_url: Optional[str] = None,
    ) -> None:
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key.
            model: Model name.
            timeout_seconds: Request timeout.
            base_url: Optional custom base URL.
        """
        super().__init__(model=model, timeout_seconds=timeout_seconds)
        self.api_key = api_key
        self.base_url = base_url
        self.client = None

    def _get_client(self) -> openai.AsyncOpenAI:
        """Get or create OpenAI client."""
        if self.client is None:
            kwargs = {
                "api_key": self.api_key,
                "timeout": self.timeout_seconds,
            }
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self.client = openai.AsyncOpenAI(**kwargs)
        return self.client

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 512,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate response from OpenAI."""
        start_time = time.perf_counter()
        error = None
        raw_text = ""
        input_tokens = 0
        output_tokens = 0
        success = False

        try:
            client = self._get_client()
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            raw_text = response.choices[0].message.content
            if response.usage:
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
            success = True
            logger.debug("OpenAI request succeeded", model=self.model)

        except openai.APITimeoutError as exc:
            error = f"OpenAI timeout after {self.timeout_seconds}s"
            logger.error(error, exc_info=True)
            raise LLMTimeoutError(error, timeout_seconds=self.timeout_seconds) from exc
        except openai.APIStatusError as exc:
            error = f"OpenAI HTTP error: {exc.status_code} - {exc.response.text}"
            logger.error(error, exc_info=True)
            raise LLMProviderError(
                error,
                provider="openai",
                status_code=exc.status_code,
            ) from exc
        except Exception as exc:
            error = str(exc)
            logger.error("OpenAI provider error", error=error, exc_info=True)
            raise LLMProviderError(error, provider="openai") from exc
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000

        cost_estimate = (input_tokens * 0.000005) + (output_tokens * 0.000015)  # approximate
        return LLMResponse(
            raw_text=raw_text,
            parsed=None,
            provider="openai",
            model=self.model,
            tokens_input=input_tokens,
            tokens_output=output_tokens,
            cost_estimate=cost_estimate,
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
        """Generate JSON response from OpenAI."""
        sys_prompt = system_prompt + "\nOutput must be valid JSON."
        return await self.generate(
            system_prompt=sys_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    async def health_check(self) -> bool:
        """Check OpenAI API health."""
        try:
            client = self._get_client()
            await client.models.list()
            return True
        except Exception:
            return False