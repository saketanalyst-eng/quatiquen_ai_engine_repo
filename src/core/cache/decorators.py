"""Cache decorators for function-level caching.

These decorators provide declarative caching for async and sync functions
with support for TTL, key generation, and cache invalidation.
"""

import asyncio
import hashlib
import inspect
import json
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar, Union, cast

from src.core.logging.logger import get_logger

logger = get_logger("quantiquan.cache")

T = TypeVar("T")
F = TypeVar("F", bound=Callable)


class Cached:
    """Cached descriptor for method-level caching.

    This class provides a descriptor-based caching mechanism for methods
    with support for TTL and key generation.
    """

    def __init__(
        self,
        ttl: int = 300,
        key_prefix: Optional[str] = None,
        cache_backend: Optional[Any] = None,
    ) -> None:
        """Initialize cached descriptor.

        Args:
            ttl: Time-to-live in seconds.
            key_prefix: Optional prefix for cache keys.
            cache_backend: Cache backend instance.
        """
        self.ttl = ttl
        self.key_prefix = key_prefix
        self.cache_backend = cache_backend

    def __call__(self, func: F) -> F:
        """Apply cache to function.

        Args:
            func: Function to cache.

        Returns:
            F: Wrapped function.
        """
        if inspect.iscoroutinefunction(func):
            return cast(F, self._wrap_async(func))
        return cast(F, self._wrap_sync(func))

    def _wrap_sync(self, func: Callable) -> Callable:
        """Wrap sync function with caching.

        Args:
            func: Sync function to wrap.

        Returns:
            Callable: Wrapped function.
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = self._generate_key(func, args, kwargs)
            backend = self._get_backend()

            if backend is not None:
                try:
                    cached_value = backend.get(key)
                    if cached_value is not None:
                        logger.debug("Cache hit", key=key, function=func.__name__)
                        return cached_value
                except Exception as exc:
                    logger.warning("Cache get failed", key=key, error=str(exc))

            logger.debug("Cache miss", key=key, function=func.__name__)
            result = func(*args, **kwargs)

            if backend is not None and result is not None:
                try:
                    backend.set(key, result, ttl=self.ttl)
                except Exception as exc:
                    logger.warning("Cache set failed", key=key, error=str(exc))

            return result
        return wrapper

    def _wrap_async(self, func: Callable) -> Callable:
        """Wrap async function with caching.

        Args:
            func: Async function to wrap.

        Returns:
            Callable: Wrapped async function.
        """
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = self._generate_key(func, args, kwargs)
            backend = self._get_backend()

            if backend is not None:
                try:
                    cached_value = await backend.get_async(key)
                    if cached_value is not None:
                        logger.debug("Cache hit", key=key, function=func.__name__)
                        return cached_value
                except Exception as exc:
                    logger.warning("Cache get failed", key=key, error=str(exc))

            logger.debug("Cache miss", key=key, function=func.__name__)
            result = await func(*args, **kwargs)

            if backend is not None and result is not None:
                try:
                    await backend.set_async(key, result, ttl=self.ttl)
                except Exception as exc:
                    logger.warning("Cache set failed", key=key, error=str(exc))

            return result
        return wrapper

    def _get_backend(self):
        """Get cache backend.

        Returns:
            Optional[Any]: Cache backend instance.
        """
        if self.cache_backend is not None:
            return self.cache_backend

        # Try to get from global cache registry
        try:
            from src.core.di.container import get_container

            container = get_container()
            if hasattr(container, "cache"):
                return container.cache
        except (ImportError, AttributeError):
            pass

        return None

    def _generate_key(self, func: Callable, args: tuple, kwargs: dict) -> str:
        """Generate cache key for function call.

        Args:
            func: The function being called.
            args: Positional arguments.
            kwargs: Keyword arguments.

        Returns:
            str: Cache key.
        """
        # Get function signature
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        # Build key components
        key_parts = []

        if self.key_prefix:
            key_parts.append(self.key_prefix)

        key_parts.append(func.__module__)
        key_parts.append(func.__name__)

        # Add argument values
        for name, value in bound_args.arguments.items():
            try:
                # Try to serialize value
                if isinstance(value, (str, int, float, bool)):
                    key_parts.append(f"{name}={value}")
                elif value is None:
                    key_parts.append(f"{name}=None")
                else:
                    # Hash complex objects
                    json_str = json.dumps(value, sort_keys=True, default=str)
                    value_hash = hashlib.md5(json_str.encode()).hexdigest()[:8]
                    key_parts.append(f"{name}=hash_{value_hash}")
            except (TypeError, ValueError):
                key_parts.append(f"{name}=unsupported")

        # Join and hash if too long
        raw_key = ":".join(key_parts)
        if len(raw_key) > 200:
            raw_key = hashlib.md5(raw_key.encode()).hexdigest()

        return raw_key


def cached(
    ttl: int = 300,
    key_prefix: Optional[str] = None,
) -> Callable:
    """Decorator for caching function results.

    Args:
        ttl: Time-to-live in seconds.
        key_prefix: Optional prefix for cache keys.

    Returns:
        Callable: Decorator function.

    Example:
        @cached(ttl=3600, key_prefix="threat")
        async def get_threat_intel(cve_id: str) -> ThreatContext:
            ...
    """
    return Cached(ttl=ttl, key_prefix=key_prefix)


def cache_async(
    ttl: int = 300,
    key_prefix: Optional[str] = None,
) -> Callable:
    """Alias for cached decorator (async compatibility).

    Args:
        ttl: Time-to-live in seconds.
        key_prefix: Optional prefix for cache keys.

    Returns:
        Callable: Decorator function.
    """
    return cached(ttl=ttl, key_prefix=key_prefix)


def invalidate_cache(
    key_pattern: Optional[str] = None,
    key_prefix: Optional[str] = None,
) -> Callable:
    """Decorator to invalidate cache after function execution.

    Args:
        key_pattern: Specific key to invalidate.
        key_prefix: Prefix pattern to invalidate.

    Returns:
        Callable: Decorator function.
    """
    def decorator(func: Callable) -> Callable:
        if inspect.iscoroutinefunction(func):
            return _invalidate_async(func, key_pattern, key_prefix)
        return _invalidate_sync(func, key_pattern, key_prefix)
    return decorator


def invalidate_async(
    key_pattern: Optional[str] = None,
    key_prefix: Optional[str] = None,
) -> Callable:
    """Alias for invalidate_cache for async functions.

    Args:
        key_pattern: Specific key to invalidate.
        key_prefix: Prefix pattern to invalidate.

    Returns:
        Callable: Decorator function.
    """
    return invalidate_cache(key_pattern=key_pattern, key_prefix=key_prefix)


def _invalidate_sync(
    func: Callable,
    key_pattern: Optional[str],
    key_prefix: Optional[str],
) -> Callable:
    """Sync invalidation wrapper."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        _do_invalidate_sync(key_pattern, key_prefix, func)
        return result
    return wrapper


