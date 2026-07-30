"""Hashing utility functions."""

import hashlib
import json
from typing import Any, Optional


def hash_string(value: str, algorithm: str = "sha256") -> str:
    """Hash a string using the specified algorithm.

    Args:
        value: String to hash.
        algorithm: Hashing algorithm (sha256, md5, sha1).

    Returns:
        str: Hex digest of the hash.

    Raises:
        ValueError: If algorithm is not supported.
    """
    if not value:
        return ""

    try:
        hasher = hashlib.new(algorithm)
        hasher.update(value.encode("utf-8"))
        return hasher.hexdigest()
    except ValueError as exc:
        raise ValueError(f"Unsupported hashing algorithm: {algorithm}") from exc


def hash_dict(data: Dict[str, Any], algorithm: str = "sha256") -> str:
    """Hash a dictionary by converting to JSON first.

    Args:
        data: Dictionary to hash.
        algorithm: Hashing algorithm.

    Returns:
        str: Hex digest of the hash.
    """
    if not data:
        return ""

    # Sort keys for deterministic output
    json_str = json.dumps(data, sort_keys=True, default=str)
    return hash_string(json_str, algorithm)


def generate_hash(*args: Any, algorithm: str = "sha256") -> str:
    """Generate a hash from multiple arguments.

    Args:
        *args: Arguments to hash.
        algorithm: Hashing algorithm.

    Returns:
        str: Hex digest of the hash.
    """
    combined = "".join(str(arg) for arg in args)
    return hash_string(combined, algorithm)


def generate_id_hash(prefix: str, identifier: str) -> str:
    """Generate a deterministic hash ID with a prefix.

    Args:
        prefix: Prefix for the ID.
        identifier: Identifier string to hash.

    Returns:
        str: Formatted hash ID (e.g., "finding_abc123").
    """
    if not prefix or not identifier:
        return ""

    hash_value = hash_string(identifier, "md5")[:8]
    return f"{prefix}_{hash_value}"


def hash_file_content(content: bytes) -> str:
    """Hash file content using SHA-256.

    Args:
        content: File content as bytes.

    Returns:
        str: Hex digest of the hash.
    """
    if not content:
        return ""

    hasher = hashlib.sha256()
    hasher.update(content)
    return hasher.hexdigest()


def hash_password(password: str) -> str:
    """Hash a password (using SHA-256, not for production use).

    Note: This is a simplified hash for non-security use cases.
    For production password hashing, use bcrypt or argon2.

    Args:
        password: Password to hash.

    Returns:
        str: Hex digest of the hash.
    """
    return hash_string(password, "sha256")