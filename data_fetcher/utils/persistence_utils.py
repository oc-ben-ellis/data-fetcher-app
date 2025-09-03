"""Persistence utility functions and helpers.

This module provides utility functions for data persistence operations,
including serialization, deserialization, and data transformation helpers.
"""

from datetime import datetime, timedelta
from typing import Any

from ..kv_store import KeyValueStore, get_global_store


class PersistenceManager:
    """Manager for persistence operations across different providers."""

    def __init__(self, prefix: str = "persistence"):
        """Initialize the persistence manager with a prefix.

        Args:
            prefix: Prefix for all persistence keys.
        """
        self.prefix = prefix
        self._store: KeyValueStore | None = None

    async def _get_store(self) -> KeyValueStore:
        """Get the key-value store instance."""
        if self._store is None:
            self._store = await get_global_store()
        return self._store

    async def save_processed_items(
        self, items: set[str], ttl: timedelta | None = None
    ) -> None:
        """Save a set of processed items."""
        store = await self._get_store()
        key = f"{self.prefix}:processed_items"
        await store.put(key, list(items), ttl=ttl or timedelta(days=7))

    async def load_processed_items(self) -> set[str]:
        """Load a set of processed items."""
        store = await self._get_store()
        key = f"{self.prefix}:processed_items"
        items = await store.get(key, [])
        if isinstance(items, list):
            return set(items)
        return set()

    async def save_state(
        self, state: dict[str, Any], ttl: timedelta | None = None
    ) -> None:
        """Save state information."""
        store = await self._get_store()
        key = f"{self.prefix}:state"
        state["last_updated"] = datetime.now().isoformat()
        await store.put(key, state, ttl=ttl or timedelta(days=7))

    async def load_state(self) -> dict[str, Any]:
        """Load state information."""
        store = await self._get_store()
        key = f"{self.prefix}:state"
        result = await store.get(key, {})
        if isinstance(result, dict):
            return result
        return {}

    async def save_error(self, item_id: str, error: str, retry_count: int = 0) -> None:
        """Save error information for an item."""
        store = await self._get_store()
        key = f"{self.prefix}:errors:{item_id}"
        error_data = {
            "item_id": item_id,
            "error": error,
            "retry_count": retry_count,
            "timestamp": datetime.now().isoformat(),
        }
        await store.put(key, error_data, ttl=timedelta(hours=24))

    async def get_error(self, item_id: str) -> dict[str, Any] | None:
        """Get error information for an item."""
        store = await self._get_store()
        key = f"{self.prefix}:errors:{item_id}"
        result = await store.get(key)
        if isinstance(result, dict):
            return result
        return None

    async def increment_retry_count(self, item_id: str) -> int:
        """Increment retry count for an item."""
        error_data = await self.get_error(item_id)
        if error_data:
            retry_count_raw = error_data.get("retry_count", 0)
            if isinstance(retry_count_raw, int):
                retry_count = retry_count_raw + 1
            else:
                retry_count = 1
            await self.save_error(item_id, error_data["error"], retry_count)
            return retry_count
        return 0

    async def get_failed_items(self, max_retries: int = 3) -> list[dict[str, Any]]:
        """Get list of failed items that haven't exceeded max retries."""
        store = await self._get_store()
        failed_items = []

        # Get all error keys
        error_keys = await store.range_get(f"{self.prefix}:errors:")

        for _key, error_data in error_keys:
            if (
                isinstance(error_data, dict)
                and error_data.get("retry_count", 0) < max_retries
            ):
                failed_items.append(error_data)

        return failed_items

    async def clear_errors(self, item_id: str | None = None) -> None:
        """Clear error information."""
        store = await self._get_store()
        if item_id:
            key = f"{self.prefix}:errors:{item_id}"
            await store.delete(key)
        else:
            # Clear all errors for this prefix
            error_keys = await store.range_get(f"{self.prefix}:errors:")
            for key, _ in error_keys:
                await store.delete(key)


class RetryManager:
    """Manager for retry logic using persistence."""

    def __init__(self, max_retries: int = 3, backoff_factor: float = 2.0):
        """Initialize the retry manager with retry configuration.

        Args:
            max_retries: Maximum number of retry attempts.
            backoff_factor: Factor for exponential backoff delay.
        """
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self._store: KeyValueStore | None = None

    async def _get_store(self) -> KeyValueStore:
        """Get the key-value store instance."""
        if self._store is None:
            self._store = await get_global_store()
        return self._store

    async def should_retry(self, item_id: str) -> bool:
        """Check if an item should be retried."""
        store = await self._get_store()
        key = f"retry:{item_id}"
        retry_data = await store.get(key)

        if not retry_data:
            return True

        retry_count_raw = retry_data.get("retry_count", 0)
        if isinstance(retry_count_raw, int):
            retry_count = retry_count_raw
        else:
            retry_count = 0
        return bool(retry_count < self.max_retries)

    async def record_retry(self, item_id: str, error: str) -> int:
        """Record a retry attempt."""
        store = await self._get_store()
        key = f"retry:{item_id}"

        retry_data = await store.get(key, {"retry_count": 0, "errors": []})
        if isinstance(retry_data, dict):
            retry_count_raw = retry_data.get("retry_count", 0)
            if isinstance(retry_count_raw, int):
                retry_count = retry_count_raw + 1
            else:
                retry_count = 1

            retry_data.update(
                {
                    "retry_count": retry_count,
                    "last_error": error,
                    "last_retry": datetime.now().isoformat(),
                    "errors": retry_data.get("errors", []) + [error],
                }
            )

            await store.put(key, retry_data, ttl=timedelta(hours=24))
            return retry_count
        return 1

    async def get_retry_delay(self, item_id: str) -> float:
        """Get the delay before next retry attempt."""
        store = await self._get_store()
        key = f"retry:{item_id}"
        retry_data = await store.get(key)

        if not retry_data:
            return 1.0  # Initial delay

        retry_count_raw = retry_data.get("retry_count", 0)
        if isinstance(retry_count_raw, int):
            retry_count = retry_count_raw
        else:
            retry_count = 0
        delay = self.backoff_factor**retry_count
        return min(60.0, delay)  # Cap at 60 seconds

    async def clear_retry_data(self, item_id: str) -> None:
        """Clear retry data for an item (when successful)."""
        store = await self._get_store()
        key = f"retry:{item_id}"
        await store.delete(key)


