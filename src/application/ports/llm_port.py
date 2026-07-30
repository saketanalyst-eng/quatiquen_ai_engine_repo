"""LLM port for generating AI summaries and explanations."""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from src.domain.entities import Finding
from src.domain.value_objects import BusinessContext, Drivers, RiskScore, ThreatContext


class LLMPort(ABC):
    """Abstract interface for LLM interaction."""

    @abstractmethod
    async def generate_summary(
        self,
        finding: Finding,
        risk_score: RiskScore,
        drivers: Drivers,
        tier: str,
        business_context: BusinessContext,
        threat_context: Optional[ThreatContext],
    ) -> Optional[str]:
        """Generate a business-friendly summary for the finding.

        Args:
            finding: The finding entity.
            risk_score: Calculated risk score.
            drivers: Score drivers.
            tier: Priority tier.
            business_context: Business context.
            threat_context: Threat context (optional).

        Returns:
            Optional[str]: Generated summary, or None if generation fails.
        """
        pass

    @abstractmethod
    async def generate_recommendation_explanation(
        self,
        finding: Finding,
        recommendation_text: str,
        business_context: BusinessContext,
    ) -> Optional[str]:
        """Generate explanation for a recommendation.

        Args:
            finding: The finding entity.
            recommendation_text: Technical recommendation.
            business_context: Business context.

        Returns:
            Optional[str]: Generated explanation, or None if fails.
        """
        pass