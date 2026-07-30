"""In-memory cache implementation (for development/testing)."""

import time
from typing import Any, Dict, Optional

from src.core.exceptions.infrastructure import CacheError
from src.core.logging.logger import get_logger

logger = get_logger("quantiquan.infrastructure.memory_cache")


class MemoryCache:
    """In-memory cache adapter implementing CachePort."""

    def __init__(self) -> None:
        """Initialize memory cache."""
        self._data: Dict[str, tuple[Any, int]] = {}  # key -> (value, expiry_timestamp)
        self.default_ttl = 300

    def _clean(self) -> None:
        """Remove expired entries."""
        now = time.time()
        expired = [k for k, (_, exp) in self._data.items() if exp < now]
        for k in expired:
            del self._data[k]

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        self._clean()
        item = self._data.get(key)
        if item is None:
            return None
        value, expiry = item
        if expiry < time.time():
            del self._data[key]
            return None
        return value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache."""
        ttl = ttl or self.default_ttl
        expiry = time.time() + ttl
        self._data[key] = (value, expiry)

    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        self._data.pop(key, None)

    async def exists(self, key: str) -> bool:
        """Check if key exists and not expired."""
        self._clean()
        return key in self._data

    async def get_async(self, key: str) -> Optional[Any]:
        """Async get alias."""
        return await self.get(key)

    async def set_async(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Async set alias."""
        await self.set(key, value, ttl)

    async def delete_pattern(self, pattern: str) -> None:
        """Delete keys matching pattern."""
        self._clean()
        keys_to_delete = [k for k in self._data.keys() if pattern in k]
        for k in keys_to_delete:
            del self._data[k]