def _invalidate_async(
    func: Callable,
    key_pattern: Optional[str],
    key_prefix: Optional[str],
) -> Callable:
    """Async invalidation wrapper."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        await _do_invalidate_async(key_pattern, key_prefix, func)
        return result
    return wrapper


def _do_invalidate_sync(key_pattern: Optional[str], key_prefix: Optional[str], func: Callable) -> None:
    """Synchronous cache invalidation."""
    try:
        from src.core.di.container import get_container

        container = get_container()
        cache_backend = getattr(container, "cache", None)

        if cache_backend is None:
            logger.warning("No cache backend available for invalidation")
            return

        if key_pattern:
            cache_backend.delete(key_pattern)
            logger.debug("Cache invalidated", key=key_pattern)
        elif key_prefix:
            cache_backend.delete_pattern(f"{key_prefix}*")
            logger.debug("Cache invalidated", prefix=key_prefix)

    except Exception as exc:
        logger.warning("Cache invalidation failed", error=str(exc))


async def _do_invalidate_async(key_pattern: Optional[str], key_prefix: Optional[str], func: Callable) -> None:
    """Asynchronous cache invalidation."""
    try:
        from src.core.di.container import get_container

        container = get_container()
        cache_backend = getattr(container, "cache", None)

        if cache_backend is None:
            logger.warning("No cache backend available for invalidation")
            return

        if key_pattern:
            await cache_backend.delete_async(key_pattern)
            logger.debug("Cache invalidated", key=key_pattern)
        elif key_prefix:
            await cache_backend.delete_pattern_async(f"{key_prefix}*")
            logger.debug("Cache invalidated", prefix=key_prefix)

    except Exception as exc:
        logger.warning("Cache invalidation failed", error=str(exc))


# Global cache registry for decorators
_CACHE_REGISTRY: Dict[str, Dict[str, Any]] = {}


def register_cached_function(
    name: str,
    func: Callable,
    ttl: int = 300,
    key_prefix: Optional[str] = None,
) -> None:
    """Register a cached function for manual invalidation.

    Args:
        name: Registered name.
        func: The cached function.
        ttl: Cache TTL.
        key_prefix: Cache key prefix.
    """
    _CACHE_REGISTRY[name] = {
        "func": func,
        "ttl": ttl,
        "key_prefix": key_prefix,
    }


def get_cached_function(name: str) -> Optional[Callable]:
    """Get a registered cached function.

    Args:
        name: Registered name.

    Returns:
        Optional[Callable]: The cached function or None.
    """
    entry = _CACHE_REGISTRY.get(name)
    return entry.get("func") if entry else None