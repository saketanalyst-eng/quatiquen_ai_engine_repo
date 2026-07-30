"""Cache port for key-value storage."""

from abc import ABC, abstractmethod
from typing import Any, Optional


class CachePort(ABC):
    """Abstract interface for caching operations."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache.

        Args:
            key: Cache key.

        Returns:
            Optional[Any]: Cached value or None if not found.
        """
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in cache with optional TTL.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl: Time-to-live in seconds.
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a value from cache.

        Args:
            key: Cache key.
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache.

        Args:
            key: Cache key.

        Returns:
            bool: True if exists.
        """
        pass

    @abstractmethod
    async def get_async(self, key: str) -> Optional[Any]:
        """Async get alias."""
        return await self.get(key)

    @abstractmethod
    async def set_async(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Async set alias."""
        await self.set(key, value, ttl)

    @abstractmethod
    async def delete_pattern(self, pattern: str) -> None:
        """Delete all keys matching a pattern.

        Args:
            pattern: Key pattern (e.g., "threat:*").
        """
        pass