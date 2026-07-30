"""Event port for publishing domain events."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class EventPort(ABC):
    """Abstract interface for publishing events."""

    @abstractmethod
    async def publish(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Publish an event.

        Args:
            event_type: Type of event (e.g., "finding.scored").
            payload: Event payload.
        """
        pass

    @abstractmethod
    async def publish_batch(self, events: list[tuple[str, Dict[str, Any]]]) -> None:
        """Publish multiple events in batch.

        Args:
            events: List of (event_type, payload) tuples.
        """
        pass