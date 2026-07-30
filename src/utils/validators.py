"""Input validation utility functions."""

import ipaddress
import re
from typing import Any, Dict, List, Optional
from uuid import UUID


def is_uuid_valid(value: str) -> bool:
    """Check if a string is a valid UUID.

    Args:
        value: String to check.

    Returns:
        bool: True if valid UUID.
    """
    try:
        UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def is_email_valid(email: str) -> bool:
    """Check if a string is a valid email address.

    Args:
        email: Email address to check.

    Returns:
        bool: True if valid email.
    """
    if not email or not isinstance(email, str):
        return False

    # Basic email validation pattern
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def is_ip_valid(ip: str) -> bool:
    """Check if a string is a valid IP address (IPv4 or IPv6).

    Args:
        ip: IP address to check.

    Returns:
        bool: True if valid IP.
    """
    if not ip or not isinstance(ip, str):
        return False

    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def is_cve_valid(cve_id: str) -> bool:
    """Check if a string is a valid CVE identifier.

    Args:
        cve_id: CVE ID to check.

    Returns:
        bool: True if valid CVE format.
    """
    if not cve_id or not isinstance(cve_id, str):
        return False

    # CVE format: CVE-YYYY-NNNNN
    pattern = r"^CVE-\d{4}-\d{4,}$"
    return bool(re.match(pattern, cve_id.upper()))


def sanitize_input(value: str, max_length: int = 1000) -> str:
    """Sanitize user input by stripping and limiting length.

    Args:
        value: Input string.
        max_length: Maximum allowed length.

    Returns:
        str: Sanitized string.
    """
    if not value or not isinstance(value, str):
        return ""

    # Strip whitespace
    sanitized = value.strip()

    # Limit length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    # Remove control characters
    sanitized = "".join(char for char in sanitized if ord(char) >= 32 or char in ("\n", "\t", "\r"))

    return sanitized


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> List[str]:
    """Validate that all required fields exist in a dictionary.

    Args:
        data: Dictionary to validate.
        required_fields: List of required field names.

    Returns:
        List[str]: List of missing field names.
    """
    if not data:
        return required_fields

    missing = []
    for field in required_fields:
        if field not in data or data[field] is None or (isinstance(data[field], str) and not data[field].strip()):
            missing.append(field)

    return missing


def validate_enum(value: str, enum_values: List[str]) -> bool:
    """Check if a value is in a list of valid enum values.

    Args:
        value: Value to check.
        enum_values: List of valid values.

    Returns:
        bool: True if valid enum value.
    """
    if not value or not isinstance(value, str):
        return False
    return value.lower() in [v.lower() for v in enum_values]


def validate_positive_number(value: float) -> bool:
    """Check if a number is positive.

    Args:
        value: Number to check.

    Returns:
        bool: True if positive.
    """
    try:
        return float(value) > 0
    except (ValueError, TypeError):
        return False


def validate_range(value: float, min_val: float, max_val: float) -> bool:
    """Check if a value is within a range (inclusive).

    Args:
        value: Value to check.
        min_val: Minimum allowed value.
        max_val: Maximum allowed value.

    Returns:
        bool: True if within range.
    """
    try:
        return min_val <= float(value) <= max_val
    except (ValueError, TypeError):
        return False