class StateTracker:
    """Track processing state and statistics."""

    def __init__(self, prefix: str = "state_tracker"):
        """Initialize the state tracker with a prefix.

        Args:
            prefix: Prefix for all state tracking keys.
        """
        self.prefix = prefix
        self._store: KeyValueStore | None = None

    async def _get_store(self) -> KeyValueStore:
        """Get the key-value store instance."""
        if self._store is None:
            self._store = await get_global_store()
        return self._store

    async def increment_counter(self, counter_name: str, amount: int = 1) -> int:
        """Increment a counter."""
        store = await self._get_store()
        key = f"{self.prefix}:counter:{counter_name}"

        current_value = await store.get(key, 0)
        if isinstance(current_value, int):
            new_value = current_value + amount
        else:
            new_value = amount

        await store.put(key, new_value, ttl=timedelta(days=30))
        return new_value

    async def get_counter(self, counter_name: str) -> int:
        """Get a counter value."""
        store = await self._get_store()
        key = f"{self.prefix}:counter:{counter_name}"
        result = await store.get(key, 0)
        if isinstance(result, int):
            return result
        return 0

    async def record_processing_time(self, operation: str, duration: float) -> None:
        """Record processing time for an operation."""
        store = await self._get_store()
        key = f"{self.prefix}:timing:{operation}"

        timing_data = await store.get(
            key,
            {
                "count": 0,
                "total_time": 0.0,
                "min_time": float("inf"),
                "max_time": 0.0,
                "last_updated": None,
            },
        )

        if isinstance(timing_data, dict):
            timing_data["count"] += 1
            timing_data["total_time"] += duration
            timing_data["min_time"] = min(timing_data["min_time"], duration)
            timing_data["max_time"] = max(timing_data["max_time"], duration)
            timing_data["last_updated"] = datetime.now().isoformat()

            await store.put(key, timing_data, ttl=timedelta(days=7))

    async def get_processing_stats(self, operation: str) -> dict[str, Any]:
        """Get processing statistics for an operation."""
        store = await self._get_store()
        key = f"{self.prefix}:timing:{operation}"
        timing_data = await store.get(key, {})

        if timing_data and timing_data.get("count", 0) > 0:
            return {
                "count": timing_data["count"],
                "avg_time": timing_data["total_time"] / timing_data["count"],
                "min_time": timing_data["min_time"],
                "max_time": timing_data["max_time"],
                "last_updated": timing_data["last_updated"],
            }

        return {}

    async def save_session_info(self, session_id: str, info: dict[str, Any]) -> None:
        """Save session information."""
        store = await self._get_store()
        key = f"{self.prefix}:session:{session_id}"
        info["created_at"] = datetime.now().isoformat()
        await store.put(key, info, ttl=timedelta(days=1))

    async def get_session_info(self, session_id: str) -> dict[str, Any] | None:
        """Get session information."""
        store = await self._get_store()
        key = f"{self.prefix}:session:{session_id}"
        result = await store.get(key)
        if isinstance(result, dict):
            return result
        return None

    async def get_state(self) -> dict[str, Any]:
        """Get the current state."""
        store = await self._get_store()
        key = f"{self.prefix}:state"
        result = await store.get(key, {})
        if isinstance(result, dict):
            return result
        return {}

    async def update_state(self, state_updates: dict[str, Any]) -> None:
        """Update the current state with new values."""
        store = await self._get_store()
        key = f"{self.prefix}:state"

        current_state = await store.get(key, {})
        if isinstance(current_state, dict):
            current_state.update(state_updates)
            current_state["last_updated"] = datetime.now().isoformat()
        else:
            current_state = state_updates
            current_state["last_updated"] = datetime.now().isoformat()

        await store.put(key, current_state, ttl=timedelta(days=7))


async def create_persistence_manager(prefix: str) -> PersistenceManager:
    """Create a persistence manager with the given prefix."""
    return PersistenceManager(prefix)


async def create_retry_manager(
    max_retries: int = 3, backoff_factor: float = 2.0
) -> RetryManager:
    """Create a retry manager with the given configuration."""
    return RetryManager(max_retries, backoff_factor)


async def create_state_tracker(prefix: str) -> StateTracker:
    """Create a state tracker with the given prefix."""
    return StateTracker(prefix)
