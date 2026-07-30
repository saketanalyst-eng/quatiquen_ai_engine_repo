"""Request schemas for API endpoints."""

from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class EvaluateFindingRequest(BaseModel):
    """Request body for /risk/calculate."""

    tenant_id: UUID = Field(..., description="Tenant identifier")
    asset_id: UUID = Field(..., description="Asset identifier")
    source: str = Field(..., description="Finding source (internal_scanner, etc.)")
    source_finding_id: str = Field(..., description="Source system ID")
    title: str = Field(..., min_length=1, max_length=500, description="Finding title")
    description: str = Field(..., min_length=1, max_length=2000, description="Finding description")
    raw_severity: float = Field(..., ge=0, le=100, description="Raw severity score")
    raw_severity_scale: str = Field(..., description="Scale: cvss_v3, cvss_v4, vendor_custom, qualitative")
    detected_at: int = Field(..., description="Detection timestamp (Unix)")
    raw_payload: Dict[str, Any] = Field(..., description="Original payload")
    cve_id: Optional[str] = Field(None, max_length=50, description="CVE identifier")
    status: Optional[str] = Field("open", description="Status: open, resolved, suppressed")

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        valid = {"internal_scanner", "external_scanner", "cloud_api", "threat_feed", "custom"}
        if v not in valid:
            raise ValueError(f"source must be one of {valid}")
        return v

    @field_validator("raw_severity_scale")
    @classmethod
    def validate_scale(cls, v: str) -> str:
        valid = {"cvss_v3", "cvss_v4", "vendor_custom", "qualitative"}
        if v not in valid:
            raise ValueError(f"raw_severity_scale must be one of {valid}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid = {"open", "resolved", "suppressed"}
        if v not in valid:
            raise ValueError(f"status must be one of {valid}")
        return v


class RecalculateRequest(BaseModel):
    """Request body for /risk/recalculate."""

    finding_id: UUID = Field(..., description="Finding identifier")
    tenant_id: UUID = Field(..., description="Tenant identifier")
    force: bool = Field(False, description="Force recalculation even if not stale")