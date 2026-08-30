"""Unit of Work implementation with SQLAlchemy."""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config.settings import get_settings
from src.core.exceptions.infrastructure import DatabaseError
from src.core.logging.logger import get_logger
from src.domain.repositories import IDecisionRepository, IFindingRepository, IUnitOfWork
from src.infrastructure.persistence.repositories import DecisionRepository, FindingRepository
from src.infrastructure.persistence.repositories.asset_repo import AssetRepository

logger = get_logger("quantiquan.infrastructure.unit_of_work")


# --- NEW P0.3: Factory function to create a dynamic session factory ---
def create_session_factory() -> async_sessionmaker:
    """Create an async session factory with dynamic database configuration.
    
    This factory reads the settings and creates the appropriate engine:
    - For 'test' environment with Supabase credentials → PostgreSQL + asyncpg
    - For all other environments → SQLite + aiosqlite (or the configured URL)
    
    Returns:
        async_sessionmaker: Configured session factory for the UnitOfWork.
    """
    settings = get_settings()
    
    # Get the dynamic database URL (handles Supabase for test environment)
    database_url = settings.get_database_url()
    
    # Determine if we're using PostgreSQL (for connection pool settings)
    is_postgres = "postgresql" in database_url
    
    # Create the async engine with appropriate pool settings
    engine = create_async_engine(
        database_url,
        echo=(settings.environment == "development"),
        pool_size=10 if is_postgres else 1,
        max_overflow=20 if is_postgres else 0,
        pool_pre_ping=True if is_postgres else False,
    )
    
    logger.info(
        "Database engine created",
        environment=settings.environment,
        is_postgres=is_postgres,
        pool_size=10 if is_postgres else 1,
    )
    
    return async_sessionmaker(
        engine,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


class UnitOfWork(IUnitOfWork):
    """SQLAlchemy implementation of Unit of Work."""

    def __init__(self, session_factory: async_sessionmaker) -> None:
        """Initialize unit of work.

        Args:
            session_factory: Async session factory.
        """
        self.session_factory = session_factory
        self.session: Optional[AsyncSession] = None
        self._finding_repo: Optional[FindingRepository] = None
        self._decision_repo: Optional[DecisionRepository] = None
        self._asset_repo: Optional[AssetRepository] = None

    @property
    def finding_repository(self) -> IFindingRepository:
        """Get finding repository."""
        if self._finding_repo is None:
            raise RuntimeError("Unit of work not initialized")
        return self._finding_repo

    @property
    def decision_repository(self) -> IDecisionRepository:
        """Get decision repository."""
        if self._decision_repo is None:
            raise RuntimeError("Unit of work not initialized")
        return self._decision_repo

    @property
    def asset_repository(self) -> AssetRepository:
        """Get asset repository."""
        if self._asset_repo is None:
            raise RuntimeError("Unit of work not initialized")
        return self._asset_repo

    async def __aenter__(self) -> "UnitOfWork":
        """Enter context manager."""
        await self.begin()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager."""
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()
        if self.session:
            await self.session.close()

    async def begin(self) -> None:
        """Begin transaction.

        This method is idempotent: if already begun, it does nothing.
        """
        if self.session is None:
            self.session = self.session_factory()
            self._finding_repo = FindingRepository(self.session)
            self._decision_repo = DecisionRepository(self.session)
            self._asset_repo = AssetRepository(self.session)
            logger.debug("Transaction begun")
        else:
            logger.debug("Transaction already begun")

    async def commit(self) -> None:
        """Commit transaction."""
        if self.session:
            try:
                await self.session.commit()
                logger.debug("Transaction committed")
            except Exception as exc:
                raise DatabaseError(f"Commit failed: {exc}", operation="commit") from exc

    async def rollback(self) -> None:
        """Rollback transaction."""
        if self.session:
            try:
                await self.session.rollback()
                logger.debug("Transaction rolled back")
            except Exception as exc:
                raise DatabaseError(f"Rollback failed: {exc}", operation="rollback") from exc