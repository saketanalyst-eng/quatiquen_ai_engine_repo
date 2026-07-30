"""Unit of Work pattern for transaction management."""

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from src.domain.repositories.interfaces import IDecisionRepository, IFindingRepository


class IUnitOfWork(ABC):
    """Unit of Work interface for managing transactions."""

    @property
    @abstractmethod
    def finding_repository(self) -> IFindingRepository:
        """Get the finding repository."""
        pass

    @property
    @abstractmethod
    def decision_repository(self) -> IDecisionRepository:
        """Get the decision repository."""
        pass

    @abstractmethod
    async def __aenter__(self) -> "IUnitOfWork":
        """Enter the context manager."""
        pass

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context manager, committing or rolling back."""
        pass

    @abstractmethod
    async def commit(self) -> None:
        """Commit the current transaction."""
        pass

    @abstractmethod
    async def rollback(self) -> None:
        """Rollback the current transaction."""
        pass

    @abstractmethod
    async def begin(self) -> None:
        """Begin a new transaction."""
        pass


# Utility context manager for easier use
@asynccontextmanager
async def unit_of_work(uow: IUnitOfWork) -> AsyncGenerator[IUnitOfWork, None]:
    """Context manager for unit of work.

    Args:
        uow: Unit of work instance.

    Yields:
        IUnitOfWork: The unit of work.
    """
    async with uow:
        yield uow 