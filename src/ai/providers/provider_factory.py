"""Factory for creating LLM providers based on configuration."""

from typing import Optional

from src.core.config.settings import get_settings
from src.core.exceptions.ai import LLMProviderError
from src.core.logging.logger import get_logger

from src.ai.providers.base_provider import BaseProvider
from src.ai.providers.gemini_provider import GeminiProvider
from src.ai.providers.groq_provider import GroqProvider
from src.ai.providers.ollama_provider import OllamaProvider
from src.ai.providers.openai_provider import OpenAIProvider

logger = get_logger("quantiquan.ai.provider_factory")


class ProviderFactory:
    """Factory for creating LLM providers.

    Supported providers: groq, openai, gemini, ollama.
    """

    @staticmethod
    def create(provider_name: str, model: Optional[str] = None) -> BaseProvider:
        """Create a provider instance.

        Args:
            provider_name: Name of the provider (groq, openai, gemini, ollama).
            model: Optional model override; uses default if not provided.

        Returns:
            BaseProvider: Provider instance.

        Raises:
            LLMProviderError: If provider is not supported or misconfigured.
        """
        settings = get_settings()
        provider_name = provider_name.lower()

        logger.info("Creating provider", provider=provider_name, model=model)

        if provider_name == "groq":
            return GroqProvider(
                api_key=settings.groq_api_key.get_secret_value(),
                model=model or settings.groq_model,
                timeout_seconds=settings.groq_timeout_seconds,
            )
        elif provider_name == "openai":
            # OpenAI config could be added to settings; for now use environment.
            api_key = settings.groq_api_key.get_secret_value()  # placeholder; should be separate
            model = model or "gpt-4o-mini"
            return OpenAIProvider(
                api_key=api_key,
                model=model,
                timeout_seconds=settings.groq_timeout_seconds,
            )
        elif provider_name == "gemini":
            # Gemini config should be separate
            api_key = settings.groq_api_key.get_secret_value()  # placeholder
            model = model or "gemini-2.0-flash-exp"
            return GeminiProvider(
                api_key=api_key,
                model=model,
                timeout_seconds=settings.groq_timeout_seconds,
            )
        elif provider_name == "ollama":
            return OllamaProvider(
                base_url="http://localhost:11434",
                model=model or "llama3.2",
                timeout_seconds=settings.groq_timeout_seconds,
            )
        else:
            raise LLMProviderError(
                f"Unsupported provider: {provider_name}",
                provider=provider_name,
            )

    @staticmethod
    def get_default_provider() -> BaseProvider:
        """Get the default provider from settings.

        Returns:
            BaseProvider: Default provider.
        """
        # Use GROQ as default V1 provider
        return ProviderFactory.create("groq")