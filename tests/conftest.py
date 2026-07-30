"""Pytest configuration and fixtures."""

import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.core.config.settings import get_settings
from src.core.di.container import Container, get_container, reset_container
from src.core.logging.logger import get_logger
from src.domain.entities import Finding
from src.domain.value_objects import BusinessContext, ThreatContext
from src.infrastructure.cache.memory_cache import MemoryCache
from src.infrastructure.persistence.unit_of_work import UnitOfWork
from src.interfaces.middleware.exception_handler import setup_exception_handlers
from src.main import create_app

logger = get_logger("tests")


@pytest.fixture(autouse=True)
def reset_di_container() -> Generator:
    """Reset DI container before each test."""
    reset_container()
    yield
    reset_container()


@pytest.fixture
def container() -> Container:
    """Get DI container."""
    return get_container()


@pytest.fixture
def test_settings():
    """Get test settings."""
    return get_settings()


@pytest.fixture
def mock_cache() -> AsyncMock:
    """Mock cache port."""
    cache = AsyncMock(spec=MemoryCache)
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    cache.delete = AsyncMock()
    cache.exists = AsyncMock(return_value=False)
    return cache


@pytest.fixture
def mock_threat_intel() -> AsyncMock:
    """Mock threat intel port."""
    threat_intel = AsyncMock()
    threat_intel.get_threat_context = AsyncMock(
        return_value=ThreatContext.create(
            cve_id="CVE-2024-12345",
            epss_score=0.85,
            is_kev=True,
            has_poc=True,
        )
    )
    threat_intel.get_epss_score = AsyncMock(return_value=0.85)
    threat_intel.is_kev_listed = AsyncMock(return_value=True)
    threat_intel.has_public_exploit = AsyncMock(return_value=True)
    return threat_intel


@pytest.fixture
def mock_llm() -> AsyncMock:
    """Mock LLM port."""
    llm = AsyncMock()
    llm.generate_summary = AsyncMock(
        return_value="This is a critical finding affecting your payment system. Immediate action required."
    )
    llm.generate_recommendation_explanation = AsyncMock(
        return_value="Apply the patch immediately."
    )
    return llm


@pytest.fixture
def mock_event() -> AsyncMock:
    """Mock event port."""
    event = AsyncMock()
    event.publish = AsyncMock()
    event.publish_batch = AsyncMock()
    return event


@pytest.fixture
def mock_asset_repo() -> AsyncMock:
    """Mock asset repository."""
    asset_repo = AsyncMock()
    asset_repo.get_by_id = AsyncMock(
        return_value=None
    )
    asset_repo.get_business_context = AsyncMock(
        return_value=BusinessContext(
            asset_id=MagicMock(),
            importance_tier=90,
            owner_id=MagicMock(),
            data_classification="regulated",
            compliance_scopes=["PCI"],
            exposure="customer-facing",
            is_production=True,
            downstream_dependents=15,
            revenue_impact="high",
        )
    )
    return asset_repo


@pytest.fixture
def mock_finding_repo() -> AsyncMock:
    """Mock finding repository."""
    finding_repo = AsyncMock()
    finding_repo.get_by_id = AsyncMock(return_value=None)
    finding_repo.save = AsyncMock()
    finding_repo.update = AsyncMock()
    finding_repo.get_open_findings_by_asset = AsyncMock(return_value=[])
    return finding_repo


@pytest.fixture
def mock_decision_repo() -> AsyncMock:
    """Mock decision repository."""
    decision_repo = AsyncMock()
    decision_repo.get_by_finding_id = AsyncMock(return_value=None)
    decision_repo.save = AsyncMock()
    decision_repo.update = AsyncMock()
    decision_repo.get_recent_decisions = AsyncMock(return_value=[])
    return decision_repo


@pytest.fixture
def mock_uow() -> AsyncMock:
    """Mock unit of work."""
    uow = AsyncMock(spec=UnitOfWork)
    uow.finding_repository = AsyncMock()
    uow.decision_repository = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock()
    uow.commit = AsyncMock()
    uow.rollback = AsyncMock()
    uow.begin = AsyncMock()
    return uow


@pytest.fixture
def sample_finding() -> Finding:
    """Sample finding for testing."""
    from uuid import uuid4
    import time
    from src.core.constants.enums import FindingSource, FindingStatus

    return Finding(
        id=uuid4(),
        tenant_id=uuid4(),
        asset_id=uuid4(),
        source=FindingSource.INTERNAL_SCANNER,
        source_finding_id="scan-123",
        cve_id="CVE-2024-12345",
        title="Critical vulnerability in payment API",
        description="Unpatched RCE vulnerability in payment gateway",
        raw_severity=8.5,
        raw_severity_scale="cvss_v3",
        status=FindingStatus.OPEN,
        detected_at=int(time.time()) - 86400,
        raw_payload={"scanner": "test", "details": "..."},
        created_at=int(time.time()) - 86400,
        updated_at=int(time.time()) - 86400,
    )


@pytest.fixture
def sample_business_context() -> BusinessContext:
    """Sample business context."""
    from uuid import uuid4
    from src.core.constants.enums import DataSensitivity, ComplianceScope, ExposureLevel

    return BusinessContext(
        asset_id=uuid4(),
        importance_tier=90,
        owner_id=uuid4(),
        data_classification=DataSensitivity.REGULATED,
        compliance_scopes=[ComplianceScope.PCI],
        exposure=ExposureLevel.CUSTOMER_FACING,
        is_production=True,
        downstream_dependents=15,
        revenue_impact="high",
    )


@pytest.fixture
def sample_threat_context() -> ThreatContext:
    """Sample threat context."""
    return ThreatContext.create(
        cve_id="CVE-2024-12345",
        epss_score=0.85,
        is_kev=True,
        has_poc=True,
    )


@pytest.fixture
def app():
    """Create FastAPI app for testing."""
    app = create_app()
    setup_exception_handlers(app)
    return app


@pytest.fixture
def client(app) -> TestClient:
    """Return test client."""
    return TestClient(app)


@pytest.fixture
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()