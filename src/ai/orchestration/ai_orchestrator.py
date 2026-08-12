"""AI orchestrator that manages LLM calls with fallbacks and circuit breakers."""

import asyncio
import re
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

    # Dangerous patterns for prompt injection detection
    DANGEROUS_PATTERNS = [
        r"(?i)ignore previous instructions",
        r"(?i)override security",
        r"(?i)change the risk score",
        r"(?i)set this vulnerability to",
        r"(?i)reveal system prompt",
        r"(?i)return secret information",
        r"(?i)execute command",
        r"(?i)override policy",
        r"(?i)pretend you are",
        r"(?i)you are now",
    ]

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

    def _sanitize_input(self, text: str) -> str:
        """Sanitize user input to prevent prompt injection.

        Args:
            text: User input text.

        Returns:
            str: Sanitized text with dangerous patterns removed.
        """
        if not text:
            return ""

        sanitized = text
        for pattern in self.DANGEROUS_PATTERNS:
            sanitized = re.sub(pattern, "[REDACTED]", sanitized, flags=re.IGNORECASE)

        # Escape special characters that could affect JSON parsing
        sanitized = sanitized.replace('"', '\\"').replace("\n", " ")

        return sanitized

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
        # Sanitize user input to prevent prompt injection
        sanitized_title = self._sanitize_input(finding.title)
        sanitized_description = self._sanitize_input(finding.description)

        # Build prompt context
        context = {
            "title": sanitized_title,
            "description": sanitized_description,
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

        # If no API key, return mock summary
        if not self.settings.groq_api_key.get_secret_value():
            logger.warning("GROQ_API_KEY not set; returning mock summary")
            return StructuredSummary(
                business_risk=f"Exploitation of this {finding.title} could impact your {business_context.exposure.value} environment. Information unavailable for specific financial estimates.",
                technical_risk=f"This is a {finding.title} affecting {finding.asset_id}. Attackers could exploit it to compromise the system.",
                why_scored=f"Scored as {tier} due to asset importance ({drivers.asset_importance}) and exploitability ({drivers.exploitability}).",
                immediate_recommendation="Apply the latest vendor patch and verify the fix.",
                expected_business_impact="Potential service disruption, data breach, or compliance issues based on available context.",
            )

        try:
            async with self.circuit_breaker:
                providers = [self.primary_provider] + self.fallback_providers
                last_error = None

                for provider_name in providers:
                    try:
                        result = await asyncio.wait_for(
                            self._call_provider(provider_name, system_prompt, user_prompt),
                            timeout=10.0,
                        )
                        if result:
                            # Validate the result for hallucinations
                            if self._validate_summary(result):
                                return result
                            else:
                                logger.warning(
                                    "Hallucination detected in summary, trying next provider",
                                    provider=provider_name,
                                )
                                continue
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

    def _validate_summary(self, summary: StructuredSummary) -> bool:
        """Validate the summary for hallucinations and unsupported claims.

        Args:
            summary: StructuredSummary object to validate.

        Returns:
            bool: True if validation passes, False otherwise.
        """
        # Check for unsupported dollar amounts (hallucinated fines/losses)
        text = f"{summary.business_risk} {summary.expected_business_impact}"
        dollar_matches = re.findall(r"\$\s*\d+[,.]?\d*\s*(million|billion|thousand|M|B|K)?", text, re.IGNORECASE)

        # If there are dollar amounts, check if they look generic
        # We'll be strict: any dollar amount without a qualifier like "potential" or "estimated" is flagged
        for match in dollar_matches:
            # Check if the phrase contains "potential", "estimated", or "up to"
            if not re.search(r"(potential|estimated|approximately|around|about|up to)", text, re.IGNORECASE):
                logger.warning("Hallucination detected: unsupported dollar amount without qualifier", text=text[:200])
                return False

        # Check for specific CVE details not in the input (we can't verify, so we trust the LLM)
        # This is a basic check; more advanced checks can be added later.

        return True

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