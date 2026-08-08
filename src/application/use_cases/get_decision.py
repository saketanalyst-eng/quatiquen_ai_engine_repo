"""Use case for retrieving an existing decision."""

from src.application.dto import GetDecisionRequest, GetDecisionResponse
from src.core.exceptions.application import UseCaseError
from src.core.exceptions.domain import EntityNotFoundError
from src.core.logging.logger import get_logger
from src.domain.repositories import IUnitOfWork
from src.domain.value_objects import Drivers
from src.interfaces.schemas.response import ConfidenceBreakdown, DriverExplanation, DriversResponse, GetDecisionResponse
from src.interfaces.schemas import ConfidenceBreakdown

logger = get_logger("quantiquan.application.get_decision")


class GetDecisionUseCase:
    """Use case to retrieve a decision by finding ID."""

    def __init__(self, unit_of_work: IUnitOfWork) -> None:
        self.uow = unit_of_work

    async def execute(self, request: GetDecisionRequest) -> GetDecisionResponse:
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

            # Reconstruct confidence breakdown
            conf_value = decision.confidence.value
            deductions = []
            if conf_value < 1.0:
                if conf_value <= 0.5:
                    deductions = [
                        ("no_asset_owner", 0.2),
                        ("single_source", 0.1),
                        ("no_threat_intel", 0.2),
                    ]
                elif conf_value <= 0.7:
                    deductions = [
                        ("no_asset_owner", 0.2),
                        ("single_source", 0.1),
                    ]
                else:
                    deductions = [("no_asset_owner", 0.2)]

            confidence_breakdown = ConfidenceBreakdown(
                percentage=int(round(conf_value * 100)),
                asset_owner_missing=any(f == "no_asset_owner" for f, _ in deductions),
                threat_intel_missing=any(f == "no_threat_intel" for f, _ in deductions),
                cmdb_missing=any(f == "no_cmdb_record" for f, _ in deductions),
                single_source=any(f == "single_source" for f, _ in deductions),
                stale_scan=any(f == "stale_finding" for f, _ in deductions),
                total_deductions=int(round((1.0 - conf_value) * 100)),
                deduction_details=[{"factor": f, "deduction": int(round(d * 100))} for f, d in deductions],
            )

            # Reconstruct explained drivers from stored numeric values
            drivers = Drivers(
                asset_importance=decision.drivers.asset_importance,
                vulnerability_severity=decision.drivers.vulnerability_severity,
                exploitability=decision.drivers.exploitability,
                business_impact=decision.drivers.business_impact,
                exposure=decision.drivers.exposure,
            )
            explained = drivers.to_explained_dict(business_context=None)
            drivers_response = DriversResponse(
                asset_importance=DriverExplanation(**explained["asset_importance"]),
                vulnerability_severity=DriverExplanation(**explained["vulnerability_severity"]),
                exploitability=DriverExplanation(**explained["exploitability"]),
                business_impact=DriverExplanation(**explained["business_impact"]),
                exposure=DriverExplanation(**explained["exposure"]),
            )

            return GetDecisionResponse(
                finding_id=decision.finding_id,
                tenant_id=decision.tenant_id,
                bis=decision.bis,
                tier=decision.tier,
                confidence=decision.confidence.value,
                confidence_breakdown=confidence_breakdown,
                drivers=drivers_response,
                recommendation_id=decision.recommendation_id,
                summary=decision.summary,
                computed_at=decision.computed_at,
                version=decision.version,
                history_available=False,
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