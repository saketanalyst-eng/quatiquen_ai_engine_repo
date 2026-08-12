"""Response schemas for API endpoints."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ---- Confidence Breakdown ----
class ConfidenceBreakdown(BaseModel):
    """Confidence score breakdown explaining each deduction."""

    overall_confidence: int = Field(..., description="Confidence as percentage (0-100)")
    categories: Dict[str, int] = Field(..., description="Scores per category (0-100)")
    factors: List[Dict[str, Any]] = Field(..., description="Individual factors with weight and score")
    deductions: List[Dict[str, Any]] = Field(..., description="List of deductions with amounts")


# ---- Structured Summary ----
class StructuredSummary(BaseModel):
    """Structured AI-generated business summary."""

    business_risk: str = Field(..., description="Business impact if vulnerability is exploited")
    technical_risk: str = Field(..., description="Technical nature of the vulnerability")
    why_scored: str = Field(..., description="Summary of key scoring drivers")
    immediate_recommendation: str = Field(..., description="Highest-priority remediation action")
    expected_business_impact: str = Field(..., description="Consequences if no action is taken")


# ---- Driver Explanation ----
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


# ---- Decision Object (NEW) ----
class DecisionObject(BaseModel):
    """Unified decision object returned by the API."""

    decision_id: UUID = Field(..., description="Unique decision identifier")
    finding_id: UUID = Field(..., description="Finding identifier")
    tenant_id: UUID = Field(..., description="Tenant identifier")

    # Decision metadata
    decision: str = Field(..., description="Business decision (e.g., 'Immediate Action Required')")
    priority: str = Field(..., description="Priority level (P0, P1, P2, P3)")
    risk_score: int = Field(..., description="Business Impact Score (integer)")
    tier: str = Field(..., description="Risk tier: Critical, High, Medium, Low")

    # Confidence
    confidence: int = Field(..., description="Confidence as percentage (0-100)")
    confidence_breakdown: ConfidenceBreakdown = Field(..., description="Detailed confidence breakdown")

    # Expected impact and fix
    expected_risk_reduction: int = Field(..., description="Expected risk reduction percentage")
    estimated_fix_time: str = Field(..., description="Estimated time to fix (e.g., '30 minutes')")
    business_owner: str = Field(..., description="Assigned business owner or team")
    next_action: str = Field(..., description="Recommended next action")
    reason: str = Field(..., description="Concise reason for the decision")

    # Drivers and summary
    drivers: DriversResponse = Field(..., description="Driver breakdown with explanations")
    summary: Optional[StructuredSummary] = Field(None, description="AI-generated structured summary")

    # Metadata
    computed_at: int = Field(..., description="Timestamp when decision was created")
    engine_version: str = Field(..., description="Engine version")
    model_version: Optional[str] = Field(None, description="LLM model version used")
    prompt_version: Optional[str] = Field(None, description="Prompt version hash")
    knowledge_base_version: Optional[str] = Field(None, description="Knowledge base version")

    @field_validator("risk_score", mode="after")
    @classmethod
    def round_risk_score(cls, v: float) -> int:
        return int(round(v))


# ---- Legacy Response (Deprecated, kept for backward compatibility) ----
class EvaluateFindingResponse(BaseModel):
    """Legacy response for /risk/calculate (deprecated, use DecisionObject)."""

    finding_id: UUID = Field(..., description="Finding identifier")
    tenant_id: UUID = Field(..., description="Tenant identifier")
    bis: float = Field(..., description="Business Impact Score (final)")
    tier: str = Field(..., description="Priority tier: Critical, High, Medium, Low")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score")
    confidence_breakdown: ConfidenceBreakdown = Field(
        ..., description="Detailed breakdown of confidence deductions"
    )
    drivers: Dict[str, float] = Field(..., description="Drivers breakdown")
    recommendation_id: Optional[UUID] = Field(None, description="Recommendation ID")
    summary: Optional[StructuredSummary] = Field(None, description="AI-generated structured business summary")
    computed_at: int = Field(..., description="Computation timestamp")

    @field_validator("bis", "confidence", mode="after")
    @classmethod
    def round_bis_and_confidence(cls, v: float) -> float:
        return round(v, 2)


class GetDecisionResponse(EvaluateFindingResponse):
    """Response for /risk/{finding_id} (legacy)."""

    version: str = Field(..., description="Scoring version")
    history_available: bool = Field(False, description="Whether history is available")
    low_confidence: bool = Field(..., description="Whether confidence is below threshold")


class RecalculateResponse(EvaluateFindingResponse):
    """Response for /risk/recalculate (legacy)."""

    previous_bis: float = Field(..., description="Previous BIS score")
    previous_tier: str = Field(..., description="Previous priority tier")