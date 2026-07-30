"""Validation engine for checking finding integrity."""

from src.core.exceptions.domain import ValidationError
from src.core.logging.logger import get_logger
from src.engine.engine_result import EngineResult, PipelineStage

logger = get_logger("quantiquan.engine.validation")


class ValidationEngine:
    """Validates that the finding meets required criteria."""

    async def execute(self, result: EngineResult) -> bool:
        """Execute validation.

        Args:
            result: Engine result state.

        Returns:
            bool: True if validation passes, False otherwise.
        """
        finding = result.finding
        if finding is None:
            result.add_error(PipelineStage.VALIDATION, "Finding is None")
            return False

        try:
            # Basic validation (finding entity already validates in constructor)
            # Additional checks
            if not finding.title:
                raise ValidationError("Finding title is empty", field="title")
            if not finding.description:
                raise ValidationError("Finding description is empty", field="description")
            if finding.raw_severity < 0 or finding.raw_severity > 100:
                raise ValidationError(
                    f"Raw severity out of range: {finding.raw_severity}",
                    field="raw_severity",
                    value=finding.raw_severity,
                )
            if finding.detected_at <= 0:
                raise ValidationError(
                    "Detected at must be positive",
                    field="detected_at",
                    value=finding.detected_at,
                )

            logger.debug("Validation passed", finding_id=str(finding.id))
            return True

        except ValidationError as exc:
            result.add_error(PipelineStage.VALIDATION, str(exc))
            logger.warning("Validation failed", finding_id=str(finding.id), error=str(exc))
            return False
        except Exception as exc:
            result.add_error(PipelineStage.VALIDATION, f"Unexpected error: {str(exc)}")
            logger.error("Validation error", finding_id=str(finding.id), error=str(exc), exc_info=True)
            return False