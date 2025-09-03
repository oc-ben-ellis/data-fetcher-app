"""Application key-value store configuration and management.

This module manages the application-wide default key-value store instance,
providing persistence and caching capabilities across the framework.

Environment Variables:
    OC_CONFIG_ID: Configuration ID to use as key prefix. Default: None
    OC_KV_STORE_TYPE: Store type to use ("memory" or "redis"). Default: "memory"
    OC_KV_STORE_SERIALIZER: Serializer to use ("json" or "pickle"). Default: "json"
    OC_KV_STORE_DEFAULT_TTL: Default TTL in seconds. Default: "3600"
    OC_KV_STORE_REDIS_HOST: Redis host (when using redis). Default: "localhost"
    OC_KV_STORE_REDIS_PORT: Redis port (when using redis). Default: "6379"
    OC_KV_STORE_REDIS_DB: Redis database number (when using redis). Default: "0"
    OC_KV_STORE_REDIS_PASSWORD: Redis password (when using redis). Default: ""
    OC_KV_STORE_REDIS_KEY_PREFIX: Redis key prefix (when using redis). Default: "oc_fetcher:"
"""

import os

from .kv_store import configure_global_store


def _get_env_int(key: str, default: int) -> int:
    """Get integer value from environment variable."""
    try:
        return int(os.getenv(key, str(default)))
    except (ValueError, TypeError):
        return default


def configure_global_kv_store() -> None:
    """Configure the application key-value store with environment variables and sensible defaults."""
    # Get store type
    store_type = os.getenv("OC_KV_STORE_TYPE", "memory").lower()

    # Get config_id for prefixing
    config_id = os.getenv("OC_CONFIG_ID")

    # Base configuration (exclude store_type to avoid duplicate named argument)
    config = {
        "serializer": os.getenv("OC_KV_STORE_SERIALIZER", "json"),
        "default_ttl": _get_env_int("OC_KV_STORE_DEFAULT_TTL", 3600),
    }

    # Add key prefix if config_id is available
    if config_id:
        config["key_prefix"] = config_id

    # Add Redis-specific configuration if using Redis
    if store_type == "redis":
        config.update(
            {
                "host": os.getenv("OC_KV_STORE_REDIS_HOST", "localhost"),
                "port": _get_env_int("OC_KV_STORE_REDIS_PORT", 6379),
                "db": _get_env_int("OC_KV_STORE_REDIS_DB", 0),
            }
        )

        # Override key_prefix with Redis-specific prefix if provided
        redis_key_prefix = os.getenv("OC_KV_STORE_REDIS_KEY_PREFIX")
        if redis_key_prefix:
            config["key_prefix"] = redis_key_prefix
        elif not config.get("key_prefix"):
            # Use default Redis prefix if no config_id or Redis-specific prefix
            config["key_prefix"] = "oc_fetcher:"

        # Only add password if it's set
        password = os.getenv("OC_KV_STORE_REDIS_PASSWORD")
        if password:
            config["password"] = password

    configure_global_store(store_type, **config)


# Configure global key-value store when this module is imported
configure_global_kv_store()


def configure_application_kv_store() -> None:
    """Alias: Configure application key-value store.

    This is an alias for ``configure_global_kv_store`` to emphasize that this
    configuration is application-wide rather than per-fetcher.
    """
    configure_global_kv_store()
