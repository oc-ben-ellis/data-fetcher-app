"""Key-value store implementations and interfaces.

This module provides key-value store implementations for caching and persistence,
including in-memory storage, Redis integration, and the base interface.
"""

import asyncio
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any, Protocol

from .base import KeyValueStore
from .memory import InMemoryKeyValueStore
from .redis_store import RedisKeyValueStore


class KeyValueStoreFactory(Protocol):
    """Protocol for key-value store factory functions."""

    def __call__(self, **kwargs: Any) -> KeyValueStore:
        """Create a key-value store instance."""
        ...


# Global store instance
_global_store: KeyValueStore | None = None
_store_lock = asyncio.Lock()


def configure_global_store(store_type: str = "memory", **kwargs: Any) -> None:
    """Configure the global key-value store.

    Args:
        store_type: Type of store to use ("memory" or "redis")
        **kwargs: Additional configuration parameters for the store
    """
    global _global_store

    if store_type == "memory":
        _global_store = InMemoryKeyValueStore(**kwargs)
    elif store_type == "redis":
        _global_store = RedisKeyValueStore(**kwargs)
    else:
        raise ValueError(f"Unknown store type: {store_type}")


async def get_global_store() -> KeyValueStore:
    """Get the global key-value store instance.

    Returns:
        The configured global key-value store

    Raises:
        RuntimeError: If no global store has been configured
    """
    global _global_store

    if _global_store is None:
        raise RuntimeError(
            "Global key-value store not configured. "
            "Call configure_global_store() first."
        )

    return _global_store


@asynccontextmanager
async def get_store_context(store_type: str = "memory", **kwargs: Any) -> Any:
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
        raise ValueError(f"Unknown store type: {store_type}")

    try:
        yield store
    finally:
        await store.close()


# Convenience functions for common operations
async def put(key: str, value: Any, prefix: str | None = None, **kwargs: Any) -> None:
    """Put a value in the global store."""
    store = await get_global_store()
    await store.put(key, value, prefix=prefix, **kwargs)


async def get(key: str, prefix: str | None = None, **kwargs: Any) -> Any | None:
    """Get a value from the global store."""
    store = await get_global_store()
    return await store.get(key, prefix=prefix, **kwargs)


async def delete(key: str, prefix: str | None = None, **kwargs: Any) -> bool:
    """Delete a value from the global store."""
    store = await get_global_store()
    return await store.delete(key, prefix=prefix, **kwargs)


async def range_get(
    start_key: str,
    end_key: str | None = None,
    limit: int | None = None,
    prefix: str | None = None,
    **kwargs: Any,
) -> list[tuple[str, Any]]:
    """Get a range of values from the global store."""
    store = await get_global_store()
    return await store.range_get(start_key, end_key, limit, prefix=prefix, **kwargs)


async def exists(key: str, prefix: str | None = None, **kwargs: Any) -> bool:
    """Check if a key exists in the global store."""
    store = await get_global_store()
    return await store.exists(key, prefix=prefix, **kwargs)


# Convenience functions that automatically use fetcher_id from context
async def put_with_fetcher_id(key: str, value: Any, ctx: Any, **kwargs: Any) -> None:
    """Put a value in the global store with fetcher_id prefix if available."""
    prefix = ctx.run_id if hasattr(ctx, "run_id") and ctx.run_id else None
    await put(key, value, prefix=prefix, **kwargs)


async def get_with_fetcher_id(key: str, ctx: Any, **kwargs: Any) -> Any | None:
    """Get a value from the global store with fetcher_id prefix if available."""
    prefix = ctx.run_id if hasattr(ctx, "run_id") and ctx.run_id else None
    return await get(key, prefix=prefix, **kwargs)


async def delete_with_fetcher_id(key: str, ctx: Any, **kwargs: Any) -> bool:
    """Delete a value from the global store with fetcher_id prefix if available."""
    prefix = ctx.run_id if hasattr(ctx, "run_id") and ctx.run_id else None
    return await delete(key, prefix=prefix, **kwargs)


async def range_get_with_fetcher_id(
    start_key: str,
    end_key: str | None = None,
    limit: int | None = None,
    ctx: Any = None,
    **kwargs: Any,
) -> list[tuple[str, Any]]:
    """Get a range of values from the global store with fetcher_id prefix if available."""
    prefix = ctx.run_id if ctx and hasattr(ctx, "run_id") and ctx.run_id else None
    return await range_get(start_key, end_key, limit, prefix=prefix, **kwargs)


async def exists_with_fetcher_id(key: str, ctx: Any, **kwargs: Any) -> bool:
    """Check if a key exists in the global store with fetcher_id prefix if available."""
    prefix = ctx.run_id if hasattr(ctx, "run_id") and ctx.run_id else None
    return await exists(key, prefix=prefix, **kwargs)


__all__ = [
    "KeyValueStore",
    "InMemoryKeyValueStore",
    "RedisKeyValueStore",
    "configure_global_store",
    "get_global_store",
    "get_store_context",
    "put",
    "get",
    "delete",
    "range_get",
    "exists",
    "put_with_fetcher_id",
    "get_with_fetcher_id",
    "delete_with_fetcher_id",
    "range_get_with_fetcher_id",
    "exists_with_fetcher_id",
]
