"""Concrete providers for infrastructure dependencies."""

from typing import Optional

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.config.settings import get_settings
from src.infrastructure.cache.memory_cache import MemoryCache
from src.infrastructure.cache.redis_cache import RedisCache
from src.infrastructure.external.epss_client import EPSSClient
from src.infrastructure.external.kev_client import KEVClient
from src.infrastructure.external.virustotal_client import VirusTotalClient
from src.infrastructure.messaging.event_publisher import EventPublisher
from src.infrastructure.persistence.unit_of_work import UnitOfWork


class InfrastructureProviders:
    """Factory for infrastructure components."""

    @staticmethod
    def create_session_factory():
        """Create async session factory."""
        settings = get_settings()
        engine = create_async_engine(
            str(settings.database_url),
            echo=settings.debug,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
        )
        return async_sessionmaker(engine, expire_on_commit=False)

    @staticmethod
    def create_unit_of_work():
        """Create Unit of Work instance."""
        session_factory = InfrastructureProviders.create_session_factory()
        return UnitOfWork(session_factory)

    @staticmethod
    def create_cache():
        """Create cache instance based on environment."""
        settings = get_settings()
        if settings.environment == "development":
            return MemoryCache()
        else:
            return RedisCache(str(settings.redis_url), default_ttl=settings.redis_ttl_default)

    @staticmethod
    def create_epss_client():
        """Create EPSS client."""
        settings = get_settings()
        return EPSSClient(base_url=settings.epss_api_url)

    @staticmethod
    def create_kev_client():
        """Create KEV client."""
        settings = get_settings()
        return KEVClient(feed_url=settings.kev_feed_url)

    @staticmethod
    def create_virustotal_client():
        """Create VirusTotal client (optional, uses placeholder)."""
        return VirusTotalClient()

    @staticmethod
    def create_event_publisher():
        """Create event publisher."""
        settings = get_settings()
        return EventPublisher(str(settings.redis_url))

    @staticmethod
    def get_all_providers() -> dict:
        """Get all infrastructure provider instances."""
        return {
            "unit_of_work": InfrastructureProviders.create_unit_of_work(),
            "cache": InfrastructureProviders.create_cache(),
            "epss_client": InfrastructureProviders.create_epss_client(),
            "kev_client": InfrastructureProviders.create_kev_client(),
            "virustotal_client": InfrastructureProviders.create_virustotal_client(),
            "event_publisher": InfrastructureProviders.create_event_publisher(),
        }