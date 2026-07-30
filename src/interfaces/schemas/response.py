"""Response schemas for API endpoints."""

from typing import Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DriversResponse(BaseModel):
    """Drivers breakdown for response."""

    asset_importance: float = Field(..., description="Asset importance score")
    vulnerability_severity: float = Field(..., description="Vulnerability severity score")
    exploitability: float = Field(..., description="Exploitability score")
    business_impact: float = Field(..., description="Business impact score")
    exposure: float = Field(..., description="Exposure score")


class EvaluateFindingResponse(BaseModel):
    """Response for /risk/calculate."""

    finding_id: UUID = Field(..., description="Finding identifier")
    tenant_id: UUID = Field(..., description="Tenant identifier")
    bis: float = Field(..., description="Business Impact Score (final)")
    tier: str = Field(..., description="Priority tier: Critical, High, Medium, Low")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score")
    drivers: Dict[str, float] = Field(..., description="Drivers breakdown")
    recommendation_id: Optional[UUID] = Field(None, description="Recommendation ID")
    summary: Optional[str] = Field(None, description="AI-generated business summary")
    computed_at: int = Field(..., description="Computation timestamp")


class GetDecisionResponse(EvaluateFindingResponse):
    """Response for /risk/{finding_id}."""

    version: str = Field(..., description="Scoring version")
    history_available: bool = Field(False, description="Whether history is available")
    low_confidence: bool = Field(..., description="Whether confidence is below threshold")


class RecalculateResponse(EvaluateFindingResponse):
    """Response for /risk/recalculate."""

    previous_bis: float = Field(..., description="Previous BIS score")
    previous_tier: str = Field(..., description="Previous priority tier")