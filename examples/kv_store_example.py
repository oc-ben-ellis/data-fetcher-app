"""Data state management example for the OC Fetcher framework."""

import asyncio
from datetime import datetime, timedelta

from data_fetcher_core.fetcher import run_fetcher
from data_fetcher_core.kv_store import (
    KeyValueStore,
    StateManagementManager,
    StateTracker,
    create_store,
)


async def setup_state_management() -> KeyValueStore:
    """Create the key-value store for state management."""
    # Create store (in production, you'd use Redis)
    return create_store(
        store_type="memory",
        serializer="json",
        default_ttl=3600,
        key_prefix="state_management_example:",
    )


async def demonstrate_state_management_managers(store: KeyValueStore) -> None:
    """Demonstrate the use of state management managers."""
    # Create state management managers for different components
    api_state_management = StateManagementManager(store, "api_provider")
    StateManagementManager(store, "sftp_provider")
    state_tracker = StateTracker(store, "example_tracker")

    # Save some processed items
    processed_urls = {
        "https://api.example.com/data/1",
        "https://api.example.com/data/2",
        "https://api.example.com/data/3",
    }
    await api_state_management.save_processed_items(processed_urls)

    # Load processed items
    await api_state_management.load_processed_items()

    # Save state information
    state = {
        "current_date": "2024-01-15",
        "current_cursor": "abc123",
        "processed_count": 150,
        "last_successful_fetch": datetime.now().isoformat(),
    }
    await api_state_management.save_state(state)

    # Load state information
    await api_state_management.load_state()

    # Demonstrate error handling
    await api_state_management.save_error("failed_url_1", "Connection timeout", 2)
    await api_state_management.save_error("failed_url_2", "Rate limit exceeded", 1)

    await api_state_management.get_failed_items(max_retries=3)

    # Demonstrate state tracking
    await state_tracker.increment_counter("api_calls", 5)
    await state_tracker.increment_counter("successful_fetches", 3)
    await state_tracker.increment_counter("failed_fetches", 2)

    await state_tracker.get_counter("api_calls")
    await state_tracker.get_counter("successful_fetches")
    await state_tracker.get_counter("failed_fetches")

    # Record processing times
    await state_tracker.record_processing_time("api_request", 1.5)
    await state_tracker.record_processing_time("api_request", 2.1)
    await state_tracker.record_processing_time("api_request", 0.8)

    stats = await state_tracker.get_processing_stats("api_request")
    if stats:
        pass


async def demonstrate_fetcher_with_state_management(_store: KeyValueStore) -> None:
    """Demonstrate running a fetcher with state management features."""
    try:
        # Run the FR API fetcher (which now has state management)
        run_fetcher("fr", concurrency=2)

    except Exception:
        pass

    try:
        # Run the US FL SFTP fetcher (which now has persistence)
        run_fetcher("us-fl", concurrency=1)

    except Exception:
        pass


async def demonstrate_kvstore_operations(store: KeyValueStore) -> None:
    """Demonstrate direct key-value store operations."""
    # Store some data
    await store.put(
        "user:123",
        {
            "name": "John Doe",
            "email": "john@example.com",
            "last_login": datetime.now().isoformat(),
        },
        ttl=timedelta(hours=24),
    )

    await store.put(
        "session:abc",
        {"user_id": "123", "started_at": datetime.now().isoformat(), "active": True},
        ttl=timedelta(hours=1),
    )

    # Retrieve data
    await store.get("user:123")
    await store.get("session:abc")

    # Check if keys exist
    await store.exists("user:123")
    await store.exists("session:abc")
    await store.exists("nonexistent:key")

    # Range operations
    await store.put("item:1", "value_1")
    await store.put("item:2", "value_2")
    await store.put("item:3", "value_3")
    await store.put("item:4", "value_4")
    await store.put("item:5", "value_5")

    # Get range of items
    await store.range_get("item:2", "item:4")

    # Get all items with prefix
    await store.range_get("item:")


async def demonstrate_error_recovery(store: KeyValueStore) -> None:
    """Demonstrate error recovery mechanisms."""
    persistence = StateManagementManager(store, "error_recovery")

    # Simulate some failed items
    failed_items = [
        ("url_1", "Connection timeout"),
        ("url_2", "Rate limit exceeded"),
        ("url_3", "Server error 500"),
        ("url_4", "Authentication failed"),
    ]

    for item_id, error in failed_items:
        await persistence.save_error(item_id, error)

    # Get failed items that can be retried
    retryable_items = await persistence.get_failed_items(max_retries=3)

    # Simulate retry attempts
    for item in retryable_items:
        item_id = item["item_id"]
        # Simulate successful retry
        await persistence.clear_errors(item_id)


async def demonstrate_monitoring(store: KeyValueStore) -> None:
    """Demonstrate monitoring and statistics."""
    tracker = StateTracker(store, "monitoring")

    # Simulate some processing activities
    operations = [
        ("api_request", 1.2),
        ("api_request", 0.8),
        ("api_request", 2.1),
        ("file_download", 5.3),
        ("file_download", 3.7),
        ("data_processing", 0.5),
        ("data_processing", 0.3),
        ("data_processing", 0.7),
    ]

    for operation, duration in operations:
        await tracker.record_processing_time(operation, duration)
        await tracker.increment_counter(f"{operation}_count")

    # Get statistics for different operations
    for operation in ["api_request", "file_download", "data_processing"]:
        stats = await tracker.get_processing_stats(operation)
        await tracker.get_counter(f"{operation}_count")

        if stats:
            pass


async def main() -> None:
    """Main function demonstrating all state management features."""
    # Setup state management
    store = await setup_state_management()

    # Demonstrate various state management features
    await demonstrate_state_management_managers(store)
    await demonstrate_kvstore_operations(store)
    await demonstrate_error_recovery(store)
    await demonstrate_monitoring(store)

    # Demonstrate fetchers with state management
    await demonstrate_fetcher_with_state_management(store)

    # Cleanup
    await store.close()


if __name__ == "__main__":
    asyncio.run(main())
