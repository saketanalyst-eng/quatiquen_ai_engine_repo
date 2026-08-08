"""Use case for evaluating a finding through the scoring pipeline."""

import time
from typing import Optional
from uuid import UUID

from src.application.dto import EvaluateFindingRequest, EvaluateFindingResponse
from src.application.ports import CachePort, EventPort, LLMPort, ThreatIntelPort
from src.core.constants.enums import PriorityTier
from src.core.exceptions.application import PipelineInterruptionError, UseCaseError
from src.core.logging.logger import get_logger
from src.domain.entities import Decision, Finding
from src.domain.repositories import IUnitOfWork
from src.domain.services import ScoringEngine
from src.domain.value_objects import BusinessContext, Confidence, Drivers, RiskScore, ThreatContext
from src.interfaces.schemas.response import (
    ConfidenceBreakdown,
    DriverExplanation,
    DriversResponse,
    EvaluateFindingResponse,
    StructuredSummary,
)

logger = get_logger("quantiquan.application.evaluate_finding")


class EvaluateFindingUseCase:
    """Use case to evaluate a new finding through the scoring pipeline.

    This orchestrates normalization, context fetching, scoring, recommendation,
    AI summary generation, and persistence.
    """

    def __init__(
        self,
        unit_of_work: IUnitOfWork,
        cache_port: CachePort,
        threat_intel_port: ThreatIntelPort,
        llm_port: LLMPort,
        event_port: EventPort,
        asset_repository: Optional["IAssetRepository"] = None,  # type: ignore
    ) -> None:
        self.uow = unit_of_work
        self.cache = cache_port
        self.threat_intel = threat_intel_port
        self.llm = llm_port
        self.event = event_port
        self.asset_repo = asset_repository
        self.scoring_engine = ScoringEngine()

    async def execute(self, request: EvaluateFindingRequest) -> EvaluateFindingResponse:
        """Execute the use case."""
        logger.info(
            "Evaluating finding",
            tenant_id=str(request.tenant_id),
            asset_id=str(request.asset_id),
            source=request.source.value,
        )

        try:
            # 1. Normalize
            finding = Finding.create(
                tenant_id=request.tenant_id,
                asset_id=request.asset_id,
                source=request.source,
                source_finding_id=request.source_finding_id,
                title=request.title,
                description=request.description,
                raw_severity=request.raw_severity,
                raw_severity_scale=request.raw_severity_scale,
                detected_at=request.detected_at,
                raw_payload=request.raw_payload,
                cve_id=request.cve_id,
                status=request.status,
            )

            # 2. Business context
            business_context = await self._get_business_context(finding.asset_id, finding.tenant_id)
            if business_context is None:
                raise PipelineInterruptionError(
                    "Business context not found for asset",
                    stage="context_builder",
                    finding_id=str(finding.id),
                )

            # 3. Threat context
            threat_context = None
            if finding.has_cve and finding.cve_id:
                threat_context = await self._get_threat_context(finding.cve_id)

            # 4. Severity normalization
            vulnerability_severity = self._normalize_severity(
                finding.raw_severity,
                finding.raw_severity_scale,
            )

            # 5. Stale status
            is_stale = finding.is_stale(int(time.time()))

            # 6. Source count
            source_count = await self._get_source_count(finding)

            # 7. Score
            risk_score, drivers, confidence = self.scoring_engine.score_finding(
                business_context=business_context,
                threat_context=threat_context or ThreatContext.create(cve_id="") if threat_context else ThreatContext.create(cve_id=""),
                vulnerability_severity=vulnerability_severity,
                is_stale=is_stale,
                source_count=source_count,
                has_cmdb_record=True,
            )

            # 8. Tier
            tier = self.scoring_engine.get_tier(risk_score.final_bis)

            # 9. Recommendation
            recommendation_id = await self._generate_recommendation(
                finding_id=finding.id,
                tenant_id=finding.tenant_id,
                risk_score=risk_score,
                drivers=drivers,
                tier=tier,
                category=self._infer_category(finding),
            )

            # 10. AI summary
            summary_obj = await self._generate_summary(
                finding=finding,
                risk_score=risk_score,
                drivers=drivers,
                tier=tier,
                business_context=business_context,
                threat_context=threat_context,
            )

            # 11. Confidence breakdown
            confidence_breakdown = ConfidenceBreakdown(
                percentage=confidence.percentage,
                asset_owner_missing=confidence.breakdown["asset_owner_missing"],
                threat_intel_missing=confidence.breakdown["threat_intel_missing"],
                cmdb_missing=confidence.breakdown["cmdb_missing"],
                single_source=confidence.breakdown["single_source"],
                stale_scan=confidence.breakdown["stale_scan"],
                total_deductions=confidence.breakdown["total_deductions"],
                deduction_details=confidence.breakdown["deduction_details"],
            )

            # 12. Build explained drivers
            explained = drivers.to_explained_dict(business_context)
            drivers_response = DriversResponse(
                asset_importance=DriverExplanation(**explained["asset_importance"]),
                vulnerability_severity=DriverExplanation(**explained["vulnerability_severity"]),
                exploitability=DriverExplanation(**explained["exploitability"]),
                business_impact=DriverExplanation(**explained["business_impact"]),
                exposure=DriverExplanation(**explained["exposure"]),
            )

            # 13. Decision
            summary_str = str(summary_obj) if summary_obj else None
            decision = Decision.create(
                finding_id=finding.id,
                tenant_id=finding.tenant_id,
                risk_score=risk_score,
                tier=PriorityTier(tier),
                confidence=confidence,
                drivers=drivers,
                recommendation_id=recommendation_id,
                summary=summary_str,
                version="1.0.0",
            )

            # 14. Persist
            async with self.uow:
                await self.uow.finding_repository.save(finding)
                await self.uow.decision_repository.save(decision)
                await self.uow.commit()

            # 15. Events
            await self._publish_events(finding, decision)

            logger.info(
                "Finding evaluated successfully",
                finding_id=str(finding.id),
                tier=tier,
                bis=risk_score.final_bis,
            )

            # 16. Response
            return EvaluateFindingResponse(
                finding_id=finding.id,
                tenant_id=finding.tenant_id,
                bis=risk_score.final_bis,
                tier=PriorityTier(tier),
                confidence=confidence.value,
                confidence_breakdown=confidence_breakdown,
                drivers=drivers_response,
                recommendation_id=recommendation_id,
                summary=summary_obj,
                computed_at=decision.computed_at,
            )

        except Exception as exc:
            logger.error(
                "Failed to evaluate finding",
                error=str(exc),
                exc_info=True,
                tenant_id=str(request.tenant_id),
                asset_id=str(request.asset_id),
            )
            raise UseCaseError(
                f"Failed to evaluate finding: {str(exc)}",
                use_case="EvaluateFindingUseCase",
                cause=exc,
            )

    # -------------------------------------------------------------------------
    # Helper methods (all preserved)
    # -------------------------------------------------------------------------

    async def _get_business_context(self, asset_id: UUID, tenant_id: UUID) -> Optional[BusinessContext]:
        cache_key = f"business_context:{asset_id}"
        try:
            cached = await self.cache.get(cache_key)
            if cached:
                pass
        except Exception as exc:
            logger.warning("Cache failed for business context", key=cache_key, error=str(exc))

        if self.uow.asset_repository:
            return await self.uow.asset_repository.get_business_context(asset_id, tenant_id)
        return None

    async def _get_threat_context(self, cve_id: str) -> ThreatContext:
        cache_key = f"threat_context:{cve_id}"
        try:
            cached = await self.cache.get(cache_key)
            if cached:
                pass
        except Exception as exc:
            logger.warning("Cache failed for threat context", key=cache_key, error=str(exc))

        context = await self.threat_intel.get_threat_context(cve_id)
        if context:
            try:
                await self.cache.set(cache_key, context, ttl=86400)
            except Exception as exc:
                logger.warning("Failed to cache threat context", key=cache_key, error=str(exc))
        return context

    def _normalize_severity(self, raw_severity: float, scale: str) -> float:
        if scale in ("cvss_v3", "cvss_v4"):
            return min(100.0, raw_severity * 10.0)
        if scale == "qualitative":
            mapping = {"low": 25, "medium": 50, "high": 75, "critical": 95}
            return min(100.0, mapping.get(str(raw_severity).lower(), 50.0))
        return min(100.0, max(0.0, raw_severity))

    async def _get_source_count(self, finding: Finding) -> int:
        return 1

    async def _generate_recommendation(
        self,
        finding_id: UUID,
        tenant_id: UUID,
        risk_score: RiskScore,
        drivers: Drivers,
        tier: str,
        category: str,
    ) -> Optional[UUID]:
        return None

    def _infer_category(self, finding: Finding) -> str:
        return "vulnerability" if finding.has_cve else "general"

    async def _generate_summary(
        self,
        finding: Finding,
        risk_score: RiskScore,
        drivers: Drivers,
        tier: str,
        business_context: BusinessContext,
        threat_context: Optional[ThreatContext],
    ) -> Optional[StructuredSummary]:
        try:
            return await self.llm.generate_summary(
                finding=finding,
                risk_score=risk_score,
                drivers=drivers,
                tier=tier,
                business_context=business_context,
                threat_context=threat_context,
            )
        except Exception as exc:
            logger.warning(
                "AI summary generation failed, proceeding without summary",
                finding_id=str(finding.id),
                error=str(exc),
            )
            return None

    async def _publish_events(self, finding: Finding, decision: Decision) -> None:
        try:
            await self.event.publish("finding.scored", {
                "finding_id": str(finding.id),
                "tenant_id": str(finding.tenant_id),
                "tier": decision.tier.value,
                "bis": decision.bis,
                "computed_at": decision.computed_at,
            })
        except Exception as exc:
            logger.warning("Failed to publish event", error=str(exc))