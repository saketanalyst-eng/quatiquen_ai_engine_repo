"""Business context value object representing asset and business information."""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from src.core.constants.enums import AssetCriticality, ComplianceScope, DataSensitivity, ExposureLevel
from src.core.constants.thresholds import COMPLIANCE_FLOOR_RAISE, DATA_SENSITIVITY_MULTIPLIER
from src.core.exceptions.domain import InvalidValueObjectError


@dataclass(frozen=True)
class BusinessContext:
    """Business context value object containing asset and business information.

    Attributes:
        asset_id: Asset identifier.
        importance_tier: Asset importance tier (0-100).
        owner_id: Optional asset owner.
        data_classification: Data sensitivity classification.
        compliance_scopes: List of compliance scopes.
        exposure: Exposure level.
        is_production: Whether the asset is in production.
        downstream_dependents: Number of downstream dependents.
        revenue_impact: Revenue impact level (none/low/medium/high).
    """

    asset_id: UUID
    importance_tier: int
    owner_id: Optional[UUID]
    data_classification: DataSensitivity
    compliance_scopes: list[ComplianceScope]
    exposure: ExposureLevel
    is_production: bool
    downstream_dependents: int
    revenue_impact: str

    def __post_init__(self) -> None:
        """Validate business context invariants."""
        if not 0 <= self.importance_tier <= 100:
            raise InvalidValueObjectError(
                f"Importance tier must be between 0 and 100, got {self.importance_tier}",
                value_object="BusinessContext",
            )
        if self.downstream_dependents < 0:
            raise InvalidValueObjectError(
                f"Downstream dependents cannot be negative, got {self.downstream_dependents}",
                value_object="BusinessContext",
            )

    @property
    def asset_criticality(self) -> AssetCriticality:
        """Get asset criticality enum."""
        return AssetCriticality.from_importance_tier(self.importance_tier)

    @property
    def has_owner(self) -> bool:
        """Check if asset has an owner."""
        return self.owner_id is not None

    @property
    def has_compliance_scope(self) -> bool:
        """Check if any compliance scope is present."""
        return len(self.compliance_scopes) > 0

    @property
    def max_compliance_floor(self) -> int:
        """Get the maximum compliance floor raise.

        Returns:
            int: Maximum floor raise value from compliance scopes.
        """
        if not self.compliance_scopes:
            return 0
        return max(COMPLIANCE_FLOOR_RAISE.get(scope.value.lower(), 0) for scope in self.compliance_scopes)

    @property
    def data_sensitivity_multiplier(self) -> float:
        """Get multiplier for data sensitivity."""
        return DATA_SENSITIVITY_MULTIPLIER.get(self.data_classification.value.lower(), 1.0)

    @property
    def environment_multiplier(self) -> float:
        """Get multiplier for environment (production vs non-production)."""
        return 1.0 if self.is_production else 0.3

    @property
    def asset_importance_score(self) -> float:
        """Get the asset importance score (0-100)."""
        return float(self.importance_tier)

    @property
    def business_impact_score(self) -> float:
        """Compute business impact score (0-100) for the scoring engine.

        Combines data sensitivity, compliance, revenue impact, and dependencies.
        """
        base = 20.0

        # Data sensitivity contribution
        if self.data_classification == DataSensitivity.REGULATED:
            base += 40.0
        elif self.data_classification == DataSensitivity.CONFIDENTIAL:
            base += 25.0
        elif self.data_classification == DataSensitivity.INTERNAL:
            base += 10.0

        # Compliance contribution
        if self.has_compliance_scope:
            base += 15.0

        # Revenue impact
        revenue_map = {"none": 0, "low": 10, "medium": 20, "high": 30}
        base += revenue_map.get(self.revenue_impact.lower(), 0)

        # Downstream dependents
        if self.downstream_dependents > 10:
            base += 15.0
        elif self.downstream_dependents > 5:
            base += 10.0
        elif self.downstream_dependents > 0:
            base += 5.0

        # Cap at 100
        return min(100.0, base)

    @property
    def exposure_score(self) -> float:
        """Get exposure score (0-100)."""
        return float(self.exposure.score())