"""Key-value store utility functions and helpers.

This module provides utility functions for key-value store implementations,
including serialization, TTL normalization, and key prefixing.
"""

import json
import pickle
from datetime import timedelta


def get_prefixed_key(key: str, prefix: str | None = None) -> str:
    """Get the key with prefix applied.

    Args:
        key: The base key
        prefix: Optional prefix to prepend to the key

    Returns:
        The key with prefix applied
    """
    if prefix:
        # Ensure prefix ends with a colon for better key organization
        if not prefix.endswith(":"):
            prefix = f"{prefix}:"
        return f"{prefix}{key}"
    return key


def serialize_value(value: object, serializer: str = "json") -> str:
    """Serialize a value for storage.

    Args:
        value: The value to serialize
        serializer: The serializer to use ("json" or "pickle")

    Returns:
        Serialized value as string

    Raises:
        ValueError: If serializer is not supported
    """
    if serializer == "json":
        return json.dumps(value, default=str)
    if serializer == "pickle":
        return pickle.dumps(value).hex()
    raise ValueError(f"Bad serializer: {serializer}")  # noqa: TRY003


def deserialize_value(value: str, serializer: str = "json") -> object:
    """Deserialize a value from storage.

    Args:
        value: The serialized value
        serializer: The serializer to use ("json" or "pickle")

    Returns:
        Deserialized value

    Raises:
        ValueError: If serializer is not supported
    """
    if serializer == "json":
        return json.loads(value)
    if serializer == "pickle":
        # Note: pickle.loads can be unsafe with untrusted data, but this is for internal use only
        return pickle.loads(bytes.fromhex(value))  # noqa: S301
    raise ValueError(f"Bad serializer: {serializer}")  # noqa: TRY003


def normalize_ttl(
    ttl: int | timedelta | None, default_ttl: int | None = None
) -> int | None:
    """Normalize TTL to seconds.

    Args:
        ttl: The TTL value to normalize
        default_ttl: Default TTL to use if ttl is None

    Returns:
        TTL in seconds, or None if no TTL should be set
    """
    if ttl is None:
        return default_ttl

    if isinstance(ttl, timedelta):
        return int(ttl.total_seconds())

    return ttl
