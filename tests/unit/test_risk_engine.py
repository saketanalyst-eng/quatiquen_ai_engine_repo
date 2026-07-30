"""Unit tests for RiskEngine."""

import pytest
from unittest.mock import MagicMock

from src.engine.risk_engine import RiskEngine
from src.engine.strategies.default_strategy import DefaultStrategy
from src.engine.engine_result import EngineResult
from src.domain.value_objects import Drivers
from src.domain.services import ScoringEngine


class TestRiskEngine:
    """Test RiskEngine."""

    def test_execute_success(self, sample_finding, sample_business_context, sample_threat_context):
        """Test successful raw BIS calculation."""
        strategy = DefaultStrategy()
        engine = RiskEngine(strategy)

        result = EngineResult(finding=sample_finding)
        result.business_context = sample_business_context
        result.threat_context = sample_threat_context
        result.vulnerability_severity = 72.0

        success = engine.execute(result)

        assert success is True
        assert result.raw_bis is not None
        assert result.raw_bis == pytest.approx(87.65, 0.01)
        assert result.drivers is not None
        assert isinstance(result.drivers, Drivers)

    def test_execute_missing_context(self, sample_finding):
        """Test failure when context missing."""
        engine = RiskEngine(DefaultStrategy())
        result = EngineResult(finding=sample_finding)

        success = engine.execute(result)

        assert success is False
        assert "Missing required context" in result.errors.get("risk_engine", "")

    def test_execute_strategy_modifies_scores(self):
        """Test that strategy modifies scores."""
        class TestStrategy(DefaultStrategy):
            def modify_scores(self, asset_importance, vulnerability_severity, exploitability, business_impact, exposure):
                return (100, 100, 100, 100, 100)  # all max

        engine = RiskEngine(TestStrategy())
        result = EngineResult(finding=MagicMock())
        result.business_context = MagicMock(
            asset_importance_score=50,
            business_impact_score=50,
            exposure_score=50,
        )
        result.threat_context = MagicMock(exploitability_score=50)
        result.vulnerability_severity = 50

        engine.execute(result)
        # With all 100, raw BIS = 100
        assert result.raw_bis == 100.0