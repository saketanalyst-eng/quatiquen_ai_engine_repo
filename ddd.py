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
    """Get the global DI container.

    Returns:
        Container: DI container instance.
    """
    return get_container()


def get_unit_of_work(container: Container = Depends(get_container_dep)) -> IUnitOfWork:
    """Get unit of work.

    Args:
        container: DI container.

    Returns:
        IUnitOfWork: Unit of work.
    """
    return container.resolve(IUnitOfWork)


def get_health_checker(container: Container = Depends(get_container_dep)) -> HealthChecker:
    """Get health checker instance.

    Args:
        container: DI container.

    Returns:
        HealthChecker: Health checker instance.
    """
    return container.resolve(HealthChecker)


def get_cache(container: Container = Depends(get_container_dep)) -> CachePort:
    """Get cache instance.

    Args:
        container: DI container.

    Returns:
        CachePort: Cache port.
    """
    return container.resolve(CachePort)


def get_asset_repository(
    container: Container = Depends(get_container_dep),
    uow: IUnitOfWork = Depends(get_unit_of_work),
) -> IAssetRepository:
    """Get asset repository.

    Args:
        container: DI container.
        uow: Unit of work.

    Returns:
        IAssetRepository: Asset repository.
    """
    return uow.asset_repository  # type: ignore


def get_finding_repository(
    container: Container = Depends(get_container_dep),
    uow: IUnitOfWork = Depends(get_unit_of_work),
) -> IFindingRepository:
    """Get finding repository.

    Args:
        container: DI container.
        uow: Unit of work.

    Returns:
        IFindingRepository: Finding repository.
    """
    return uow.finding_repository


def get_decision_repository(
    container: Container = Depends(get_container_dep),
    uow: IUnitOfWork = Depends(get_unit_of_work),
) -> IDecisionRepository:
    """Get decision repository.

    Args:
        container: DI container.
        uow: Unit of work.

    Returns:
        IDecisionRepository: Decision repository.
    """
    return uow.decision_repository


def get_threat_intel_port(container: Container = Depends(get_container_dep)) -> ThreatIntelPort:
    """Get threat intel port.

    Args:
        container: DI container.

    Returns:
        ThreatIntelPort: Threat intel port.
    """
    return container.resolve(ThreatIntelPort)


def get_llm_port(container: Container = Depends(get_container_dep)) -> LLMPort:
    """Get LLM port.

    Args:
        container: DI container.

    Returns:
        LLMPort: LLM port.
    """
    return container.resolve(LLMPort)


def get_event_port(container: Container = Depends(get_container_dep)) -> EventPort:
    """Get event port.

    Args:
        container: DI container.

    Returns:
        EventPort: Event port.
    """
    return container.resolve(EventPort)


def get_strategy(container: Container = Depends(get_container_dep)) -> Strategy:
    """Get scoring strategy.

    Args:
        container: DI container.

    Returns:
        Strategy: Strategy instance.
    """
    return DefaultStrategy()


def get_engine_config(container: Container = Depends(get_container_dep)) -> EngineConfig:
    """Get engine configuration.

    Args:
        container: DI container.

    Returns:
        EngineConfig: Engine config.
    """
    return DEFAULT_CONFIG


def get_orchestrator(
    cache: CachePort = Depends(get_cache),
    threat_intel: ThreatIntelPort = Depends(get_threat_intel_port),
    llm: LLMPort = Depends(get_llm_port),
    event: EventPort = Depends(get_event_port),
    asset_repo: IAssetRepository = Depends(get_asset_repository),
    config: EngineConfig = Depends(get_engine_config),
    strategy: Strategy = Depends(get_strategy),
) -> Orchestrator:
    """Get orchestrator instance.

    Args:
        cache: Cache port.
        threat_intel: Threat intel port.
        llm: LLM port.
        event: Event port.
        asset_repo: Asset repository.
        config: Engine config.
        strategy: Scoring strategy.

    Returns:
        Orchestrator: Orchestrator instance.
    """
    return Orchestrator(
        cache_port=cache,
        threat_intel_port=threat_intel,
        llm_port=llm,
        event_port=event,
        asset_repository=asset_repo,
        config=config,
        strategy=strategy,
    )


def get_evaluate_finding_use_case(
    finding_repo: IFindingRepository = Depends(get_finding_repository),
    decision_repo: IDecisionRepository = Depends(get_decision_repository),
    uow: IUnitOfWork = Depends(get_unit_of_work),
    cache: CachePort = Depends(get_cache),
    threat_intel: ThreatIntelPort = Depends(get_threat_intel_port),
    llm: LLMPort = Depends(get_llm_port),
    event: EventPort = Depends(get_event_port),
    asset_repo: IAssetRepository = Depends(get_asset_repository),
) -> EvaluateFindingUseCase:
    """Get evaluate finding use case.

    Args:
        finding_repo: Finding repository.
        decision_repo: Decision repository.
        uow: Unit of work.
        cache: Cache port.
        threat_intel: Threat intel port.
        llm: LLM port.
        event: Event port.
        asset_repo: Asset repository.

    Returns:
        EvaluateFindingUseCase: Use case instance.
    """
    return EvaluateFindingUseCase(
        finding_repository=finding_repo,
        decision_repository=decision_repo,
        unit_of_work=uow,
        cache_port=cache,
        threat_intel_port=threat_intel,
        llm_port=llm,
        event_port=event,
        asset_repository=asset_repo,
    )


def get_get_decision_use_case(
    decision_repo: IDecisionRepository = Depends(get_decision_repository),
) -> GetDecisionUseCase:
    """Get get decision use case.

    Args:
        decision_repo: Decision repository.

    Returns:
        GetDecisionUseCase: Use case instance.
    """
    return GetDecisionUseCase(decision_repository=decision_repo)


def get_recalculate_use_case(
    finding_repo: IFindingRepository = Depends(get_finding_repository),
    decision_repo: IDecisionRepository = Depends(get_decision_repository),
    uow: IUnitOfWork = Depends(get_unit_of_work),
    asset_repo: IAssetRepository = Depends(get_asset_repository),
    threat_intel: ThreatIntelPort = Depends(get_threat_intel_port),
) -> RecalculateUseCase:
    """Get recalculate use case.

    Args:
        finding_repo: Finding repository.
        decision_repo: Decision repository.
        uow: Unit of work.
        asset_repo: Asset repository.
        threat_intel: Threat intel port.

    Returns:
        RecalculateUseCase: Use case instance.
    """
    return RecalculateUseCase(
        finding_repository=finding_repo,
        decision_repository=decision_repo,
        unit_of_work=uow,
        asset_repository=asset_repo,
        threat_intel_port=threat_intel,
    )