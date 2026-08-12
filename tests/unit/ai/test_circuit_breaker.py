"""Tests for AI failure isolation – AI failure never blocks scoring."""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_ai_failure_does_not_block_scoring():
    """Test that AI failure does not prevent scoring and decision generation."""
    # ✅ Import inside the function to avoid circular import
    from src.application.use_cases.evaluate_finding import EvaluateFindingUseCase
    from src.core.constants.enums import FindingSource, FindingStatus
    from src.domain.value_objects import RiskScore, Drivers, Confidence

    # Mock dependencies
    mock_uow = AsyncMock()
    mock_cache = AsyncMock()
    mock_threat_intel = AsyncMock()
    mock_llm = AsyncMock()
    mock_event = AsyncMock()
    mock_asset_repo = AsyncMock()

    # Simulate AI failure (LLM raises exception)
    mock_llm.generate_summary = AsyncMock(side_effect=Exception("LLM service unavailable"))

    use_case = EvaluateFindingUseCase(
        unit_of_work=mock_uow,
        cache_port=mock_cache,
        threat_intel_port=mock_threat_intel,
        llm_port=mock_llm,
        event_port=mock_event,
        asset_repository=mock_asset_repo,
    )

    # Mock business context and threat context
    mock_asset_repo.get_business_context = AsyncMock(return_value=AsyncMock(
        asset_importance_score=90,
        business_impact_score=100,
        exposure_score=70,
        has_owner=True,
        is_production=True,
        data_classification=AsyncMock(value="regulated"),
        compliance_scopes=[],
        downstream_dependents=15,
        revenue_impact="high",
    ))
    mock_threat_intel.get_threat_context = AsyncMock(return_value=AsyncMock(
        exploitability_score=70,
        is_exploitable=True,
    ))

    # Mock scoring engine
    with patch.object(use_case.scoring_engine, 'score_finding') as mock_score:
        mock_score.return_value = (
            RiskScore(raw_bis=84.0, final_bis=71.4, confidence_multiplier=0.85),
            Drivers(asset_importance=90, vulnerability_severity=85, exploitability=70, business_impact=100, exposure=70),
            Confidence(value=0.5, deductions=[]),
        )

        request = AsyncMock(
            tenant_id=AsyncMock(),
            asset_id=AsyncMock(),
            source=FindingSource.INTERNAL_SCANNER,
            source_finding_id="scan-123",
            title="Test Finding",
            description="Test Description",
            raw_severity=8.5,
            raw_severity_scale="cvss_v3",
            detected_at=1690000000,
            raw_payload={},
            status=FindingStatus.OPEN,
        )

        result = await use_case.execute(request)

        # Assertions
        assert result is not None
        assert result.risk_score is not None
        assert result.decision is not None
        assert result.summary is None
        mock_llm.generate_summary.assert_called_once()
        assert result.decision_id is not None
        assert result.finding_id is not None


