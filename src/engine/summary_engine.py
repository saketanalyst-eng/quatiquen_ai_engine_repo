"""Summary engine generates AI explanation."""

from typing import Optional

from src.application.ports import LLMPort
from src.core.logging.logger import get_logger
from src.engine.config import EngineConfig
from src.engine.engine_result import EngineResult, PipelineStage

logger = get_logger("quantiquan.engine.summary_engine")


class SummaryEngine:
    """Generates AI summary for the decision."""

    def __init__(self, llm_port: LLMPort, config: EngineConfig) -> None:
        """Initialize summary engine.

        Args:
            llm_port: LLM port for generating summaries.
            config: Engine configuration.
        """
        self.llm_port = llm_port
        self.config = config

    async def execute(self, result: EngineResult) -> None:
        """Generate summary.

        Args:
            result: Engine result state.

        Returns:
            None: Summary is added to result.
        """
        if not self.config.enable_ai_summary:
            return

        finding = result.finding
        risk_score = result.risk_score
        drivers = result.drivers
        tier = result.tier
        business_context = result.business_context
        threat_context = result.threat_context

        if any(v is None for v in [finding, risk_score, drivers, tier, business_context]):
            logger.warning("Cannot generate summary: missing data")
            return

        try:
            summary = await self.llm_port.generate_summary(
                finding=finding,
                risk_score=risk_score,
                drivers=drivers,
                tier=tier,
                business_context=business_context,
                threat_context=threat_context,
            )
            result.summary = summary

            logger.debug(
                "Summary generated",
                finding_id=str(finding.id),
                has_summary=bool(summary),
            )

        except Exception as exc:
            logger.error(
                "Summary generation failed",
                finding_id=str(finding.id),
                error=str(exc),
                exc_info=True,
            )
            # Non-fatal: continue without summary