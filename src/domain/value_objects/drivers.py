"""Drivers value object representing the five scoring factors."""

from dataclasses import dataclass

from src.core.constants.scoring_weights import (
    ASSET_IMPORTANCE_WEIGHT,
    BUSINESS_IMPACT_WEIGHT,
    EXPLOITABILITY_WEIGHT,
    EXPOSURE_WEIGHT,
    VULNERABILITY_SEVERITY_WEIGHT,
)
from src.core.exceptions.domain import InvalidValueObjectError


@dataclass(frozen=True)
class Drivers:
    """Drivers value object containing the five scoring factors.

    Attributes:
        asset_importance: Asset importance score (0-100).
        vulnerability_severity: Vulnerability severity score (0-100).
        exploitability: Exploitability score (0-100).
        business_impact: Business impact score (0-100).
        exposure: Exposure score (0-100).
    """

    asset_importance: float
    vulnerability_severity: float
    exploitability: float
    business_impact: float
    exposure: float

    def __post_init__(self) -> None:
        """Validate driver scores."""
        for name, value in [
            ("asset_importance", self.asset_importance),
            ("vulnerability_severity", self.vulnerability_severity),
            ("exploitability", self.exploitability),
            ("business_impact", self.business_impact),
            ("exposure", self.exposure),
        ]:
            if not 0 <= value <= 100:
                raise InvalidValueObjectError(
                    f"{name} must be between 0 and 100, got {value}",
                    value_object="Drivers",
                )

    @property
    def raw_bis(self) -> float:
        """Calculate raw BIS using the weights defined in Section 7.2.

        Formula:
        raw_BIS = AI*0.25 + VS*0.20 + EX*0.25 + BI*0.20 + EXP*0.10
        """
        return (
            self.asset_importance * ASSET_IMPORTANCE_WEIGHT
            + self.vulnerability_severity * VULNERABILITY_SEVERITY_WEIGHT
            + self.exploitability * EXPLOITABILITY_WEIGHT
            + self.business_impact * BUSINESS_IMPACT_WEIGHT
            + self.exposure * EXPOSURE_WEIGHT
        )

    def to_dict(self) -> dict[str, float]:
        """Return drivers as a dictionary with weights."""
        return {
            "asset_importance": self.asset_importance,
            "vulnerability_severity": self.vulnerability_severity,
            "exploitability": self.exploitability,
            "business_impact": self.business_impact,
            "exposure": self.exposure,
        }

    def to_weighted_dict(self) -> dict[str, dict[str, float]]:
        """Return drivers with weights for display."""
        return {
            "asset_importance": {"value": self.asset_importance, "weight": ASSET_IMPORTANCE_WEIGHT},
            "vulnerability_severity": {"value": self.vulnerability_severity, "weight": VULNERABILITY_SEVERITY_WEIGHT},
            "exploitability": {"value": self.exploitability, "weight": EXPLOITABILITY_WEIGHT},
            "business_impact": {"value": self.business_impact, "weight": BUSINESS_IMPACT_WEIGHT},
            "exposure": {"value": self.exposure, "weight": EXPOSURE_WEIGHT},
        }