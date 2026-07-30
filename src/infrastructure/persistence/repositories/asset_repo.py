"""Asset repository implementation using SQLAlchemy."""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions.infrastructure import DatabaseError
from src.core.logging.logger import get_logger
from src.domain.entities import Asset
from src.domain.repositories import IAssetRepository
from src.domain.value_objects import BusinessContext
from src.infrastructure.persistence.mappers import AssetMapper
from src.infrastructure.persistence.models import AssetModel

logger = get_logger("quantiquan.infrastructure.asset_repo")


class AssetRepository(IAssetRepository):
    """SQLAlchemy implementation of IAssetRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: SQLAlchemy async session.
        """
        self.session = session

    async def get_by_id(self, asset_id: UUID, tenant_id: UUID) -> Optional[Asset]:
        """Get an asset by ID."""
        try:
            stmt = select(AssetModel).where(
                AssetModel.id == asset_id,
                AssetModel.tenant_id == tenant_id,
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()
            return AssetMapper.to_domain(model) if model else None
        except Exception as exc:
            logger.error("Failed to get asset", asset_id=str(asset_id), error=str(exc), exc_info=True)
            raise DatabaseError(f"Failed to get asset: {exc}", operation="get_by_id") from exc

    async def get_business_context(self, asset_id: UUID, tenant_id: UUID) -> Optional[BusinessContext]:
        """Get business context for an asset."""
        try:
            stmt = select(AssetModel).where(
                AssetModel.id == asset_id,
                AssetModel.tenant_id == tenant_id,
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()
            if not model:
                return None
            return AssetMapper.to_business_context(model)
        except Exception as exc:
            logger.error("Failed to get business context", asset_id=str(asset_id), error=str(exc), exc_info=True)
            raise DatabaseError(f"Failed to get business context: {exc}", operation="get_business_context") from exc