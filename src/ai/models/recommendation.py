"""Structured recommendation explanation model."""

from pydantic import BaseModel, Field


class RecommendationResponse(BaseModel):
    """Structured output for recommendation explanation.

    Attributes:
        explanation: Plain-language rationale for the recommendation.
        priority: Matching priority tier.
        estimated_effort: Effort estimate (low, medium, high).
        technical_details: Technical steps (optional, can be from KB).
    """

    explanation: str = Field(
        ...,
        description="Plain-language rationale for why this recommendation is appropriate.",
        max_length=400,
    )
    priority: str = Field(
        ...,
        description="Priority tier matching the finding.",
        pattern="^(Critical|High|Medium|Low)$",
    )
    estimated_effort: str = Field(
        ...,
        description="Estimated effort to implement (low, medium, high).",
        pattern="^(low|medium|high)$",
    )
    technical_details: str = Field(
        "",
        description="Technical remediation steps (if available).",
        max_length=1000,
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "explanation": "Since this vulnerability is actively exploited and affects a critical asset, immediate patching is recommended to reduce risk.",
                "priority": "Critical",
                "estimated_effort": "medium",
                "technical_details": "Apply the security patch from vendor and restart the service.",
            }
        }