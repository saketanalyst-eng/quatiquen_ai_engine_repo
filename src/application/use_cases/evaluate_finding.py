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
from src.domain.repositories import IDecisionRepository, IFindingRepository, IUnitOfWork
from src.domain.services import ScoringEngine
from src.domain.value_objects import BusinessContext, Confidence, Drivers, RiskScore, ThreatContext

logger = get_logger("quantiquan.application.evaluate_finding")


class EvaluateFindingUseCase:
    """Use case to evaluate a new finding through the scoring pipeline.

    This orchestrates normalization, context fetching, scoring, recommendation,
    AI summary generation, and persistence.
    """

    def __init__(
        self,
        finding_repository: IFindingRepository,
        decision_repository: IDecisionRepository,
        unit_of_work: IUnitOfWork,
        cache_port: CachePort,
        threat_intel_port: ThreatIntelPort,
        llm_port: LLMPort,
        event_port: EventPort,
        asset_repository: Optional["IAssetRepository"] = None,  # type: ignore
    ) -> None:
        """Initialize use case.

        Args:
            finding_repository: Finding repository.
            decision_repository: Decision repository.
            unit_of_work: Unit of work for transactions.
            cache_port: Cache port.
            threat_intel_port: Threat intelligence port.
            llm_port: LLM port.
            event_port: Event port.
            asset_repository: Asset repository (optional, if not provided will use finding's asset).
        """
        self.finding_repo = finding_repository
        self.decision_repo = decision_repository
        self.uow = unit_of_work
        self.cache = cache_port
        self.threat_intel = threat_intel_port
        self.llm = llm_port
        self.event = event_port
        self.asset_repo = asset_repository
        self.scoring_engine = ScoringEngine()

    async def execute(self, request: EvaluateFindingRequest) -> EvaluateFindingResponse:
        """Execute the use case.

        Args:
            request: Evaluation request.

        Returns:
            EvaluateFindingResponse: Result of evaluation.

        Raises:
            UseCaseError: If any step fails.
        """
        logger.info(
            "Evaluating finding",
            tenant_id=str(request.tenant_id),
            asset_id=str(request.asset_id),
            source=request.source.value,
        )

        try:
            # 1. Normalize: create finding entity
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

            # 2. Fetch business context
            business_context = await self._get_business_context(finding.asset_id, finding.tenant_id)
            if business_context is None:
                raise PipelineInterruptionError(
                    "Business context not found for asset",
                    stage="context_builder",
                    finding_id=str(finding.id),
                )

            # 3. Fetch threat context (if CVE exists)
            threat_context = None
            if finding.has_cve and finding.cve_id:
                threat_context = await self._get_threat_context(finding.cve_id)

            # 4. Normalize vulnerability severity
            vulnerability_severity = self._normalize_severity(
                finding.raw_severity,
                finding.raw_severity_scale,
            )

            # 5. Determine stale status
            is_stale = finding.is_stale(int(time.time()))

            # 6. Get source count (for confidence)
            source_count = await self._get_source_count(finding)

            # 7. Score the finding
            risk_score, drivers, confidence = self.scoring_engine.score_finding(
                business_context=business_context,
                threat_context=threat_context or ThreatContext.create(cve_id="") if threat_context else ThreatContext.create(cve_id=""),
                vulnerability_severity=vulnerability_severity,
                is_stale=is_stale,
                source_count=source_count,
                has_cmdb_record=True,  # Assume CMDB exists; could be derived from asset repository
            )

            # 8. Determine tier
            tier = self.scoring_engine.get_tier(risk_score.final_bis)

            # 9. Generate recommendation
            recommendation_id = await self._generate_recommendation(
                finding_id=finding.id,
                tenant_id=finding.tenant_id,
                risk_score=risk_score,
                drivers=drivers,
                tier=tier,
                category=self._infer_category(finding),
            )

            # 10. Generate AI summary (non-blocking, may be None)
            summary = await self._generate_summary(
                finding=finding,
                risk_score=risk_score,
                drivers=drivers,
                tier=tier,
                business_context=business_context,
                threat_context=threat_context,
            )

            # 11. Build decision aggregate
            decision = Decision.create(
                finding_id=finding.id,
                tenant_id=finding.tenant_id,
                risk_score=risk_score,
                tier=PriorityTier(tier),
                confidence=confidence,
                drivers=drivers,
                recommendation_id=recommendation_id,
                summary=summary,
                version="1.0.0",
            )

            # 12. Persist in transaction
            async with self.uow:
                await self.finding_repo.save(finding)
                await self.decision_repo.save(decision)
                await self.uow.commit()

            # 13. Publish events
            await self._publish_events(finding, decision)

            logger.info(
                "Finding evaluated successfully",
                finding_id=str(finding.id),
                tier=tier,
                bis=risk_score.final_bis,
            )

            return EvaluateFindingResponse(
                finding_id=finding.id,
                tenant_id=finding.tenant_id,
                bis=risk_score.final_bis,
                tier=PriorityTier(tier),
                confidence=confidence.value,
                drivers=drivers.to_dict(),
                recommendation_id=recommendation_id,
                summary=summary,
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

    async def _get_business_context(self, asset_id: UUID, tenant_id: UUID) -> Optional[BusinessContext]:
        """Get business context for asset from cache or repository."""
        cache_key = f"business_context:{asset_id}"
        try:
            cached = await self.cache.get(cache_key)
            if cached:
                # In a real implementation, deserialize from cache
                # For simplicity, we assume cache stores BusinessContext object
                # but we would need serialization. Here we'll just fetch from repo.
                pass
        except Exception as exc:
            logger.warning("Cache failed for business context", key=cache_key, error=str(exc))

        # Fetch from repository (would use asset repository)
        if self.asset_repo:
            return await self.asset_repo.get_business_context(asset_id, tenant_id)
        return None

    async def _get_threat_context(self, cve_id: str) -> ThreatContext:
        """Get threat context for CVE from cache or external source."""
        cache_key = f"threat_context:{cve_id}"
        try:
            cached = await self.cache.get(cache_key)
            if cached:
                # Deserialize and return
                pass
        except Exception as exc:
            logger.warning("Cache failed for threat context", key=cache_key, error=str(exc))

        # Fetch from threat intel port
        context = await self.threat_intel.get_threat_context(cve_id)
        if context:
            try:
                await self.cache.set(cache_key, context, ttl=86400)  # 24h
            except Exception as exc:
                logger.warning("Failed to cache threat context", key=cache_key, error=str(exc))
        return context

    def _normalize_severity(self, raw_severity: float, scale: str) -> float:
        """Normalize raw severity to 0-100 scale."""
        if scale == "cvss_v3" or scale == "cvss_v4":
            # CVSS is 0-10, multiply by 10
            return min(100.0, raw_severity * 10.0)
        if scale == "qualitative":
            # Qualitative mapping: Low=25, Medium=50, High=75, Critical=95
            mapping = {"low": 25, "medium": 50, "high": 75, "critical": 95}
            normalized = mapping.get(str(raw_severity).lower(), 50.0)
            return min(100.0, normalized)
        # vendor_custom or unknown: clamp to 0-100
        return min(100.0, max(0.0, raw_severity))

    async def _get_source_count(self, finding: Finding) -> int:
        """Get number of sources reporting this finding."""
        # In reality, we would query other findings with same source_finding_id or asset
        # For now, return 1
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
        """Generate recommendation for the finding.

        Placeholder: In production, would use knowledge base.
        """
        # For now, return None (no recommendation)
        return None

    def _infer_category(self, finding: Finding) -> str:
        """Infer category from finding title/description."""
        # Simple heuristic: if CVE exists, category = "vulnerability"
        if finding.has_cve:
            return "vulnerability"
        return "general"

    async def _generate_summary(
        self,
        finding: Finding,
        risk_score: RiskScore,
        drivers: Drivers,
        tier: str,
        business_context: BusinessContext,
        threat_context: Optional[ThreatContext],
    ) -> Optional[str]:
        """Generate AI summary (non-blocking)."""
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
        """Publish events after scoring."""
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