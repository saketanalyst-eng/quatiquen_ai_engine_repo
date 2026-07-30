"""EPSS API client."""

import asyncio
import json
from typing import Optional

import httpx

from src.application.ports import ThreatIntelPort
from src.core.exceptions.infrastructure import ExternalServiceError
from src.core.logging.logger import get_logger
from src.domain.value_objects import ThreatContext

logger = get_logger("quantiquan.infrastructure.epss_client")


class EPSSClient(ThreatIntelPort):
    """Client for FIRST.org EPSS API."""

    def __init__(self, base_url: str = "https://api.first.org/epss/v1/") -> None:
        """Initialize EPSS client.

        Args:
            base_url: EPSS API base URL.
        """
        self.base_url = base_url
        self.client = None

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=5.0)
        return self.client

    async def get_threat_context(self, cve_id: str) -> ThreatContext:
        """Get threat context for a CVE."""
        epss = await self.get_epss_score(cve_id)
        is_kev = await self.is_kev_listed(cve_id)
        has_poc = await self.has_public_exploit(cve_id)
        return ThreatContext.create(cve_id=cve_id, epss_score=epss, is_kev=is_kev, has_poc=has_poc)

    async def get_epss_score(self, cve_id: str) -> Optional[float]:
        """Get EPSS score for a CVE."""
        try:
            client = self._get_client()
            response = await client.get(f"{self.base_url}?cve={cve_id}")
            response.raise_for_status()
            data = response.json()
            # EPSS returns an array of data
            if data.get("data"):
                for item in data["data"]:
                    if item.get("cve") == cve_id:
                        return float(item.get("epss", 0.0))
            return None
        except (httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            logger.warning("EPSS request failed", cve_id=cve_id, error=str(exc))
            return None
        except Exception as exc:
            logger.error("EPSS client error", cve_id=cve_id, error=str(exc), exc_info=True)
            return None

    async def is_kev_listed(self, cve_id: str) -> bool:
        """Check KEV listing - defer to KEV client."""
        from src.infrastructure.external.kev_client import KEVClient
        kev = KEVClient()
        return await kev.is_kev_listed(cve_id)

    async def has_public_exploit(self, cve_id: str) -> bool:
        """Check public exploit - defer to VirusTotal client."""
        from src.infrastructure.external.virustotal_client import VirusTotalClient
        vt = VirusTotalClient()
        return await vt.has_public_exploit(cve_id)

    async def close(self) -> None:
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()