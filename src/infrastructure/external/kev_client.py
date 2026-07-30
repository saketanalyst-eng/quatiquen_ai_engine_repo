"""CISA KEV feed client."""

import json
from typing import Dict, Set

import httpx

from src.core.logging.logger import get_logger

logger = get_logger("quantiquan.infrastructure.kev_client")


class KEVClient:
    """Client for CISA Known Exploited Vulnerabilities catalog."""

    def __init__(self, feed_url: str = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json") -> None:
        """Initialize KEV client.

        Args:
            feed_url: URL of the KEV feed.
        """
        self.feed_url = feed_url
        self._cache: Dict[str, bool] = {}
        self._last_fetch: int = 0
        self._cache_ttl = 86400  # 24h

    async def _fetch_feed(self) -> Set[str]:
        """Fetch KEV feed and return set of CVE IDs."""
        if self._last_fetch and (__import__("time").time() - self._last_fetch) < self._cache_ttl:
            return set(self._cache.keys())

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.feed_url)
                response.raise_for_status()
                data = response.json()
                vulns = data.get("vulnerabilities", [])
                cves = set()
                for v in vulns:
                    cve = v.get("cveID")
                    if cve:
                        cves.add(cve)
                self._cache = {cve: True for cve in cves}
                self._last_fetch = __import__("time").time()
                logger.info("KEV feed fetched", count=len(cves))
                return cves
        except Exception as exc:
            logger.error("Failed to fetch KEV feed", error=str(exc), exc_info=True)
            return set(self._cache.keys())  # return cached if available

    async def is_kev_listed(self, cve_id: str) -> bool:
        """Check if CVE is in KEV catalog."""
        cves = await self._fetch_feed()
        return cve_id in cves