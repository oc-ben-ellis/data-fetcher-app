"""KV store-backed persistent queue implementation with recovery and compensating actions.

This module provides a robust persistent queue implementation using the existing
KeyValueStore for durability and resumability across application restarts.
Includes automatic recovery from inconsistencies and compensating actions for failures.
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
    """Queue implementation using KeyValueStore for persistence with recovery.

    Uses a simple counter-based approach:
    - queue:items:{id} -> serialized item
    - queue:next_id -> next available ID
    - queue:size -> current queue size

    This implementation provides thread-safe, persistent queuing that survives
    application restarts, enabling resumable operations without re-querying
    remote data providers. Includes automatic recovery from inconsistencies.
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
        self._initialized = False

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

    async def _ensure_initialized(self) -> None:
        """Ensure queue is initialized and recovered."""
        if not self._initialized:
            await self._recover_queue_state()
            self._initialized = True

    async def _recover_queue_state(self) -> None:
        """Recover queue state by scanning for orphaned items and fixing counters."""
        async with self._lock:
            logger.debug("Starting queue state recovery", namespace=self._ns)
            
            # Get current counters
            stored_next_id = cast("int", await self._kv.get(self._keys["next_id"], default=0))
            stored_size = cast("int", await self._kv.get(self._keys["size"], default=0))
            
            # Scan for actual items in the queue
            items_prefix = f"{self._ns}:items:"
            actual_items = await self._kv.range_get(items_prefix)
            
            if actual_items:
                # Find the actual range of items
                item_ids = []
                for key, _ in actual_items:
                    # Extract ID from key like "namespace:items:123"
                    item_id_str = key.split(":")[-1]
                    try:
                        item_ids.append(int(item_id_str))
                    except ValueError:
                        logger.warning("Invalid item key found during recovery", key=key)
                        continue
                
                if item_ids:
                    actual_start_id = min(item_ids)
                    actual_end_id = max(item_ids) + 1
                    actual_size = len(item_ids)
                    
                    # Check for inconsistencies
                    expected_start_id = stored_next_id - stored_size
                    
                    if actual_start_id != expected_start_id or actual_size != stored_size:
                        logger.warning(
                            "Queue state inconsistency detected",
                            namespace=self._ns,
                            stored_size=stored_size,
                            actual_size=actual_size,
                            stored_next_id=stored_next_id,
                            actual_start_id=actual_start_id,
                            actual_end_id=actual_end_id
                        )
                        
                        # Fix the counters
                        await self._kv.put(self._keys["next_id"], actual_end_id)
                        await self._kv.put(self._keys["size"], actual_size)
                        
                        logger.info(
                            "Queue state recovered",
                            namespace=self._ns,
                            new_size=actual_size,
                            new_next_id=actual_end_id
                        )
                    else:
                        logger.debug("Queue state is consistent", namespace=self._ns)
                else:
                    # No valid items found, reset counters
                    if stored_size > 0 or stored_next_id > 0:
                        logger.warning(
                            "No valid items found but counters are non-zero, resetting",
                            namespace=self._ns,
                            stored_size=stored_size,
                            stored_next_id=stored_next_id
                        )
                        await self._kv.put(self._keys["next_id"], 0)
                        await self._kv.put(self._keys["size"], 0)
            else:
                # No items found, reset counters if they're non-zero
                if stored_size > 0 or stored_next_id > 0:
                    logger.warning(
                        "No items found but counters are non-zero, resetting",
                        namespace=self._ns,
                        stored_size=stored_size,
                        stored_next_id=stored_next_id
                    )
                    await self._kv.put(self._keys["next_id"], 0)
                    await self._kv.put(self._keys["size"], 0)

    async def enqueue(self, items: Iterable[object]) -> int:
        """Add items to the queue with compensating actions.

        Args:
            items: Iterable of items to add to the queue.

        Returns:
            Number of items successfully enqueued.

        Raises:
            StorageError: If queue operations fail.
        """
        await self._ensure_initialized()
        
        if items is None:
            error_message = "items cannot be None"  # type: ignore[unreachable]
            raise ValueError(error_message)

        items_list = list(items)
        if not items_list:
            return 0

        try:
            async with self._lock:
                # Get current state
                next_id = cast("int", await self._kv.get(self._keys["next_id"], default=0))
                current_size = cast("int", await self._kv.get(self._keys["size"], default=0))
                
                # Track items we've stored for rollback
                stored_item_ids = []
                
                try:
                    # Store items with sequential IDs
                    for item in items_list:
                        try:
                            serialized_item = self._ser.dumps(item)
                            await self._kv.put(self._item_key(next_id), serialized_item)
                            stored_item_ids.append(next_id)
                            next_id += 1
                        except Exception as e:
                            # Rollback: delete any items we've stored so far
                            for item_id in stored_item_ids:
                                await self._kv.delete(self._item_key(item_id))
                            
                            logger.exception(
                                "Failed to store item, rolled back",
                                namespace=self._ns,
                                item_id=next_id,
                                error=str(e)
                            )
                            error_message = "Failed to store item"
                            raise StorageError(error_message, "kv_store") from e

                    # Update counters
                    await self._kv.put(self._keys["next_id"], next_id)
                    await self._kv.put(self._keys["size"], current_size + len(items_list))
                    
                    logger.debug(
                        "Items enqueued successfully",
                        namespace=self._ns,
                        count=len(items_list),
                        new_size=current_size + len(items_list)
                    )
                    
                    return len(items_list)
                    
                except Exception as e:
                    # Final rollback if counter updates fail
                    for item_id in stored_item_ids:
                        await self._kv.delete(self._item_key(item_id))
                    raise

        except Exception as e:
            if isinstance(e, StorageError):
                raise
            error_message = "Failed to enqueue items"
            raise StorageError(error_message, "kv_store") from e

    async def dequeue(self, max_items: int = 1) -> list[object]:
        """Remove items from the queue with compensating actions.

        Args:
            max_items: Maximum number of items to dequeue. Defaults to 1.

        Returns:
            List of dequeued items. May be empty if queue is empty.

        Raises:
            StorageError: If queue operations fail.
        """
        await self._ensure_initialized()
        
        if max_items <= 0:
            return []

        try:
            async with self._lock:
                current_size = cast("int", await self._kv.get(self._keys["size"], default=0))
                if current_size == 0:
                    return []

                # Get items to dequeue
                items_to_get = min(max_items, current_size)
                next_id = cast("int", await self._kv.get(self._keys["next_id"], default=0))
                start_id = next_id - current_size

                results = []
                deleted_item_ids = []
                
                try:
                    for i in range(items_to_get):
                        item_id = start_id + i
                        item_key = self._item_key(item_id)
                        
                        try:
                            item_data = await self._kv.get(item_key)
                            if item_data is not None:
                                deserialized_item = self._ser.loads(cast("str", item_data))
                                results.append(deserialized_item)
                                await self._kv.delete(item_key)
                                deleted_item_ids.append(item_id)
                            else:
                                logger.warning(
                                    "Item not found during dequeue",
                                    namespace=self._ns,
                                    item_id=item_id
                                )
                                
                        except Exception as e:
                            logger.exception(
                                "Failed to dequeue item",
                                namespace=self._ns,
                                item_id=item_id,
                                error=str(e)
                            )
                            error_message = "Failed to dequeue item"
                            raise StorageError(error_message, "kv_store") from e

                    # Update size
                    new_size = current_size - len(results)
                    await self._kv.put(self._keys["size"], new_size)
                    
                    logger.debug(
                        "Items dequeued successfully",
                        namespace=self._ns,
                        count=len(results),
                        new_size=new_size
                    )
                    
                    return results
                    
                except Exception as e:
                    # If size update fails, we need to recover
                    logger.error(
                        "Size update failed, queue may be inconsistent",
                        namespace=self._ns,
                        error=str(e)
                    )
                    # Trigger queue recovery on next operation
                    self._initialized = False
                    raise

        except Exception as e:
            if isinstance(e, StorageError):
                raise
            error_message = "Failed to dequeue items"
            raise StorageError(error_message, "kv_store") from e

    async def size(self) -> int:
        """Get current queue size.

        Returns:
            Current number of items in the queue.
        """
        await self._ensure_initialized()
        return cast("int", await self._kv.get(self._keys["size"], default=0))

    async def peek(self, max_items: int = 1) -> list[object]:
        """Peek at items without removing them.

        Args:
            max_items: Maximum number of items to peek at. Defaults to 1.

        Returns:
            List of items at the front of the queue without removing them.
        """
        await self._ensure_initialized()
        
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
        await self._ensure_initialized()
        
        async with self._lock:
            current_size = cast("int", await self._kv.get(self._keys["size"], default=0))
            if current_size == 0:
                return 0

            # Delete all item keys
            next_id = cast("int", await self._kv.get(self._keys["next_id"], default=0))
            start_id = next_id - current_size

            for item_id in range(start_id, next_id):
                await self._kv.delete(self._item_key(item_id))

            # Reset counters
            await self._kv.put(self._keys["size"], 0)
            await self._kv.put(self._keys["next_id"], 0)

        return current_size

    async def close(self) -> None:
        """Cleanup resources.

        KV store handles its own cleanup, so this is a no-op.
        """
        # KV store handles its own cleanup
        pass
