

"""Audit logging for immutable event tracking."""

import json
import time
from typing import Any, Dict, Optional
from uuid import UUID

from src.core.logging.logger import get_logger


class AuditLogger:
    """Audit logger for immutable event trails.

    This logger writes structured audit events that cannot be modified
    after creation. Used for compliance and forensic analysis.
    """

    def __init__(self, logger_name: str = "quantiquan.audit") -> None:
        """Initialize audit logger.

        Args:
            logger_name: Name for the logger instance.
        """
        self.logger = get_logger(logger_name)

    def log_event(
        self,
        event_type: str,
        tenant_id: str,
        finding_id: str,
        data: Dict[str, Any],
        user_id: Optional[str] = None,
        source: Optional[str] = None,
    ) -> None:
        """Log an audit event.

        Args:
            event_type: Type of event (e.g., "FINDING_CREATED", "SCORED").
            tenant_id: Tenant identifier.
            finding_id: Finding identifier.
            data: Event data payload.
            user_id: Optional user identifier.
            source: Optional event source.
        """
        event = {
            "event_type": event_type,
            "tenant_id": str(tenant_id),
            "finding_id": str(finding_id),
            "user_id": str(user_id) if user_id else None,
            "source": source,
            "data": data,
            "timestamp": time.time(),
            "iso_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        self.logger.info(
            "AUDIT_EVENT",
            **event,
        )

    def log_finding_created(
        self,
        tenant_id: str,
        finding_id: str,
        source: str,
        raw_payload: Dict[str, Any],
    ) -> None:
        """Log finding creation event.

        Args:
            tenant_id: Tenant identifier.
            finding_id: Finding identifier.
            source: Source of the finding.
            raw_payload: Raw finding payload.
        """
        self.log_event(
            event_type="FINDING_CREATED",
            tenant_id=tenant_id,
            finding_id=finding_id,
            data={
                "source": source,
                "raw_payload": raw_payload,
            },
            source=source,
        )

    def log_finding_scored(
        self,
        tenant_id: str,
        finding_id: str,
        bis: float,
        tier: str,
        confidence: float,
        drivers: Dict[str, float],
    ) -> None:
        """Log finding scoring event.

        Args:
            tenant_id: Tenant identifier.
            finding_id: Finding identifier.
            bis: Business Impact Score.
            tier: Priority tier.
            confidence: Confidence score.
            drivers: Scoring drivers breakdown.
        """
        self.log_event(
            event_type="FINDING_SCORED",
            tenant_id=tenant_id,
            finding_id=finding_id,
            data={
                "bis": bis,
                "tier": tier,
                "confidence": confidence,
                "drivers": drivers,
            },
        )

    def log_recommendation_generated(
        self,
        tenant_id: str,
        finding_id: str,
        recommendation_id: str,
        action: str,
    ) -> None:
        """Log recommendation generation event.

        Args:
            tenant_id: Tenant identifier.
            finding_id: Finding identifier.
            recommendation_id: Recommendation identifier.
            action: Recommended action.
        """
        self.log_event(
            event_type="RECOMMENDATION_GENERATED",
            tenant_id=tenant_id,
            finding_id=finding_id,
            data={
                "recommendation_id": recommendation_id,
                "action": action,
            },
        )

    def log_ai_summary_generated(
        self,
        tenant_id: str,
        finding_id: str,
        summary: Optional[str],
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Log AI summary generation event.

        Args:
            tenant_id: Tenant identifier.
            finding_id: Finding identifier.
            summary: Generated summary (or None).
            success: Whether generation succeeded.
            error: Optional error message.
        """
        self.log_event(
            event_type="AI_SUMMARY_GENERATED",
            tenant_id=tenant_id,
            finding_id=finding_id,
            data={
                "success": success,
                "summary": summary[:500] if summary else None,
                "error": error,
            },
        )