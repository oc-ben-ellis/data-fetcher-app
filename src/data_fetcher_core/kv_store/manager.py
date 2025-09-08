"""State management manager and related utilities.

This module provides high-level state management functionality including
StateManagementManager and StateTracker classes for managing
application state and processing statistics.
"""

from datetime import UTC, datetime, timedelta
from typing import Any, cast

from .base import KeyValueStore


class StateManagementManager:
    """Manager for state management operations across different providers."""

    def __init__(self, store: KeyValueStore, prefix: str = "state_management") -> None:
        """Initialize the state management manager with a store and prefix.

        Args:
            store: The key-value store instance to use.
            prefix: Prefix for all state management keys.
        """
        self.store = store
        self.prefix = prefix

    async def save_processed_items(
        self, items: set[str], ttl: timedelta | None = None
    ) -> None:
        """Save a set of processed items."""
        key = f"{self.prefix}:processed_items"
        await self.store.put(key, list(items), ttl=ttl or timedelta(days=7))

    async def load_processed_items(self) -> set[str]:
        """Load a set of processed items."""
        key = f"{self.prefix}:processed_items"
        items = await self.store.get(key, [])
        if isinstance(items, list):
            return set(items)
        return set()

    async def save_state(
        self, state: dict[str, Any], ttl: timedelta | None = None
    ) -> None:
        """Save state information."""
        key = f"{self.prefix}:state"
        state["last_updated"] = datetime.now(UTC).isoformat()
        await self.store.put(key, state, ttl=ttl or timedelta(days=7))

    async def load_state(self) -> dict[str, Any]:
        """Load state information."""
        key = f"{self.prefix}:state"
        result = await self.store.get(key, {})
        if isinstance(result, dict):
            return result
        return {}

    async def save_error(self, item_id: str, error: str, retry_count: int = 0) -> None:
        """Save error information for an item."""
        key = f"{self.prefix}:errors:{item_id}"
        error_data = {
            "item_id": item_id,
            "error": error,
            "retry_count": retry_count,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        await self.store.put(key, error_data, ttl=timedelta(hours=24))

    async def get_error(self, item_id: str) -> dict[str, Any] | None:
        """Get error information for an item."""
        key = f"{self.prefix}:errors:{item_id}"
        result = await self.store.get(key)
        if isinstance(result, dict):
            return result
        return None

    async def increment_retry_count(self, item_id: str) -> int:
        """Increment retry count for an item."""
        error_data = await self.get_error(item_id)
        if error_data:
            retry_count_raw = error_data.get("retry_count", 0)
            retry_count = retry_count_raw + 1 if isinstance(retry_count_raw, int) else 1
            await self.save_error(item_id, error_data["error"], retry_count)
            return retry_count
        return 0

    async def get_failed_items(self, max_retries: int = 3) -> list[dict[str, Any]]:
        """Get list of failed items that haven't exceeded max retries."""
        failed_items = []

        # Get all error keys
        error_keys = await self.store.range_get(f"{self.prefix}:errors:")

        for _key, error_data in error_keys:
            if (
                isinstance(error_data, dict)
                and error_data.get("retry_count", 0) < max_retries
            ):
                failed_items.append(error_data)

        return failed_items

    async def clear_errors(self, item_id: str | None = None) -> None:
        """Clear error information."""
        if item_id:
            key = f"{self.prefix}:errors:{item_id}"
            await self.store.delete(key)
        else:
            # Clear all errors for this prefix
            error_keys = await self.store.range_get(f"{self.prefix}:errors:")
            for key, _ in error_keys:
                await self.store.delete(key)


class StateTracker:
    """Track processing state and statistics."""

    def __init__(self, store: KeyValueStore, prefix: str = "state_tracker") -> None:
        """Initialize the state tracker with a store and prefix.

        Args:
            store: The key-value store instance to use.
            prefix: Prefix for all state tracking keys.
        """
        self.store = store
        self.prefix = prefix

    async def increment_counter(self, counter_name: str, amount: int = 1) -> int:
        """Increment a counter."""
        key = f"{self.prefix}:counter:{counter_name}"

        current_value = await self.store.get(key, 0)
        new_value = current_value + amount if isinstance(current_value, int) else amount

        await self.store.put(key, new_value, ttl=timedelta(days=30))
        return new_value

    async def get_counter(self, counter_name: str) -> int:
        """Get a counter value."""
        key = f"{self.prefix}:counter:{counter_name}"
        result = await self.store.get(key, 0)
        if isinstance(result, int):
            return result
        return 0

    async def record_processing_time(self, operation: str, duration: float) -> None:
        """Record processing time for an operation."""
        key = f"{self.prefix}:timing:{operation}"

        timing_data = await self.store.get(
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
            timing_data["last_updated"] = datetime.now(UTC).isoformat()

            await self.store.put(key, timing_data, ttl=timedelta(days=7))

    async def get_processing_stats(self, operation: str) -> dict[str, Any]:
        """Get processing statistics for an operation."""
        key = f"{self.prefix}:timing:{operation}"
        timing_data = await self.store.get(key, {})

        if timing_data:
            timing_data_dict = cast("dict[str, Any]", timing_data)
            if timing_data_dict.get("count", 0) > 0:
                return {
                    "count": timing_data_dict["count"],
                    "avg_time": timing_data_dict["total_time"]
                    / timing_data_dict["count"],
                    "min_time": timing_data_dict["min_time"],
                    "max_time": timing_data_dict["max_time"],
                    "last_updated": timing_data_dict["last_updated"],
                }

        return {}

    async def save_session_info(self, session_id: str, info: dict[str, Any]) -> None:
        """Save session information."""
        key = f"{self.prefix}:session:{session_id}"
        info["created_at"] = datetime.now(UTC).isoformat()
        await self.store.put(key, info, ttl=timedelta(days=1))

    async def get_session_info(self, session_id: str) -> dict[str, Any] | None:
        """Get session information."""
        key = f"{self.prefix}:session:{session_id}"
        result = await self.store.get(key)
        if isinstance(result, dict):
            return result
        return None

    async def get_state(self) -> dict[str, Any]:
        """Get the current state."""
        key = f"{self.prefix}:state"
        result = await self.store.get(key, {})
        if isinstance(result, dict):
            return result
        return {}

    async def update_state(self, state_updates: dict[str, Any]) -> None:
        """Update the current state with new values."""
        key = f"{self.prefix}:state"

        current_state = await self.store.get(key, {})
        if isinstance(current_state, dict):
            current_state.update(state_updates)
            current_state["last_updated"] = datetime.now(UTC).isoformat()
        else:
            current_state = state_updates
            current_state["last_updated"] = datetime.now(UTC).isoformat()

        await self.store.put(key, current_state, ttl=timedelta(days=7))


# Factory functions for creating manager instances
def create_state_management_manager(
    store: KeyValueStore, prefix: str
) -> StateManagementManager:
    """Create a state management manager with the given store and prefix.

    Args:
        store: The key-value store instance to use.
        prefix: Prefix for all state management keys.

    Returns:
        A configured StateManagementManager instance.
    """
    return StateManagementManager(store, prefix)


def create_state_tracker(store: KeyValueStore, prefix: str) -> StateTracker:
    """Create a state tracker with the given store and prefix.

    Args:
        store: The key-value store instance to use.
        prefix: Prefix for all state tracking keys.

    Returns:
        A configured StateTracker instance.
    """
    return StateTracker(store, prefix)
