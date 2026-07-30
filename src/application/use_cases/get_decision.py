"""Use case for retrieving an existing decision."""

from src.application.dto import GetDecisionRequest, GetDecisionResponse
from src.core.constants.enums import PriorityTier
from src.core.exceptions.application import UseCaseError
from src.core.exceptions.domain import EntityNotFoundError
from src.core.logging.logger import get_logger
from src.domain.entities import Decision
from src.domain.repositories import IDecisionRepository

logger = get_logger("quantiquan.application.get_decision")


class GetDecisionUseCase:
    """Use case to retrieve a decision by finding ID."""

    def __init__(self, decision_repository: IDecisionRepository) -> None:
        """Initialize use case.

        Args:
            decision_repository: Decision repository.
        """
        self.decision_repo = decision_repository

    async def execute(self, request: GetDecisionRequest) -> GetDecisionResponse:
        """Execute the use case.

        Args:
            request: Get decision request.

        Returns:
            GetDecisionResponse: Decision data.

        Raises:
            EntityNotFoundError: If decision not found.
            UseCaseError: If any other error occurs.
        """
        logger.info(
            "Retrieving decision",
            finding_id=str(request.finding_id),
            tenant_id=str(request.tenant_id),
        )

        try:
            decision = await self.decision_repo.get_by_finding_id(
                request.finding_id,
                request.tenant_id,
            )
            if decision is None:
                raise EntityNotFoundError("Decision", str(request.finding_id))

            return GetDecisionResponse(
                finding_id=decision.finding_id,
                tenant_id=decision.tenant_id,
                bis=decision.bis,
                tier=decision.tier,
                confidence=decision.confidence.value,
                drivers=decision.drivers.to_dict(),
                recommendation_id=decision.recommendation_id,
                summary=decision.summary,
                computed_at=decision.computed_at,
                version=decision.version,
                history_available=False,  # Would need history repository
                low_confidence=decision.confidence.is_low,
            )

        except EntityNotFoundError:
            raise
        except Exception as exc:
            logger.error(
                "Failed to retrieve decision",
                finding_id=str(request.finding_id),
                error=str(exc),
                exc_info=True,
            )
            raise UseCaseError(
                f"Failed to retrieve decision: {str(exc)}",
                use_case="GetDecisionUseCase",
                cause=exc,
            )