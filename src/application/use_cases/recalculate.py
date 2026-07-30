"""Use case for recalculating a finding's score."""

import time
from typing import Optional

from src.application.dto import RecalculateRequest, RecalculateResponse
from src.core.constants.enums import PriorityTier
from src.core.exceptions.application import PipelineInterruptionError, UseCaseError
from src.core.exceptions.domain import EntityNotFoundError
from src.core.logging.logger import get_logger
from src.domain.entities import Decision
from src.domain.repositories import IDecisionRepository, IFindingRepository, IUnitOfWork
from src.domain.services import ScoringEngine
from src.domain.value_objects import BusinessContext, ThreatContext

logger = get_logger("quantiquan.application.recalculate")


class RecalculateUseCase:
    """Use case to recalculate a finding's score (e.g., after weight changes)."""

    def __init__(
        self,
        finding_repository: IFindingRepository,
        decision_repository: IDecisionRepository,
        unit_of_work: IUnitOfWork,
        asset_repository: Optional["IAssetRepository"] = None,  # type: ignore
        threat_intel_port: Optional["ThreatIntelPort"] = None,  # type: ignore
    ) -> None:
        """Initialize use case.

        Args:
            finding_repository: Finding repository.
            decision_repository: Decision repository.
            unit_of_work: Unit of work.
            asset_repository: Asset repository (optional).
            threat_intel_port: Threat intel port (optional).
        """
        self.finding_repo = finding_repository
        self.decision_repo = decision_repository
        self.uow = unit_of_work
        self.asset_repo = asset_repository
        self.threat_intel = threat_intel_port
        self.scoring_engine = ScoringEngine()

    async def execute(self, request: RecalculateRequest) -> RecalculateResponse:
        """Execute the use case.

        Args:
            request: Recalculate request.

        Returns:
            RecalculateResponse: Recalculated decision.

        Raises:
            EntityNotFoundError: If finding or decision not found.
            UseCaseError: If any error occurs.
        """
        logger.info(
            "Recalculating finding",
            finding_id=str(request.finding_id),
            tenant_id=str(request.tenant_id),
            force=request.force,
        )

        try:
            # 1. Retrieve existing finding and decision
            finding = await self.finding_repo.get_by_id(
                request.finding_id,
                request.tenant_id,
            )
            if finding is None:
                raise EntityNotFoundError("Finding", str(request.finding_id))

            old_decision = await self.decision_repo.get_by_finding_id(
                request.finding_id,
                request.tenant_id,
            )
            if old_decision is None:
                raise EntityNotFoundError("Decision", str(request.finding_id))

            # 2. Fetch business context
            business_context = await self._get_business_context(
                finding.asset_id,
                finding.tenant_id,
            )
            if business_context is None:
                raise PipelineInterruptionError(
                    "Business context not found",
                    stage="recalculate",
                    finding_id=str(finding.id),
                )

            # 3. Fetch threat context (if CVE exists)
            threat_context = None
            if finding.has_cve and finding.cve_id and self.threat_intel:
                threat_context = await self.threat_intel.get_threat_context(finding.cve_id)

            # 4. Compute new scores
            vulnerability_severity = self._normalize_severity(
                finding.raw_severity,
                finding.raw_severity_scale,
            )
            is_stale = finding.is_stale(int(time.time()))
            source_count = 1  # Placeholder

            risk_score, drivers, confidence = self.scoring_engine.score_finding(
                business_context=business_context,
                threat_context=threat_context or ThreatContext.create(cve_id="") if threat_context else ThreatContext.create(cve_id=""),
                vulnerability_severity=vulnerability_severity,
                is_stale=is_stale,
                source_count=source_count,
                has_cmdb_record=True,
            )

            tier = self.scoring_engine.get_tier(risk_score.final_bis)

            # 5. Create new decision
            new_decision = Decision.create(
                finding_id=finding.id,
                tenant_id=finding.tenant_id,
                risk_score=risk_score,
                tier=PriorityTier(tier),
                confidence=confidence,
                drivers=drivers,
                recommendation_id=old_decision.recommendation_id,
                summary=old_decision.summary,  # Keep existing summary
                version="1.0.0",
            )

            # 6. Persist in transaction
            async with self.uow:
                await self.decision_repo.update(new_decision)
                await self.uow.commit()

            logger.info(
                "Finding recalculated",
                finding_id=str(finding.id),
                old_bis=old_decision.bis,
                new_bis=risk_score.final_bis,
            )

            return RecalculateResponse(
                finding_id=finding.id,
                tenant_id=finding.tenant_id,
                bis=risk_score.final_bis,
                tier=PriorityTier(tier),
                confidence=confidence.value,
                drivers=drivers.to_dict(),
                recommendation_id=new_decision.recommendation_id,
                summary=new_decision.summary,
                computed_at=new_decision.computed_at,
                previous_bis=old_decision.bis,
                previous_tier=old_decision.tier.value,
            )

        except (EntityNotFoundError, PipelineInterruptionError):
            raise
        except Exception as exc:
            logger.error(
                "Failed to recalculate finding",
                finding_id=str(request.finding_id),
                error=str(exc),
                exc_info=True,
            )
            raise UseCaseError(
                f"Failed to recalculate finding: {str(exc)}",
                use_case="RecalculateUseCase",
                cause=exc,
            )

    async def _get_business_context(self, asset_id, tenant_id):
        """Placeholder: fetch from asset repo."""
        if self.asset_repo:
            return await self.asset_repo.get_business_context(asset_id, tenant_id)
        return None

    def _normalize_severity(self, raw_severity: float, scale: str) -> float:
        """Normalize severity to 0-100."""
        if scale in ("cvss_v3", "cvss_v4"):
            return min(100.0, raw_severity * 10.0)
        if scale == "qualitative":
            mapping = {"low": 25, "medium": 50, "high": 75, "critical": 95}
            return min(100.0, mapping.get(str(raw_severity).lower(), 50.0))
        return min(100.0, max(0.0, raw_severity))