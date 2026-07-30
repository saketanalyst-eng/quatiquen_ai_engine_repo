"""Context builder for fetching business and threat context."""

import asyncio
import time
from typing import Optional

from src.application.ports import CachePort, ThreatIntelPort
from src.core.logging.logger import get_logger
from src.domain.entities import Finding
from src.domain.repositories import IAssetRepository
from src.domain.value_objects import BusinessContext, ThreatContext
from src.engine.config import EngineConfig
from src.engine.engine_result import EngineResult, PipelineStage

logger = get_logger("quantiquan.engine.context_builder")


class ContextBuilder:
    """Fetches business and threat context for a finding."""

    def __init__(
        self,
        cache_port: CachePort,
        threat_intel_port: ThreatIntelPort,
        asset_repository: IAssetRepository,
        config: EngineConfig,
    ) -> None:
        """Initialize context builder.

        Args:
            cache_port: Cache port for caching contexts.
            threat_intel_port: Threat intel port.
            asset_repository: Asset repository.
            config: Engine configuration.
        """
        self.cache_port = cache_port
        self.threat_intel_port = threat_intel_port
        self.asset_repository = asset_repository
        self.config = config

    async def execute(self, result: EngineResult) -> bool:
        """Execute context building.

        Args:
            result: Engine result state.

        Returns:
            bool: True if successful, False otherwise.
        """
        finding = result.finding
        if finding is None:
            result.add_error(PipelineStage.CONTEXT_BUILDER, "Finding is None")
            return False

        try:
            # Fetch business context
            business_context = await self._fetch_business_context(finding)
            if business_context is None:
                result.add_error(PipelineStage.CONTEXT_BUILDER, "Business context not found")
                return False
            result.business_context = business_context

            # Fetch threat context (if CVE exists)
            if finding.has_cve:
                threat_context = await self._fetch_threat_context(finding.cve_id)
                result.threat_context = threat_context
            else:
                # Create empty threat context
                result.threat_context = ThreatContext.create(cve_id="")

            logger.debug(
                "Context built",
                finding_id=str(finding.id),
                has_business=bool(result.business_context),
                has_threat=bool(result.threat_context),
            )

            return True

        except Exception as exc:
            result.add_error(PipelineStage.CONTEXT_BUILDER, str(exc))
            logger.error(
                "Context builder failed",
                finding_id=str(finding.id),
                error=str(exc),
                exc_info=True,
            )
            return False

    async def _fetch_business_context(self, finding: Finding) -> Optional[BusinessContext]:
        """Fetch business context from cache or repository."""
        cache_key = f"business_context:{finding.asset_id}"
        try:
            cached = await self.cache_port.get(cache_key)
            if cached and isinstance(cached, BusinessContext):
                logger.debug("Business context cache hit", asset_id=str(finding.asset_id))
                return cached
        except Exception as exc:
            logger.warning("Cache get failed for business context", error=str(exc))

        # Fetch from repository
        context = await self.asset_repository.get_business_context(
            finding.asset_id,
            finding.tenant_id,
        )
        if context:
            try:
                await self.cache_port.set(cache_key, context, ttl=3600)
            except Exception as exc:
                logger.warning("Cache set failed for business context", error=str(exc))

        return context

    async def _fetch_threat_context(self, cve_id: str) -> ThreatContext:
        """Fetch threat context from cache or external source."""
        cache_key = f"threat_context:{cve_id}"
        try:
            cached = await self.cache_port.get(cache_key)
            if cached and isinstance(cached, ThreatContext):
                logger.debug("Threat context cache hit", cve_id=cve_id)
                return cached
        except Exception as exc:
            logger.warning("Cache get failed for threat context", error=str(exc))

        # Fetch from threat intel port
        context = await self.threat_intel_port.get_threat_context(cve_id)
        if context:
            try:
                await self.cache_port.set(cache_key, context, ttl=86400)
            except Exception as exc:
                logger.warning("Cache set failed for threat context", error=str(exc))

        return context