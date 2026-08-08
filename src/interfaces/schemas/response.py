"""Response schemas for API endpoints."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ConfidenceBreakdown(BaseModel):
    """Confidence score breakdown explaining each deduction."""

    percentage: int = Field(..., description="Confidence as percentage (0-100)")
    asset_owner_missing: bool = Field(..., description="True if asset has no assigned owner")
    threat_intel_missing: bool = Field(..., description="True if no threat intel available")
    cmdb_missing: bool = Field(..., description="True if asset not found in CMDB")
    single_source: bool = Field(..., description="True if finding reported by only one source")
    stale_scan: bool = Field(..., description="True if finding is older than 30 days")
    total_deductions: int = Field(..., description="Total percentage points deducted")
    deduction_details: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of each deduction with factor name and amount in percentage points"
    )


class StructuredSummary(BaseModel):
    """Structured AI-generated business summary."""

    business_risk: str = Field(..., description="Business impact if vulnerability is exploited")
    technical_risk: str = Field(..., description="Technical nature of the vulnerability")
    why_scored: str = Field(..., description="Summary of key scoring drivers")
    immediate_recommendation: str = Field(..., description="Highest-priority remediation action")
    expected_business_impact: str = Field(..., description="Consequences if no action is taken")


class DriverExplanation(BaseModel):
    """Driver value with a human-readable explanation."""

    value: float = Field(..., description="Driver value (0-100)")
    explanation: str = Field(..., description="Short explanation of why this score was assigned")


class DriversResponse(BaseModel):
    """Drivers breakdown for response."""

    asset_importance: DriverExplanation
    vulnerability_severity: DriverExplanation
    exploitability: DriverExplanation
    business_impact: DriverExplanation
    exposure: DriverExplanation


class EvaluateFindingResponse(BaseModel):
    """Response for /risk/calculate."""

    finding_id: UUID = Field(..., description="Finding identifier")
    tenant_id: UUID = Field(..., description="Tenant identifier")
    bis: float = Field(..., description="Business Impact Score (final)")
    tier: str = Field(..., description="Priority tier: Critical, High, Medium, Low")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score")
    confidence_breakdown: ConfidenceBreakdown = Field(
        ..., description="Detailed breakdown of confidence deductions"
    )
    drivers: DriversResponse = Field(..., description="Drivers breakdown")
    recommendation_id: Optional[UUID] = Field(None, description="Recommendation ID")
    summary: Optional[StructuredSummary] = Field(None, description="AI-generated structured business summary")
    computed_at: int = Field(..., description="Computation timestamp")

    @field_validator("bis", "confidence", mode="after")
    @classmethod
    def round_bis_and_confidence(cls, v: float) -> float:
        return round(v, 2)


class GetDecisionResponse(EvaluateFindingResponse):
    """Response for /risk/{finding_id}."""

    version: str = Field(..., description="Scoring version")
    history_available: bool = Field(False, description="Whether history is available")
    low_confidence: bool = Field(..., description="Whether confidence is below threshold")


class RecalculateResponse(EvaluateFindingResponse):
    """Response for /risk/recalculate."""

    previous_bis: float = Field(..., description="Previous BIS score")
    previous_tier: str = Field(..., description="Previous priority tier")