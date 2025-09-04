"""Base key-value store interface and abstract classes.

This module defines the base KeyValueStore interface and abstract classes
that all key-value store implementations must implement.
"""

import json
import pickle
from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Any, cast


class KeyValueStore(ABC):
    """Abstract base class for key-value store implementations.

    This class defines the interface that all key-value store implementations
    must follow. It provides basic CRUD operations plus range queries.
    """

    def __init__(self, **kwargs: object) -> None:
        """Initialize the key-value store."""
        self._serializer: str = cast("str", kwargs.get("serializer", "json"))
        self._default_ttl: int | None = cast("int | None", kwargs.get("default_ttl"))
        self._key_prefix: str = cast("str", kwargs.get("key_prefix", "")) or ""

    def _get_prefixed_key(self, key: str, prefix: str | None = None) -> str:
        """Get the key with prefix applied."""
        # Use provided prefix if available, otherwise use instance prefix
        effective_prefix = prefix if prefix is not None else self._key_prefix
        if effective_prefix:
            # Ensure prefix ends with a colon for better key organization
            if not effective_prefix.endswith(":"):
                effective_prefix = f"{effective_prefix}:"
            return f"{effective_prefix}{key}"
        return key

    @abstractmethod
    async def put(
        self,
        key: str,
        value: object,
        ttl: int | timedelta | None = None,
        prefix: str | None = None,
        **kwargs: object,
    ) -> None:
        """Store a value with the given key.

        Args:
            key: The key to store the value under
            value: The value to store
            ttl: Time-to-live in seconds or as timedelta. If None, uses default_ttl
            prefix: Optional prefix to prepend to the key. If None, uses the store's default prefix
            **kwargs: Additional implementation-specific parameters
        """

    @abstractmethod
    async def get(
        self,
        key: str,
        default: object = None,
        prefix: str | None = None,
        **kwargs: object,
    ) -> object | None:
        """Retrieve a value by key.

        Args:
            key: The key to retrieve
            default: Default value to return if key doesn't exist
            prefix: Optional prefix to prepend to the key. If None, uses the store's default prefix
            **kwargs: Additional implementation-specific parameters

        Returns:
            The stored value or default if not found
        """

    @abstractmethod
    async def delete(
        self, key: str, prefix: str | None = None, **kwargs: object
    ) -> bool:
        """Delete a key-value pair.

        Args:
            key: The key to delete
            prefix: Optional prefix to prepend to the key. If None, uses the store's default prefix
            **kwargs: Additional implementation-specific parameters

        Returns:
            True if the key was deleted, False if it didn't exist
        """

    @abstractmethod
    async def exists(
        self, key: str, prefix: str | None = None, **kwargs: object
    ) -> bool:
        """Check if a key exists.

        Args:
            key: The key to check
            prefix: Optional prefix to prepend to the key. If None, uses the store's default prefix
            **kwargs: Additional implementation-specific parameters

        Returns:
            True if the key exists, False otherwise
        """

    @abstractmethod
    async def range_get(
        self,
        start_key: str,
        end_key: str | None = None,
        limit: int | None = None,
        prefix: str | None = None,
        **kwargs: object,
    ) -> list[tuple[str, Any]]:
        """Get a range of key-value pairs.

        Args:
            start_key: The starting key (inclusive)
            end_key: The ending key (exclusive). If None, no upper bound
            limit: Maximum number of results to return
            prefix: Optional prefix to prepend to the keys. If None, uses the store's default prefix
            **kwargs: Additional implementation-specific parameters

        Returns:
            List of (key, value) tuples in the specified range
        """

    @abstractmethod
    async def close(self) -> None:
        """Close the store and release any resources."""

    def _serialize(self, value: object) -> str:
        """Serialize a value for storage."""
        if self._serializer == "json":
            return json.dumps(value, default=str)
        if self._serializer == "pickle":
            return pickle.dumps(value).hex()
        raise ValueError(f"Bad serializer: {self._serializer}")  # noqa: TRY003

    def _deserialize(self, value: str) -> object:
        """Deserialize a value from storage."""
        if self._serializer == "json":
            return json.loads(value)
        if self._serializer == "pickle":
            # Note: pickle.loads can be unsafe with untrusted data, but this is for internal use only
            return pickle.loads(bytes.fromhex(value))  # noqa: S301
        raise ValueError(f"Bad serializer: {self._serializer}")  # noqa: TRY003

    def _normalize_ttl(self, ttl: int | timedelta | None) -> int | None:
        """Normalize TTL to seconds."""
        if ttl is None:
            return self._default_ttl

        if isinstance(ttl, timedelta):
            return int(ttl.total_seconds())

        return ttl

    async def __aenter__(self) -> "KeyValueStore":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self, exc_type: object, exc_val: object, exc_tb: object
    ) -> None:
        """Async context manager exit."""
        await self.close()
