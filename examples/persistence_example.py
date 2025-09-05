"""Data persistence example for the OC Fetcher framework."""

import asyncio
from datetime import datetime, timedelta

from data_fetcher_core.fetcher import run_fetcher
from data_fetcher_core.kv_store import (
    configure_global_store,
    get_global_store,
    range_get,
)
from data_fetcher_core.utils.persistence_utils import (
    create_persistence_manager,
    create_retry_manager,
    create_state_tracker,
)


async def setup_persistence() -> None:
    """Configure the key-value store for persistence."""
    # Configure global store (in production, you'd use Redis)
    configure_global_store(
        store_type="memory",
        serializer="json",
        default_ttl=3600,
        key_prefix="persistence_example:",
    )


async def demonstrate_persistence_managers() -> None:
    """Demonstrate the use of persistence managers."""
    # Create persistence managers for different components
    api_persistence = await create_persistence_manager("api_provider")
    await create_persistence_manager("sftp_provider")
    retry_manager = await create_retry_manager(max_retries=3, backoff_factor=2.0)
    state_tracker = await create_state_tracker("example_tracker")

    # Save some processed items
    processed_urls = {
        "https://api.example.com/data/1",
        "https://api.example.com/data/2",
        "https://api.example.com/data/3",
    }
    await api_persistence.save_processed_items(processed_urls)

    # Load processed items
    await api_persistence.load_processed_items()

    # Save state information
    state = {
        "current_date": "2024-01-15",
        "current_cursor": "abc123",
        "processed_count": 150,
        "last_successful_fetch": datetime.now().isoformat(),
    }
    await api_persistence.save_state(state)

    # Load state information
    await api_persistence.load_state()

    # Demonstrate error handling
    await api_persistence.save_error("failed_url_1", "Connection timeout", 2)
    await api_persistence.save_error("failed_url_2", "Rate limit exceeded", 1)

    await api_persistence.get_failed_items(max_retries=3)

    # Demonstrate retry logic
    await retry_manager.should_retry("failed_url_1")

    await retry_manager.record_retry("failed_url_1", "Connection timeout")

    await retry_manager.get_retry_delay("failed_url_1")

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


async def demonstrate_fetcher_with_persistence() -> None:
    """Demonstrate running a fetcher with persistence features."""
    try:
        # Run the FR API fetcher (which now has persistence)
        run_fetcher("fr-api", concurrency=2)

    except Exception:
        pass

    try:
        # Run the US FL SFTP fetcher (which now has persistence)
        run_fetcher("us-fl", concurrency=1)

    except Exception:
        pass


async def demonstrate_kvstore_operations() -> None:
    """Demonstrate direct key-value store operations."""
    store = await get_global_store()

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
    await range_get("item:2", "item:4")

    # Get all items with prefix
    await range_get("item:")


async def demonstrate_error_recovery() -> None:
    """Demonstrate error recovery and retry mechanisms."""
    persistence = await create_persistence_manager("error_recovery")
    retry_manager = await create_retry_manager(max_retries=3, backoff_factor=1.5)

    # Simulate some failed items
    failed_items = [
        ("url_1", "Connection timeout"),
        ("url_2", "Rate limit exceeded"),
        ("url_3", "Server error 500"),
        ("url_4", "Authentication failed"),
    ]

    for item_id, error in failed_items:
        await persistence.save_error(item_id, error)
        await retry_manager.record_retry(item_id, error)

    # Get failed items that can be retried
    retryable_items = await persistence.get_failed_items(max_retries=3)

    # Simulate retry attempts
    for item in retryable_items:
        item_id = item["item_id"]
        should_retry = await retry_manager.should_retry(item_id)
        await retry_manager.get_retry_delay(item_id)

        if should_retry:
            # Simulate successful retry
            await retry_manager.clear_retry_data(item_id)
            await persistence.clear_errors(item_id)


async def demonstrate_monitoring() -> None:
    """Demonstrate monitoring and statistics."""
    tracker = await create_state_tracker("monitoring")

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
    """Main function demonstrating all persistence features."""
    # Setup persistence
    await setup_persistence()

    # Demonstrate various persistence features
    await demonstrate_persistence_managers()
    await demonstrate_kvstore_operations()
    await demonstrate_error_recovery()
    await demonstrate_monitoring()

    # Demonstrate fetchers with persistence
    await demonstrate_fetcher_with_persistence()


if __name__ == "__main__":
    asyncio.run(main())
