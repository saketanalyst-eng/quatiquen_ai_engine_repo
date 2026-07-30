"""Request DTOs for use cases."""

from dataclasses import dataclass
from typing import Any, Optional
from uuid import UUID

from src.core.constants.enums import FindingSource, FindingStatus


@dataclass(frozen=True)
class EvaluateFindingRequest:
    """Request to evaluate a new finding."""

    tenant_id: UUID
    asset_id: UUID
    source: FindingSource
    source_finding_id: str
    title: str
    description: str
    raw_severity: float
    raw_severity_scale: str
    detected_at: int
    raw_payload: dict[str, Any]
    cve_id: Optional[str] = None
    status: FindingStatus = FindingStatus.OPEN


@dataclass(frozen=True)
class GetDecisionRequest:
    """Request to get an existing decision."""

    finding_id: UUID
    tenant_id: UUID


@dataclass(frozen=True)
class RecalculateRequest:
    """Request to recalculate a finding's score."""

    finding_id: UUID
    tenant_id: UUID
    force: bool = False