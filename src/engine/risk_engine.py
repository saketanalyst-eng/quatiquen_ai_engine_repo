"""Risk engine that calculates raw BIS using the domain scoring service."""

from src.core.logging.logger import get_logger
from src.domain.services import ScoringEngine
from src.engine.engine_result import EngineResult, PipelineStage
from src.engine.strategies.base_strategy import Strategy
from src.engine.strategies.default_strategy import DefaultStrategy

logger = get_logger("quantiquan.engine.risk_engine")


class RiskEngine:
    """Calculates raw BIS using the domain scoring engine and a strategy."""

    def __init__(self, strategy: Strategy) -> None:
        """Initialize risk engine.

        Args:
            strategy: Strategy for scoring (e.g., weight overrides).
        """
        self.strategy = strategy or DefaultStrategy()
        self.scoring_engine = ScoringEngine()

    def execute(self, result: EngineResult) -> bool:
        """Calculate raw BIS.

        Args:
            result: Engine result state.

        Returns:
            bool: True if successful.
        """
        finding = result.finding
        business_context = result.business_context
        threat_context = result.threat_context
        vulnerability_severity = result.vulnerability_severity

        if any(v is None for v in [finding, business_context, threat_context, vulnerability_severity]):
            result.add_error(PipelineStage.RISK_ENGINE, "Missing required context for scoring")
            return False

        try:
            # Get driver scores from context
            asset_importance = business_context.asset_importance_score
            exploitability = threat_context.exploitability_score
            business_impact = business_context.business_impact_score
            exposure = business_context.exposure_score

            # Apply strategy to modify scores if needed
            if self.strategy:
                asset_importance, vulnerability_severity, exploitability, business_impact, exposure = (
                    self.strategy.modify_scores(
                        asset_importance=asset_importance,
                        vulnerability_severity=vulnerability_severity,
                        exploitability=exploitability,
                        business_impact=business_impact,
                        exposure=exposure,
                    )
                )

            # Calculate raw BIS using domain scoring engine
            raw_bis = self.scoring_engine.calculate_raw_bis(
                asset_importance=asset_importance,
                vulnerability_severity=vulnerability_severity,
                exploitability=exploitability,
                business_impact=business_impact,
                exposure=exposure,
            )

            result.raw_bis = raw_bis

            # Build drivers
            drivers = self.scoring_engine.compute_drivers(
                asset_importance=asset_importance,
                vulnerability_severity=vulnerability_severity,
                exploitability=exploitability,
                business_impact=business_impact,
                exposure=exposure,
            )
            result.drivers = drivers

            logger.debug(
                "Raw BIS calculated",
                finding_id=str(finding.id),
                raw_bis=raw_bis,
                drivers=drivers.to_dict(),
            )

            return True

        except Exception as exc:
            result.add_error(PipelineStage.RISK_ENGINE, str(exc))
            logger.error(
                "Risk engine failed",
                finding_id=str(finding.id),
                error=str(exc),
                exc_info=True,
            )
            return False