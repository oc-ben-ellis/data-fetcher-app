# Persistence Features with Key-Value Store

This document describes the persistence features implemented in the OC Fetcher framework using the key-value store system.

## Overview

The persistence features provide:

- **State Persistence**: Save and restore processing state across restarts
- **Error Tracking**: Track failed requests with retry logic
- **Processing Statistics**: Monitor performance and track metrics
- **Resume Capability**: Continue processing from where it left off
- **Fault Tolerance**: Handle failures gracefully with automatic recovery

## Key Components

### 1. Bundle Locator Persistence

All bundle locators now include built-in persistence capabilities:

#### API Bundle Locators
- **Processed URLs**: Track which URLs have been processed
- **Pagination State**: Save current cursor and date progression
- **Error Handling**: Track failed requests for retry
- **Rate Limiting State**: Persist rate limiting information

#### SFTP Bundle Locators
- **Processed Files**: Track which files have been downloaded
- **Directory State**: Save file queue and initialization state
- **Error Tracking**: Monitor failed file transfers
- **Processing Results**: Store metadata about successful transfers

### 2. Persistence Managers

Utility classes for managing persistence operations:

#### PersistenceManager
```python
from data_fetcher.utils.persistence_utils import create_persistence_manager

# Create a persistence manager
persistence = await create_persistence_manager("my_provider")

# Save processed items
await persistence.save_processed_items({"url1", "url2", "url3"})

# Load processed items
processed = await persistence.load_processed_items()

# Save state
await persistence.save_state({
    "current_date": "2024-01-15",
    "processed_count": 150
})

# Handle errors
await persistence.save_error("failed_url", "Connection timeout", 2)
failed_items = await persistence.get_failed_items(max_retries=3)
```

#### RetryManager
```python
from data_fetcher.utils.persistence_utils import create_retry_manager

# Create a retry manager
retry_manager = await create_retry_manager(max_retries=3, backoff_factor=2.0)

# Check if item should be retried
if await retry_manager.should_retry("failed_item"):
    # Record retry attempt
    retry_count = await retry_manager.record_retry("failed_item", "Error message")

    # Get delay before next retry
    delay = await retry_manager.get_retry_delay("failed_item")
    await asyncio.sleep(delay)

    # Clear retry data on success
    await retry_manager.clear_retry_data("failed_item")
```

#### StateTracker
```python
from data_fetcher.utils.persistence_utils import create_state_tracker

# Create a state tracker
tracker = await create_state_tracker("my_tracker")

# Track counters
await tracker.increment_counter("api_calls", 5)
await tracker.increment_counter("successful_fetches", 3)

# Record processing times
await tracker.record_processing_time("api_request", 1.5)

# Get statistics
stats = await tracker.get_processing_stats("api_request")
count = await tracker.get_counter("api_calls")
```

## Configuration

### Environment Variables

Configure persistence using environment variables:

```bash
# Store type (memory or redis)
export OC_KV_STORE_TYPE=redis

# Redis configuration
export OC_KV_STORE_REDIS_HOST=localhost
export OC_KV_STORE_REDIS_PORT=6379
export OC_KV_STORE_REDIS_PASSWORD=your_password
export OC_KV_STORE_REDIS_DB=0

# Key prefix for namespacing
export OC_KV_STORE_REDIS_KEY_PREFIX=data_fetcher:

# Serialization format
export OC_KV_STORE_SERIALIZER=json

# Default TTL
export OC_KV_STORE_DEFAULT_TTL=3600
```

### Programmatic Configuration

```python
from data_fetcher.kv_store import configure_global_store

# Configure for production
configure_global_store(
    store_type="redis",
    host="redis.example.com",
    port=6379,
    password="your_password",
    key_prefix="data_fetcher:",
    serializer="json",
    default_ttl=3600
)
```

## Usage Examples

### 1. Basic Persistence in Bundle Locators

The bundle locators automatically handle persistence:

```python
from data_fetcher import run_fetcher

# Run with persistence (automatic)
result = await run_fetcher("fr-api", concurrency=2)

# The bundle locator will:
# - Save processed URLs
# - Track pagination state
# - Handle errors with retry logic
# - Resume from last known state on restart
```

### 2. Custom Error Handling

```python
from data_fetcher.utils.persistence_utils import create_persistence_manager, create_retry_manager

async def handle_failed_request(request, error):
    persistence = await create_persistence_manager("my_provider")
    retry_manager = await create_retry_manager(max_retries=3)

    # Save error
    await persistence.save_error(request.url, str(error))

    # Check if we should retry
    if await retry_manager.should_retry(request.url):
        retry_count = await retry_manager.record_retry(request.url, str(error))
        delay = await retry_manager.get_retry_delay(request.url)

        print(f"Retrying {request.url} in {delay:.2f} seconds (attempt {retry_count})")
        return True

    return False
```

