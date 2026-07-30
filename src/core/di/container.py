"""Dependency Injection container for the application.

This container provides a central registry for all dependencies,
implementing the Service Locator pattern with dependency injection.
"""

from typing import Any, Callable, Dict, Optional, Type, TypeVar

from src.core.logging.logger import get_logger

logger = get_logger("quantiquan.di")

T = TypeVar("T")


class Container:
    """Dependency injection container.

    This container holds factories for creating dependencies. Dependencies
    are lazily instantiated and cached as singletons.
    """

    def __init__(self) -> None:
        """Initialize the DI container."""
        self._factories: Dict[str, Callable[[], Any]] = {}
        self._instances: Dict[str, Any] = {}
        self._singletons: Dict[str, bool] = {}
        self._initialized = False

    def register(
        self,
        interface: Type[T],
        factory: Callable[[], T],
        singleton: bool = True,
    ) -> None:
        """Register a dependency.

        Args:
            interface: The interface or type to register.
            factory: Factory function that creates the dependency.
            singleton: Whether to use singleton lifetime.
        """
        key = self._get_key(interface)
        self._factories[key] = factory
        self._singletons[key] = singleton
        logger.debug("Dependency registered", interface=interface.__name__, singleton=singleton)

    def register_instance(
        self,
        interface: Type[T],
        instance: T,
    ) -> None:
        """Register an existing instance.

        Args:
            interface: The interface or type to register.
            instance: The instance to use.
        """
        key = self._get_key(interface)
        self._instances[key] = instance
        self._singletons[key] = True
        logger.debug("Instance registered", interface=interface.__name__)

    def resolve(self, interface: Type[T]) -> T:
        """Resolve a dependency.

        Args:
            interface: The interface or type to resolve.

        Returns:
            T: The resolved dependency.

        Raises:
            KeyError: If the dependency is not registered.
        """
        key = self._get_key(interface)

        # Check if instance already exists
        if key in self._instances:
            return self._instances[key]

        # Check if factory exists
        factory = self._factories.get(key)
        if factory is None:
            raise KeyError(f"Dependency not registered: {interface.__name__}")

        # Create instance
        instance = factory()

        # Cache if singleton
        if self._singletons.get(key, False):
            self._instances[key] = instance

        logger.debug("Dependency resolved", interface=interface.__name__)
        return instance

    def get(self, interface: Type[T]) -> Optional[T]:
        """Get a dependency without raising an error.

        Args:
            interface: The interface or type to resolve.

        Returns:
            Optional[T]: The resolved dependency or None.
        """
        try:
            return self.resolve(interface)
        except KeyError:
            return None

    def clear(self) -> None:
        """Clear all registered dependencies."""
        self._factories.clear()
        self._instances.clear()
        self._singletons.clear()
        self._initialized = False
        logger.debug("Container cleared")

    def _get_key(self, interface: Type) -> str:
        """Get a unique key for an interface.

        Args:
            interface: The interface type.

        Returns:
            str: Unique key.
        """
        return f"{interface.__module__}.{interface.__name__}"

    @property
    def initialized(self) -> bool:
        """Check if container is initialized.

        Returns:
            bool: True if initialized.
        """
        return self._initialized

    def initialize(self) -> None:
        """Initialize the container with core dependencies."""
        if self._initialized:
            return

        # Register core services
        self._register_core_dependencies()
        self._initialized = True
        logger.info("Container initialized")

    def _register_core_dependencies(self) -> None:
        """Register core dependencies."""
        # Import here to avoid circular imports
        from src.application.ports import CachePort, EventPort, LLMPort, ThreatIntelPort
        from src.core.config.settings import get_settings
        from src.core.logging.logger import get_logger as get_core_logger
        from src.core.monitoring.health import HealthChecker
        from src.core.monitoring.metrics import get_metrics_collector
        from src.core.security.api_key import APIKeyHandler
        from src.core.security.authentication import AuthenticationHandler
        from src.core.security.jwt import JWTHandler
        from src.domain.repositories import IUnitOfWork
        from src.infrastructure.cache.memory_cache import MemoryCache
        from src.infrastructure.cache.redis_cache import RedisCache
        from src.infrastructure.di.providers import InfrastructureProviders
        from src.infrastructure.external.epss_client import EPSSClient
        from src.infrastructure.messaging.event_publisher import EventPublisher
        from src.infrastructure.persistence.unit_of_work import UnitOfWork
        from src.ai.orchestration.ai_orchestrator import AIOrchestrator

        # Settings
        self.register(
            get_settings.__class__,
            get_settings,
            singleton=True,
        )

        # Logger
        self.register(
            type(get_core_logger("")),
            lambda: get_core_logger("quantiquan"),
            singleton=True,
        )

        # Health Checker
        self.register(HealthChecker, lambda: HealthChecker(), singleton=True)

        # Metrics
        self.register(
            type(get_metrics_collector()),
            get_metrics_collector,
            singleton=True,
        )

        # JWT Handler
        def _jwt_factory():
            settings = get_settings()
            return JWTHandler(
                secret=settings.jwt_secret.get_secret_value(),
                algorithm=settings.jwt_algorithm,
                expiry_minutes=settings.jwt_expiry_minutes,
            )
        self.register(JWTHandler, _jwt_factory, singleton=True)

        # API Key Handler
        def _api_key_factory():
            return APIKeyHandler()
        self.register(APIKeyHandler, _api_key_factory, singleton=True)

        # Authentication Handler
        def _auth_factory():
            settings = get_settings()
            return AuthenticationHandler(
                jwt_handler=self.resolve(JWTHandler),
                api_key_handler=self.resolve(APIKeyHandler),
                api_key_header=settings.api_key_header,
            )
        self.register(AuthenticationHandler, _auth_factory, singleton=True)

        # Unit of Work
        self.register(IUnitOfWork, InfrastructureProviders.create_unit_of_work, singleton=False)

        # ---- Port registrations ----

        # Cache Port
        def _cache_factory():
            settings = get_settings()
            if settings.environment == "development":
                return MemoryCache()
            return InfrastructureProviders.create_cache()  # RedisCache
        self.register(CachePort, _cache_factory, singleton=True)

        # Threat Intel Port
        self.register(ThreatIntelPort, InfrastructureProviders.create_epss_client, singleton=True)

        # LLM Port – use AIOrchestrator (it should implement LLMPort)
        def _llm_factory():
            # Create AIOrchestrator with default providers
            return AIOrchestrator()
        self.register(LLMPort, _llm_factory, singleton=True)

        # Event Port
        self.register(EventPort, InfrastructureProviders.create_event_publisher, singleton=True)

        logger.debug("Core dependencies registered")


# Global container instance
_container: Optional[Container] = None


def get_container() -> Container:
    """Get the global container instance.

    Returns:
        Container: Global container instance.

    Raises:
        RuntimeError: If container is not initialized.
    """
    global _container
    if _container is None:
        _container = Container()
        _container.initialize()
    return _container


def reset_container() -> None:
    """Reset the global container.

    This should only be used in tests.
    """
    global _container
    if _container is not None:
        _container.clear()
        _container = None
    logger.debug("Container reset")