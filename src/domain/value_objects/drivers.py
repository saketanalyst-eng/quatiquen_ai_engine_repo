"""Drivers value object representing the five scoring factors."""

from dataclasses import dataclass
from typing import Any, Dict, Optional

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

    # ----------------------------------------------------------------------
    # NEW: Driver Explanations
    # ----------------------------------------------------------------------

    def to_explained_dict(self, business_context: Optional[Any] = None) -> Dict[str, Dict[str, Any]]:
        """Return drivers with value and a human‑readable explanation.

        Args:
            business_context: Optional BusinessContext object (for richer explanations).

        Returns:
            Dict with structure:
            {
                "asset_importance": {"value": 90, "explanation": "..."},
                "vulnerability_severity": {"value": 85, "explanation": "..."},
                ...
            }
        """
        return {
            "asset_importance": {
                "value": self.asset_importance,
                "explanation": self._asset_importance_explanation(business_context),
            },
            "vulnerability_severity": {
                "value": self.vulnerability_severity,
                "explanation": self._severity_explanation(),
            },
            "exploitability": {
                "value": self.exploitability,
                "explanation": self._exploitability_explanation(),
            },
            "business_impact": {
                "value": self.business_impact,
                "explanation": self._business_impact_explanation(business_context),
            },
            "exposure": {
                "value": self.exposure,
                "explanation": self._exposure_explanation(business_context),
            },
        }

    def _asset_importance_explanation(self, business_context: Optional[Any]) -> str:
        """Explain the asset importance score."""
        if business_context:
            if business_context.is_production:
                env = "Production"
            else:
                env = "Non-production"
            return f"{env} asset with criticality {int(self.asset_importance)}/100."
        return f"Asset criticality {int(self.asset_importance)}/100."

    def _severity_explanation(self) -> str:
        """Explain the vulnerability severity score."""
        if self.vulnerability_severity >= 80:
            return f"Critical vulnerability (severity {int(self.vulnerability_severity)}/100)."
        elif self.vulnerability_severity >= 60:
            return f"High severity vulnerability (severity {int(self.vulnerability_severity)}/100)."
        else:
            return f"Moderate severity vulnerability (severity {int(self.vulnerability_severity)}/100)."

    def _exploitability_explanation(self) -> str:
        """Explain the exploitability score."""
        if self.exploitability >= 80:
            return f"Highly exploitable (score {int(self.exploitability)}/100)."
        elif self.exploitability >= 50:
            return f"Moderately exploitable (score {int(self.exploitability)}/100)."
        else:
            return f"Low exploitability (score {int(self.exploitability)}/100)."

    def _business_impact_explanation(self, business_context: Optional[Any]) -> str:
        """Explain the business impact score."""
        if business_context:
            if business_context.has_compliance_scope:
                scopes = ", ".join([s.value for s in business_context.compliance_scopes])
                return f"High business impact ({int(self.business_impact)}/100) due to compliance scope ({scopes}) and regulated data."
            elif business_context.data_classification.value == "regulated":
                return f"High business impact ({int(self.business_impact)}/100) due to regulated data."
            else:
                return f"Business impact {int(self.business_impact)}/100."
        return f"Business impact {int(self.business_impact)}/100."

    def _exposure_explanation(self, business_context: Optional[Any]) -> str:
        """Explain the exposure score."""
        if business_context:
            exposure_str = business_context.exposure.value.replace("-", " ").title()
            return f"Exposure level: {exposure_str} (score {int(self.exposure)}/100)."
        return f"Exposure score {int(self.exposure)}/100."