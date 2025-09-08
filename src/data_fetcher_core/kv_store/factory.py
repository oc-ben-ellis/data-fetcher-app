"""Key-value store factory functions.

This module provides factory functions for creating key-value store instances
including in-memory storage and Redis integration.
"""

import os

from .base import KeyValueStore
from .memory import InMemoryKeyValueStore
from .redis import RedisKeyValueStore


class UnknownStoreTypeError(ValueError):
    """Raised when an unknown key-value store type is specified."""

    def __init__(self, store_type: str) -> None:
        """Initialize the unknown store type error.

        Args:
            store_type: The unknown store type that was specified.
        """
        super().__init__(f"Unknown store type: {store_type}")
        self.store_type = store_type


def _get_env_int(key: str, default: int) -> int:
    """Get integer value from environment variable."""
    try:
        return int(os.getenv(key, str(default)))
    except (ValueError, TypeError):
        return default


def _get_base_kv_config(
    serializer: str | None = None,
    default_ttl: int | None = None,
    config_id: str | None = None,
) -> dict[str, str | int]:
    """Get base key-value store configuration.

    Args:
        serializer: Serializer to use ("json" or "pickle").
        default_ttl: Default TTL in seconds.
        config_id: Configuration ID to use as key prefix.

    Returns:
        Base configuration dictionary.
    """
    config: dict[str, str | int] = {}

    config["serializer"] = (
        serializer or os.getenv("OC_KV_STORE_SERIALIZER", "json") or "json"
    )
    config["default_ttl"] = default_ttl or _get_env_int("OC_KV_STORE_DEFAULT_TTL", 3600)

    if config_id or os.getenv("OC_CONFIG_ID"):
        key_prefix = config_id or os.getenv("OC_CONFIG_ID")
        if key_prefix:
            config["key_prefix"] = key_prefix

    return config


def _get_redis_config(
    redis_host: str | None = None,
    redis_port: int | None = None,
    redis_db: int | None = None,
    redis_password: str | None = None,
    redis_key_prefix: str | None = None,
    base_config: dict[str, str | int] | None = None,
) -> dict[str, str | int]:
    """Get Redis-specific configuration.

    Args:
        redis_host: Redis host.
        redis_port: Redis port.
        redis_db: Redis database number.
        redis_password: Redis password.
        redis_key_prefix: Redis key prefix.
        base_config: Base configuration to extend.

    Returns:
        Redis configuration dictionary.
    """
    config: dict[str, str | int] = base_config.copy() if base_config else {}

    config["host"] = (
        redis_host or os.getenv("OC_KV_STORE_REDIS_HOST", "localhost") or "localhost"
    )
    config["port"] = redis_port or _get_env_int("OC_KV_STORE_REDIS_PORT", 6379)
    config["db"] = redis_db or _get_env_int("OC_KV_STORE_REDIS_DB", 0)

    # Handle key prefix with Redis-specific logic
    redis_key_prefix_value = redis_key_prefix or os.getenv(
        "OC_KV_STORE_REDIS_KEY_PREFIX"
    )
    if redis_key_prefix_value:
        config["key_prefix"] = redis_key_prefix_value
    elif not config.get("key_prefix"):
        config["key_prefix"] = "data_fetcher:"

    # Only add password if it's set
    redis_password_value = redis_password or os.getenv("OC_KV_STORE_REDIS_PASSWORD")
    if redis_password_value:
        config["password"] = redis_password_value

    return config


def create_store(store_type: str = "redis", **kwargs: object) -> KeyValueStore:
    """Create a key-value store instance.

    Args:
        store_type: Type of store to use ("memory" or "redis")
        **kwargs: Additional configuration parameters for the store

    Returns:
        A configured key-value store instance

    Raises:
        ValueError: If store_type is not supported
    """
    if store_type == "memory":
        return InMemoryKeyValueStore(**kwargs)
    if store_type == "redis":
        return RedisKeyValueStore(**kwargs)
    raise ValueError(f"Unknown store: {store_type}")  # noqa: TRY003


def create_kv_store(
    store_type: str | None = None,
    config_id: str | None = None,
    serializer: str | None = None,
    default_ttl: int | None = None,
    redis_host: str | None = None,
    redis_port: int | None = None,
    redis_db: int | None = None,
    redis_password: str | None = None,
    redis_key_prefix: str | None = None,
) -> KeyValueStore:
    """Create a key-value store instance with comprehensive configuration.

    Args:
        store_type: Store type to use ("memory" or "redis").
                   If None, uses OC_KV_STORE_TYPE env var or "redis".
        config_id: Configuration ID to use as key prefix.
                  If None, uses OC_CONFIG_ID env var.
        serializer: Serializer to use ("json" or "pickle").
                   If None, uses OC_KV_STORE_SERIALIZER env var or "json".
        default_ttl: Default TTL in seconds.
                    If None, uses OC_KV_STORE_DEFAULT_TTL env var or 3600.
        redis_host: Redis host (when using redis).
                   If None, uses OC_KV_STORE_REDIS_HOST env var or "localhost".
        redis_port: Redis port (when using redis).
                   If None, uses OC_KV_STORE_REDIS_PORT env var or 6379.
        redis_db: Redis database number (when using redis).
                 If None, uses OC_KV_STORE_REDIS_DB env var or 0.
        redis_password: Redis password (when using redis).
                       If None, uses OC_KV_STORE_REDIS_PASSWORD env var.
        redis_key_prefix: Redis key prefix (when using redis).
                         If None, uses OC_KV_STORE_REDIS_KEY_PREFIX env var.

    Returns:
        Configured key-value store instance.
    """
    store_type_str = (
        store_type or os.getenv("OC_KV_STORE_TYPE", "redis") or "redis"
    ).lower()

    base_config = _get_base_kv_config(serializer, default_ttl, config_id)

    if store_type_str == "memory":
        return InMemoryKeyValueStore(**base_config)

    if store_type_str == "redis":
        redis_config = _get_redis_config(
            redis_host,
            redis_port,
            redis_db,
            redis_password,
            redis_key_prefix,
            base_config,
        )
        return RedisKeyValueStore(**redis_config)

    raise UnknownStoreTypeError(store_type_str)
