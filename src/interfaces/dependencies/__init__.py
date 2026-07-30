"""Dependency injection for FastAPI."""

from src.interfaces.dependencies.inject import (
    get_asset_repository,
    get_cache,
    get_container,
    get_decision_repository,
    get_evaluate_finding_use_case,
    get_finding_repository,
    get_get_decision_use_case,
    get_health_checker,
    get_recalculate_use_case,
    get_unit_of_work,
)

__all__ = [
    "get_asset_repository",
    "get_cache",
    "get_container",
    "get_decision_repository",
    "get_evaluate_finding_use_case",
    "get_finding_repository",
    "get_get_decision_use_case",
    "get_health_checker",
    "get_recalculate_use_case",
    "get_unit_of_work",
]