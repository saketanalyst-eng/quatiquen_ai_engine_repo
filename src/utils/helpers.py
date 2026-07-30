"""Generic helper utility functions."""

import asyncio
import time
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast

from src.core.logging.logger import get_logger

logger = get_logger("quantiquan.utils.helpers")

T = TypeVar("T")
U = TypeVar("U")


def chunk_list(items: List[T], chunk_size: int) -> List[List[T]]:
    """Split a list into chunks of specified size.

    Args:
        items: List to chunk.
        chunk_size: Maximum size of each chunk.

    Returns:
        List[List[T]]: List of chunks.

    Raises:
        ValueError: If chunk_size <= 0.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")

    if not items:
        return []

    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


def safe_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Safely get a value from a dictionary.

    Args:
        data: Dictionary to get from.
        key: Key to look up.
        default: Default value if key not found.

    Returns:
        Any: Value or default.
    """
    return data.get(key, default)


def safe_merge(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """Safely merge two dictionaries, preserving values from dict2.

    Args:
        dict1: Base dictionary.
        dict2: Override dictionary.

    Returns:
        Dict[str, Any]: Merged dictionary.
    """
    result = dict(dict1)
    for key, value in dict2.items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            result[key] = safe_merge(result[key], value)
        else:
            result[key] = value
    return result


def retry_sync(
    func: Callable[..., T],
    retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Callable[..., T]:
    """Retry decorator for synchronous functions.

    Args:
        func: Function to wrap.
        retries: Number of retry attempts.
        delay: Initial delay between retries in seconds.
        backoff: Multiplier for exponential backoff.
        exceptions: Tuple of exceptions to catch and retry.

    Returns:
        Callable[..., T]: Wrapped function.

    Example:
        @retry_sync(retries=3, delay=0.5)
        def api_call():
            return requests.get(url)
    """
    def wrapper(*args, **kwargs) -> T:
        current_delay = delay
        last_exception = None

        for attempt in range(retries + 1):
            try:
                return func(*args, **kwargs)
            except exceptions as exc:
                last_exception = exc
                if attempt == retries:
                    raise

                logger.warning(
                    "Sync retry attempt failed",
                    function=func.__name__,
                    attempt=attempt + 1,
                    max_retries=retries,
                    delay=current_delay,
                    error=str(exc),
                )
                time.sleep(current_delay)
                current_delay *= backoff

        raise last_exception  # type: ignore

    return wrapper


def retry_async(
    func: Callable[..., T],
    retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Callable[..., T]:
    """Retry decorator for asynchronous functions.

    Args:
        func: Async function to wrap.
        retries: Number of retry attempts.
        delay: Initial delay between retries in seconds.
        backoff: Multiplier for exponential backoff.
        exceptions: Tuple of exceptions to catch and retry.

    Returns:
        Callable[..., T]: Wrapped async function.

    Example:
        @retry_async(retries=3, delay=0.5)
        async def api_call():
            return await client.get(url)
    """
    async def wrapper(*args, **kwargs) -> T:
        current_delay = delay
        last_exception = None

        for attempt in range(retries + 1):
            try:
                return await func(*args, **kwargs)
            except exceptions as exc:
                last_exception = exc
                if attempt == retries:
                    raise

                logger.warning(
                    "Async retry attempt failed",
                    function=func.__name__,
                    attempt=attempt + 1,
                    max_retries=retries,
                    delay=current_delay,
                    error=str(exc),
                )
                await asyncio.sleep(current_delay)
                current_delay *= backoff

        raise last_exception  # type: ignore

    return wrapper