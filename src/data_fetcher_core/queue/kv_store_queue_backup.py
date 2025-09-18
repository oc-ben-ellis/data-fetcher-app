"""KV store-backed persistent queue implementation.

This module provides a persistent queue implementation using the existing
KeyValueStore for durability and resumability across application restarts.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast

import structlog

if TYPE_CHECKING:
    from collections.abc import Iterable

    from data_fetcher_core.kv_store.base import KeyValueStore

    from .base import Serializer

from data_fetcher_core.exceptions import ConfigurationError, StorageError

# Get logger for this module
logger = structlog.get_logger(__name__)


class KVStoreQueue:
    """Queue implementation using KeyValueStore for persistence.

    Uses a simple counter-based approach:
    - queue:items:{id} -> serialized item
    - queue:next_id -> next available ID
    - queue:size -> current queue size

    This implementation provides thread-safe, persistent queuing that survives
    application restarts, enabling resumable operations without re-querying
    remote data providers.
    """

    def __init__(
        self, kv_store: KeyValueStore, namespace: str, serializer: Serializer
    ) -> None:
        """Initialize the KV store queue.

        Args:
            kv_store: The key-value store to use for persistence.
            namespace: Namespace for queue keys (e.g., "fetch:run_id").
            serializer: Serializer for queue items.

        Raises:
            ConfigurationError: If namespace is empty or invalid.
        """
        if not namespace or not isinstance(namespace, str) or not namespace.strip():
            error_message = "namespace must be a non-empty string"
            raise ConfigurationError(error_message, "queue")

        if kv_store is None:
            error_message = "kv_store is required"  # type: ignore[unreachable]
            raise ConfigurationError(error_message, "queue")

        if serializer is None:
            error_message = "serializer is required"  # type: ignore[unreachable]
            raise ConfigurationError(error_message, "queue")

        self._kv = kv_store
        self._ns = namespace.strip()
        self._ser = serializer
        self._lock = asyncio.Lock()  # async-level safety

        logger.debug("KVStoreQueue initialized", namespace=self._ns)

    @property
    def _keys(self) -> dict[str, str]:
        """Get the key names for queue metadata.

        Returns:
            Dictionary mapping metadata names to their key names.
        """
        return {
            "next_id": f"{self._ns}:next_id",
            "size": f"{self._ns}:size",
        }

    def _item_key(self, item_id: int) -> str:
        """Get the key name for a specific item.

        Args:
            item_id: The item ID.

        Returns:
            The key name for the item.
        """
        return f"{self._ns}:items:{item_id}"

    async def enqueue(self, items: Iterable[object]) -> int:
        """Add items to the queue.

        Args:
            items: Iterable of items to add to the queue.

        Returns:
            Number of items successfully enqueued.

        Raises:
            StorageError: If queue operations fail.
        """
        if items is None:
            error_message = "items cannot be None"  # type: ignore[unreachable]
            raise ValueError(error_message)

        items_list = list(items)
        if not items_list:
            return 0

        try:
            async with self._lock:
                # Get current next_id and size
                next_id = cast(
                    "int", await self._kv.get(self._keys["next_id"], default=0)
                )
                current_size = cast(
                    "int", await self._kv.get(self._keys["size"], default=0)
                )

                # Store items with sequential IDs
                for item in items_list:
                    try:
                        serialized_item = self._ser.dumps(item)
                        await self._kv.put(self._item_key(next_id), serialized_item)
                        next_id += 1
                    except Exception as e:
                        logger.exception(
                            "Failed to serialize or store item",
                            item_id=next_id,
                            error=str(e),
                        )
                        error_message = "Failed to store item"
                        raise StorageError(error_message, "kv_store") from e

                # Update counters
                await self._kv.put(self._keys["next_id"], next_id)
                await self._kv.put(self._keys["size"], current_size + len(items_list))

                logger.debug(
                    "Items enqueued successfully",
                    count=len(items_list),
                    new_size=current_size + len(items_list),
                )

            return len(items_list)

        except Exception as e:
            if isinstance(e, StorageError):
                raise
            error_message = "Failed to enqueue items"
            raise StorageError(error_message, "kv_store") from e

    async def dequeue(self, max_items: int = 1) -> list[object]:
        """Remove items from the queue.

        Args:
            max_items: Maximum number of items to dequeue. Defaults to 1.

        Returns:
            List of dequeued items. May be empty if queue is empty.

        Raises:
            StorageError: If queue operations fail.
        """
        if max_items <= 0:
            return []

        try:
            results = []
            async with self._lock:
                current_size = cast(
                    "int", await self._kv.get(self._keys["size"], default=0)
                )
                if current_size == 0:
                    return []

                # Get items to dequeue (from the beginning)
                items_to_get = min(max_items, current_size)
                next_id = cast(
                    "int", await self._kv.get(self._keys["next_id"], default=0)
                )
                start_id = next_id - current_size

                for i in range(items_to_get):
                    item_id = start_id + i
                    item_key = self._item_key(item_id)
                    try:
                        item_data = await self._kv.get(item_key)
                        if item_data is not None:
                            deserialized_item = self._ser.loads(cast("str", item_data))
                            results.append(deserialized_item)
                            await self._kv.delete(item_key)
                        else:
                            logger.warning(
                                "Item not found during dequeue",
                                item_id=item_id,
                                item_key=item_key,
                            )
                    except Exception as e:
                        logger.exception(
                            "Failed to deserialize or delete item",
                            item_id=item_id,
                            error=str(e),
                        )
                        error_message = "Failed to dequeue item"
                        raise StorageError(error_message, "kv_store") from e

                # Update size
                new_size = current_size - len(results)
                await self._kv.put(self._keys["size"], new_size)

                logger.debug(
                    "Items dequeued successfully", count=len(results), new_size=new_size
                )

        except Exception as e:
            if isinstance(e, StorageError):
                raise
            error_message = "Failed to dequeue items"
            raise StorageError(error_message, "kv_store") from e
        else:
            return results

    async def size(self) -> int:
        """Get current queue size.

        Returns:
            Current number of items in the queue.
        """
        return cast("int", await self._kv.get(self._keys["size"], default=0))

    async def peek(self, max_items: int = 1) -> list[object]:
        """Peek at items without removing them.

        Args:
            max_items: Maximum number of items to peek at. Defaults to 1.

        Returns:
            List of items at the front of the queue without removing them.
        """
        if max_items <= 0:
            return []

        results = []
        current_size = cast("int", await self._kv.get(self._keys["size"], default=0))
        if current_size == 0:
            return []

        items_to_get = min(max_items, current_size)
        next_id = cast("int", await self._kv.get(self._keys["next_id"], default=0))
        start_id = next_id - current_size

        for i in range(items_to_get):
            item_id = start_id + i
            item_key = self._item_key(item_id)
            item_data = await self._kv.get(item_key)
            if item_data is not None:
                results.append(self._ser.loads(cast("str", item_data)))

        return results

    async def clear(self) -> int:
        """Clear all items from queue.

        Returns:
            Number of items that were cleared from the queue.
        """
        async with self._lock:
            current_size = cast(
                "int", await self._kv.get(self._keys["size"], default=0)
            )
            if current_size == 0:
                return 0

            # Delete all item keys
            next_id = cast("int", await self._kv.get(self._keys["next_id"], default=0))
            start_id = next_id - current_size

            for item_id in range(start_id, next_id):
                await self._kv.delete(self._item_key(item_id))

            # Reset counters
            await self._kv.put(self._keys["size"], 0)

        return current_size

    async def close(self) -> None:
        """Cleanup resources.

        KV store handles its own cleanup, so this is a no-op.
        """
        # KV store handles its own cleanup
