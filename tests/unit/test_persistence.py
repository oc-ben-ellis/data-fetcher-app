"""Tests for persistence utilities and data handling.

This module contains unit tests for persistence functionality,
including serialization, caching, and data transformation.
"""

import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime

import pytest

from data_fetcher.kv_store import configure_global_store, get_global_store
from data_fetcher.utils.persistence_utils import (
    create_persistence_manager,
    create_retry_manager,
    create_state_tracker,
)


@pytest.fixture
async def setup_kvstore() -> AsyncGenerator[None, None]:
    """Setup key-value store for testing."""
    configure_global_store(
        store_type="memory",
        serializer="json",
        default_ttl=3600,
        key_prefix="test_persistence:",
    )
    yield
    # Cleanup
    store = await get_global_store()
    await store.close()


@pytest.mark.asyncio
async def test_persistence_manager(setup_kvstore: None) -> None:
    """Test PersistenceManager functionality."""
    persistence = await create_persistence_manager("test_provider_1")

    # Test saving and loading processed items
    processed_items = {"url1", "url2", "url3"}
    await persistence.save_processed_items(processed_items)

    loaded_items = await persistence.load_processed_items()
    assert loaded_items == processed_items

    # Test saving and loading state
    state = {
        "current_date": "2024-01-15",
        "processed_count": 150,
        "last_successful_fetch": datetime.now().isoformat(),
    }
    await persistence.save_state(state)

    loaded_state = await persistence.load_state()
    assert loaded_state["current_date"] == state["current_date"]
    assert loaded_state["processed_count"] == state["processed_count"]

    # Test error handling
    await persistence.save_error("failed_url", "Connection timeout", 2)
    failed_items = await persistence.get_failed_items(max_retries=3)
    # Filter out non-error items (state data)
    error_items = [item for item in failed_items if "error" in item]
    assert len(error_items) == 1
    assert error_items[0]["item_id"] == "failed_url"
    assert error_items[0]["error"] == "Connection timeout"
    assert error_items[0]["retry_count"] == 2


@pytest.mark.asyncio
async def test_retry_manager(setup_kvstore: None) -> None:
    """Test RetryManager functionality."""
    retry_manager = await create_retry_manager(max_retries=3, backoff_factor=2.0)

    # Test initial retry state
    assert await retry_manager.should_retry("test_item") is True

    # Test recording retries
    retry_count = await retry_manager.record_retry("test_item", "Test error")
    assert retry_count == 1

    retry_count = await retry_manager.record_retry("test_item", "Test error")
    assert retry_count == 2

    retry_count = await retry_manager.record_retry("test_item", "Test error")
    assert retry_count == 3

    # Test max retries reached
    assert await retry_manager.should_retry("test_item") is False

    # Test retry delay calculation
    delay = await retry_manager.get_retry_delay("test_item")
    assert delay == 8.0  # 2^3 = 8, capped at 60

    # Test clearing retry data
    await retry_manager.clear_retry_data("test_item")
    assert await retry_manager.should_retry("test_item") is True


@pytest.mark.asyncio
async def test_state_tracker(setup_kvstore: None) -> None:
    """Test StateTracker functionality."""
    tracker = await create_state_tracker("test_provider_2")

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
    tracker2 = await create_state_tracker("test_provider_2")
    state2 = await tracker2.get_state()
    assert state2 == state


@pytest.mark.asyncio
async def test_kvstore_operations(setup_kvstore: None) -> None:
    """Test basic key-value store operations used by persistence."""
    store = await get_global_store()

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
async def test_range_operations(setup_kvstore: None) -> None:
    """Test range operations used by persistence managers."""
    store = await get_global_store()

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


@pytest.mark.asyncio
async def test_error_recovery(setup_kvstore: None) -> None:
    """Test error recovery and retry mechanisms.

    Note: max_retries=2 means we can retry up to 2 times total.
    - 0 retries: should retry (True)
    - 1 retry: should retry (True) - haven't reached limit yet
    - 2 retries: should NOT retry (False) - reached the limit
    """
    persistence = await create_persistence_manager("test_provider_3")
    retry_manager = await create_retry_manager(max_retries=2)

    # Simulate failed items
    failed_items = ["url1", "url2", "url3"]
    for item in failed_items:
        await persistence.save_error(item, "Network error", 1)

    # Test getting failed items
    failed = await persistence.get_failed_items(max_retries=2)
    error_items = [item for item in failed if "error" in item]
    assert len(error_items) >= 3  # May include items from other tests

    # Test retry logic
    for item in failed_items:
        assert await retry_manager.should_retry(item) is True
        retry_count = await retry_manager.record_retry(item, "Retry error")
        assert retry_count == 1  # First retry should be 1

    # Test that we can still retry after 1 retry (max_retries=2 means we can retry up to 2 times)
    for item in failed_items:
        assert await retry_manager.should_retry(item) is True

    # Record second retry to reach max_retries
    for item in failed_items:
        retry_count = await retry_manager.record_retry(item, "Retry error 2")
        assert retry_count == 2  # Second retry should be 2

    # Test max retries reached
    for item in failed_items:
        assert await retry_manager.should_retry(item) is False

    # Test clearing retry data
    await retry_manager.clear_retry_data("url1")
    assert await retry_manager.should_retry("url1") is True


@pytest.mark.asyncio
async def test_persistence_integration(setup_kvstore: None) -> None:
    """Test integration between different persistence components."""
    persistence = await create_persistence_manager("test_provider_4")
    retry_manager = await create_retry_manager(max_retries=3)
    tracker = await create_state_tracker("test_provider_4")

    # Simulate a complete workflow
    processed_items = {"url1", "url2", "url3"}
    await persistence.save_processed_items(processed_items)

    # Update state
    await tracker.update_state({"processed_count": 3, "last_update": "2024-01-15"})

    # Simulate some failures
    await persistence.save_error("url4", "Connection failed", 1)
    await persistence.save_error("url5", "Timeout", 2)

    # Test retry logic
    assert await retry_manager.should_retry("url4") is True
    assert await retry_manager.should_retry("url5") is True

    # Record retries
    await retry_manager.record_retry("url4", "Retry 1")
    await retry_manager.record_retry("url5", "Retry 2")

    # Verify state consistency
    loaded_items = await persistence.load_processed_items()
    assert loaded_items == processed_items

    state = await tracker.get_state()
    assert state["processed_count"] == 3

    failed_items = await persistence.get_failed_items(max_retries=3)
    error_items = [item for item in failed_items if "error" in item]
    assert len(error_items) == 2


if __name__ == "__main__":
    pytest.main([__file__])
