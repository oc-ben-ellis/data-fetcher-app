# State Management System

The OC Fetcher state management system provides flexible state persistence capabilities with multiple backend implementations for storing and retrieving application state.

## Overview

The state management system offers:

- **Generic Interface**: Common interface for different state storage backends
- **Multiple Implementations**: In-memory (testing) and Redis (production)
- **Application Configuration**: Automatic setup with optional override
- **TTL Support**: Automatic expiration of state data
- **Range Queries**: Efficient retrieval of state key ranges
- **Serialization Options**: JSON and pickle support
- **Async/Await Support**: Fully asynchronous interface

## Quick Start

### Basic Usage

```python
from data_fetcher_core.kv_store import create_store

# Create a store instance
store = create_store(store_type="memory")

# Store and retrieve state data
await store.put("user:123", {"name": "John Doe", "email": "john@example.com"})
user_data = await store.get("user:123")
print(user_data)  # {"name": "John Doe", "email": "john@example.com"}

# Check if state key exists
if await store.exists("user:123"):
    print("User state data found")

# Delete state data
await store.delete("user:123")
```

### Range Operations

```python
from data_fetcher_core.kv_store import create_store

# Create a store instance
store = create_store(store_type="memory")

# Store multiple items
for i in range(10):
    await store.put(f"item:{i}", f"value_{i}")

# Get range of items
results = await store.range_get("item:3", "item:7")
# Returns: [("item:3", "value_3"), ("item:4", "value_4"), ...]

# Get all items with prefix
all_items = await store.range_get("item:")
# Returns all items starting with "item:"

# Get limited results
limited_results = await store.range_get("item:", limit=5)
# Returns first 5 items
```

## Store Implementations

### In-Memory Store

Perfect for testing and development:

```python
from data_fetcher_core.kv_store import create_store

# Create an in-memory store
store = create_store(
    store_type="memory",
    serializer="json",
    default_ttl=3600,  # 1 hour default TTL
)

# Use the store
await store.put("key", "value")
value = await store.get("key")
await store.close()
```

**Features:**
- Fast access (no network overhead)
- No external dependencies
- Data lost on application restart
- Automatic cleanup of expired keys
- Thread-safe operations

### Redis Store

Designed for production use:

```python
from data_fetcher_core.kv_store import create_store

# Create a Redis store
store = create_store(
    store_type="redis",
    host="localhost",
    port=6379,
    password="password",
    db=0,
    key_prefix="myapp:",
    serializer="json",
    default_ttl=3600,
)

# Use the store
await store.put("key", "value")
value = await store.get("key")
await store.close()
```

**Features:**
- Persistent storage
- High performance
- Built-in TTL support
- Cluster support
- Key prefixing for namespacing

## Advanced Usage

### TTL (Time-to-Live)

Control how long data persists:

```python
from datetime import timedelta

# TTL in seconds
await put("temp_data", "value", ttl=300)  # 5 minutes

# TTL using timedelta
await put("session_data", "value", ttl=timedelta(hours=2))

# No TTL (uses default or never expires)
await put("permanent_data", "value")
```

### Serialization Options

Choose between JSON and pickle serialization:

```python
from data_fetcher_core.kv_store import create_store

# JSON serialization (default, human-readable)
store = create_store(
    store_type="memory",
    serializer="json",
)

# Pickle serialization (supports more Python types)
store = create_store(
    store_type="memory",
    serializer="pickle",
)

# Store complex objects
await store.put("complex_data", {
    "datetime": datetime.now(),
    "set_data": {1, 2, 3},
    "function": lambda x: x * 2,
})
```

### Context Manager Usage

Use stores as context managers for automatic cleanup:

```python
from data_fetcher_core.kv_store import get_store_context

async with get_store_context("memory", serializer="json") as store:
    await store.put("key", "value")
    result = await store.get("key")
    # Store automatically closed when exiting context
```

### Store Management

Create and manage store instances:

```python
from data_fetcher_core.kv_store import create_store

# Create a store instance
store = create_store(store_type="memory")

# Use store methods directly
await store.put("key", "value")
value = await store.get("key")

# Get store statistics
if hasattr(store, 'get_stats'):
    stats = store.get_stats()
    print(f"Total keys: {stats['total_keys']}")
```

## Configuration

### Application Configuration

