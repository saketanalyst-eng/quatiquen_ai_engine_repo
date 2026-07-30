"""Priority engine determines the tier from final BIS."""

from src.core.logging.logger import get_logger
from src.domain.services import ScoringEngine
from src.engine.engine_result import EngineResult, PipelineStage

logger = get_logger("quantiquan.engine.priority_engine")


class PriorityEngine:
    """Determines priority tier from risk score."""

    def __init__(self) -> None:
        """Initialize priority engine."""
        self.scoring_engine = ScoringEngine()

    def execute(self, result: EngineResult) -> bool:
        """Determine tier.

        Args:
            result: Engine result state.

        Returns:
            bool: True if successful.
        """
        risk_score = result.risk_score
        if risk_score is None:
            result.add_error(PipelineStage.PRIORITY_ENGINE, "Risk score is None")
            return False

        try:
            tier = self.scoring_engine.get_tier(risk_score.final_bis)
            result.tier = tier

            logger.debug(
                "Priority determined",
                finding_id=str(result.finding.id if result.finding else None),
                tier=tier,
                final_bis=risk_score.final_bis,
            )

            return True

        except Exception as exc:
            result.add_error(PipelineStage.PRIORITY_ENGINE, str(exc))
            logger.error(
                "Priority engine failed",
                error=str(exc),
                exc_info=True,
            )
            return False