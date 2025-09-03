# Key-Value Store Usage Guide

The OC Fetcher framework includes a generic key-value store system that provides flexible caching and state management capabilities. This guide explains how to use the key-value store effectively.

## Overview

The key-value store system provides:

- **Generic Interface**: Common interface for different storage backends
- **Multiple Implementations**: In-memory (for testing) and Redis (for production)
- **Application Configuration**: Easy app-wide store setup and access
- **TTL Support**: Automatic expiration of cached data
- **Range Queries**: Efficient retrieval of key ranges
- **Serialization Options**: JSON and pickle serialization support

## Quick Start

### Basic Usage

```python
from oc_fetcher.kv_store import put, get, delete, exists

# The global key-value store is automatically configured when the module is imported
# Store and retrieve data
await put("user:123", {"name": "John Doe", "email": "john@example.com"})
user_data = await get("user:123")
print(user_data)  # {"name": "John Doe", "email": "john@example.com"}

# Check if key exists
if await exists("user:123"):
    print("User data found")

# Delete data
await delete("user:123")
```

### Production Setup with Redis

```python
from oc_fetcher.kv_store import configure_global_store

# Override the default configuration for production
configure_global_store(
    store_type="redis",
    host="redis.example.com",
    port=6379,
    password="your_password",
    db=0,
    key_prefix="oc_fetcher:",
    serializer="json",
    default_ttl=3600,
)
```

## Store Implementations

### In-Memory Store

The in-memory store is perfect for testing and development:

```python
from oc_fetcher.kv_store import InMemoryKeyValueStore

# Create an in-memory store
store = InMemoryKeyValueStore(
    serializer="json",
    default_ttl=3600,
)

# Use the store
await store.put("key", "value")
value = await store.get("key")
```

**Features:**
- Fast access (no network overhead)
- No external dependencies
- Data lost on application restart
- Automatic cleanup of expired keys
- Thread-safe operations

### Redis Store

The Redis store is designed for production use:

```python
from oc_fetcher.kv_store import RedisKeyValueStore

# Create a Redis store
store = RedisKeyValueStore(
    host="localhost",
    port=6379,
    password="password",
    db=0,
    key_prefix="myapp:",
    serializer="json",
    default_ttl=3600,
)
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

### Range Queries

Retrieve multiple keys efficiently:

```python
# Store multiple keys
for i in range(10):
    await put(f"user:{i}", {"id": i, "name": f"User {i}"})

# Get range of keys
users = await range_get("user:3", "user:7")
# Returns: [("user:3", {...}), ("user:4", {...}), ...]

# Get range with limit
limited_users = await range_get("user:0", limit=5)
# Returns first 5 users

# Get all keys starting with prefix
all_users = await range_get("user:")
```

### Serialization Options

Choose between JSON and pickle serialization:

```python
# JSON serialization (default, human-readable)
configure_global_store(
    store_type="memory",
    serializer="json",
)

# Pickle serialization (supports more Python types)
configure_global_store(
    store_type="memory",
    serializer="pickle",
)

# Store complex objects
await put("complex_data", {
    "datetime": datetime.now(),
    "set_data": {1, 2, 3},
    "function": lambda x: x * 2,
})
```

### Context Manager Usage

Use stores as context managers for automatic cleanup:

```python
from oc_fetcher.kv_store import get_store_context

async with get_store_context("memory", serializer="json") as store:
    await store.put("key", "value")
    result = await store.get("key")
    # Store automatically closed when exiting context
```

## Integration with Fetcher Configurations

### In Bundle Locators

Use the key-value store for caching and state management:

```python
from oc_fetcher.kv_store import get_global_store

class CachingBundleLocator:
    async def get_next_urls(self, ctx):
        store = await get_global_store()

        # Check if we've already processed this recently
        cache_key = f"processed:{self.base_url}"
        if await store.exists(cache_key):
            return []  # Already processed

        # Mark as processed
        await store.put(cache_key, True, ttl=3600)

        # Return URLs to process
        return [{"url": f"{self.base_url}/page1"}]

    async def handle_url_processed(self, request, bundle_refs, ctx):
        store = await get_global_store()

        # Store processing results
        result_key = f"result:{request['url']}"
        await store.put(result_key, {
            "url": request["url"],
            "bundle_count": len(bundle_refs),
            "timestamp": datetime.now().isoformat(),
        }, ttl=timedelta(hours=24))
```

### In Configuration Setup

The global key-value store is automatically configured when the module is imported.
You can override the configuration in your fetcher configuration if needed:

```python
def _setup_my_fetcher() -> FetchContext:
    # Override global store configuration if needed
    configure_global_store(
        store_type="redis",
        host="localhost",
        port=6379,
        key_prefix="my_fetcher:",
        serializer="json",
        default_ttl=3600,
    )

    # Rest of configuration...
    return create_fetcher_config().build()
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
from oc_fetcher.kv_store import get_global_store

async def safe_get(key: str, default=None):
    try:
        store = await get_global_store()
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
store = await get_global_store()

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
# Development (in-memory - default)
# No configuration needed, automatically uses in-memory store

# Production (Redis)
configure_global_store("redis", host="prod-redis.example.com")

# Code remains the same
await put("key", "value")
value = await get("key")
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
# Use pickle for complex objects
configure_global_store(serializer="pickle")

# Or handle serialization manually
import json
data = {"complex": object}
try:
    await put("key", data)
except Exception:
    # Fallback to JSON-safe data
    await put("key", json.loads(json.dumps(data, default=str)))
```

**TTL Issues**
```python
# Check if TTL is working
await put("test", "value", ttl=1)
print(f"Exists: {await exists('test')}")
await asyncio.sleep(2)
print(f"Exists after TTL: {await exists('test')}")
```

For more information, see the test files and example configurations in the project.

## Integration with Bundle Locators

```python
class CachingBundleLocator:
    async def get_next_urls(self, ctx):
        from oc_fetcher.kv_store import get_global_store

        store = await get_global_store()
        cache_key = f"processed:{self.base_url}"

        if await store.exists(cache_key):
            return []  # Already processed

        await store.put(cache_key, True, ttl=3600)
        return [{"url": f"{self.base_url}/page1"}]
```
