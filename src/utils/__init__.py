"""Utility functions module.

This module provides reusable utility functions that are framework-agnostic
and contain no business logic. These utilities can be used across all layers.
"""

from src.utils.datetime_utils import (
    age_in_days,
    age_in_hours,
    format_iso8601,
    human_readable_duration,
    is_timestamp_valid,
    now_timestamp,
)
from src.utils.hashing import generate_hash, generate_id_hash, hash_dict, hash_string
from src.utils.helpers import chunk_list, retry_async, retry_sync, safe_get, safe_merge
from src.utils.json_utils import JSONEncoder, safe_json_dumps, safe_json_loads
from src.utils.serialization import from_dict, to_dict
from src.utils.validators import (
    is_cve_valid,
    is_email_valid,
    is_ip_valid,
    is_uuid_valid,
    sanitize_input,
    validate_required_fields,
)

__all__ = [
    "JSONEncoder",
    "age_in_days",
    "age_in_hours",
    "chunk_list",
    "format_iso8601",
    "from_dict",
    "generate_hash",
    "generate_id_hash",
    "hash_dict",
    "hash_string",
    "human_readable_duration",
    "is_cve_valid",
    "is_email_valid",
    "is_ip_valid",
    "is_timestamp_valid",
    "is_uuid_valid",
    "now_timestamp",
    "retry_async",
    "retry_sync",
    "safe_get",
    "safe_json_dumps",
    "safe_json_loads",
    "safe_merge",
    "sanitize_input",
    "to_dict",
    "validate_required_fields",
]