### 3. Monitoring and Statistics

```python
from data_fetcher.utils.persistence_utils import create_state_tracker

async def monitor_processing():
    tracker = await create_state_tracker("monitoring")

    # Track various metrics
    await tracker.increment_counter("total_requests")
    await tracker.record_processing_time("api_request", duration)

    # Get statistics
    stats = await tracker.get_processing_stats("api_request")
    total_requests = await tracker.get_counter("total_requests")

    print(f"Total requests: {total_requests}")
    print(f"Average API request time: {stats['avg_time']:.2f}s")
```

### 4. Recovery and Cleanup

```python
from data_fetcher.utils.persistence_utils import create_persistence_manager

async def cleanup_and_recover():
    persistence = await create_persistence_manager("my_provider")

    # Get failed items
    failed_items = await persistence.get_failed_items(max_retries=3)

    # Retry failed items
    for item in failed_items:
        if await retry_item(item):
            await persistence.clear_errors(item['item_id'])

    # Clear old data
    await persistence.clear_errors()  # Clear all errors
```

## Data Structure

### Key Naming Convention

The persistence system uses a hierarchical key structure:

```
{prefix}:{type}:{identifier}
```

Examples:
- `fr_siren_provider:processed_urls:https://api.insee.fr/...`
- `us_fl_daily_provider:state:/doc/cor`
- `api_provider:errors:https://api.example.com/data/1`
- `retry:failed_url_1`
- `state_tracker:counter:api_calls`

### Data Types

#### Processed Items
```json
{
  "url1",
  "url2",
  "url3"
}
```

#### State Information
```json
{
  "current_date": "2024-01-15",
  "current_cursor": "abc123",
  "processed_count": 150,
  "last_updated": "2024-01-15T10:30:00Z"
}
```

#### Error Information
```json
{
  "item_id": "failed_url_1",
  "error": "Connection timeout",
  "retry_count": 2,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Processing Statistics
```json
{
  "count": 100,
  "total_time": 150.5,
  "min_time": 0.1,
  "max_time": 5.2,
  "last_updated": "2024-01-15T10:30:00Z"
}
```

## Best Practices

### 1. Key Prefixing
Always use meaningful prefixes to avoid key collisions:

```python
# Good
persistence_prefix="fr_siren_provider"

# Avoid
persistence_prefix="provider"
```

### 2. TTL Management
Set appropriate TTL values for different data types:

```python
# Short-lived data (errors, retry info)
ttl=timedelta(hours=24)

# Medium-lived data (state, processed items)
ttl=timedelta(days=7)

# Long-lived data (statistics, configuration)
ttl=timedelta(days=30)
```

### 3. Error Handling
Always handle persistence errors gracefully:

```python
try:
    await persistence.save_state(state)
except Exception as e:
    print(f"Failed to save state: {e}")
    # Continue processing without persistence
```

### 4. Cleanup
Regularly clean up old data to prevent storage bloat:

```python
# Clear old errors
await persistence.clear_errors()

# Clear old retry data
await retry_manager.clear_retry_data("old_item")
```

## Migration from Non-Persistent Bundle Locators

Existing configurations will automatically benefit from persistence. No code changes are required for basic persistence features.

To enable advanced features:

1. **Add persistence prefixes** to bundle locator configurations
2. **Implement error handlers** using the persistence managers
3. **Add monitoring** with state trackers
4. **Configure the key-value store** for your environment

## Troubleshooting

### Common Issues

1. **Memory Usage**: Use Redis for production to avoid memory bloat
2. **Key Collisions**: Use unique prefixes for different bundle locators
3. **TTL Expiration**: Monitor TTL settings to prevent data loss
4. **Connection Issues**: Handle Redis connection failures gracefully

### Debugging

Enable debug logging to see persistence operations:

```python
import logging
logging.getLogger("data_fetcher.kv_store").setLevel(logging.DEBUG)
```

### Monitoring

Use the state tracker to monitor persistence operations:

```python
tracker = await create_state_tracker("persistence_monitor")
await tracker.increment_counter("persistence_operations")
await tracker.record_processing_time("state_save", duration)
```

## Performance Considerations

1. **Batch Operations**: Group persistence operations when possible
2. **Async Operations**: All persistence operations are async
3. **Connection Pooling**: Redis connections are pooled for efficiency
4. **Serialization**: Use JSON for human-readable data, pickle for complex objects
5. **TTL Optimization**: Set appropriate TTL values to balance storage and performance
