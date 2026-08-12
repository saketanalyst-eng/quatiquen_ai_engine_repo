"""Use case for retrieving an existing decision."""

from uuid import uuid4

from src.application.dto import GetDecisionRequest, GetDecisionResponse
from src.core.config.settings import get_settings
from src.core.constants.enums import PriorityTier
from src.core.exceptions.application import UseCaseError
from src.core.exceptions.domain import EntityNotFoundError
from src.core.logging.logger import get_logger
from src.domain.repositories import IUnitOfWork
from src.domain.value_objects.priority import PriorityMapping
from src.interfaces.schemas.response import (
    ConfidenceBreakdown,
    DecisionObject,
    DriverExplanation,
    DriversResponse,
)

logger = get_logger("quantiquan.application.get_decision")


class GetDecisionUseCase:
    """Use case to retrieve a decision by finding ID."""

    def __init__(self, unit_of_work: IUnitOfWork) -> None:
        self.uow = unit_of_work

    async def execute(self, request: GetDecisionRequest) -> DecisionObject:
        """Execute the use case.

        Args:
            request: Get decision request.

        Returns:
            DecisionObject: Unified decision response.

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
            decision = await self.uow.decision_repository.get_by_finding_id(
                request.finding_id,
                request.tenant_id,
            )
            if decision is None:
                raise EntityNotFoundError("Decision", str(request.finding_id))

            # Reconstruct from stored data
            tier_enum = PriorityTier(decision.tier)
            decision_text = PriorityMapping.get_decision(tier_enum)
            priority_level = PriorityMapping.get_priority(tier_enum)
            due_hours = PriorityMapping.get_due_hours(tier_enum)

            # Confidence breakdown (reconstruct from stored confidence)
            detailed = decision.confidence.to_detailed_breakdown()
            confidence_breakdown = ConfidenceBreakdown(
                overall_confidence=decision.confidence.percentage,
                categories=detailed["categories"],
                factors=detailed["factors"],
                deductions=detailed["deductions"],
            )

            # Reconstruct drivers with explanations
            explained = decision.drivers.to_explained_dict(business_context=None)
            drivers_response = DriversResponse(
                asset_importance=DriverExplanation(**explained["asset_importance"]),
                vulnerability_severity=DriverExplanation(**explained["vulnerability_severity"]),
                exploitability=DriverExplanation(**explained["exploitability"]),
                business_impact=DriverExplanation(**explained["business_impact"]),
                exposure=DriverExplanation(**explained["exposure"]),
            )

            # Expected risk reduction
            expected_risk_reduction = int(round(decision.drivers.exploitability * 0.5 + 10))

            # Estimate fix time
            if due_hours <= 4:
                estimated_fix_time = f"{due_hours} hours"
            elif due_hours <= 24:
                estimated_fix_time = f"{due_hours} hours"
            else:
                days = due_hours // 24
                estimated_fix_time = f"{days} days"

            # Business owner (from stored data or fallback)
            business_owner = "Unassigned"  # Could be fetched from user repo

            # Build reason
            reason_parts = [
                drivers_response.asset_importance.explanation,
                drivers_response.vulnerability_severity.explanation,
                drivers_response.exploitability.explanation,
                drivers_response.business_impact.explanation,
                drivers_response.exposure.explanation,
            ]
            reason = " ".join(reason_parts)

            # Next action (from stored summary or fallback)
            next_action = "Review and remediate"
            if decision.summary:
                try:
                    import json
                    summary_data = json.loads(decision.summary)
                    if isinstance(summary_data, dict):
                        next_action = summary_data.get("immediate_recommendation", next_action)
                except (json.JSONDecodeError, AttributeError, TypeError):
                    pass

            # Metadata
            settings = get_settings()
            engine_version = settings.app_version
            model_version = settings.groq_model

            return DecisionObject(
                decision_id=uuid4(),
                finding_id=decision.finding_id,
                tenant_id=decision.tenant_id,
                decision=decision_text,
                priority=priority_level,
                risk_score=int(round(decision.bis)),
                tier=decision.tier,
                confidence=decision.confidence.percentage,
                confidence_breakdown=confidence_breakdown,
                expected_risk_reduction=expected_risk_reduction,
                estimated_fix_time=estimated_fix_time,
                business_owner=business_owner,
                next_action=next_action,
                reason=reason,
                drivers=drivers_response,
                summary=None,  # Could reconstruct from stored summary
                computed_at=decision.computed_at,
                engine_version=engine_version,
                model_version=model_version,
                prompt_version=None,
                knowledge_base_version=None,
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