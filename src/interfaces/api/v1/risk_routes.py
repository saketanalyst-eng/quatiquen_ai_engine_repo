"""Risk scoring API routes."""

from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.application.dto import EvaluateFindingRequest, GetDecisionRequest, RecalculateRequest
from src.application.use_cases import EvaluateFindingUseCase, GetDecisionUseCase, RecalculateUseCase
from src.core.constants.enums import FindingSource, FindingStatus
from src.core.exceptions.domain import EntityNotFoundError, ValidationError
from src.core.logging.logger import get_logger
from src.interfaces.dependencies.inject import (
    get_evaluate_finding_use_case,
    get_get_decision_use_case,
    get_recalculate_use_case,
)
from src.interfaces.schemas.request import (
    EvaluateFindingRequest as EvaluateFindingRequestSchema,
    RecalculateRequest as RecalculateRequestSchema,
)
from src.interfaces.schemas.response import (
    EvaluateFindingResponse,
    GetDecisionResponse,
    RecalculateResponse,
)

logger = get_logger("quantiquan.interfaces.risk_routes")

router = APIRouter()


@router.post(
    "/risk/calculate",
    response_model=EvaluateFindingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def calculate_risk(
    request: EvaluateFindingRequestSchema,
    use_case: EvaluateFindingUseCase = Depends(get_evaluate_finding_use_case),
) -> Dict[str, Any]:
    """Calculate risk for a new finding.

    Args:
        request: Request payload.
        use_case: Use case instance.

    Returns:
        Dict[str, Any]: Scoring response.

    Raises:
        HTTPException: On validation errors.
    """
    try:
        # Convert schema to DTO
        dto = EvaluateFindingRequest(
            tenant_id=request.tenant_id,
            asset_id=request.asset_id,
            source=FindingSource(request.source),
            source_finding_id=request.source_finding_id,
            title=request.title,
            description=request.description,
            raw_severity=request.raw_severity,
            raw_severity_scale=request.raw_severity_scale,
            detected_at=request.detected_at,
            raw_payload=request.raw_payload,
            cve_id=request.cve_id,
            status=FindingStatus(request.status) if request.status else FindingStatus.OPEN,
        )
        result = await use_case.execute(dto)
        return result.__dict__
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "validation_error", "message": str(exc), "field": exc.detail.get("field")},
        )
    except Exception as exc:
        logger.error("Risk calculation failed", error=str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": "Failed to calculate risk"},
        )


@router.get(
    "/risk/{finding_id}",
    response_model=GetDecisionResponse,
    status_code=status.HTTP_200_OK,
)
async def get_decision(
    finding_id: UUID,
    tenant_id: UUID = Query(..., description="Tenant ID for isolation"),
    use_case: GetDecisionUseCase = Depends(get_get_decision_use_case),
) -> Dict[str, Any]:
    """Get decision for a finding.

    Args:
        finding_id: Finding ID.
        tenant_id: Tenant ID.
        use_case: Use case instance.

    Returns:
        Dict[str, Any]: Decision data.

    Raises:
        HTTPException: If not found or error.
    """
    try:
        dto = GetDecisionRequest(finding_id=finding_id, tenant_id=tenant_id)
        result = await use_case.execute(dto)
        return result.__dict__
    except EntityNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": str(exc)},
        )
    except Exception as exc:
        logger.error("Get decision failed", finding_id=str(finding_id), error=str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": "Failed to retrieve decision"},
        )


@router.post(
    "/risk/recalculate",
    response_model=RecalculateResponse,
    status_code=status.HTTP_200_OK,
)
async def recalculate_risk(
    request: RecalculateRequestSchema,
    use_case: RecalculateUseCase = Depends(get_recalculate_use_case),
) -> Dict[str, Any]:
    """Recalculate risk for an existing finding.

    Args:
        request: Request payload.
        use_case: Use case instance.

    Returns:
        Dict[str, Any]: Updated decision.

    Raises:
        HTTPException: On validation or not found.
    """
    try:
        dto = RecalculateRequest(
            finding_id=request.finding_id,
            tenant_id=request.tenant_id,
            force=request.force,
        )
        result = await use_case.execute(dto)
        return result.__dict__
    except EntityNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": str(exc)},
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "validation_error", "message": str(exc)},
        )
    except Exception as exc:
        logger.error("Recalculation failed", finding_id=str(request.finding_id), error=str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": "Failed to recalculate risk"},
        )