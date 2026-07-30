"""Integration tests for repositories using testcontainers or mocked SQLAlchemy."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.domain.entities import Decision, Finding
from src.infrastructure.persistence.models import Base
from src.infrastructure.persistence.repositories import DecisionRepository, FindingRepository
from src.infrastructure.persistence.unit_of_work import UnitOfWork


@pytest.mark.asyncio
async def test_finding_repository_save_and_get():
    """Test saving and retrieving a finding."""
    # Use in-memory SQLite for testing
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        repo = FindingRepository(session)
        finding = MagicMock(spec=Finding)
        finding.id = MagicMock()
        finding.tenant_id = MagicMock()
        finding.asset_id = MagicMock()
        finding.source = "internal_scanner"
        finding.source_finding_id = "scan-123"
        finding.title = "Test"
        finding.description = "Desc"
        finding.raw_severity = 7.5
        finding.raw_severity_scale = "cvss_v3"
        finding.status = "open"
        finding.detected_at = 1234567890
        finding.raw_payload = {}
        finding.cve_id = None
        finding.created_at = 1234567890
        finding.updated_at = 1234567890

        # Save
        await repo.save(finding)
        await session.commit()

        # Retrieve
        retrieved = await repo.get_by_id(finding.id, finding.tenant_id)
        assert retrieved is not None
        assert retrieved.id == finding.id


@pytest.mark.asyncio
async def test_unit_of_work_commit():
    """Test unit of work commit."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    uow = UnitOfWork(session_factory)

    async with uow:
        # Perform operations
        pass
    # Should commit without error