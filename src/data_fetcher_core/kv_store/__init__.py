"""Key-value store implementations and interfaces.

This module provides key-value store implementations for persisting application state,
including in-memory storage, Redis integration, and the base interface.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Protocol, cast

from .base import BaseKeyValueStore, KeyValueStore
from .factory import create_kv_store, create_store
from .manager import (
    StateManagementManager,
    StateTracker,
    create_state_management_manager,
    create_state_tracker,
)
from .memory import InMemoryKeyValueStore
from .redis import RedisKeyValueStore


class KeyValueStoreFactory(Protocol):
    """Protocol for state management factory functions."""

    def __call__(self, **kwargs: object) -> KeyValueStore:
        """Create a state management store instance."""
        ...


@asynccontextmanager
async def get_store_context(
    store_type: str = "redis", **kwargs: object
) -> AsyncIterator[KeyValueStore]:
    """Context manager for getting a state management store instance.

    Args:
        store_type: Type of store to use ("memory" or "redis")
        **kwargs: Additional configuration parameters for the store

    Yields:
        A state management store instance
    """
    store = create_store(store_type, **kwargs)

    try:
        yield store
    finally:
        await store.close()


__all__ = [
    "BaseKeyValueStore",
    "InMemoryKeyValueStore",
    "KeyValueStore",
    "RedisKeyValueStore",
    "StateManagementManager",
    "StateTracker",
    "create_kv_store",
    "create_state_management_manager",
    "create_state_tracker",
    "create_store",
    "get_store_context",
]
