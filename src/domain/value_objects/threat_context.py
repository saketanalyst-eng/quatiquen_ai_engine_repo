"""Threat context value object representing external threat intelligence."""

from dataclasses import dataclass
from typing import Optional

from src.core.exceptions.domain import InvalidValueObjectError


@dataclass(frozen=True)
class ThreatContext:
    """Threat context value object containing external threat intelligence.

    Attributes:
        cve_id: The CVE identifier.
        epss_score: EPSS probability score (0-1).
        is_kev: Whether the CVE is in the CISA KEV catalog.
        has_poc: Whether a public PoC/exploit exists.
        exploit_available: Overall exploit availability (derived from above).
        fetched_at: Timestamp when context was fetched.
    """

    cve_id: str
    epss_score: Optional[float]
    is_kev: bool
    has_poc: bool
    fetched_at: int

    def __post_init__(self) -> None:
        """Validate threat context invariants."""
        if not self.cve_id or self.cve_id.strip() == "":
            raise InvalidValueObjectError("CVE ID cannot be empty", value_object="ThreatContext")
        if self.epss_score is not None and not 0 <= self.epss_score <= 1:
            raise InvalidValueObjectError(
                f"EPSS score must be between 0 and 1, got {self.epss_score}",
                value_object="ThreatContext",
            )

    @property
    def is_exploitable(self) -> bool:
        """Check if the CVE is considered exploitable."""
        return self.is_kev or self.has_poc or (self.epss_score is not None and self.epss_score > 0.1)

    @property
    def exploitability_score(self) -> float:
        """Compute exploitability score (0-100) for the scoring engine.

        This is a simplified mapping; actual logic should be in the scoring engine.
        """
        if self.is_kev:
            return 92.0
        if self.has_poc:
            return 70.0
        if self.epss_score is not None:
            # Map EPSS from 0-1 to 0-100, with a floor of 10
            return max(10.0, self.epss_score * 100)
        return 10.0

    @classmethod
    def create(
        cls,
        cve_id: str,
        epss_score: Optional[float] = None,
        is_kev: bool = False,
        has_poc: bool = False,
    ) -> "ThreatContext":
        """Factory method to create a threat context.

        Args:
            cve_id: CVE identifier.
            epss_score: EPSS probability score.
            is_kev: Whether in CISA KEV.
            has_poc: Whether PoC exists.

        Returns:
            ThreatContext: New threat context value object.
        """
        fetched_at = int(__import__("time").time())
        return cls(
            cve_id=cve_id,
            epss_score=epss_score,
            is_kev=is_kev,
            has_poc=has_poc,
            fetched_at=fetched_at,
        )