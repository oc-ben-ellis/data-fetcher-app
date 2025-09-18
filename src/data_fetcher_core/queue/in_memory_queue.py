"""In-memory queue implementation.

This module provides an in-memory queue implementation using asyncio.Queue
for fast, non-persistent queuing within a single process.
"""

from __future__ import annotations

import asyncio
from collections import deque
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from collections.abc import Iterable

    from .base import Serializer

from data_fetcher_core.exceptions import ConfigurationError

# Get logger for this module
logger = structlog.get_logger(__name__)


class InMemoryQueue:
    """In-memory queue implementation using asyncio.Queue.

    This implementation provides fast, non-persistent queuing that is lost
    when the application restarts. Useful for single-process scenarios where
    persistence is handled by the locators.
    """

    def __init__(self, serializer: Serializer) -> None:
        """Initialize the in-memory queue.

        Args:
            serializer: Serializer for queue items.

        Raises:
            ConfigurationError: If serializer is None.
        """
        if serializer is None:
            error_message = "serializer is required"
            raise ConfigurationError(error_message, "queue")

        self._ser = serializer
        self._queue: asyncio.Queue[object] = asyncio.Queue()
        self._peek_buffer: deque[object] = deque()  # For peek operations

        logger.debug("InMemoryQueue initialized")

    async def enqueue(self, items: Iterable[object]) -> int:
        """Add items to the queue.

        Args:
            items: Iterable of items to add to the queue.

        Returns:
            Number of items successfully enqueued.
        """
        if items is None:
            error_message = "items cannot be None"
            raise ValueError(error_message)

        items_list = list(items)
        if not items_list:
            return 0

        # Add items to the queue
        for item in items_list:
            await self._queue.put(item)

        logger.debug(
            "Items enqueued successfully",
            count=len(items_list),
            queue_size=self._queue.qsize()
        )

        return len(items_list)

    async def dequeue(self, max_items: int = 1) -> list[object]:
        """Remove items from the queue.

        Args:
            max_items: Maximum number of items to dequeue. Defaults to 1.

        Returns:
            List of dequeued items. May be empty if queue is empty.
        """
        if max_items <= 0:
            return []

        results = []
        items_to_get = min(max_items, self._queue.qsize())

        for _ in range(items_to_get):
            try:
                # Use get_nowait to avoid blocking
                item = self._queue.get_nowait()
                results.append(item)
                self._queue.task_done()
            except asyncio.QueueEmpty:
                break

        logger.debug(
            "Items dequeued successfully",
            count=len(results),
            queue_size=self._queue.qsize()
        )

        return results

    async def size(self) -> int:
        """Get current queue size.

        Returns:
            Current number of items in the queue.
        """
        return self._queue.qsize()

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
        items_to_peek = min(max_items, self._queue.qsize())

        # Temporarily store items we peek at
        temp_items = []
        
        try:
            # Get items from queue
            for _ in range(items_to_peek):
                try:
                    item = self._queue.get_nowait()
                    results.append(item)
                    temp_items.append(item)
                except asyncio.QueueEmpty:
                    break

            # Put items back in the same order
            for item in temp_items:
                await self._queue.put(item)

        except Exception as e:
            # If something goes wrong, try to restore items
            for item in temp_items:
                try:
                    await self._queue.put(item)
                except Exception:
                    logger.exception("Failed to restore item after peek error", error=str(e))
            raise

        return results

    async def clear(self) -> int:
        """Clear all items from queue.

        Returns:
            Number of items that were cleared from the queue.
        """
        cleared_count = self._queue.qsize()
        
        # Drain the queue
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except asyncio.QueueEmpty:
                break

        logger.debug("Queue cleared", cleared_count=cleared_count)
        return cleared_count

    async def close(self) -> None:
        """Cleanup resources.

        In-memory queue doesn't need cleanup.
        """
        # In-memory queue doesn't need cleanup
        pass
