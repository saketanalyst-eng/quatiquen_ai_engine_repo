"""Decision mapper builds final Decision aggregate from pipeline state."""

from src.core.constants.enums import PriorityTier
from src.core.logging.logger import get_logger
from src.domain.entities import Decision
from src.domain.value_objects import RiskScore
from src.engine.engine_result import EngineResult, PipelineStage

logger = get_logger("quantiquan.engine.decision_mapper")


class DecisionMapper:
    """Maps pipeline result to a Decision aggregate."""

    def execute(self, result: EngineResult) -> None:
        """Build and store Decision in result.

        Args:
            result: Engine result state.

        Returns:
            None: Decision is added to result.
        """
        finding = result.finding
        risk_score = result.risk_score
        drivers = result.drivers
        confidence = result.confidence
        tier = result.tier
        recommendation_id = result.recommendation_id
        summary = result.summary

        if any(v is None for v in [finding, risk_score, drivers, confidence, tier]):
            result.add_error(PipelineStage.DECISION_MAPPER, "Missing required data for decision")
            return

        try:
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

            result.decision = decision

            logger.debug(
                "Decision created",
                finding_id=str(finding.id),
                tier=tier,
                bis=risk_score.final_bis,
            )

        except Exception as exc:
            result.add_error(PipelineStage.DECISION_MAPPER, str(exc))
            logger.error(
                "Decision mapping failed",
                finding_id=str(finding.id),
                error=str(exc),
                exc_info=True,
            )