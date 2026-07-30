"""Pipeline workflow definition with conditional execution."""

import time
from typing import Optional

from src.application.ports import CachePort, EventPort, LLMPort, ThreatIntelPort
from src.core.logging.logger import get_logger
from src.domain.entities import Finding
from src.domain.repositories import IAssetRepository
from src.engine.config import EngineConfig
from src.engine.context_builder import ContextBuilder
from src.engine.decision_mapper import DecisionMapper
from src.engine.engine_result import EngineResult, PipelineStage
from src.engine.priority_engine import PriorityEngine
from src.engine.recommendation_engine import RecommendationEngine
from src.engine.risk_engine import RiskEngine
from src.engine.rules_engine import RulesEngine
from src.engine.score_normalizer import ScoreNormalizer
from src.engine.strategies.base_strategy import Strategy
from src.engine.summary_engine import SummaryEngine
from src.engine.validation_engine import ValidationEngine

logger = get_logger("quantiquan.engine.workflow")


class Workflow:
    """Defines and executes the scoring pipeline steps.

    Steps are executed in order with conditional skips based on config.
    """

    def __init__(
        self,
        cache_port: CachePort,
        threat_intel_port: ThreatIntelPort,
        llm_port: LLMPort,
        asset_repository: IAssetRepository,
        config: EngineConfig,
        strategy: Strategy,
        event_port: Optional[EventPort] = None,
    ) -> None:
        """Initialize workflow.

        Args:
            cache_port: Cache port.
            threat_intel_port: Threat intel port.
            llm_port: LLM port.
            asset_repository: Asset repository.
            config: Engine configuration.
            strategy: Scoring strategy.
            event_port: Event port (optional).
        """
        self.cache_port = cache_port
        self.threat_intel_port = threat_intel_port
        self.llm_port = llm_port
        self.asset_repository = asset_repository
        self.config = config
        self.strategy = strategy
        self.event_port = event_port
        self.logger = logger.bind(component="workflow")

        # Initialize engines
        self.validation_engine = ValidationEngine()
        self.context_builder = ContextBuilder(
            cache_port=cache_port,
            threat_intel_port=threat_intel_port,
            asset_repository=asset_repository,
            config=config,
        )
        self.score_normalizer = ScoreNormalizer()
        self.risk_engine = RiskEngine(strategy=strategy)
        self.rules_engine = RulesEngine(config=config)
        self.recommendation_engine = RecommendationEngine(config=config)
        self.summary_engine = SummaryEngine(llm_port=llm_port, config=config)
        self.decision_mapper = DecisionMapper()
        self.priority_engine = PriorityEngine()

    async def execute(self, finding: Finding) -> EngineResult:
        """Execute the full pipeline.

        Args:
            finding: Finding to process.

        Returns:
            EngineResult: Pipeline result.
        """
        result = EngineResult(finding=finding)
        start_time = time.perf_counter()

        try:
            # Step 1: Validation
            result.set_stage(PipelineStage.VALIDATION)
            if not await self.validation_engine.execute(result):
                return result

            # Step 2: Context Builder
            result.set_stage(PipelineStage.CONTEXT_BUILDER)
            if not await self.context_builder.execute(result):
                return result

            # Step 3: Score Normalizer
            result.set_stage(PipelineStage.SCORE_NORMALIZER)
            if not self.score_normalizer.execute(result):
                return result

            # Step 4: Risk Engine
            result.set_stage(PipelineStage.RISK_ENGINE)
            if not self.risk_engine.execute(result):
                return result

            # Step 5: Priority Engine (determines tier from risk_score)
            result.set_stage(PipelineStage.PRIORITY_ENGINE)
            if not self.priority_engine.execute(result):
                return result

            # Step 6: Rules Engine (applies overrides)
            result.set_stage(PipelineStage.RULES_ENGINE)
            if not self.rules_engine.execute(result):
                return result

            # Step 7: Recommendation Engine
            result.set_stage(PipelineStage.RECOMMENDATION_ENGINE)
            if self.config.enable_recommendation:
                await self.recommendation_engine.execute(result)
            else:
                self.logger.debug("Recommendation engine disabled")

            # Step 8: Summary Engine (conditional)
            result.set_stage(PipelineStage.SUMMARY_ENGINE)
            if self._should_run_summary(result):
                await self.summary_engine.execute(result)
            else:
                self.logger.debug("Summary engine skipped (conditional)")

            # Step 9: Decision Mapper (build final decision)
            result.set_stage(PipelineStage.DECISION_MAPPER)
            self.decision_mapper.execute(result)

            # Mark complete
            result.complete()

            # Publish event if successful
            if result.decision and self.event_port:
                await self.event_port.publish(
                    "finding.scored",
                    {
                        "finding_id": str(result.finding.id),
                        "tenant_id": str(result.finding.tenant_id),
                        "tier": result.tier,
                        "bis": result.risk_score.final_bis if result.risk_score else None,
                        "computed_at": result.decision.computed_at if result.decision else int(time.time()),
                    },
                )

        except Exception as exc:
            self.logger.error(
                "Pipeline execution failed",
                error=str(exc),
                exc_info=True,
                finding_id=str(finding.id),
            )
            result.add_error(result.current_stage, str(exc))

        duration = time.perf_counter() - start_time
        result.set_metric("total_duration", duration)
        self.logger.info(
            "Pipeline execution completed",
            finding_id=str(finding.id),
            duration_ms=duration * 1000,
            has_errors=result.has_error(),
            stages=len(result.errors),
        )

        return result

    def _should_run_summary(self, result: EngineResult) -> bool:
        """Determine if summary engine should run.

        Conditions:
        - AI summary enabled
        - Not skipped due to low confidence
        - Not skipped due to missing CVE (if configured)
        - No critical errors in earlier stages
        """
        if not self.config.enable_ai_summary:
            return False

        if result.has_error():
            return False

        # Skip if low confidence and configured to do so
        if self.config.skip_summary_on_low_confidence and result.confidence:
            if result.confidence.value < self.config.low_confidence_threshold:
                self.logger.debug(
                    "Skipping summary: low confidence",
                    confidence=result.confidence.value,
                )
                return False

        # Skip if no CVE and configured to do so
        if self.config.skip_summary_if_no_cve and result.finding:
            if not result.finding.has_cve:
                self.logger.debug("Skipping summary: no CVE")
                return False

        return True