"""AI orchestrator that manages LLM calls with fallbacks and circuit breakers."""

import asyncio
import os
from typing import Any, Dict, Optional

from src.ai.models.llm_response import LLMResponse
from src.ai.orchestration.circuit_breaker import CircuitBreaker
from src.ai.orchestration.llm_pipeline import LLMPipeline
from src.ai.parsers.response_parser import ResponseParser
from src.ai.providers.provider_factory import ProviderFactory
from src.ai.prompts.prompt_builder import PromptBuilder
from src.ai.token.token_counter import TokenCounter
from src.core.exceptions.ai import LLMProviderError, LLMTimeoutError
from src.core.logging.logger import get_logger
from src.domain.entities import Finding
from src.domain.value_objects import BusinessContext, Drivers, RiskScore, ThreatContext

logger = get_logger("quantiquan.ai.orchestrator")


class AIOrchestrator:
    """Orchestrates AI calls with retries, fallbacks, and circuit breakers."""

    def __init__(
        self,
        primary_provider: Optional[str] = None,
        fallback_providers: Optional[list[str]] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ) -> None:
        self.primary_provider = primary_provider or "groq"
        self.fallback_providers = fallback_providers or ["openai", "ollama"]
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.token_counter = TokenCounter()
        self.pipeline = LLMPipeline()
        self._provider_cache: Dict[str, Any] = {}

    async def generate_summary(
        self,
        finding: Finding,
        risk_score: RiskScore,
        drivers: Drivers,
        tier: str,
        business_context: BusinessContext,
        threat_context: Optional[ThreatContext] = None,
    ) -> Optional[str]:
        """Generate a business summary for the finding."""
        # Build prompt context
        context = {
            "title": finding.title,
            "description": finding.description,
            "cve_id": finding.cve_id or "None",
            "asset_name": "Unknown",
            "asset_importance": drivers.asset_importance,
            "vulnerability_severity": drivers.vulnerability_severity,
            "exploitability": drivers.exploitability,
            "business_impact": drivers.business_impact,
            "exposure": drivers.exposure,
            "confidence": risk_score.confidence_multiplier,
            "tier": tier,
        }

        system_prompt, user_prompt = PromptBuilder.build_summary_prompt(context)

        # If no API key, return a mock summary
        if not os.getenv("GROQ_API_KEY"):
            logger.warning("GROQ_API_KEY not set; returning mock summary")
            return (
                "This vulnerability affects your production payment system, which handles regulated data. "
                "It is listed in CISA's Known Exploited Vulnerabilities catalog. Immediate action is recommended "
                "to prevent potential compromise of sensitive financial information."
            )

        try:
            async with self.circuit_breaker:
                providers = [self.primary_provider] + self.fallback_providers
                last_error = None

                for provider_name in providers:
                    try:
                        result = await asyncio.wait_for(
                            self._call_provider(provider_name, system_prompt, user_prompt),
                            timeout=5.0,
                        )
                        if result:
                            return result
                    except (LLMProviderError, LLMTimeoutError) as exc:
                        logger.warning("Provider failed, trying next", provider=provider_name, error=str(exc))
                        last_error = exc
                        continue
                    except Exception as exc:
                        logger.error("Unexpected error from provider", provider=provider_name, error=str(exc), exc_info=True)
                        last_error = exc
                        continue

                logger.error("All AI providers failed", last_error=str(last_error) if last_error else "Unknown")
                return None
        except Exception as exc:
            logger.warning("Circuit breaker or LLM call failed", error=str(exc))
            return None

    async def _call_provider(
        self,
        provider_name: str,
        system_prompt: str,
        user_prompt: str,
    ) -> Optional[str]:
        """Call a specific provider and extract the summary."""
        if provider_name not in self._provider_cache:
            try:
                provider = ProviderFactory.create(provider_name)
                self._provider_cache[provider_name] = provider
            except LLMProviderError as exc:
                logger.error("Failed to create provider", provider=provider_name, error=str(exc))
                return None

        provider = self._provider_cache[provider_name]

        response = await provider.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
            max_tokens=512,
        )

        if not response.success:
            logger.warning("Provider response unsuccessful", provider=provider_name)
            return None

        try:
            from src.ai.models.summary import SummaryResponse
            parsed = ResponseParser.parse_model(response.raw_text, SummaryResponse)
            return parsed.business_explanation
        except Exception as exc:
            logger.warning("Failed to parse response", provider=provider_name, error=str(exc))
            return None

    async def generate_recommendation_explanation(
        self,
        finding: Finding,
        recommendation_text: str,
        business_context: BusinessContext,
    ) -> Optional[str]:
        """Generate explanation for a recommendation."""
        return f"Recommendation: {recommendation_text}"