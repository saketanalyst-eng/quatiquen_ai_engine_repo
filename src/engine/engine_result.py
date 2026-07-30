"""Pipeline state container."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from src.domain.entities import Decision, Finding
from src.domain.value_objects import BusinessContext, Confidence, Drivers, RiskScore, ThreatContext


class PipelineStage(str, Enum):
    """Stages of the pipeline."""

    VALIDATION = "validation"
    CONTEXT_BUILDER = "context_builder"
    SCORE_NORMALIZER = "score_normalizer"
    RISK_ENGINE = "risk_engine"
    CONFIDENCE_ENGINE = "confidence_engine"
    PRIORITY_ENGINE = "priority_engine"
    RULES_ENGINE = "rules_engine"
    RECOMMENDATION_ENGINE = "recommendation_engine"
    SUMMARY_ENGINE = "summary_engine"
    DECISION_MAPPER = "decision_mapper"
    COMPLETE = "complete"


@dataclass
class EngineResult:
    """State container for pipeline execution."""

    finding: Optional[Finding] = None
    business_context: Optional[BusinessContext] = None
    threat_context: Optional[ThreatContext] = None
    vulnerability_severity: Optional[float] = None
    raw_bis: Optional[float] = None
    risk_score: Optional[RiskScore] = None
    drivers: Optional[Drivers] = None
    confidence: Optional[Confidence] = None
    tier: Optional[str] = None
    recommendation_id: Optional[UUID] = None
    summary: Optional[str] = None
    decision: Optional[Decision] = None

    # Pipeline metadata
    current_stage: PipelineStage = PipelineStage.VALIDATION
    errors: dict[PipelineStage, str] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)
    is_complete: bool = False

    def add_error(self, stage: PipelineStage, error: str) -> None:
        """Record an error at a pipeline stage."""
        self.errors[stage] = error

    def set_stage(self, stage: PipelineStage) -> None:
        """Set current pipeline stage."""
        self.current_stage = stage

    def complete(self) -> None:
        """Mark pipeline as complete."""
        self.is_complete = True
        self.current_stage = PipelineStage.COMPLETE

    def has_error(self) -> bool:
        """Check if any error occurred."""
        return len(self.errors) > 0

    def get_error(self, stage: PipelineStage) -> Optional[str]:
        """Get error for a specific stage."""
        return self.errors.get(stage)

    def set_metric(self, name: str, value: float) -> None:
        """Set a pipeline metric."""
        self.metrics[name] = value