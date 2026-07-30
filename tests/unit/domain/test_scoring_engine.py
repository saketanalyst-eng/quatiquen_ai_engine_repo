"""Unit tests for domain scoring engine.

Includes the golden test from Section 7.5 of the blueprint.
"""

import pytest

from src.domain.services import ScoringEngine
from src.domain.value_objects import BusinessContext, Confidence, Drivers, RiskScore, ThreatContext


class TestScoringEngine:
    """Test the scoring engine pure functions."""

    def test_calculate_raw_bis_golden(self) -> None:
        """Golden test from Section 7.5: CVE-2024-XXXX should yield raw_BIS 87.65."""
        asset_importance = 95.0
        vulnerability_severity = 72.0
        exploitability = 92.0
        business_impact = 90.0
        exposure = 85.0

        raw_bis = ScoringEngine.calculate_raw_bis(
            asset_importance=asset_importance,
            vulnerability_severity=vulnerability_severity,
            exploitability=exploitability,
            business_impact=business_impact,
            exposure=exposure,
        )

        # Expected raw_BIS = 87.65 (from blueprint worked example)
        assert raw_bis == pytest.approx(87.65, 0.01)

    def test_apply_confidence_multiplier_golden(self) -> None:
        """Test confidence multiplier application with golden example."""
        raw_bis = 87.65
        confidence = Confidence(value=0.9, deductions=[])

        risk_score = ScoringEngine.apply_confidence_multiplier(raw_bis, confidence)

        # multiplier = 0.7 + 0.3*0.9 = 0.97
        # final = 87.65 * 0.97 = 85.0205 -> floor -> 85.0
        assert risk_score.final_bis == pytest.approx(85.0, 0.01)
        assert risk_score.raw_bis == raw_bis
        assert risk_score.confidence_multiplier == pytest.approx(0.97, 0.01)

    def test_get_tier_boundaries(self) -> None:
        """Test tier boundaries as defined in Section 7.4."""
        assert ScoringEngine.get_tier(100) == "Critical"
        assert ScoringEngine.get_tier(85) == "Critical"
        assert ScoringEngine.get_tier(84.9) == "High"
        assert ScoringEngine.get_tier(65) == "High"
        assert ScoringEngine.get_tier(64.9) == "Medium"
        assert ScoringEngine.get_tier(35) == "Medium"
        assert ScoringEngine.get_tier(34.9) == "Low"
        assert ScoringEngine.get_tier(0) == "Low"

    def test_calculate_confidence(self) -> None:
        """Test confidence calculation with deductions."""
        # All factors positive -> confidence 1.0
        confidence = ScoringEngine.calculate_confidence(
            has_owner=True,
            is_stale=False,
            has_threat_intel=True,
            has_cmdb_record=True,
            source_count=3,
        )
        assert confidence.value == 1.0
        assert len(confidence.deductions) == 0

        # Missing owner -> 0.8
        confidence = ScoringEngine.calculate_confidence(
            has_owner=False,
            is_stale=False,
            has_threat_intel=True,
            has_cmdb_record=True,
            source_count=3,
        )
        assert confidence.value == 0.8
        assert ("no_asset_owner", 0.2) in confidence.deductions

        # Stale -> 0.8, no owner -> 0.8, cumulative -> 0.6
        confidence = ScoringEngine.calculate_confidence(
            has_owner=False,
            is_stale=True,
            has_threat_intel=True,
            has_cmdb_record=True,
            source_count=3,
        )
        assert confidence.value == 0.6

        # All deductions max -> 0.1 (0.1 min)
        confidence = ScoringEngine.calculate_confidence(
            has_owner=False,
            is_stale=True,
            has_threat_intel=False,
            has_cmdb_record=False,
            source_count=1,
        )
        assert confidence.value == 0.0  # Clamped to 0

    def test_score_finding_integration(self, sample_finding, sample_business_context, sample_threat_context) -> None:
        """Integration test for score_finding method."""
        risk_score, drivers, confidence = ScoringEngine.score_finding(
            business_context=sample_business_context,
            threat_context=sample_threat_context,
            vulnerability_severity=72.0,
            is_stale=False,
            source_count=3,
            has_cmdb_record=True,
        )

        assert risk_score.raw_bis == pytest.approx(87.65, 0.01)
        assert risk_score.final_bis == pytest.approx(85.0, 0.01)  # confidence 1.0 -> same
        assert confidence.value == 1.0
        assert drivers.asset_importance == sample_business_context.asset_importance_score
        assert drivers.vulnerability_severity == 72.0

    def test_normalize_severity(self) -> None:
        """Test severity normalization logic."""
        engine = ScoringEngine()
        # CVSS 8.5 -> 85
        assert engine._normalize_severity(8.5, "cvss_v3") == 85.0
        # Qualitative
        assert engine._normalize_severity("high", "qualitative") == 75.0
        assert engine._normalize_severity("critical", "qualitative") == 95.0
        # Vendor custom: clamp
        assert engine._normalize_severity(120, "vendor_custom") == 100.0
        assert engine._normalize_severity(-10, "vendor_custom") == 0.0