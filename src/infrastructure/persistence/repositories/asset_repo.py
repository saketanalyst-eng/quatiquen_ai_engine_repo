"""Asset repository implementation using SQLAlchemy."""

from typing import Optional
from uuid import UUID

from sqlalchemy import String, cast, select
from sqlalchemy.dialects.postgresql import insert
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
                cast(AssetModel.id, String) == str(asset_id),
                cast(AssetModel.tenant_id, String) == str(tenant_id),
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
                cast(AssetModel.id, String) == str(asset_id),
                cast(AssetModel.tenant_id, String) == str(tenant_id),
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()
            if not model:
                return None
            return AssetMapper.to_business_context(model)
        except Exception as exc:
            logger.error("Failed to get business context", asset_id=str(asset_id), error=str(exc), exc_info=True)
            raise DatabaseError(f"Failed to get business context: {exc}", operation="get_business_context") from exc

    # -----------------------------------------------------------------------
    # PASSIVE DISCOVERY: auto-create asset on first reference
    # -----------------------------------------------------------------------
    async def create_if_missing(
        self,
        asset_id: UUID,
        tenant_id: UUID,
        name: Optional[str] = None,
        asset_type: str = "unknown",
    ) -> None:
        """Create an asset with safe defaults if it doesn't already exist.

        Called when a finding references an asset we haven't seen before.
        Never overwrites an existing asset — only creates when absent.

        Defaults are intentionally conservative:
          • importance_tier = 50 (neutral midpoint)
          • data_classification = 'internal'
          • exposure = 'internal-only'
          • is_production = False
          • compliance_scopes = []
          • revenue_impact = 'none'
        """
        try:
            model_dict = {
                "id": asset_id,
                "tenant_id": tenant_id,
                "name": name or f"Auto-discovered asset {str(asset_id)[:8]}",
                "asset_type": asset_type,
                "importance_tier": 50,
                "owner_id": None,
                "data_classification": "internal",
                "compliance_scopes": [],
                "exposure": "internal-only",
                "is_production": False,
                "downstream_dependents": 0,
                "revenue_impact": "none",
            }

            # INSERT ... ON CONFLICT DO NOTHING → creates only if absent.
            # Never overwrites an existing asset's enriched metadata.
            stmt = insert(AssetModel).values(**model_dict).on_conflict_do_nothing(
                index_elements=["id"]
            )
            await self.session.execute(stmt)

            logger.info(
                "Asset auto-created (passive discovery)",
                asset_id=str(asset_id),
                tenant_id=str(tenant_id),
            )
        except Exception as exc:
            logger.error(
                "Failed to auto-create asset",
                asset_id=str(asset_id),
                error=str(exc),
                exc_info=True,
            )
            raise DatabaseError(
                f"Failed to auto-create asset: {exc}",
                operation="create_if_missing",
            ) from exc