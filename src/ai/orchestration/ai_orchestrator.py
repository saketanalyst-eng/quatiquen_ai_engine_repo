"""AI orchestrator that manages LLM calls with fallbacks and circuit breakers."""

import asyncio
from typing import Any, Dict, Optional

from src.ai.models.llm_response import LLMResponse
from src.ai.orchestration.circuit_breaker import CircuitBreaker
from src.ai.orchestration.llm_pipeline import LLMPipeline
from src.ai.parsers.response_parser import ResponseParser
from src.ai.providers.provider_factory import ProviderFactory
from src.ai.prompts.prompt_builder import PromptBuilder
from src.ai.token.token_counter import TokenCounter
from src.core.config.settings import get_settings
from src.core.exceptions.ai import LLMProviderError, LLMTimeoutError
from src.core.logging.logger import get_logger
from src.domain.entities import Finding
from src.domain.value_objects import BusinessContext, Drivers, RiskScore, ThreatContext
from src.interfaces.schemas.response import StructuredSummary

logger = get_logger("quantiquan.ai.orchestrator")


class AIOrchestrator:
    """Orchestrates AI calls with retries, fallbacks, and circuit breakers."""

    def __init__(
        self,
        primary_provider: Optional[str] = None,
        fallback_providers: Optional[list[str]] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ) -> None:
        self.settings = get_settings()
        self.primary_provider = primary_provider or "groq"
        self.fallback_providers = fallback_providers or ["openai", "ollama"]
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.token_counter = TokenCounter()
        self.pipeline = LLMPipeline()
        self._provider_cache: Dict[str, Any] = {}
        logger.info(f"Groq API Key loaded: {bool(self.settings.groq_api_key.get_secret_value())}")

    async def generate_summary(
        self,
        finding: Finding,
        risk_score: RiskScore,
        drivers: Drivers,
        tier: str,
        business_context: BusinessContext,
        threat_context: Optional[ThreatContext] = None,
    ) -> Optional[StructuredSummary]:
        """Generate a structured business summary for the finding.

        Returns:
            StructuredSummary: Object with business_risk, technical_risk,
            why_scored, immediate_recommendation, expected_business_impact.
        """
        # Build rich context for the prompt
        context = {
            "title": finding.title,
            "description": finding.description,
            "cve_id": finding.cve_id or "None",
            "asset_name": "Unknown",
            "asset_type": getattr(business_context, "asset_type", "Unknown"),
            "asset_importance": drivers.asset_importance,
            "data_classification": business_context.data_classification.value if business_context else "Unknown",
            "compliance_scopes": ", ".join([c.value for c in business_context.compliance_scopes]) if business_context else "None",
            "exposure": business_context.exposure.value if business_context else "Internal",
            "is_production": business_context.is_production if business_context else False,
            "revenue_impact": business_context.revenue_impact if business_context else "Unknown",
            "downstream_dependents": business_context.downstream_dependents if business_context else 0,
            "vulnerability_severity": drivers.vulnerability_severity,
            "exploitability": drivers.exploitability,
            "business_impact": drivers.business_impact,
            "confidence": risk_score.confidence_multiplier,
            "tier": tier,
        }

        system_prompt, user_prompt = PromptBuilder.build_summary_prompt(context)

        # Use settings.groq_api_key to check if key is set
        if not self.settings.groq_api_key.get_secret_value():
            logger.warning("GROQ_API_KEY not set; returning mock structured summary")
            return StructuredSummary(
                business_risk=f"Exploitation of this {finding.title} could impact your {business_context.exposure.value} environment.",
                technical_risk=f"This is a {finding.title} affecting {finding.asset_id}. Attackers could exploit it to compromise the system.",
                why_scored=f"Scored as {tier} due to asset importance ({drivers.asset_importance}) and exploitability ({drivers.exploitability}).",
                immediate_recommendation="Apply the latest vendor patch and verify the fix.",
                expected_business_impact="Potential service disruption, data breach, or compliance fines.",
            )

        try:
            async with self.circuit_breaker:
                providers = [self.primary_provider] + self.fallback_providers
                last_error = None

                for provider_name in providers:
                    try:
                        result = await asyncio.wait_for(
                            self._call_provider(provider_name, system_prompt, user_prompt),
                            timeout=10.0,  # increased from 5.0
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
    ) -> Optional[StructuredSummary]:
        """Call a specific provider and parse the response into StructuredSummary."""
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
            temperature=0.4,
            max_tokens=1024,
        )

        if not response.success:
            logger.warning("Provider response unsuccessful", provider=provider_name)
            return None

        try:
            parsed = ResponseParser.parse_model(response.raw_text, StructuredSummary)
            return parsed
        except Exception as exc:
            logger.warning("Failed to parse structured summary", provider=provider_name, error=str(exc))
            return None

    async def generate_recommendation_explanation(
        self,
        finding: Finding,
        recommendation_text: str,
        business_context: BusinessContext,
    ) -> Optional[str]:
        """Generate explanation for a recommendation."""
        return f"Recommendation: {recommendation_text}"