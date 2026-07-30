"""Asset entity representing a monitored asset."""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from src.core.constants.enums import AssetCriticality, ComplianceScope, DataSensitivity, ExposureLevel
from src.core.exceptions.domain import ValidationError


@dataclass(frozen=True)
class Asset:
    """Asset entity representing a monitored asset with business context.

    Attributes:
        id: Unique asset identifier.
        tenant_id: Tenant that owns the asset.
        name: Asset name.
        asset_type: Type of asset (server, app, api, db).
        importance_tier: Criticality tier (0-100).
        owner_id: Optional user ID of the asset owner.
        data_classification: Data sensitivity classification.
        compliance_scopes: List of compliance frameworks applicable.
        exposure: Exposure level.
        is_production: Whether the asset is in production.
        downstream_dependents: Count of services depending on this asset.
        revenue_impact: Revenue impact level (none/low/medium/high).
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id: UUID
    tenant_id: UUID
    name: str
    asset_type: str
    importance_tier: int
    owner_id: Optional[UUID]
    data_classification: DataSensitivity
    compliance_scopes: list[ComplianceScope]
    exposure: ExposureLevel
    is_production: bool
    downstream_dependents: int
    revenue_impact: str
    created_at: int
    updated_at: int

    def __post_init__(self) -> None:
        """Validate asset invariants."""
        if not self.name:
            raise ValidationError("Asset name cannot be empty", field="name")
        if not 0 <= self.importance_tier <= 100:
            raise ValidationError(
                f"Importance tier must be between 0 and 100, got {self.importance_tier}",
                field="importance_tier",
                value=self.importance_tier,
            )
        if self.downstream_dependents < 0:
            raise ValidationError(
                f"Downstream dependents cannot be negative, got {self.downstream_dependents}",
                field="downstream_dependents",
                value=self.downstream_dependents,
            )

    @property
    def criticality(self) -> AssetCriticality:
        """Get the asset criticality enum from importance tier."""
        return AssetCriticality.from_importance_tier(self.importance_tier)

    @property
    def is_critical(self) -> bool:
        """Check if the asset is critical (importance >= 85)."""
        return self.importance_tier >= 85

    @property
    def has_compliance_scope(self) -> bool:
        """Check if the asset has any compliance scope."""
        return len(self.compliance_scopes) > 0

    @property
    def exposure_score(self) -> int:
        """Get the exposure score (0-100)."""
        return self.exposure.score()

    def is_owned(self) -> bool:
        """Check if the asset has an assigned owner."""
        return self.owner_id is not None

    def has_regulated_data(self) -> bool:
        """Check if the asset holds regulated data."""
        return self.data_classification == DataSensitivity.REGULATED