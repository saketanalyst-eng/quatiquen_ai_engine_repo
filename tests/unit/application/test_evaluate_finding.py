"""Unit tests for EvaluateFindingUseCase."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.dto.request import EvaluateFindingRequest
from src.application.use_cases.evaluate_finding import EvaluateFindingUseCase
from src.core.constants.enums import FindingSource, FindingStatus
from src.domain.entities import Decision
from src.domain.value_objects import RiskScore, Drivers, Confidence


class TestEvaluateFindingUseCase:
    """Test EvaluateFindingUseCase."""

    @pytest.mark.asyncio
    async def test_execute_success(
        self,
        mock_finding_repo,
        mock_decision_repo,
        mock_uow,
        mock_cache,
        mock_threat_intel,
        mock_llm,
        mock_event,
        mock_asset_repo,
        sample_finding,
    ) -> None:
        """Test successful evaluation."""
        # Setup: mock repositories to return sample finding, etc.
        mock_finding_repo.get_by_id = AsyncMock(return_value=None)
        mock_finding_repo.save = AsyncMock()
        mock_decision_repo.save = AsyncMock()
        mock_uow.commit = AsyncMock()
        mock_asset_repo.get_business_context = AsyncMock(
            return_value=MagicMock(
                asset_importance_score=90.0,
                business_impact_score=80.0,
                exposure_score=70.0,
                has_owner=True,
                is_production=True,
                data_classification="regulated",
                compliance_scopes=["PCI"],
                downstream_dependents=15,
                revenue_impact="high",
            )
        )
        mock_threat_intel.get_threat_context = AsyncMock(
            return_value=MagicMock(
                exploitability_score=80.0,
                is_exploitable=True,
            )
        )
        mock_llm.generate_summary = AsyncMock(return_value="Test summary")

        use_case = EvaluateFindingUseCase(
            finding_repository=mock_finding_repo,
            decision_repository=mock_decision_repo,
            unit_of_work=mock_uow,
            cache_port=mock_cache,
            threat_intel_port=mock_threat_intel,
            llm_port=mock_llm,
            event_port=mock_event,
            asset_repository=mock_asset_repo,
        )

        request = EvaluateFindingRequest(
            tenant_id=MagicMock(),
            asset_id=MagicMock(),
            source=FindingSource.INTERNAL_SCANNER,
            source_finding_id="scan-123",
            title="Test Finding",
            description="Description",
            raw_severity=7.5,
            raw_severity_scale="cvss_v3",
            detected_at=1234567890,
            raw_payload={},
            cve_id="CVE-2024-12345",
            status=FindingStatus.OPEN,
        )

        response = await use_case.execute(request)

        assert response is not None
        assert response.bis is not None
        assert response.tier is not None
        assert response.confidence is not None
        assert response.summary is not None
        assert mock_uow.commit.called

    @pytest.mark.asyncio
    async def test_execute_missing_business_context(
        self,
        mock_finding_repo,
        mock_decision_repo,
        mock_uow,
        mock_cache,
        mock_threat_intel,
        mock_llm,
        mock_event,
        mock_asset_repo,
    ) -> None:
        """Test failure when business context is missing."""
        mock_asset_repo.get_business_context = AsyncMock(return_value=None)

        use_case = EvaluateFindingUseCase(
            finding_repository=mock_finding_repo,
            decision_repository=mock_decision_repo,
            unit_of_work=mock_uow,
            cache_port=mock_cache,
            threat_intel_port=mock_threat_intel,
            llm_port=mock_llm,
            event_port=mock_event,
            asset_repository=mock_asset_repo,
        )

        request = EvaluateFindingRequest(
            tenant_id=MagicMock(),
            asset_id=MagicMock(),
            source=FindingSource.INTERNAL_SCANNER,
            source_finding_id="scan-123",
            title="Test",
            description="Desc",
            raw_severity=5.0,
            raw_severity_scale="cvss_v3",
            detected_at=1234567890,
            raw_payload={},
        )

        with pytest.raises(Exception):  # Should raise UseCaseError
            await use_case.execute(request)