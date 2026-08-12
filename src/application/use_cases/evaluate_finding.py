"""Use case for evaluating a finding through the scoring pipeline."""

import time
from typing import Optional
from uuid import UUID, uuid4

from src.application.dto import EvaluateFindingRequest, EvaluateFindingResponse
from src.application.ports import CachePort, EventPort, LLMPort, ThreatIntelPort
from src.core.config.settings import get_settings
from src.core.constants.enums import PriorityTier
from src.core.exceptions.application import PipelineInterruptionError, UseCaseError
from src.core.logging.logger import get_logger
from src.domain.entities import Decision, Finding
from src.domain.repositories import IUnitOfWork
from src.domain.services import ScoringEngine
from src.domain.value_objects import BusinessContext, Confidence, Drivers, RiskScore, ThreatContext
from src.domain.value_objects.priority import PriorityMapping
from src.interfaces.schemas.response import (
    ConfidenceBreakdown,
    DecisionObject,
    DriverExplanation,
    DriversResponse,
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

    async def execute(
        self,
        request: EvaluateFindingRequest,
        request_id: Optional[str] = None,
    ) -> DecisionObject:
        """Execute the use case.

        Args:
            request: Evaluation request.
            request_id: Optional request ID for tracing.

        Returns:
            DecisionObject: Unified decision response.

        Raises:
            UseCaseError: If any step fails.
        """
        start_time = time.perf_counter()

        logger.info(
            "Evaluating finding",
            tenant_id=str(request.tenant_id),
            asset_id=str(request.asset_id),
            source=request.source.value,
            request_id=request_id,
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

            # 9. Recommendation (placeholder)
            recommendation_id = await self._generate_recommendation(
                finding_id=finding.id,
                tenant_id=finding.tenant_id,
                risk_score=risk_score,
                drivers=drivers,
                tier=tier,
                category=self._infer_category(finding),
            )

            # 10. AI summary (non-blocking)
            summary_obj = await self._generate_summary(
                finding=finding,
                risk_score=risk_score,
                drivers=drivers,
                tier=tier,
                business_context=business_context,
                threat_context=threat_context,
            )

            # 11. Build detailed confidence breakdown
            detailed_breakdown = confidence.to_detailed_breakdown()
            confidence_breakdown = ConfidenceBreakdown(
                overall_confidence=confidence.percentage,
                categories=detailed_breakdown["categories"],
                factors=detailed_breakdown["factors"],
                deductions=detailed_breakdown["deductions"],
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

            # 13. Get decision metadata from tier
            tier_enum = PriorityTier(tier)
            decision_text = PriorityMapping.get_decision(tier_enum)
            priority_level = PriorityMapping.get_priority(tier_enum)
            due_hours = PriorityMapping.get_due_hours(tier_enum)

            # 14. Compute expected risk reduction
            expected_risk_reduction = int(round(drivers.exploitability * 0.5 + 10))

            # 15. Estimate fix time
            if due_hours <= 4:
                estimated_fix_time = f"{due_hours} hours"
            elif due_hours <= 24:
                estimated_fix_time = f"{due_hours} hours"
            else:
                days = due_hours // 24
                estimated_fix_time = f"{days} days"

            # 16. Business owner
            business_owner = "Unassigned"
            if business_context and business_context.owner_id:
                # In future, fetch name from user repository
                business_owner = "Assigned Owner"

            # 17. Build reason (combine driver explanations)
            reason_parts = [
                drivers_response.asset_importance.explanation,
                drivers_response.vulnerability_severity.explanation,
                drivers_response.exploitability.explanation,
                drivers_response.business_impact.explanation,
                drivers_response.exposure.explanation,
            ]
            reason = " ".join(reason_parts)

            # 18. Next action (from summary or fallback)
            next_action = summary_obj.immediate_recommendation if summary_obj else "Review and remediate"

            # 19. Build decision aggregate
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

            # 20. Persist
            async with self.uow:
                await self.uow.finding_repository.save(finding)
                await self.uow.decision_repository.save(decision)
                await self.uow.commit()

            # 21. Publish events
            await self._publish_events(finding, decision)

            # 22. Build DecisionObject
            decision_id = uuid4()
            decision_timestamp = int(time.time())
            processing_time_ms = (time.perf_counter() - start_time) * 1000
            settings = get_settings()
            engine_version = settings.app_version
            model_version = settings.groq_model

            decision_object = DecisionObject(
                decision_id=decision_id,
                finding_id=finding.id,
                tenant_id=finding.tenant_id,
                decision=decision_text,
                priority=priority_level,
                risk_score=int(round(risk_score.final_bis)),
                tier=tier,
                confidence=confidence.percentage,
                confidence_breakdown=confidence_breakdown,
                expected_risk_reduction=expected_risk_reduction,
                estimated_fix_time=estimated_fix_time,
                business_owner=business_owner,
                next_action=next_action,
                reason=reason,
                drivers=drivers_response,
                summary=summary_obj,
                computed_at=decision_timestamp,
                engine_version=engine_version,
                model_version=model_version,
                prompt_version=None,
                knowledge_base_version=None,
            )

            logger.info(
                "Finding evaluated successfully",
                finding_id=str(finding.id),
                tier=tier,
                risk_score=int(round(risk_score.final_bis)),
                decision_id=str(decision_id),
                processing_time_ms=round(processing_time_ms, 2),
            )

            return decision_object

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
            summary = await self.llm.generate_summary(
                finding=finding,
                risk_score=risk_score,
                drivers=drivers,
                tier=tier,
                business_context=business_context,
                threat_context=threat_context,
            )
            return summary
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