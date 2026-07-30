"""Redis cache implementation."""

import json
from typing import Any, Optional

import redis.asyncio as redis

from src.core.exceptions.infrastructure import CacheError
from src.core.logging.logger import get_logger

logger = get_logger("quantiquan.infrastructure.redis_cache")


class RedisCache:
    """Redis cache adapter implementing CachePort."""

    def __init__(self, redis_url: str, default_ttl: int = 300) -> None:
        """Initialize Redis cache.

        Args:
            redis_url: Redis connection URL.
            default_ttl: Default TTL in seconds.
        """
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.client: Optional[redis.Redis] = None

    async def _get_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self.client is None:
            self.client = redis.from_url(self.redis_url, decode_responses=True)
        return self.client

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            client = await self._get_client()
            value = await client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception as exc:
            logger.warning("Redis get failed", key=key, error=str(exc))
            raise CacheError(f"Redis get failed: {exc}", key=key, operation="get") from exc

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache."""
        try:
            client = await self._get_client()
            ttl = ttl or self.default_ttl
            serialized = json.dumps(value, default=str)
            await client.setex(key, ttl, serialized)
        except Exception as exc:
            logger.warning("Redis set failed", key=key, error=str(exc))
            raise CacheError(f"Redis set failed: {exc}", key=key, operation="set") from exc

    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        try:
            client = await self._get_client()
            await client.delete(key)
        except Exception as exc:
            logger.warning("Redis delete failed", key=key, error=str(exc))
            raise CacheError(f"Redis delete failed: {exc}", key=key, operation="delete") from exc

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            client = await self._get_client()
            return await client.exists(key) > 0
        except Exception as exc:
            logger.warning("Redis exists failed", key=key, error=str(exc))
            return False

    async def get_async(self, key: str) -> Optional[Any]:
        """Async get alias."""
        return await self.get(key)

    async def set_async(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Async set alias."""
        await self.set(key, value, ttl)

    async def delete_pattern(self, pattern: str) -> None:
        """Delete keys matching pattern."""
        try:
            client = await self._get_client()
            keys = await client.keys(pattern)
            if keys:
                await client.delete(*keys)
        except Exception as exc:
            logger.warning("Redis delete pattern failed", pattern=pattern, error=str(exc))
            raise CacheError(f"Redis delete pattern failed: {exc}", key=pattern, operation="delete_pattern") from exc