"""Abstract repository interfaces for domain aggregates."""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from src.domain.entities import Asset, Decision, Finding, Recommendation
from src.domain.value_objects import BusinessContext, ThreatContext


class IFindingRepository(ABC):
    """Repository interface for finding aggregates."""

    @abstractmethod
    async def get_by_id(self, finding_id: UUID, tenant_id: UUID) -> Optional[Finding]:
        """Get a finding by its ID.

        Args:
            finding_id: Finding identifier.
            tenant_id: Tenant identifier.

        Returns:
            Optional[Finding]: Finding if found, else None.
        """
        pass

    @abstractmethod
    async def save(self, finding: Finding) -> None:
        """Save a finding.

        Args:
            finding: Finding entity to save.
        """
        pass

    @abstractmethod
    async def update(self, finding: Finding) -> None:
        """Update an existing finding.

        Args:
            finding: Finding entity with updated values.
        """
        pass

    @abstractmethod
    async def get_open_findings_by_asset(self, asset_id: UUID, tenant_id: UUID) -> list[Finding]:
        """Get all open findings for an asset.

        Args:
            asset_id: Asset identifier.
            tenant_id: Tenant identifier.

        Returns:
            list[Finding]: List of open findings.
        """
        pass


class IDecisionRepository(ABC):
    """Repository interface for decision aggregates."""

    @abstractmethod
    async def get_by_finding_id(self, finding_id: UUID, tenant_id: UUID) -> Optional[Decision]:
        """Get a decision by finding ID.

        Args:
            finding_id: Finding identifier.
            tenant_id: Tenant identifier.

        Returns:
            Optional[Decision]: Decision if found, else None.
        """
        pass

    @abstractmethod
    async def save(self, decision: Decision) -> None:
        """Save a decision.

        Args:
            decision: Decision aggregate to save.
        """
        pass

    @abstractmethod
    async def update(self, decision: Decision) -> None:
        """Update an existing decision.

        Args:
            decision: Decision aggregate with updated values.
        """
        pass

    @abstractmethod
    async def get_recent_decisions(self, tenant_id: UUID, limit: int = 100) -> list[Decision]:
        """Get most recent decisions for a tenant.

        Args:
            tenant_id: Tenant identifier.
            limit: Maximum number of decisions to return.

        Returns:
            list[Decision]: List of recent decisions.
        """
        pass


class IAssetRepository(ABC):
    """Repository interface for asset entities."""

    @abstractmethod
    async def get_by_id(self, asset_id: UUID, tenant_id: UUID) -> Optional[Asset]:
        """Get an asset by its ID.

        Args:
            asset_id: Asset identifier.
            tenant_id: Tenant identifier.

        Returns:
            Optional[Asset]: Asset if found, else None.
        """
        pass

    @abstractmethod
    async def get_business_context(self, asset_id: UUID, tenant_id: UUID) -> Optional[BusinessContext]:
        """Get business context for an asset.

        Args:
            asset_id: Asset identifier.
            tenant_id: Tenant identifier.

        Returns:
            Optional[BusinessContext]: Business context if found, else None.
        """
        pass


class IThreatIntelRepository(ABC):
    """Repository interface for threat intelligence."""

    @abstractmethod
    async def get_threat_context(self, cve_id: str) -> Optional[ThreatContext]:
        """Get threat context for a CVE.

        Args:
            cve_id: CVE identifier.

        Returns:
            Optional[ThreatContext]: Threat context if available, else None.
        """
        pass