@pytest.mark.asyncio
async def test_ai_timeout_does_not_block_scoring():
    """Test that AI timeout does not prevent scoring."""
    # ✅ Import inside the function
    from src.application.use_cases.evaluate_finding import EvaluateFindingUseCase
    from src.core.constants.enums import FindingSource, FindingStatus
    from src.domain.value_objects import RiskScore, Drivers, Confidence

    mock_uow = AsyncMock()
    mock_cache = AsyncMock()
    mock_threat_intel = AsyncMock()
    mock_llm = AsyncMock()
    mock_event = AsyncMock()
    mock_asset_repo = AsyncMock()

    mock_llm.generate_summary = AsyncMock(side_effect=TimeoutError("LLM timeout"))

    use_case = EvaluateFindingUseCase(
        unit_of_work=mock_uow,
        cache_port=mock_cache,
        threat_intel_port=mock_threat_intel,
        llm_port=mock_llm,
        event_port=mock_event,
        asset_repository=mock_asset_repo,
    )

    mock_asset_repo.get_business_context = AsyncMock(return_value=AsyncMock(
        asset_importance_score=90,
        business_impact_score=100,
        exposure_score=70,
        has_owner=True,
        is_production=True,
        data_classification=AsyncMock(value="regulated"),
        compliance_scopes=[],
        downstream_dependents=15,
        revenue_impact="high",
    ))
    mock_threat_intel.get_threat_context = AsyncMock(return_value=AsyncMock(
        exploitability_score=70,
        is_exploitable=True,
    ))

    with patch.object(use_case.scoring_engine, 'score_finding') as mock_score:
        mock_score.return_value = (
            RiskScore(raw_bis=84.0, final_bis=71.4, confidence_multiplier=0.85),
            Drivers(asset_importance=90, vulnerability_severity=85, exploitability=70, business_impact=100, exposure=70),
            Confidence(value=0.5, deductions=[]),
        )

        request = AsyncMock(
            tenant_id=AsyncMock(),
            asset_id=AsyncMock(),
            source=FindingSource.INTERNAL_SCANNER,
            source_finding_id="scan-123",
            title="Test Finding",
            description="Test Description",
            raw_severity=8.5,
            raw_severity_scale="cvss_v3",
            detected_at=1690000000,
            raw_payload={},
            status=FindingStatus.OPEN,
        )

        result = await use_case.execute(request)

        assert result is not None
        assert result.risk_score is not None
        assert result.summary is None


@pytest.mark.asyncio
async def test_ai_malformed_response_does_not_block_scoring():
    """Test that AI malformed response does not prevent scoring."""
    # ✅ Import inside the function
    from src.application.use_cases.evaluate_finding import EvaluateFindingUseCase
    from src.core.constants.enums import FindingSource, FindingStatus
    from src.domain.value_objects import RiskScore, Drivers, Confidence

    mock_uow = AsyncMock()
    mock_cache = AsyncMock()
    mock_threat_intel = AsyncMock()
    mock_llm = AsyncMock()
    mock_event = AsyncMock()
    mock_asset_repo = AsyncMock()

    # Mock LLM to return invalid JSON (or non-structured response)
    mock_llm.generate_summary = AsyncMock(return_value="Not a valid JSON response")

    use_case = EvaluateFindingUseCase(
        unit_of_work=mock_uow,
        cache_port=mock_cache,
        threat_intel_port=mock_threat_intel,
        llm_port=mock_llm,
        event_port=mock_event,
        asset_repository=mock_asset_repo,
    )

    mock_asset_repo.get_business_context = AsyncMock(return_value=AsyncMock(
        asset_importance_score=90,
        business_impact_score=100,
        exposure_score=70,
        has_owner=True,
        is_production=True,
        data_classification=AsyncMock(value="regulated"),
        compliance_scopes=[],
        downstream_dependents=15,
        revenue_impact="high",
    ))
    mock_threat_intel.get_threat_context = AsyncMock(return_value=AsyncMock(
        exploitability_score=70,
        is_exploitable=True,
    ))

    with patch.object(use_case.scoring_engine, 'score_finding') as mock_score:
        mock_score.return_value = (
            RiskScore(raw_bis=84.0, final_bis=71.4, confidence_multiplier=0.85),
            Drivers(asset_importance=90, vulnerability_severity=85, exploitability=70, business_impact=100, exposure=70),
            Confidence(value=0.5, deductions=[]),
        )

        request = AsyncMock(
            tenant_id=AsyncMock(),
            asset_id=AsyncMock(),
            source=FindingSource.INTERNAL_SCANNER,
            source_finding_id="scan-123",
            title="Test Finding",
            description="Test Description",
            raw_severity=8.5,
            raw_severity_scale="cvss_v3",
            detected_at=1690000000,
            raw_payload={},
            status=FindingStatus.OPEN,
        )

        result = await use_case.execute(request)

        assert result is not None
        assert result.risk_score is not None
        # Summary should be None because parsing failed
        assert result.summary is None