The application store is automatically configured when the module is imported:

```python
# Create store instances as needed
from data_fetcher_core.kv_store import create_store

# Development (in-memory)
store = create_store(
    store_type="memory",
    serializer="json",
    default_ttl=3600,
)

# Production (Redis)
store = create_store(
    store_type="redis",
    host="redis.example.com",
    port=6379,
    password="your_password",
    db=0,
    key_prefix="data_fetcher:",
    serializer="json",
    default_ttl=3600,
)
```

### Configuration Parameters

#### In-Memory Store
- `serializer`: "json" or "pickle" (default: "json")
- `default_ttl`: Default time-to-live in seconds (default: None)

#### Redis Store
- `host`: Redis server hostname (default: "localhost")
- `port`: Redis server port (default: 6379)
- `password`: Redis password (default: None)
- `db`: Redis database number (default: 0)
- `ssl`: Use SSL connection (default: False)
- `timeout`: Connection timeout in seconds (default: 10.0)
- `max_connections`: Maximum connections in pool (default: 10)
- `key_prefix`: Prefix for all keys (default: "data_fetcher:")
- `serializer`: "json" or "pickle" (default: "json")
- `default_ttl`: Default time-to-live in seconds (default: None)

## Integration Examples

### Frontier Provider Caching

```python

class CachingFrontierProvider:
    def __init__(self, base_url: str):
        self.base_url = base_url

    async def get_next_urls(self, ctx):

        # Check if we've already processed this recently
        cache_key = f"processed:{self.base_url}"
        if await store.exists(cache_key):
            return []  # Already processed

        # Mark as processed with 1-hour TTL
        await store.put(cache_key, True, ttl=3600)

        # Return URLs to process
        return [{"url": f"{self.base_url}/page1"}]

    async def handle_url_processed(self, request, bundle_refs, ctx):

        # Store processing results
        result_key = f"result:{request['url']}"
        await store.put(result_key, {
            "url": request["url"],
            "bundle_count": len(bundle_refs),
            "timestamp": datetime.now().isoformat(),
        }, ttl=timedelta(hours=24))
```

### API Response Caching

```python
# DEPRECATED: Global helper functions removed - use store instance methods directly

async def cached_api_call(url: str, cache_ttl: int = 300):
    """Make an API call with caching."""
    cache_key = f"api_response:{url}"

    # Check cache first
    if await exists(cache_key):
        cached_response = await get(cache_key)
        print(f"Cache hit for {url}")
        return cached_response

    # Make API call
    print(f"Cache miss for {url}, making API call")
    response = await make_api_call(url)

    # Cache the response
    await put(cache_key, response, ttl=cache_ttl)

    return response
```

### Session Management

```python
# DEPRECATED: Global helper functions removed - use store instance methods directly

async def create_session(user_id: str, session_data: dict):
    """Create a new user session."""
    session_id = generate_session_id()
    session_key = f"session:{session_id}"

    await put(session_key, {
        "user_id": user_id,
        "data": session_data,
        "created_at": datetime.now().isoformat(),
    }, ttl=timedelta(hours=24))

    return session_id

async def get_session(session_id: str):
    """Retrieve session data."""
    session_key = f"session:{session_id}"
    return await get(session_key)

async def delete_session(session_id: str):
    """Delete a session."""
    session_key = f"session:{session_id}"
    await delete(session_key)
```

### Batch Processing State

```python
# DEPRECATED: Global helper functions removed - use store instance methods directly

async def track_batch_progress(batch_id: str, total_items: int):
    """Track progress of a batch processing job."""
    progress_key = f"batch_progress:{batch_id}"

    await put(progress_key, {
        "total_items": total_items,
        "processed_items": 0,
        "failed_items": 0,
        "started_at": datetime.now().isoformat(),
    })

async def update_batch_progress(batch_id: str, processed: int = 1, failed: int = 0):
    """Update batch processing progress."""
    progress_key = f"batch_progress:{batch_id}"
    progress = await get(progress_key)

    if progress:
        progress["processed_items"] += processed
        progress["failed_items"] += failed
        await put(progress_key, progress)

async def get_all_batch_progress():
    """Get progress for all active batches."""
    return await range_get("batch_progress:")
```

## Best Practices

### Key Naming

Use consistent key naming patterns:

