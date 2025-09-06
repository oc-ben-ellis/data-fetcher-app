"""Base key-value store interface and protocols.

This module defines the base KeyValueStore protocol for persisting application state
across different storage backends. All key-value store implementations must implement this protocol.
"""

from datetime import timedelta
from typing import Any, Protocol, cast

from .helper import deserialize_value, get_prefixed_key, normalize_ttl, serialize_value


class KeyValueStore(Protocol):
    """Protocol for key-value store implementations.

    This protocol defines the interface that all key-value store implementations
    must follow for persisting application state. It provides basic CRUD operations
    plus range queries for state data.
    """

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
        ...

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
        ...

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
        ...

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
        ...

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
        ...

    async def close(self) -> None:
        """Close the store and release any resources."""
        ...

    async def __aenter__(self) -> "KeyValueStore":
        """Async context manager entry."""
        ...

    async def __aexit__(
        self, exc_type: object, exc_val: object, exc_tb: object
    ) -> None:
        """Async context manager exit."""
        ...


class BaseKeyValueStore:
    """Base class providing common functionality for key-value store implementations.

    This class provides helper methods and initialization logic that concrete
    implementations can inherit from. It implements the KeyValueStore protocol.
    """

    def __init__(self, **kwargs: object) -> None:
        """Initialize the key-value store with common configuration."""
        self._serializer: str = cast("str", kwargs.get("serializer", "json"))
        self._default_ttl: int | None = cast("int | None", kwargs.get("default_ttl"))
        self._key_prefix: str = cast("str", kwargs.get("key_prefix", "")) or ""

    def _get_prefixed_key(self, key: str, prefix: str | None = None) -> str:
        """Get the key with prefix applied."""
        effective_prefix = prefix if prefix is not None else self._key_prefix
        return get_prefixed_key(key, effective_prefix)

    def _serialize(self, value: object) -> str:
        """Serialize a value for storage."""
        return serialize_value(value, self._serializer)

    def _deserialize(self, value: str) -> object:
        """Deserialize a value from storage."""
        return deserialize_value(value, self._serializer)

    def _normalize_ttl(self, ttl: int | timedelta | None) -> int | None:
        """Normalize TTL to seconds."""
        return normalize_ttl(ttl, self._default_ttl)

    async def close(self) -> None:
        """Close the store and release any resources."""
        # Base implementation does nothing - subclasses should override if needed

    async def __aenter__(self) -> "KeyValueStore":
        """Async context manager entry."""
        return cast("KeyValueStore", self)

    async def __aexit__(
        self, exc_type: object, exc_val: object, exc_tb: object
    ) -> None:
        """Async context manager exit."""
        await self.close()
