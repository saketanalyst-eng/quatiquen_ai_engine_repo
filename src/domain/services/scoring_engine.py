"""Scoring engine implementing deterministic risk scoring logic.

This module contains pure functions for calculating Business Impact Score (BIS),
confidence, and priority tiers as defined in Sections 7, 8, and 9 of the blueprint.
"""

from typing import Tuple

from src.core.constants.scoring_weights import (
    ASSET_IMPORTANCE_WEIGHT,
    BUSINESS_IMPACT_WEIGHT,
    EXPLOITABILITY_WEIGHT,
    EXPOSURE_WEIGHT,
    VULNERABILITY_SEVERITY_WEIGHT,
)
from src.core.constants.thresholds import (
    TIER_CRITICAL_LOW,
    TIER_HIGH_LOW,
    TIER_MEDIUM_LOW,
)
from src.core.exceptions.domain import ValidationError
from src.domain.value_objects import BusinessContext, Confidence, Drivers, RiskScore, ThreatContext


class ScoringEngine:
    """Domain service for deterministic risk scoring.

    This service implements the exact scoring formulas from the blueprint.
    All methods are pure functions with no side effects.
    """

    @staticmethod
    def calculate_raw_bis(
        asset_importance: float,
        vulnerability_severity: float,
        exploitability: float,
        business_impact: float,
        exposure: float,
    ) -> float:
        """Calculate raw Business Impact Score (BIS) using Section 7.2 formula.

        Args:
            asset_importance: Asset importance score (0-100).
            vulnerability_severity: Vulnerability severity score (0-100).
            exploitability: Exploitability score (0-100).
            business_impact: Business impact score (0-100).
            exposure: Exposure score (0-100).

        Returns:
            float: Raw BIS (0-100).

        Raises:
            ValidationError: If any input is out of range.
        """
        for name, value in [
            ("asset_importance", asset_importance),
            ("vulnerability_severity", vulnerability_severity),
            ("exploitability", exploitability),
            ("business_impact", business_impact),
            ("exposure", exposure),
        ]:
            if not 0 <= value <= 100:
                raise ValidationError(
                    f"{name} must be between 0 and 100, got {value}",
                    field=name,
                    value=value,
                )

        raw_bis = (
            asset_importance * ASSET_IMPORTANCE_WEIGHT
            + vulnerability_severity * VULNERABILITY_SEVERITY_WEIGHT
            + exploitability * EXPLOITABILITY_WEIGHT
            + business_impact * BUSINESS_IMPACT_WEIGHT
            + exposure * EXPOSURE_WEIGHT
        )

        # Ensure result is within bounds (floating point tolerance)
        return max(0.0, min(100.0, raw_bis))

    @staticmethod
    def calculate_confidence(
        has_owner: bool,
        is_stale: bool,
        has_threat_intel: bool,
        has_cmdb_record: bool,
        source_count: int,
    ) -> Confidence:
        """Calculate confidence score using Section 9 deductions.

        Args:
            has_owner: Whether the asset has an owner.
            is_stale: Whether the finding is stale (>30 days).
            has_threat_intel: Whether threat intel exists for the CVE.
            has_cmdb_record: Whether the asset is in CMDB.
            source_count: Number of sources reporting the finding.

        Returns:
            Confidence: Confidence value object with score and deductions.
        """
        return Confidence.create(
            has_owner=has_owner,
            is_stale=is_stale,
            has_threat_intel=has_threat_intel,
            has_cmdb_record=has_cmdb_record,
            source_count=source_count,
        )

    @staticmethod
    def apply_confidence_multiplier(raw_bis: float, confidence: Confidence) -> RiskScore:
        """Apply confidence multiplier to raw BIS as defined in Section 7.3.

        multiplier = 0.7 + (0.3 * confidence)
        final_BIS = raw_BIS * multiplier

        Args:
            raw_bis: Raw BIS (0-100).
            confidence: Confidence value object.

        Returns:
            RiskScore: Risk score with raw and final BIS.

        Raises:
            ValidationError: If raw_bis is out of range.
        """
        if not 0 <= raw_bis <= 100:
            raise ValidationError(
                f"Raw BIS must be between 0 and 100, got {raw_bis}",
                field="raw_bis",
                value=raw_bis,
            )

        multiplier = confidence.multiplier
        # Floor is 0.7 per blueprint Section 7.3
        final_bis = raw_bis * multiplier

        # Ensure final BIS does not exceed 100 due to floating point
        final_bis = min(100.0, final_bis)

        return RiskScore.create(raw_bis=raw_bis, confidence_multiplier=multiplier)

    @staticmethod
    def get_tier(final_bis: float) -> str:
        """Get priority tier from final BIS as defined in Section 7.4.

        Args:
            final_bis: Final BIS (0-100).

        Returns:
            str: Priority tier (Critical, High, Medium, Low).

        Raises:
            ValidationError: If final_bis is out of range.
        """
        if not 0 <= final_bis <= 100:
            raise ValidationError(
                f"Final BIS must be between 0 and 100, got {final_bis}",
                field="final_bis",
                value=final_bis,
            )

        if final_bis >= TIER_CRITICAL_LOW:
            return "Critical"
        if final_bis >= TIER_HIGH_LOW:
            return "High"
        if final_bis >= TIER_MEDIUM_LOW:
            return "Medium"
        return "Low"

    @staticmethod
    def compute_drivers(
        asset_importance: float,
        vulnerability_severity: float,
        exploitability: float,
        business_impact: float,
        exposure: float,
    ) -> Drivers:
        """Compute drivers value object from raw scores.

        Args:
            asset_importance: Asset importance score.
            vulnerability_severity: Vulnerability severity score.
            exploitability: Exploitability score.
            business_impact: Business impact score.
            exposure: Exposure score.

        Returns:
            Drivers: Drivers value object.
        """
        return Drivers(
            asset_importance=asset_importance,
            vulnerability_severity=vulnerability_severity,
            exploitability=exploitability,
            business_impact=business_impact,
            exposure=exposure,
        )

    @staticmethod
    def score_finding(
        business_context: BusinessContext,
        threat_context: ThreatContext,
        vulnerability_severity: float,
        is_stale: bool,
        source_count: int,
        has_cmdb_record: bool = True,
    ) -> Tuple[RiskScore, Drivers, Confidence]:
        """Complete scoring pipeline for a finding.

        This method orchestrates the entire scoring process using the
        provided contexts and metadata.

        Args:
            business_context: Business context for the asset.
            threat_context: Threat context for the CVE.
            vulnerability_severity: Normalized vulnerability severity (0-100).
            is_stale: Whether the finding is stale.
            source_count: Number of sources reporting the finding.
            has_cmdb_record: Whether asset is in CMDB.

        Returns:
            Tuple[RiskScore, Drivers, Confidence]: Risk score, drivers, and confidence.
        """
        # Extract driver scores
        asset_importance = business_context.asset_importance_score
        exploitability = threat_context.exploitability_score
        business_impact = business_context.business_impact_score
        exposure = business_context.exposure_score

        # Calculate raw BIS
        raw_bis = ScoringEngine.calculate_raw_bis(
            asset_importance=asset_importance,
            vulnerability_severity=vulnerability_severity,
            exploitability=exploitability,
            business_impact=business_impact,
            exposure=exposure,
        )

        # Calculate confidence
        confidence = ScoringEngine.calculate_confidence(
            has_owner=business_context.has_owner,
            is_stale=is_stale,
            has_threat_intel=threat_context.is_exploitable,
            has_cmdb_record=has_cmdb_record,
            source_count=source_count,
        )

        # Apply confidence multiplier
        risk_score = ScoringEngine.apply_confidence_multiplier(raw_bis, confidence)

        # Build drivers
        drivers = ScoringEngine.compute_drivers(
            asset_importance=asset_importance,
            vulnerability_severity=vulnerability_severity,
            exploitability=exploitability,
            business_impact=business_impact,
            exposure=exposure,
        )

        return risk_score, drivers, confidence