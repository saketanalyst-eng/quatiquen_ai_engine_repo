"""Normalizes raw severity scores to 0-100 scale."""

from src.core.logging.logger import get_logger
from src.engine.engine_result import EngineResult, PipelineStage

logger = get_logger("quantiquan.engine.score_normalizer")


class ScoreNormalizer:
    """Normalizes vulnerability severity scores to a 0-100 scale."""

    def execute(self, result: EngineResult) -> bool:
        """Normalize severity and store in result.

        Args:
            result: Engine result state.

        Returns:
            bool: True if successful.
        """
        finding = result.finding
        if finding is None:
            result.add_error(PipelineStage.SCORE_NORMALIZER, "Finding is None")
            return False

        try:
            raw_severity = finding.raw_severity
            scale = finding.raw_severity_scale

            normalized = self._normalize(raw_severity, scale)
            result.vulnerability_severity = normalized

            logger.debug(
                "Severity normalized",
                finding_id=str(finding.id),
                raw=raw_severity,
                scale=scale,
                normalized=normalized,
            )

            return True

        except Exception as exc:
            result.add_error(PipelineStage.SCORE_NORMALIZER, str(exc))
            logger.error(
                "Score normalization failed",
                finding_id=str(finding.id),
                error=str(exc),
                exc_info=True,
            )
            return False

    def _normalize(self, raw_severity: float, scale: str) -> float:
        """Normalize severity to 0-100.

        Args:
            raw_severity: Raw severity value.
            scale: Scale identifier.

        Returns:
            float: Normalized score (0-100).
        """
        if scale in ("cvss_v3", "cvss_v4"):
            # CVSS is 0-10, multiply by 10, cap at 100
            return min(100.0, max(0.0, raw_severity * 10.0))
        if scale == "qualitative":
            mapping = {
                "low": 25.0,
                "medium": 50.0,
                "high": 75.0,
                "critical": 95.0,
            }
            return min(100.0, mapping.get(str(raw_severity).lower(), 50.0))
        # vendor_custom or unknown: assume already 0-100, clamp
        return min(100.0, max(0.0, raw_severity))