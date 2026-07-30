"""Datetime utility functions."""

import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Union


def now_timestamp() -> int:
    """Get current Unix timestamp.

    Returns:
        int: Current Unix timestamp in seconds.
    """
    return int(time.time())


def format_iso8601(timestamp: Optional[int] = None) -> str:
    """Format a timestamp as ISO 8601 string.

    Args:
        timestamp: Unix timestamp (seconds). Defaults to current time.

    Returns:
        str: ISO 8601 formatted string.
    """
    if timestamp is None:
        timestamp = now_timestamp()

    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return dt.isoformat()


def age_in_days(timestamp: int, current_timestamp: Optional[int] = None) -> float:
    """Calculate age in days since a timestamp.

    Args:
        timestamp: Earlier timestamp in seconds.
        current_timestamp: Current timestamp (defaults to now).

    Returns:
        float: Age in days (fractional).
    """
    if current_timestamp is None:
        current_timestamp = now_timestamp()

    if timestamp > current_timestamp:
        return 0.0

    seconds_diff = current_timestamp - timestamp
    return seconds_diff / (24 * 3600)


def age_in_hours(timestamp: int, current_timestamp: Optional[int] = None) -> float:
    """Calculate age in hours since a timestamp.

    Args:
        timestamp: Earlier timestamp in seconds.
        current_timestamp: Current timestamp (defaults to now).

    Returns:
        float: Age in hours (fractional).
    """
    if current_timestamp is None:
        current_timestamp = now_timestamp()

    if timestamp > current_timestamp:
        return 0.0

    seconds_diff = current_timestamp - timestamp
    return seconds_diff / 3600


def is_timestamp_valid(timestamp: int, min_timestamp: int = 946684800) -> bool:
    """Check if a timestamp is valid and within a reasonable range.

    Args:
        timestamp: Timestamp to validate.
        min_timestamp: Minimum allowed timestamp (default: 2000-01-01).

    Returns:
        bool: True if valid.
    """
    if timestamp <= 0:
        return False

    if timestamp < min_timestamp:
        return False

    # Check against future (allow 1 year ahead)
    max_future = now_timestamp() + (365 * 24 * 3600)
    if timestamp > max_future:
        return False

    return True


def human_readable_duration(seconds: int) -> str:
    """Convert seconds to human-readable duration string.

    Args:
        seconds: Duration in seconds.

    Returns:
        str: Human-readable string (e.g., "2d 3h 30m").
    """
    if seconds < 60:
        return f"{seconds}s"

    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m {seconds % 60}s"

    hours = minutes // 60
    minutes = minutes % 60
    if hours < 24:
        return f"{hours}h {minutes}m"

    days = hours // 24
    hours = hours % 24
    if days < 30:
        return f"{days}d {hours}h"

    months = days // 30
    days = days % 30
    if months < 12:
        return f"{months}mo {days}d"

    years = months // 12
    months = months % 12
    return f"{years}y {months}mo"


def parse_iso8601(iso_string: str) -> Optional[datetime]:
    """Parse ISO 8601 string to datetime.

    Args:
        iso_string: ISO 8601 formatted string.

    Returns:
        Optional[datetime]: Parsed datetime or None.
    """
    try:
        return datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    except ValueError:
        return None


def to_timestamp(dt: Union[datetime, int, str]) -> Optional[int]:
    """Convert datetime or ISO string to Unix timestamp.

    Args:
        dt: Datetime object, timestamp, or ISO string.

    Returns:
        Optional[int]: Unix timestamp or None.
    """
    if isinstance(dt, int):
        return dt

    if isinstance(dt, datetime):
        return int(dt.timestamp())

    if isinstance(dt, str):
        parsed = parse_iso8601(dt)
        if parsed:
            return int(parsed.timestamp())

    return None


def add_days_to_timestamp(timestamp: int, days: int) -> int:
    """Add days to a Unix timestamp.

    Args:
        timestamp: Base timestamp.
        days: Number of days to add.

    Returns:
        int: New timestamp.
    """
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    new_dt = dt + timedelta(days=days)
    return int(new_dt.timestamp())