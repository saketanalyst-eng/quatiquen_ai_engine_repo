"""Confidence value object representing data completeness and trust."""

from dataclasses import dataclass
from typing import List, Tuple, Optional

from src.core.constants.thresholds import (
    CONFIDENCE_FLOOR,
    CONFIDENCE_MAX,
    CONFIDENCE_MIN,
    CONFIDENCE_MULTIPLIER_BASE,
    CONFIDENCE_MULTIPLIER_SCALE,
    DEDUCTION_NO_CMDB,
    DEDUCTION_NO_OWNER,
    DEDUCTION_NO_THREAT_INTEL,
    DEDUCTION_SINGLE_SOURCE,
    DEDUCTION_STALE_SCAN,
)
from src.core.exceptions.domain import InvalidValueObjectError


@dataclass(frozen=True)
class Confidence:
    """Confidence value object representing data completeness and trust.

    Attributes:
        value: Confidence score (0.0-1.0).
        deductions: List of deductions applied with reasons.
    """

    value: float
    deductions: List[Tuple[str, float]]

    def __post_init__(self) -> None:
        """Validate confidence invariants."""
        if not CONFIDENCE_MIN <= self.value <= CONFIDENCE_MAX:
            raise InvalidValueObjectError(
                f"Confidence must be between 0 and 1, got {self.value}",
                value_object="Confidence",
            )

    @property
    def multiplier(self) -> float:
        """Get the confidence multiplier (0.7-1.0) as defined in Section 9.

        Formula: multiplier = 0.7 + (0.3 * confidence)
        """
        return CONFIDENCE_MULTIPLIER_BASE + (CONFIDENCE_MULTIPLIER_SCALE * self.value)

    @property
    def is_high(self) -> bool:
        """Check if confidence is high (>= 0.7)."""
        return self.value >= 0.7

    @property
    def is_low(self) -> bool:
        """Check if confidence is low (< 0.7)."""
        return self.value < 0.7

    @property
    def percentage(self) -> int:
        """Get confidence as a percentage (0-100)."""
        return int(round(self.value * 100))

    @property
    def breakdown(self) -> dict:
        """Get a detailed breakdown of confidence factors.

        Returns:
            dict: {
                "asset_owner_missing": bool,
                "threat_intel_missing": bool,
                "cmdb_missing": bool,
                "single_source": bool,
                "stale_scan": bool,
                "total_deductions": int,  # percentage points deducted
                "deduction_details": [{"factor": str, "deduction": int}]
            }
        """
        return {
            "asset_owner_missing": any(f == "no_asset_owner" for f, _ in self.deductions),
            "threat_intel_missing": any(f == "no_threat_intel" for f, _ in self.deductions),
            "cmdb_missing": any(f == "no_cmdb_record" for f, _ in self.deductions),
            "single_source": any(f == "single_source" for f, _ in self.deductions),
            "stale_scan": any(f == "stale_finding" for f, _ in self.deductions),
            "total_deductions": int(round((1.0 - self.value) * 100)),
            "deduction_details": [{"factor": f, "deduction": int(round(d * 100))} for f, d in self.deductions],
        }

    @classmethod
    def create(
        cls,
        has_owner: bool,
        is_stale: bool,
        has_threat_intel: bool,
        has_cmdb_record: bool,
        source_count: int,
    ) -> "Confidence":
        """Create confidence score from data completeness factors.

        Args:
            has_owner: Whether the asset has an assigned owner.
            is_stale: Whether the finding is stale (>30 days).
            has_threat_intel: Whether threat intel was found for the CVE.
            has_cmdb_record: Whether the asset is in the CMDB.
            source_count: Number of sources that reported this finding.

        Returns:
            Confidence: New confidence value object.
        """
        deductions = []
        score = 1.0

        if not has_owner:
            score -= DEDUCTION_NO_OWNER
            deductions.append(("no_asset_owner", DEDUCTION_NO_OWNER))

        if is_stale:
            score -= DEDUCTION_STALE_SCAN
            deductions.append(("stale_finding", DEDUCTION_STALE_SCAN))

        if not has_threat_intel:
            score -= DEDUCTION_NO_THREAT_INTEL
            deductions.append(("no_threat_intel", DEDUCTION_NO_THREAT_INTEL))

        if not has_cmdb_record:
            score -= DEDUCTION_NO_CMDB
            deductions.append(("no_cmdb_record", DEDUCTION_NO_CMDB))

        if source_count <= 1:
            score -= DEDUCTION_SINGLE_SOURCE
            deductions.append(("single_source", DEDUCTION_SINGLE_SOURCE))

        # Clamp to [0, 1]
        score = max(CONFIDENCE_MIN, min(CONFIDENCE_MAX, score))

        return cls(value=score, deductions=tuple(deductions))