```python
# Good key patterns
await put("user:123:profile", user_data)
await put("session:abc123:data", session_data)
await put("cache:api:users:list", api_response)
await put("stats:daily:2024-01-01", daily_stats)

# Avoid generic keys
await put("data", value)  # Too generic
await put("temp", value)  # Unclear purpose
```

### TTL Strategy

Choose appropriate TTL values:

```python
# Short-lived cache (API responses)
await put("api:users", users_data, ttl=300)  # 5 minutes

# Session data
await put("session:user123", session_data, ttl=3600)  # 1 hour

# Long-lived data
await put("config:app_settings", config_data, ttl=86400)  # 24 hours

# Permanent data (no TTL)
await put("user:123:profile", profile_data)  # No expiration
```

### Error Handling

Handle store errors gracefully:

```python

async def safe_get(key: str, default=None):
    try:
        return await store.get(key, default=default)
    except Exception as e:
        print(f"Error accessing key-value store: {e}")
        return default

# Usage
user_data = await safe_get("user:123", default={"name": "Unknown"})
```

### Performance Considerations

- **Batch Operations**: Use range queries instead of multiple individual gets
- **Key Prefixing**: Use prefixes to organize data and enable efficient range queries
- **TTL Management**: Set appropriate TTL to prevent memory bloat
- **Connection Pooling**: Redis store automatically manages connection pools

## Monitoring and Debugging

### Get Store Statistics

```python

# In-memory store stats
if hasattr(store, 'get_stats'):
    stats = store.get_stats()
    print(f"Total keys: {stats['total_keys']}")
    print(f"Expiring keys: {stats['expiring_keys']}")

# Redis store stats
if hasattr(store, 'get_stats'):
    stats = await store.get_stats()
    print(f"Redis version: {stats['redis_version']}")
    print(f"Memory usage: {stats['used_memory_human']}")
```

### Debugging Tips

1. **Check Key Existence**: Use `exists()` before operations
2. **Monitor TTL**: Check if keys are expiring unexpectedly
3. **Use Prefixes**: Organize keys with prefixes for easier debugging
4. **Log Operations**: Add logging for critical store operations

## Migration and Compatibility

### Switching Between Stores

The interface is consistent across implementations:

```python
from data_fetcher_core.kv_store import create_store

# Development (in-memory)
store = create_store(store_type="memory")

# Production (Redis)
store = create_store(store_type="redis", host="prod-redis.example.com")

# Code remains the same
await store.put("key", "value")
value = await store.get("key")
```

### Data Migration

When migrating from in-memory to Redis:

1. Export data from in-memory store (if needed)
2. Configure Redis store with same key prefix
3. Update configuration to use Redis
4. Verify data accessibility

## Troubleshooting

### Common Issues

**Connection Errors (Redis)**
```python
# Check Redis connection
try:
    store = RedisKeyValueStore(host="localhost", port=6379)
    await store._ensure_connection()
    print("Redis connection successful")
except Exception as e:
    print(f"Redis connection failed: {e}")
```

**Serialization Errors**
```python
from data_fetcher_core.kv_store import create_store

# Use pickle for complex objects
store = create_store(store_type="memory", serializer="pickle")

# Or handle serialization manually
import json
data = {"complex": object}
try:
    await store.put("key", data)
except Exception:
    # Fallback to JSON-safe data
    await store.put("key", json.loads(json.dumps(data, default=str)))
```

**TTL Issues**
```python
from data_fetcher_core.kv_store import create_store

store = create_store(store_type="memory")

# Check if TTL is working
await store.put("test", "value", ttl=1)
print(f"Exists: {await store.exists('test')}")
await asyncio.sleep(2)
print(f"Exists after TTL: {await store.exists('test')}")
```

## API Reference

### Store Methods

- `put(key, value, ttl=None, **kwargs)` - Store a value
- `get(key, default=None, **kwargs)` - Retrieve a value
- `delete(key, **kwargs)` - Delete a key-value pair
- `exists(key, **kwargs)` - Check if key exists
- `range_get(start_key, end_key=None, limit=None, **kwargs)` - Get range of values
- `close()` - Close the store and release resources

### Factory Functions

- `create_store(store_type, **kwargs)` - Create a store instance
- `get_store_context(store_type, **kwargs)` - Context manager for store instances
