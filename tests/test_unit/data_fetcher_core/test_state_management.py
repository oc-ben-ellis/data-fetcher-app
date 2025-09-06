"""Tests for state management utilities and data handling.

This module contains unit tests for state management functionality,
including serialization, caching, and data transformation.
"""

import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime

import pytest

from data_fetcher_core.kv_store import (
    StateManagementManager,
    StateTracker,
    create_state_tracker,
    create_store,
)

# TODO: create_retry_manager function is not implemented yet


@pytest.fixture
async def setup_kvstore() -> AsyncGenerator[StateManagementManager]:
    """Setup key-value store for testing."""
    store = create_store(
        store_type="memory",
        serializer="json",
        default_ttl=3600,
        key_prefix="test_persistence:",
    )
    manager = StateManagementManager(store, "test_persistence")
    yield manager
    # Cleanup
    await store.close()


@pytest.mark.asyncio
async def test_state_management_manager(setup_kvstore: StateManagementManager) -> None:
    """Test StateManagementManager functionality."""
    state_management = setup_kvstore

    # Test saving and loading processed items
    processed_items = {"url1", "url2", "url3"}
    await state_management.save_processed_items(processed_items)

    loaded_items = await state_management.load_processed_items()
    assert loaded_items == processed_items

    # Test saving and loading state
    state = {
        "current_date": "2024-01-15",
        "processed_count": 150,
        "last_successful_fetch": datetime.now().isoformat(),
    }
    await state_management.save_state(state)

    loaded_state = await state_management.load_state()
    assert loaded_state["current_date"] == state["current_date"]
    assert loaded_state["processed_count"] == state["processed_count"]

    # Test error handling
    await state_management.save_error("failed_url", "Connection timeout", 2)
    failed_items = await state_management.get_failed_items(max_retries=3)
    # Filter out non-error items (state data)
    error_items = [item for item in failed_items if "error" in item]
    assert len(error_items) == 1
    assert error_items[0]["item_id"] == "failed_url"
    assert error_items[0]["error"] == "Connection timeout"
    assert error_items[0]["retry_count"] == 2


# TODO: RetryManager functionality is not implemented yet


@pytest.mark.asyncio
async def test_state_tracker(setup_kvstore: StateManagementManager) -> None:
    """Test StateTracker functionality."""
    store = setup_kvstore.store
    tracker = StateTracker(store, "test_provider_2")

    # Test initial state
    initial_state = await tracker.get_state()
    assert initial_state == {}

    # Test updating state
    await tracker.update_state({"key1": "value1", "count": 10})
    state = await tracker.get_state()
    assert state["key1"] == "value1"
    assert state["count"] == 10

    # Test incremental updates
    await tracker.update_state({"count": 15, "new_key": "new_value"})
    state = await tracker.get_state()
    assert state["key1"] == "value1"  # Preserved
    assert state["count"] == 15  # Updated
    assert state["new_key"] == "new_value"  # Added

    # Test state persistence across instances
    tracker2 = create_state_tracker(store, "test_provider_2")
    state2 = await tracker2.get_state()
    assert state2 == state


@pytest.mark.asyncio
async def test_kvstore_operations(setup_kvstore: StateManagementManager) -> None:
    """Test basic key-value store operations used by state management."""
    store = setup_kvstore.store

    # Test basic operations
    await store.put("test_key", {"data": "value"})
    result = await store.get("test_key")
    assert result == {"data": "value"}

    # Test exists
    assert await store.exists("test_key") is True
    assert await store.exists("nonexistent_key") is False

    # Test delete
    assert await store.delete("test_key") is True
    assert await store.exists("test_key") is False

    # Test TTL
    await store.put("ttl_key", "ttl_value", ttl=1)
    assert await store.exists("ttl_key") is True
    await asyncio.sleep(1.1)
    assert await store.exists("ttl_key") is False


@pytest.mark.asyncio
async def test_range_operations(setup_kvstore: StateManagementManager) -> None:
    """Test range operations used by state management managers."""
    store = setup_kvstore.store

    # Store multiple items
    await store.put("item:1", {"id": "1", "status": "processed"})
    await store.put("item:2", {"id": "2", "status": "processed"})
    await store.put("item:3", {"id": "3", "status": "failed"})
    await store.put("error:1", {"id": "1", "error": "timeout"})

    # Test range get
    items = await store.range_get("item:")
    # The range_get returns all items with the prefix, including any that might be stored by other tests
    assert len(items) >= 3
    # Verify we have the expected items
    item_keys = [item[0] for item in items]
    assert "item:1" in item_keys
    assert "item:2" in item_keys
    assert "item:3" in item_keys

    # Test range get with limit
    items = await store.range_get("item:", limit=2)
    assert len(items) == 2

    # Test range get with end key
    items = await store.range_get("item:1", "item:3")
    assert len(items) == 2  # item:1 and item:2 (exclusive of item:3)
    assert items[0][0] == "item:1"
    assert items[1][0] == "item:2"


# TODO: RetryManager functionality is not implemented yet
# These tests are commented out until RetryManager is implemented


if __name__ == "__main__":
    pytest.main([__file__])
