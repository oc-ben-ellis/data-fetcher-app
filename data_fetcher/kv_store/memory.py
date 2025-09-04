"""In-memory key-value store implementation.

This module provides the InMemoryKeyValueStore class for fast, temporary
storage of key-value pairs in memory, useful for caching and testing.
"""

import asyncio
import contextlib
import time
from datetime import timedelta
from typing import Any

import structlog

from .base import KeyValueStore

# Get logger for this module
logger = structlog.get_logger(__name__)


class InMemoryKeyValueStore(KeyValueStore):
    """In-memory key-value store implementation.

    This store keeps all data in memory using Python dictionaries. It supports
    TTL (time-to-live) functionality and range queries. Data is not persisted
    and will be lost when the application restarts.
    """

    def __init__(self, **kwargs: object) -> None:
        """Initialize the in-memory store."""
        super().__init__(**kwargs)
        self._store: dict[str, Any] = {}
        self._expiry_times: dict[str, float] = {}
        self._lock = asyncio.Lock()

        # Cleanup task will be started when first operation is performed
        self._cleanup_task: asyncio.Task[Any] | None = None
        self._cleanup_started = False

    async def put(
        self,
        key: str,
        value: object,
        ttl: int | timedelta | None = None,
        prefix: str | None = None,
        **kwargs: object,  # noqa: ARG002
    ) -> None:
        """Store a value with the given key."""
        # Start cleanup task if needed
        await self._ensure_cleanup_started()

        # Apply key prefix
        prefixed_key = self._get_prefixed_key(key, prefix)

        async with self._lock:
            # Serialize the value
            serialized_value = self._serialize(value)

            # Store the value
            self._store[prefixed_key] = serialized_value

            # Set expiry time if TTL is specified
            ttl_seconds = self._normalize_ttl(ttl)
            if ttl_seconds is not None:
                self._expiry_times[prefixed_key] = time.time() + ttl_seconds
            elif prefixed_key in self._expiry_times:
                # Remove expiry if no TTL specified
                del self._expiry_times[prefixed_key]

    async def get(
        self,
        key: str,
        default: object = None,
        prefix: str | None = None,
        **kwargs: object,  # noqa: ARG002
    ) -> object | None:
        """Retrieve a value by key."""
        # Apply key prefix
        prefixed_key = self._get_prefixed_key(key, prefix)

        async with self._lock:
            # Check if key exists and is not expired
            if not await self._is_valid_key(prefixed_key):
                return default

            # Get and deserialize the value
            serialized_value = self._store[prefixed_key]
            return self._deserialize(serialized_value)

    async def delete(
        self,
        key: str,
        prefix: str | None = None,
        **kwargs: object,  # noqa: ARG002
    ) -> bool:
        """Delete a key-value pair."""
        # Apply key prefix
        prefixed_key = self._get_prefixed_key(key, prefix)

        async with self._lock:
            if prefixed_key in self._store:
                del self._store[prefixed_key]
                if prefixed_key in self._expiry_times:
                    del self._expiry_times[prefixed_key]
                return True
            return False

    async def exists(
        self,
        key: str,
        prefix: str | None = None,
        **kwargs: object,  # noqa: ARG002
    ) -> bool:
        """Check if a key exists."""
        # Apply key prefix
        prefixed_key = self._get_prefixed_key(key, prefix)

        async with self._lock:
            return await self._is_valid_key(prefixed_key)

    async def range_get(
        self,
        start_key: str,
        end_key: str | None = None,
        limit: int | None = None,
        prefix: str | None = None,
        **kwargs: object,  # noqa: ARG002
    ) -> list[tuple[str, Any]]:
        """Get a range of key-value pairs."""
        # Apply key prefix to start and end keys
        prefixed_start_key = self._get_prefixed_key(start_key, prefix)
        prefixed_end_key = (
            self._get_prefixed_key(end_key, prefix) if end_key is not None else None
        )

        async with self._lock:
            # Get all valid keys in the range that match the current prefix
            valid_keys = []
            effective_prefix = prefix if prefix is not None else self._key_prefix
            for key in sorted(self._store.keys()):
                # Only include keys that start with the current prefix
                if effective_prefix and not key.startswith(effective_prefix):
                    continue
                if key < prefixed_start_key:
                    continue
                if prefixed_end_key is not None and key >= prefixed_end_key:
                    break
                if await self._is_valid_key(key):
                    valid_keys.append(key)

            # Apply limit
            if limit is not None:
                valid_keys = valid_keys[:limit]

            # Return key-value pairs (strip prefix from returned keys)
            result = []
            for key in valid_keys:
                serialized_value = self._store[key]
                value = self._deserialize(serialized_value)
                # Strip prefix from returned key
                original_key = (
                    key[len(effective_prefix) :]
                    if effective_prefix and key.startswith(effective_prefix)
                    else key
                )
                result.append((original_key, value))

            return result

    async def close(self) -> None:
        """Close the store and release resources."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task

        async with self._lock:
            self._store.clear()
            self._expiry_times.clear()

    async def _ensure_cleanup_started(self) -> None:
        """Ensure the cleanup task is started."""
        if not self._cleanup_started and self._default_ttl is not None:
            self._cleanup_task = asyncio.create_task(self._cleanup_expired_keys())
            self._cleanup_started = True

    async def _is_valid_key(self, key: str) -> bool:
        """Check if a key exists and is not expired."""
        if key not in self._store:
            return False

        # Check if key has expired
        if key in self._expiry_times and time.time() > self._expiry_times[key]:
            # Remove expired key
            del self._store[key]
            del self._expiry_times[key]
            return False

        return True

    async def _cleanup_expired_keys(self) -> None:
        """Background task to clean up expired keys."""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute

                async with self._lock:
                    current_time = time.time()
                    expired_keys = [
                        key
                        for key, expiry_time in self._expiry_times.items()
                        if current_time > expiry_time
                    ]

                    for key in expired_keys:
                        if key in self._store:
                            del self._store[key]
                        del self._expiry_times[key]

            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue cleanup
                logger.exception(
                    "Error during cleanup task",
                    error=str(e),
                )
                continue

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the store."""
        return {
            "total_keys": len(self._store),
            "expiring_keys": len(self._expiry_times),
            "serializer": self._serializer,
            "default_ttl": self._default_ttl,
        }
