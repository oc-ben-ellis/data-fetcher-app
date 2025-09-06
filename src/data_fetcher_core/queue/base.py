"""Base queue interface and protocols.

This module defines the base RequestQueue protocol for persistent queue implementations
that enable resumable operations without re-querying remote data providers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Iterable


class Serializer(Protocol):
    """Protocol for serializing/deserializing queue items.

    Implementations should handle the conversion between Python objects
    and their serialized string representation for storage.
    """

    def dumps(self, obj: object) -> str:
        """Serialize object to string representation.

        Args:
            obj: The object to serialize.

        Returns:
            String representation of the object.
        """
        ...

    def loads(self, data: str) -> object:
        """Deserialize string to object.

        Args:
            data: The string data to deserialize.

        Returns:
            The deserialized object.
        """
        ...


class RequestQueue(Protocol):
    """Protocol for persistent, resumable, thread-safe queue implementations.

    This protocol defines the interface that all persistent queue implementations
    must follow for managing request queues that survive application restarts.
    """

    async def enqueue(self, items: Iterable[object]) -> int:
        """Add items to the queue.

        Args:
            items: Iterable of items to add to the queue.

        Returns:
            Number of items successfully enqueued.
        """
        ...

    async def dequeue(self, max_items: int = 1) -> list[object]:
        """Atomically remove up to max_items from the queue.

        Args:
            max_items: Maximum number of items to dequeue. Defaults to 1.

        Returns:
            List of dequeued items. May be empty if queue is empty.
        """
        ...

    async def size(self) -> int:
        """Get current queue size.

        Returns:
            Current number of items in the queue.
        """
        ...

    async def peek(self, max_items: int = 1) -> list[object]:
        """Peek at items without removing them.

        Args:
            max_items: Maximum number of items to peek at. Defaults to 1.

        Returns:
            List of items at the front of the queue without removing them.
        """
        ...

    async def clear(self) -> int:
        """Clear all items from queue.

        Returns:
            Number of items that were cleared from the queue.
        """
        ...

    async def close(self) -> None:
        """Cleanup resources.

        Should be called when the queue is no longer needed to release
        any resources held by the implementation.
        """
        ...
