"""Structured summary response model."""

from pydantic import BaseModel, Field


class SummaryResponse(BaseModel):
    """Structured output from the summary LLM call.

    Attributes:
        business_explanation: Plain-language business explanation of the risk.
        urgency: Perceived urgency level (critical, high, medium, low).
        recommended_action: High-level recommended action.
        key_drivers: Brief explanation of why this finding matters.
    """

    business_explanation: str = Field(
        ...,
        description="Plain-language business explanation of the risk and impact.",
        max_length=500,
    )
    urgency: str = Field(
        ...,
        description="Perceived urgency level (critical, high, medium, low).",
        pattern="^(critical|high|medium|low)$",
    )
    recommended_action: str = Field(
        ...,
        description="High-level recommended action for the business.",
        max_length=200,
    )
    key_drivers: str = Field(
        ...,
        description="Brief explanation of why this finding matters to the business.",
        max_length=300,
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "business_explanation": "This vulnerability affects your production payment system, which handles regulated financial data. If exploited, it could lead to significant financial loss and compliance violations.",
                "urgency": "critical",
                "recommended_action": "Apply the vendor patch immediately and verify the system is protected.",
                "key_drivers": "The asset is mission-critical, the exploit is actively used in the wild, and the data is regulated.",
            }
        }