"""Dependency injection functions for FastAPI."""

from fastapi import Depends

from src.application.ports import CachePort, EventPort, LLMPort, ThreatIntelPort
from src.application.use_cases import EvaluateFindingUseCase, GetDecisionUseCase, RecalculateUseCase
from src.core.di.container import Container, get_container
from src.core.monitoring.health import HealthChecker
from src.domain.repositories import IAssetRepository, IDecisionRepository, IFindingRepository, IUnitOfWork
from src.engine.config import DEFAULT_CONFIG, EngineConfig
from src.engine.orchestrator import Orchestrator
from src.engine.strategies.base_strategy import Strategy
from src.engine.strategies.default_strategy import DefaultStrategy


def get_container_dep() -> Container:
    """Get the global DI container."""
    return get_container()


async def get_unit_of_work(container: Container = Depends(get_container_dep)) -> IUnitOfWork:
    """Get a Unit of Work instance and start it."""
    uow = container.resolve(IUnitOfWork)
    await uow.begin()
    return uow


def get_health_checker(container: Container = Depends(get_container_dep)) -> HealthChecker:
    """Get health checker instance."""
    return container.resolve(HealthChecker)


def get_cache(container: Container = Depends(get_container_dep)) -> CachePort:
    """Get cache instance."""
    return container.resolve(CachePort)


async def get_asset_repository(
    uow: IUnitOfWork = Depends(get_unit_of_work),
) -> IAssetRepository:
    """Get asset repository (UOW already started)."""
    return uow.asset_repository


async def get_finding_repository(
    uow: IUnitOfWork = Depends(get_unit_of_work),
) -> IFindingRepository:
    """Get finding repository (UOW already started)."""
    return uow.finding_repository


async def get_decision_repository(
    uow: IUnitOfWork = Depends(get_unit_of_work),
) -> IDecisionRepository:
    """Get decision repository (UOW already started)."""
    return uow.decision_repository


def get_threat_intel_port(container: Container = Depends(get_container_dep)) -> ThreatIntelPort:
    """Get threat intel port."""
    return container.resolve(ThreatIntelPort)


def get_llm_port(container: Container = Depends(get_container_dep)) -> LLMPort:
    """Get LLM port."""
    return container.resolve(LLMPort)


def get_event_port(container: Container = Depends(get_container_dep)) -> EventPort:
    """Get event port."""
    return container.resolve(EventPort)


def get_strategy(container: Container = Depends(get_container_dep)) -> Strategy:
    """Get scoring strategy."""
    return DefaultStrategy()


def get_engine_config(container: Container = Depends(get_container_dep)) -> EngineConfig:
    """Get engine configuration."""
    return DEFAULT_CONFIG


async def get_orchestrator(
    cache: CachePort = Depends(get_cache),
    threat_intel: ThreatIntelPort = Depends(get_threat_intel_port),
    llm: LLMPort = Depends(get_llm_port),
    event: EventPort = Depends(get_event_port),
    asset_repo: IAssetRepository = Depends(get_asset_repository),
    config: EngineConfig = Depends(get_engine_config),
    strategy: Strategy = Depends(get_strategy),
) -> Orchestrator:
    """Get orchestrator instance."""
    return Orchestrator(
        cache_port=cache,
        threat_intel_port=threat_intel,
        llm_port=llm,
        event_port=event,
        asset_repository=asset_repo,
        config=config,
        strategy=strategy,
    )


# ✅ FIXED: Use-case factories now only pass unit_of_work and ports
async def get_evaluate_finding_use_case(
    uow: IUnitOfWork = Depends(get_unit_of_work),
    cache: CachePort = Depends(get_cache),
    threat_intel: ThreatIntelPort = Depends(get_threat_intel_port),
    llm: LLMPort = Depends(get_llm_port),
    event: EventPort = Depends(get_event_port),
) -> EvaluateFindingUseCase:
    """Get evaluate finding use case."""
    return EvaluateFindingUseCase(
        unit_of_work=uow,
        cache_port=cache,
        threat_intel_port=threat_intel,
        llm_port=llm,
        event_port=event,
    )


async def get_get_decision_use_case(
    uow: IUnitOfWork = Depends(get_unit_of_work),
) -> GetDecisionUseCase:
    """Get get decision use case."""
    return GetDecisionUseCase(unit_of_work=uow)


async def get_recalculate_use_case(
    uow: IUnitOfWork = Depends(get_unit_of_work),
    threat_intel: ThreatIntelPort = Depends(get_threat_intel_port),
) -> RecalculateUseCase:
    """Get recalculate use case."""
    return RecalculateUseCase(
        unit_of_work=uow,
        threat_intel_port=threat_intel,
    )