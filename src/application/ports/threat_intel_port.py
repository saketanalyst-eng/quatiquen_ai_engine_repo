"""Threat intelligence port for fetching external threat data."""

from abc import ABC, abstractmethod
from typing import Optional

from src.domain.value_objects import ThreatContext


class ThreatIntelPort(ABC):
    """Abstract interface for threat intelligence providers."""

    @abstractmethod
    async def get_threat_context(self, cve_id: str) -> ThreatContext:
        """Get threat context for a CVE.

        Args:
            cve_id: CVE identifier.

        Returns:
            ThreatContext: Threat context object.
        """
        pass

    @abstractmethod
    async def get_epss_score(self, cve_id: str) -> Optional[float]:
        """Get EPSS score for a CVE.

        Args:
            cve_id: CVE identifier.

        Returns:
            Optional[float]: EPSS score (0-1), or None if not available.
        """
        pass

    @abstractmethod
    async def is_kev_listed(self, cve_id: str) -> bool:
        """Check if CVE is in CISA KEV catalog.

        Args:
            cve_id: CVE identifier.

        Returns:
            bool: True if listed.
        """
        pass

    @abstractmethod
    async def has_public_exploit(self, cve_id: str) -> bool:
        """Check if public exploit exists.

        Args:
            cve_id: CVE identifier.

        Returns:
            bool: True if exploit available.
        """
        pass