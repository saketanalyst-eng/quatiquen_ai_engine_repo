"""Serialization utility functions."""

import json
from datetime import datetime
from typing import Any, Dict, Optional, Type, TypeVar
from uuid import UUID

from pydantic import BaseModel

from src.core.logging.logger import get_logger

logger = get_logger("quantiquan.utils.serialization")

T = TypeVar("T", bound=BaseModel)


def to_dict(obj: Any, exclude_none: bool = True) -> Dict[str, Any]:
    """Convert an object to a dictionary.

    Args:
        obj: Object to convert (supports dataclasses, BaseModel, dict).
        exclude_none: Whether to exclude None values.

    Returns:
        Dict[str, Any]: Dictionary representation.
    """
    if obj is None:
        return {}

    if isinstance(obj, BaseModel):
        return obj.model_dump(exclude_none=exclude_none)

    if isinstance(obj, dict):
        return {k: to_dict(v, exclude_none) for k, v in obj.items()}

    if hasattr(obj, "__dataclass_fields__"):
        from dataclasses import asdict

        return asdict(obj)

    if hasattr(obj, "__dict__"):
        return {k: to_dict(v, exclude_none) for k, v in obj.__dict__.items() if not k.startswith("_")}

    return {}


def from_dict(data: Dict[str, Any], model_class: Type[T]) -> T:
    """Convert a dictionary to a Pydantic model.

    Args:
        data: Dictionary data.
        model_class: Pydantic model class.

    Returns:
        T: Model instance.

    Raises:
        ValueError: If validation fails.
    """
    if not data:
        raise ValueError("Cannot create model from empty data")

    try:
        return model_class(**data)
    except Exception as exc:
        logger.error("Failed to deserialize model", model=model_class.__name__, error=str(exc))
        raise ValueError(f"Failed to deserialize model: {exc}") from exc


def serialize_enum(value: Any) -> str:
    """Serialize an enum to its value.

    Args:
        value: Enum value.

    Returns:
        str: String representation.
    """
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def deserialize_datetime(value: Any) -> Optional[datetime]:
    """Deserialize a datetime from string or timestamp.

    Args:
        value: Datetime string, timestamp, or datetime object.

    Returns:
        Optional[datetime]: Parsed datetime object.
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, (int, float)):
        from datetime import datetime as dt

        return dt.fromtimestamp(value)

    if isinstance(value, str):
        try:
            from datetime import datetime as dt

            # Try ISO format
            return dt.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass

    return None


def serialize_datetime(value: datetime) -> str:
    """Serialize a datetime to ISO format.

    Args:
        value: Datetime object.

    Returns:
        str: ISO format string.
    """
    if value is None:
        return ""

    if isinstance(value, datetime):
        return value.isoformat()

    return str(value)


def serialize_uuid(value: UUID) -> str:
    """Serialize a UUID to string.

    Args:
        value: UUID object.

    Returns:
        str: String representation.
    """
    if value is None:
        return ""

    if isinstance(value, UUID):
        return str(value)

    return str(value)