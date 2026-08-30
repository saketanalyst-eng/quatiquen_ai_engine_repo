"""Decision aggregate representing the final risk decision for a finding."""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from src.core.constants.enums import PriorityTier
from src.core.exceptions.domain import ValidationError
from src.domain.value_objects import Confidence, Drivers, RiskScore


@dataclass(frozen=True)
class Decision:
    """Decision aggregate representing the final risk decision.

    This entity combines the risk score, confidence, drivers, recommendation,
    and AI summary into a single immutable aggregate.

    Attributes:
        finding_id: The finding this decision applies to.
        tenant_id: Tenant identifier.
        risk_score: Final risk score (BIS).
        tier: Priority tier.
        confidence: Confidence score.
        drivers: Scoring drivers breakdown.
        recommendation_id: Optional recommendation ID.
        summary: Optional AI-generated business summary.
        computed_at: Timestamp when decision was computed.
        version: Version of the scoring formula used.
        job_id: Queue job execution identity (for idempotency).
        trace_id: End-to-end request/processing trace.
        knowledge_version: Version of the knowledge/rules used.
    """

    finding_id: UUID
    tenant_id: UUID
    risk_score: RiskScore
    tier: PriorityTier
    confidence: Confidence
    drivers: Drivers
    recommendation_id: Optional[UUID]
    summary: Optional[str]
    computed_at: int
    version: str
    
    # NEW PRODUCTION HARDENING FIELDS (P0 & P1)
    job_id: UUID
    trace_id: UUID
    knowledge_version: str

    def __post_init__(self) -> None:
        """Validate decision invariants."""
        if self.risk_score.final_bis < 0 or self.risk_score.final_bis > 100:
            raise ValidationError(
                f"Final BIS must be between 0 and 100, got {self.risk_score.final_bis}",
                field="risk_score",
            )
        if self.confidence.value < 0 or self.confidence.value > 1:
            raise ValidationError(
                f"Confidence must be between 0 and 1, got {self.confidence.value}",
                field="confidence",
            )

    @property
    def bis(self) -> float:
        """Get the final BIS value."""
        return self.risk_score.final_bis

    @property
    def raw_bis(self) -> float:
        """Get the raw BIS value (before confidence adjustment)."""
        return self.risk_score.raw_bis

    @property
    def is_critical(self) -> bool:
        """Check if the decision is critical."""
        return self.tier == PriorityTier.CRITICAL

    @property
    def is_high_or_critical(self) -> bool:
        """Check if the decision is high or critical."""
        return self.tier in (PriorityTier.HIGH, PriorityTier.CRITICAL)

    @property
    def has_recommendation(self) -> bool:
        """Check if a recommendation is attached."""
        return self.recommendation_id is not None

    @property
    def has_summary(self) -> bool:
        """Check if an AI summary is available."""
        return self.summary is not None and self.summary.strip() != ""

    @property
    def confidence_multiplier(self) -> float:
        """Get the confidence multiplier (0.7 to 1.0)."""
        return self.confidence.multiplier

    @classmethod
    def create(
        cls,
        finding_id: UUID,
        tenant_id: UUID,
        risk_score: RiskScore,
        tier: PriorityTier,
        confidence: Confidence,
        drivers: Drivers,
        job_id: UUID,  # NEW required parameter
        trace_id: UUID,  # NEW required parameter
        recommendation_id: Optional[UUID] = None,
        summary: Optional[str] = None,
        version: str = "1.0.0",
        knowledge_version: str = "1.0.0",  # NEW parameter with default
    ) -> "Decision":
        """Factory method to create a decision.

        Args:
            finding_id: Finding identifier.
            tenant_id: Tenant identifier.
            risk_score: Final risk score.
            tier: Priority tier.
            confidence: Confidence score.
            drivers: Scoring drivers.
            job_id: Queue job identity (for idempotency).
            trace_id: End-to-end trace identity.
            recommendation_id: Optional recommendation ID.
            summary: Optional AI summary.
            version: Scoring version.
            knowledge_version: Knowledge/rules version used.

        Returns:
            Decision: New decision instance.
        """
        computed_at = int(__import__("time").time())
        return cls(
            finding_id=finding_id,
            tenant_id=tenant_id,
            risk_score=risk_score,
            tier=tier,
            confidence=confidence,
            drivers=drivers,
            recommendation_id=recommendation_id,
            summary=summary,
            computed_at=computed_at,
            version=version,
            job_id=job_id,
            trace_id=trace_id,
            knowledge_version=knowledge_version,
        )