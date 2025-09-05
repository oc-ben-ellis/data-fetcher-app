"""Key-value store implementations and interfaces.

This module provides key-value store implementations for caching and persistence,
including in-memory storage, Redis integration, and the base interface.
"""

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Protocol, cast

from .base import KeyValueStore
from .memory import InMemoryKeyValueStore
from .redis_store import RedisKeyValueStore


class KeyValueStoreFactory(Protocol):
    """Protocol for key-value store factory functions."""

    def __call__(self, **kwargs: object) -> KeyValueStore:
        """Create a key-value store instance."""
        ...


class GlobalStoreManager:
    """Manager for the global key-value store instance."""

    def __init__(self) -> None:
        """Initialize the global store manager."""
        self._store: KeyValueStore | None = None
        self._lock = asyncio.Lock()

    def configure(self, store_type: str = "memory", **kwargs: object) -> None:
        """Configure the global key-value store.

        Args:
            store_type: Type of store to use ("memory" or "redis")
            **kwargs: Additional configuration parameters for the store
        """
        if store_type == "memory":
            self._store = InMemoryKeyValueStore(**kwargs)
        elif store_type == "redis":
            self._store = RedisKeyValueStore(**kwargs)
        else:
            raise ValueError(f"Unknown store: {store_type}")  # noqa: TRY003

    async def get(self) -> KeyValueStore:
        """Get the global key-value store instance.

        Returns:
            The configured global key-value store

        Raises:
            RuntimeError: If no global store has been configured
        """
        if self._store is None:
            raise RuntimeError("Global key-value store not configured")  # noqa: TRY003

        return self._store


# Global store manager instance
_global_store_manager = GlobalStoreManager()


def configure_global_store(store_type: str = "memory", **kwargs: object) -> None:
    """Configure the global key-value store.

    Args:
        store_type: Type of store to use ("memory" or "redis")
        **kwargs: Additional configuration parameters for the store
    """
    _global_store_manager.configure(store_type, **kwargs)


async def get_global_store() -> KeyValueStore:
    """Get the global key-value store instance.

    Returns:
        The configured global key-value store

    Raises:
        RuntimeError: If no global store has been configured
    """
    return await _global_store_manager.get()


@asynccontextmanager
async def get_store_context(
    store_type: str = "memory", **kwargs: object
) -> AsyncIterator[KeyValueStore]:
    """Context manager for getting a key-value store instance.

    Args:
        store_type: Type of store to use ("memory" or "redis")
        **kwargs: Additional configuration parameters for the store

    Yields:
        A key-value store instance
    """
    store: KeyValueStore
    if store_type == "memory":
        store = InMemoryKeyValueStore(**kwargs)
    elif store_type == "redis":
        store = RedisKeyValueStore(**kwargs)
    else:
        raise ValueError(f"Unknown store: {store_type}")  # noqa: TRY003

    try:
        yield store
    finally:
        await store.close()


# Convenience functions for common operations
async def put(
    key: str,
    value: object,
    prefix: str | None = None,
    ttl: int | None = None,
    **kwargs: object,
) -> None:
    """Put a value in the global store."""
    store = await get_global_store()
    await store.put(key, value, ttl=ttl, prefix=prefix, **kwargs)


async def get(key: str, prefix: str | None = None, **kwargs: object) -> object | None:
    """Get a value from the global store."""
    store = await get_global_store()
    return await store.get(key, prefix=prefix, **kwargs)


async def delete(key: str, prefix: str | None = None, **kwargs: object) -> bool:
    """Delete a value from the global store."""
    store = await get_global_store()
    return await store.delete(key, prefix=prefix, **kwargs)


async def range_get(
    start_key: str,
    end_key: str | None = None,
    limit: int | None = None,
    prefix: str | None = None,
    **kwargs: object,
) -> list[tuple[str, Any]]:
    """Get a range of values from the global store."""
    store = await get_global_store()
    return await store.range_get(start_key, end_key, limit, prefix=prefix, **kwargs)


async def exists(key: str, prefix: str | None = None, **kwargs: object) -> bool:
    """Check if a key exists in the global store."""
    store = await get_global_store()
    return await store.exists(key, prefix=prefix, **kwargs)


# Convenience functions that automatically use fetcher_id from context
async def put_with_fetcher_id(
    key: str, value: object, ctx: object, **kwargs: object
) -> None:
    """Put a value in the global store with fetcher_id prefix if available."""
    prefix = ctx.run_id if hasattr(ctx, "run_id") and ctx.run_id else None
    ttl = cast("int | None", kwargs.pop("ttl", None)) if "ttl" in kwargs else None
    await put(key, value, prefix=prefix, ttl=ttl, **kwargs)


async def get_with_fetcher_id(key: str, ctx: object, **kwargs: object) -> object | None:
    """Get a value from the global store with fetcher_id prefix if available."""
    prefix = ctx.run_id if hasattr(ctx, "run_id") and ctx.run_id else None
    return await get(key, prefix=prefix, **kwargs)


async def delete_with_fetcher_id(key: str, ctx: object, **kwargs: object) -> bool:
    """Delete a value from the global store with fetcher_id prefix if available."""
    prefix = ctx.run_id if hasattr(ctx, "run_id") and ctx.run_id else None
    return await delete(key, prefix=prefix, **kwargs)


async def range_get_with_fetcher_id(
    start_key: str,
    end_key: str | None = None,
    limit: int | None = None,
    ctx: object = None,
    **kwargs: object,
) -> list[tuple[str, Any]]:
    """Get a range of values from the global store with fetcher_id prefix if available."""
    prefix = ctx.run_id if ctx and hasattr(ctx, "run_id") and ctx.run_id else None
    return await range_get(start_key, end_key, limit, prefix=prefix, **kwargs)


async def exists_with_fetcher_id(key: str, ctx: object, **kwargs: object) -> bool:
    """Check if a key exists in the global store with fetcher_id prefix if available."""
    prefix = ctx.run_id if hasattr(ctx, "run_id") and ctx.run_id else None
    return await exists(key, prefix=prefix, **kwargs)


__all__ = [
    "InMemoryKeyValueStore",
    "KeyValueStore",
    "RedisKeyValueStore",
    "configure_global_store",
    "delete",
    "delete_with_fetcher_id",
    "exists",
    "exists_with_fetcher_id",
    "get",
    "get_global_store",
    "get_store_context",
    "get_with_fetcher_id",
    "put",
    "put_with_fetcher_id",
    "range_get",
    "range_get_with_fetcher_id",
]
