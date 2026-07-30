"""JSON serialization utility functions."""

import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from src.core.logging.logger import get_logger

logger = get_logger("quantiquan.utils.json_utils")


class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles common non-serializable types.

    Supports:
        - UUID
        - datetime
        - Enum
        - bytes
        - Set
        - Custom objects with __dict__
    """

    def default(self, obj: Any) -> Any:
        """Encode special types.

        Args:
            obj: Object to encode.

        Returns:
            Any: JSON-serializable value.
        """
        if isinstance(obj, UUID):
            return str(obj)

        if isinstance(obj, datetime):
            return obj.isoformat()

        if isinstance(obj, Enum):
            return obj.value

        if isinstance(obj, bytes):
            return obj.hex()

        if isinstance(obj, set):
            return list(obj)

        if hasattr(obj, "__dict__"):
            return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}

        return super().default(obj)


def safe_json_dumps(
    data: Any,
    indent: Optional[int] = None,
    sort_keys: bool = True,
    default: Optional[callable] = None,
) -> str:
    """Safely convert an object to JSON with custom serialization.

    Args:
        data: Data to serialize.
        indent: Indentation for pretty printing.
        sort_keys: Sort dictionary keys.
        default: Custom default serialization function.

    Returns:
        str: JSON string.

    Raises:
        json.JSONDecodeError: If serialization fails.
    """
    try:
        encoder = JSONEncoder(indent=indent, sort_keys=sort_keys)
        if default:
            encoder.default = default
        return encoder.encode(data)
    except TypeError as exc:
        logger.error("JSON serialization failed", error=str(exc))
        raise json.JSONDecodeError(f"Serialization failed: {exc}", "", 0) from exc


def safe_json_loads(json_string: str, default: Any = None) -> Any:
    """Safely parse JSON string with fallback.

    Args:
        json_string: JSON string to parse.
        default: Default value if parsing fails.

    Returns:
        Any: Parsed data or default.
    """
    if not json_string or not isinstance(json_string, str):
        return default

    try:
        return json.loads(json_string)
    except json.JSONDecodeError as exc:
        logger.warning("JSON parsing failed", error=str(exc), snippet=json_string[:100])
        return default


def json_serialize_legacy(
    data: Dict[str, Any],
    indent: Optional[int] = None,
) -> str:
    """Legacy JSON serialization with all custom types.

    Args:
        data: Dictionary to serialize.
        indent: Indentation.

    Returns:
        str: JSON string.
    """
    def default_serializer(obj: Any) -> Any:
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, bytes):
            return obj.hex()
        if isinstance(obj, set):
            return list(obj)
        if hasattr(obj, "__dict__"):
            return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
        return str(obj)

    return json.dumps(data, default=default_serializer, indent=indent, sort_keys=True)


def json_extract_value(json_str: str, path: Union[str, List[str]]) -> Any:
    """Extract a value from a JSON string using a dot-separated path.

    Args:
        json_str: JSON string.
        path: Dot-separated path (e.g., "data.attributes.id") or list of keys.

    Returns:
        Any: Extracted value or None if not found.
    """
    data = safe_json_loads(json_str)
    if data is None:
        return None

    if isinstance(path, str):
        path = path.split(".")

    current = data
    for key in path:
        if isinstance(current, dict):
            current = current.get(key)
            if current is None:
                return None
        else:
            return None

    return current


def json_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge two JSON dictionaries.

    Args:
        base: Base dictionary.
        override: Override dictionary.

    Returns:
        Dict[str, Any]: Merged result.
    """
    result = base.copy()
    for key, value in override.items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            result[key] = json_merge(result[key], value)
        else:
            result[key] = value
    return result


def json_minify(json_str: str) -> str:
    """Remove whitespace from JSON string.

    Args:
        json_str: JSON string to minify.

    Returns:
        str: Minified JSON string.
    """
    try:
        data = json.loads(json_str)
        return json.dumps(data, separators=(",", ":"))
    except json.JSONDecodeError:
        return json_str