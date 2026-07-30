"""Finding entity representing a security finding."""

from dataclasses import dataclass
from typing import Any, Optional
from uuid import UUID, uuid4

from src.core.constants.enums import FindingSource, FindingStatus
from src.core.exceptions.domain import ValidationError


@dataclass(frozen=True)
class Finding:
    """Finding entity representing a security finding from any source.

    Attributes:
        id: Unique finding identifier.
        tenant_id: Tenant that owns the finding.
        asset_id: Asset this finding applies to.
        source: Source system (internal_scanner, external_scanner, etc.).
        source_finding_id: Source system's own ID for this finding.
        cve_id: Optional CVE identifier.
        title: Finding title.
        description: Finding description.
        raw_severity: Original severity score from source.
        raw_severity_scale: Scale of the raw severity (cvss_v3, cvss_v4, vendor_custom, qualitative).
        status: Current status (open, resolved, suppressed).
        detected_at: Detection timestamp.
        raw_payload: Original source payload for audit.
        created_at: Entity creation timestamp.
        updated_at: Entity update timestamp.
    """

    id: UUID
    tenant_id: UUID
    asset_id: UUID
    source: FindingSource
    source_finding_id: str
    cve_id: Optional[str]
    title: str
    description: str
    raw_severity: float
    raw_severity_scale: str
    status: FindingStatus
    detected_at: int
    raw_payload: dict[str, Any]
    created_at: int
    updated_at: int

    def __post_init__(self) -> None:
        """Validate finding invariants."""
        if not self.title:
            raise ValidationError("Finding title cannot be empty", field="title")
        if not self.description:
            raise ValidationError("Finding description cannot be empty", field="description")
        if self.raw_severity < 0:
            raise ValidationError(
                f"Raw severity cannot be negative, got {self.raw_severity}",
                field="raw_severity",
                value=self.raw_severity,
            )
        if self.detected_at <= 0:
            raise ValidationError("Detected at must be a positive timestamp", field="detected_at")
        if self.raw_severity_scale not in ("cvss_v3", "cvss_v4", "vendor_custom", "qualitative"):
            raise ValidationError(
                f"Invalid raw_severity_scale: {self.raw_severity_scale}",
                field="raw_severity_scale",
                value=self.raw_severity_scale,
            )

    @property
    def is_open(self) -> bool:
        """Check if the finding is open."""
        return self.status == FindingStatus.OPEN

    @property
    def is_resolved(self) -> bool:
        """Check if the finding is resolved."""
        return self.status == FindingStatus.RESOLVED

    @property
    def is_suppressed(self) -> bool:
        """Check if the finding is suppressed."""
        return self.status == FindingStatus.SUPPRESSED

    @property
    def has_cve(self) -> bool:
        """Check if the finding has a CVE identifier."""
        return self.cve_id is not None and self.cve_id.strip() != ""

    def age_in_days(self, current_time: int) -> float:
        """Calculate age of the finding in days.

        Args:
            current_time: Current timestamp.

        Returns:
            float: Age in days.
        """
        if current_time <= self.detected_at:
            return 0.0
        return (current_time - self.detected_at) / (24 * 3600)

    def is_stale(self, current_time: int, stale_days: int = 30) -> bool:
        """Check if the finding is stale (older than stale_days).

        Args:
            current_time: Current timestamp.
            stale_days: Number of days after which a finding is considered stale.

        Returns:
            bool: True if stale.
        """
        return self.age_in_days(current_time) > stale_days

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        asset_id: UUID,
        source: FindingSource,
        source_finding_id: str,
        title: str,
        description: str,
        raw_severity: float,
        raw_severity_scale: str,
        detected_at: int,
        raw_payload: dict[str, Any],
        cve_id: Optional[str] = None,
        status: FindingStatus = FindingStatus.OPEN,
    ) -> "Finding":
        """Factory method to create a new finding.

        Args:
            tenant_id: Tenant identifier.
            asset_id: Asset identifier.
            source: Source system.
            source_finding_id: Source-specific ID.
            title: Finding title.
            description: Finding description.
            raw_severity: Original severity score.
            raw_severity_scale: Scale of the raw severity.
            detected_at: Detection timestamp.
            raw_payload: Original source payload.
            cve_id: Optional CVE identifier.
            status: Initial status (default: open).

        Returns:
            Finding: New finding instance.

        Raises:
            ValidationError: If validation fails.
        """
        now = int(__import__("time").time())
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            asset_id=asset_id,
            source=source,
            source_finding_id=source_finding_id,
            cve_id=cve_id,
            title=title,
            description=description,
            raw_severity=raw_severity,
            raw_severity_scale=raw_severity_scale,
            status=status,
            detected_at=detected_at,
            raw_payload=raw_payload,
            created_at=now,
            updated_at=now,
        )