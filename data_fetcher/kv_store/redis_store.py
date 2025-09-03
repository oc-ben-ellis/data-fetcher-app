"""Redis key-value store implementation.

This module provides the RedisKeyValueStore class for persistent storage
using Redis, including connection management and Redis-specific operations.
"""

from datetime import timedelta
from typing import Any

from .base import KeyValueStore


class RedisKeyValueStore(KeyValueStore):
    """Redis key-value store implementation.

    This store uses Redis as the backend and provides persistent storage
    with high performance. It supports TTL functionality and range queries
    using Redis SCAN and ZRANGE operations.
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the Redis store."""
        super().__init__(**kwargs)

        # Redis connection parameters
        self._host = kwargs.get("host", "localhost")
        self._port = kwargs.get("port", 6379)
        self._db = kwargs.get("db", 0)
        self._password = kwargs.get("password", None)
        self._ssl = kwargs.get("ssl", False)
        self._timeout = kwargs.get("timeout", 10.0)
        self._max_connections = kwargs.get("max_connections", 10)

        # Redis client
        self._redis: Any = None
        self._pool: Any = None

    async def _ensure_connection(self) -> None:
        """Ensure Redis connection is established."""
        if self._redis is None:
            try:
                import redis.asyncio as redis

                # Create connection pool
                connection_kwargs = {
                    "host": self._host,
                    "port": self._port,
                    "db": self._db,
                    "password": self._password,
                    "socket_timeout": self._timeout,
                    "socket_connect_timeout": self._timeout,
                    "max_connections": self._max_connections,
                    "decode_responses": True,
                }

                # Only add SSL if it's True
                if self._ssl:
                    connection_kwargs["ssl"] = self._ssl

                self._pool = redis.ConnectionPool(**connection_kwargs)

                # Create Redis client
                self._redis = redis.Redis(connection_pool=self._pool)

                # Test connection
                await self._redis.ping()

            except ImportError as err:
                raise ImportError(
                    "Redis client not available. Install with: pip install redis"
                ) from err
            except Exception as e:
                raise ConnectionError(f"Failed to connect to Redis: {e}") from e

    async def put(
        self,
        key: str,
        value: Any,
        ttl: int | timedelta | None = None,
        prefix: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Store a value with the given key."""
        await self._ensure_connection()

        # Serialize the value
        serialized_value = self._serialize(value)

        # Apply key prefix
        prefixed_key = self._get_prefixed_key(key, prefix)

        # Store the value
        if ttl is not None:
            ttl_seconds = self._normalize_ttl(ttl)
            await self._redis.setex(prefixed_key, ttl_seconds, serialized_value)
        else:
            await self._redis.set(prefixed_key, serialized_value)

    async def get(
        self, key: str, default: Any = None, prefix: str | None = None, **kwargs: Any
    ) -> Any | None:
        """Retrieve a value by key."""
        await self._ensure_connection()

        # Apply key prefix
        prefixed_key = self._get_prefixed_key(key, prefix)

        # Get the value
        serialized_value = await self._redis.get(prefixed_key)

        if serialized_value is None:
            return default

        # Deserialize and return
        return self._deserialize(serialized_value)

    async def delete(self, key: str, prefix: str | None = None, **kwargs: Any) -> bool:
        """Delete a key-value pair."""
        await self._ensure_connection()

        # Apply key prefix
        prefixed_key = self._get_prefixed_key(key, prefix)

        # Delete the key
        result = await self._redis.delete(prefixed_key)
        return bool(result > 0)

    async def exists(self, key: str, prefix: str | None = None, **kwargs: Any) -> bool:
        """Check if a key exists."""
        await self._ensure_connection()

        # Apply key prefix
        prefixed_key = self._get_prefixed_key(key, prefix)

        # Check if key exists
        result = await self._redis.exists(prefixed_key)
        return bool(result > 0)

    async def range_get(
        self,
        start_key: str,
        end_key: str | None = None,
        limit: int | None = None,
        prefix: str | None = None,
        **kwargs: Any,
    ) -> list[tuple[str, Any]]:
        """Get a range of key-value pairs."""
        await self._ensure_connection()

        # Apply key prefixes
        self._get_prefixed_key(start_key, prefix)
        prefixed_end_key = self._get_prefixed_key(end_key, prefix) if end_key else None

        # Use SCAN to get keys in range
        result = []
        cursor = 0

        while True:
            # Scan for keys with current prefix
            effective_prefix = prefix if prefix is not None else self._key_prefix
            scan_pattern = f"{effective_prefix}*" if effective_prefix else "*"
            cursor, keys = await self._redis.scan(
                cursor=cursor, match=scan_pattern, count=100
            )

            for key in keys:
                # Remove prefix for comparison
                original_key = (
                    key[len(effective_prefix) :]
                    if effective_prefix and key.startswith(effective_prefix)
                    else key
                )

                # Check if key is in range
                if original_key < start_key:
                    continue
                if prefixed_end_key and key >= prefixed_end_key:
                    continue

                # Get the value
                value = await self._redis.get(key)
                if value is not None:
                    deserialized_value = self._deserialize(value)
                    result.append((original_key, deserialized_value))

                # Apply limit
                if limit is not None and len(result) >= limit:
                    # Sort result before returning when limit is applied
                    result.sort(key=lambda x: x[0])
                    return result

            # Stop if we've scanned all keys
            if cursor == 0:
                break

        # Sort result before returning to ensure consistent ordering
        result.sort(key=lambda x: x[0])
        return result

    async def close(self) -> None:
        """Close the store and release resources."""
        if self._redis is not None:
            # redis-py asyncio deprecates close() in favor of aclose() in 5.0.1
            await self._redis.aclose()
            self._redis = None

        if self._pool is not None:
            await self._pool.disconnect()

    async def get_stats(self) -> dict[str, Any]:
        """Get statistics about the store."""
        await self._ensure_connection()

        try:
            info = await self._redis.info()
            return {
                "redis_version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": info.get("used_memory_human"),
                "total_commands_processed": info.get("total_commands_processed"),
                "key_prefix": self._key_prefix,
                "serializer": self._serializer,
                "default_ttl": self._default_ttl,
            }
        except Exception:
            return {
                "key_prefix": self._key_prefix,
                "serializer": self._serializer,
                "default_ttl": self._default_ttl,
                "error": "Could not retrieve Redis stats",
            }

    async def flush_db(self) -> None:
        """Flush all data from the current database."""
        await self._ensure_connection()
        await self._redis.flushdb()

    async def get_keys_by_pattern(self, pattern: str) -> list[str]:
        """Get keys matching a pattern."""
        await self._ensure_connection()

        prefixed_pattern = f"{self._key_prefix}{pattern}"
        keys = []
        cursor = 0

        while True:
            cursor, batch_keys = await self._redis.scan(
                cursor=cursor, match=prefixed_pattern, count=100
            )

            # Remove prefix from keys
            for key in batch_keys:
                original_key = key[len(self._key_prefix) :]
                keys.append(original_key)

            if cursor == 0:
                break

        return keys
