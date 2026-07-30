"""Risk score value object representing Business Impact Score (BIS)."""

from dataclasses import dataclass
from typing import Optional

from src.core.constants.thresholds import TIER_CRITICAL_LOW, TIER_HIGH_LOW, TIER_MEDIUM_LOW
from src.core.exceptions.domain import InvalidValueObjectError


@dataclass(frozen=True)
class RiskScore:
    """Risk score value object containing raw and final BIS.

    Attributes:
        raw_bis: Raw BIS before confidence adjustment (0-100).
        final_bis: Final BIS after confidence adjustment (0-100).
        confidence_multiplier: The multiplier applied (0.7-1.0).
    """

    raw_bis: float
    final_bis: float
    confidence_multiplier: float

    def __post_init__(self) -> None:
        """Validate risk score invariants."""
        if not 0 <= self.raw_bis <= 100:
            raise InvalidValueObjectError(
                f"Raw BIS must be between 0 and 100, got {self.raw_bis}",
                value_object="RiskScore",
            )
        if not 0 <= self.final_bis <= 100:
            raise InvalidValueObjectError(
                f"Final BIS must be between 0 and 100, got {self.final_bis}",
                value_object="RiskScore",
            )
        if not 0.7 <= self.confidence_multiplier <= 1.0:
            raise InvalidValueObjectError(
                f"Confidence multiplier must be between 0.7 and 1.0, got {self.confidence_multiplier}",
                value_object="RiskScore",
            )

    @property
    def tier(self) -> str:
        """Get the priority tier based on final BIS."""
        if self.final_bis >= TIER_CRITICAL_LOW:
            return "Critical"
        if self.final_bis >= TIER_HIGH_LOW:
            return "High"
        if self.final_bis >= TIER_MEDIUM_LOW:
            return "Medium"
        return "Low"

    @property
    def is_critical(self) -> bool:
        """Check if the score is critical."""
        return self.final_bis >= TIER_CRITICAL_LOW

    @property
    def is_high_or_critical(self) -> bool:
        """Check if the score is high or critical."""
        return self.final_bis >= TIER_HIGH_LOW

    @classmethod
    def create(cls, raw_bis: float, confidence_multiplier: float) -> "RiskScore":
        """Create a risk score from raw BIS and confidence multiplier.

        Args:
            raw_bis: Raw BIS (0-100).
            confidence_multiplier: Confidence multiplier (0.7-1.0).

        Returns:
            RiskScore: New risk score instance.

        Raises:
            InvalidValueObjectError: If validation fails.
        """
        final_bis = raw_bis * confidence_multiplier
        return cls(raw_bis=raw_bis, final_bis=final_bis, confidence_multiplier=confidence_multiplier)