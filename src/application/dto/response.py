"""Response DTOs for use cases."""

from dataclasses import dataclass
from typing import Any, Optional
from uuid import UUID

from src.core.constants.enums import PriorityTier


@dataclass(frozen=True)
class EvaluateFindingResponse:
    """Response from evaluating a finding."""

    finding_id: UUID
    tenant_id: UUID
    bis: float
    tier: PriorityTier
    confidence: float
    drivers: dict[str, float]
    recommendation_id: Optional[UUID]
    summary: Optional[str]
    computed_at: int


@dataclass(frozen=True)
class GetDecisionResponse:
    """Response from getting a decision."""

    finding_id: UUID
    tenant_id: UUID
    bis: float
    tier: PriorityTier
    confidence: float
    drivers: dict[str, float]
    recommendation_id: Optional[UUID]
    summary: Optional[str]
    computed_at: int
    version: str
    history_available: bool
    low_confidence: bool


@dataclass(frozen=True)
class RecalculateResponse:
    """Response from recalculating a decision."""

    finding_id: UUID
    tenant_id: UUID
    bis: float
    tier: PriorityTier
    confidence: float
    drivers: dict[str, float]
    recommendation_id: Optional[UUID]
    summary: Optional[str]
    computed_at: int
    previous_bis: float
    previous_tier: str