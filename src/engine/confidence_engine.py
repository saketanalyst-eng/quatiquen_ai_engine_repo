"""Confidence engine calculates confidence based on data completeness."""

import time

from src.core.logging.logger import get_logger
from src.domain.services import ScoringEngine
from src.engine.engine_result import EngineResult, PipelineStage

logger = get_logger("quantiquan.engine.confidence_engine")


class ConfidenceEngine:
    """Calculates confidence score using the domain scoring engine."""

    def __init__(self) -> None:
        """Initialize confidence engine."""
        self.scoring_engine = ScoringEngine()

    def execute(self, result: EngineResult) -> bool:
        """Calculate confidence.

        Args:
            result: Engine result state.

        Returns:
            bool: True if successful.
        """
        finding = result.finding
        business_context = result.business_context

        if any(v is None for v in [finding, business_context]):
            result.add_error(PipelineStage.CONFIDENCE_ENGINE, "Missing required data for confidence")
            return False

        try:
            # Determine factors
            has_owner = business_context.has_owner
            is_stale = finding.is_stale(int(time.time()))
            # Threat intel may not exist; check if we have it
            has_threat_intel = result.threat_context is not None and result.threat_context.is_exploitable
            # Assume CMDB record exists (would be inferred from asset repo)
            has_cmdb_record = True
            source_count = 1  # Placeholder

            # Calculate confidence
            confidence = self.scoring_engine.calculate_confidence(
                has_owner=has_owner,
                is_stale=is_stale,
                has_threat_intel=has_threat_intel,
                has_cmdb_record=has_cmdb_record,
                source_count=source_count,
            )

            result.confidence = confidence

            # Apply confidence to raw BIS to get final risk score
            if result.raw_bis is not None:
                risk_score = self.scoring_engine.apply_confidence_multiplier(
                    result.raw_bis,
                    confidence,
                )
                result.risk_score = risk_score
            else:
                result.add_error(PipelineStage.CONFIDENCE_ENGINE, "Raw BIS not available for confidence application")

            logger.debug(
                "Confidence calculated",
                finding_id=str(finding.id),
                confidence=confidence.value,
                multiplier=confidence.multiplier,
                deductions=[d[0] for d in confidence.deductions],
            )

            return True

        except Exception as exc:
            result.add_error(PipelineStage.CONFIDENCE_ENGINE, str(exc))
            logger.error(
                "Confidence engine failed",
                finding_id=str(finding.id),
                error=str(exc),
                exc_info=True,
            )
            return False