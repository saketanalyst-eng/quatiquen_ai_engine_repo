"""Finding repository implementation using SQLAlchemy."""

from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
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

    async def get_by_source(
        self,
        tenant_id: UUID,
        source: str,
        source_finding_id: str,
    ) -> Optional[Finding]:
        """
        Get a finding by its logical identity: (tenant_id, source, source_finding_id).
        This is the same key used for UPSERT conflict resolution.
        """
        try:
            stmt = select(FindingModel).where(
                FindingModel.tenant_id == str(tenant_id),
                FindingModel.source == source,
                FindingModel.source_finding_id == source_finding_id,
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()
            return FindingMapper.to_domain(model) if model else None
        except Exception as exc:
            logger.error(
                "Failed to get finding by source",
                tenant_id=str(tenant_id),
                source=source,
                source_finding_id=source_finding_id,
                error=str(exc),
                exc_info=True,
            )
            raise DatabaseError(
                f"Failed to get finding by source: {exc}",
                operation="get_by_source",
            ) from exc

    async def save(self, finding: Finding) -> None:
        """
        Save a finding using PostgreSQL UPSERT (idempotent).

        Conflict target: (tenant_id, source, source_finding_id) — tenant-scoped.

        Behaviour:
          • If a finding with the same logical identity already exists, UPDATE
            the existing row in place (title, description, severity, etc.).
          • The original `finding.id` is preserved (id not in the SET clause),
            so downstream risk / decision / history rows remain linked to the
            same logical finding.
          • Historical risk/decision rows are never deleted or overwritten.
          • Each recalculation produces a new `job_id` in the use case, which
            results in a new `risk_scores` row — full history is retained.
        """
        try:
            model = FindingMapper.to_model(finding)

            # Ensure primary key is set (UPSERT requires a concrete id)
            if model.id is None:
                model.id = str(uuid4())

            model_dict = {
                "id": model.id,
                "tenant_id": model.tenant_id,
                "asset_id": model.asset_id,
                "source": model.source,
                "source_finding_id": model.source_finding_id,
                "cve_id": model.cve_id,
                "title": model.title,
                "description": model.description,
                "raw_severity": model.raw_severity,
                "raw_severity_scale": model.raw_severity_scale,
                "status": model.status,
                "detected_at": model.detected_at,
                "raw_payload": model.raw_payload,
            }

            # UPSERT: ON CONFLICT (tenant_id, source, source_finding_id) DO UPDATE
            #   • id NOT in SET → original finding.id preserved
            #   • created_at NOT in SET → original timestamp preserved
            #   • updated_at refreshed on every recalculation
            stmt = insert(FindingModel).values(**model_dict)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_finding_source",
                set_={
                    "asset_id": stmt.excluded.asset_id,
                    "cve_id": stmt.excluded.cve_id,
                    "title": stmt.excluded.title,
                    "description": stmt.excluded.description,
                    "raw_severity": stmt.excluded.raw_severity,
                    "raw_severity_scale": stmt.excluded.raw_severity_scale,
                    "status": stmt.excluded.status,
                    "detected_at": stmt.excluded.detected_at,
                    "raw_payload": stmt.excluded.raw_payload,
                    "updated_at": func.now(),
                },
            )

            await self.session.execute(stmt)

        except Exception as exc:
            logger.error(
                "Failed to save finding",
                finding_id=str(finding.id),
                source_finding_id=str(getattr(finding, "source_finding_id", None)),
                error=str(exc),
                exc_info=True,
            )
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