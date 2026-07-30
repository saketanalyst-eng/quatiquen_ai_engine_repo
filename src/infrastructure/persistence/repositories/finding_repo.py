"""Finding repository implementation using SQLAlchemy."""

from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions.infrastructure import DatabaseError
from src.core.logging.logger import get_logger
from src.domain.entities import Finding
from src.domain.repositories import IFindingRepository
from src.infrastructure.persistence.mappers import FindingMapper
from src.infrastructure.persistence.models import FindingModel

logger = get_logger("quantiquan.infrastructure.finding_repo")


class FindingRepository(IFindingRepository):
    """SQLAlchemy implementation of IFindingRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: SQLAlchemy async session.
        """
        self.session = session

    async def get_by_id(self, finding_id: UUID, tenant_id: UUID) -> Optional[Finding]:
        """Get a finding by ID."""
        try:
            stmt = select(FindingModel).where(
                FindingModel.id == finding_id,
                FindingModel.tenant_id == tenant_id,
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()
            return FindingMapper.to_domain(model) if model else None
        except Exception as exc:
            logger.error("Failed to get finding", finding_id=str(finding_id), error=str(exc), exc_info=True)
            raise DatabaseError(f"Failed to get finding: {exc}", operation="get_by_id") from exc

    async def save(self, finding: Finding) -> None:
        """Save a new finding."""
        try:
            model = FindingMapper.to_model(finding)
            self.session.add(model)
        except Exception as exc:
            logger.error("Failed to save finding", finding_id=str(finding.id), error=str(exc), exc_info=True)
            raise DatabaseError(f"Failed to save finding: {exc}", operation="save") from exc

    async def update(self, finding: Finding) -> None:
        """Update an existing finding."""
        try:
            stmt = (
                update(FindingModel)
                .where(
                    FindingModel.id == finding.id,
                    FindingModel.tenant_id == finding.tenant_id,
                )
                .values(
                    status=finding.status.value,
                    updated_at=__import__("datetime").datetime.utcnow(),
                )
            )
            await self.session.execute(stmt)
        except Exception as exc:
            logger.error("Failed to update finding", finding_id=str(finding.id), error=str(exc), exc_info=True)
            raise DatabaseError(f"Failed to update finding: {exc}", operation="update") from exc

    async def get_open_findings_by_asset(self, asset_id: UUID, tenant_id: UUID) -> list[Finding]:
        """Get all open findings for an asset."""
        try:
            stmt = select(FindingModel).where(
                FindingModel.asset_id == asset_id,
                FindingModel.tenant_id == tenant_id,
                FindingModel.status == "open",
            )
            result = await self.session.execute(stmt)
            models = result.scalars().all()
            return [FindingMapper.to_domain(m) for m in models]
        except Exception as exc:
            logger.error("Failed to get open findings", asset_id=str(asset_id), error=str(exc), exc_info=True)
            raise DatabaseError(f"Failed to get open findings: {exc}", operation="get_open_findings_by_asset") from exc