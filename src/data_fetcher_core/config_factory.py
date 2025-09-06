"""Configuration factory functions for creating application components.

This module provides factory functions to create credential providers, key-value stores,
and storage instances based on environment variables and CLI arguments, without using
global state.

Environment Variables:
    OC_CREDENTIAL_PROVIDER_TYPE: Provider type to use ("aws" or "environment"). Default: "aws"
    OC_CREDENTIAL_PROVIDER_AWS_REGION: AWS region for Secrets Manager. Default: "eu-west-2"
    AWS_REGION: Standard AWS region environment variable (takes precedence over OC_CREDENTIAL_PROVIDER_AWS_REGION)
    OC_CREDENTIAL_PROVIDER_AWS_ENDPOINT_URL: AWS endpoint URL for LocalStack testing. Default: None
    OC_CREDENTIAL_PROVIDER_ENV_PREFIX: Environment variable prefix for environment provider. Default: "OC_CREDENTIAL_"

    OC_CONFIG_ID: Configuration ID to use as key prefix. Default: None
    OC_KV_STORE_TYPE: Store type to use ("memory" or "redis"). Default: "redis"
    OC_KV_STORE_SERIALIZER: Serializer to use ("json" or "pickle"). Default: "json"
    OC_KV_STORE_DEFAULT_TTL: Default TTL in seconds. Default: "3600"
    OC_KV_STORE_REDIS_HOST: Redis host (when using redis). Default: "localhost"
    OC_KV_STORE_REDIS_PORT: Redis port (when using redis). Default: "6379"
    OC_KV_STORE_REDIS_DB: Redis database number (when using redis). Default: "0"
    OC_KV_STORE_REDIS_PASSWORD: Redis password (when using redis). Default: None

    OC_STORAGE_TYPE: Storage type to use ("s3" or "file"). Default: "s3"
    OC_STORAGE_S3_BUCKET: S3 bucket name (when using s3). Default: None
    OC_STORAGE_S3_PREFIX: S3 key prefix (when using s3). Default: ""
    OC_STORAGE_S3_REGION: S3 region (when using s3). Default: "eu-west-2"
    OC_STORAGE_S3_ENDPOINT_URL: S3 endpoint URL for LocalStack testing. Default: None
    OC_STORAGE_USE_UNZIP: Whether to use unzip decorator. Default: "true"
    OC_STORAGE_USE_BUNDLER: Whether to use bundler decorator. Default: "true"
    OC_STORAGE_FILE_PATH: File storage path (when using file storage). Default: "tmp/file_storage"
"""


# UnknownStorageTypeError moved to data_fetcher_core.storage.factory


class StorageCreationError(Exception):
    """Raised when storage creation fails."""

    def __init__(self, storage_type: str) -> None:
        """Initialize the error with storage type information.

        Args:
            storage_type: The type of storage that failed to create.
        """
        super().__init__(f"Failed to create storage of type: {storage_type}")
        self.storage_type = storage_type


from dataclasses import dataclass
from typing import TypedDict, Unpack, cast

from data_fetcher_core.credentials import (
    CredentialProvider,
    create_credential_provider,
)
from data_fetcher_core.kv_store import (
    KeyValueStore,
    create_kv_store,
)
from data_fetcher_core.storage import Storage, create_storage_config_instance


class ConfigKwargs(TypedDict, total=False):
    """Type definition for configuration kwargs."""

    # AWS credential provider kwargs
    aws_region: str
    aws_endpoint_url: str
    # Environment credential provider kwargs
    env_prefix: str
    # Redis store kwargs
    redis_host: str
    redis_port: int
    redis_db: int
    redis_password: str
    # Storage kwargs
    s3_bucket: str
    s3_prefix: str
    s3_region: str
    s3_endpoint_url: str
    file_path: str
    use_unzip: bool
    use_bundler: bool
    # Common kwargs
    serializer: str
    default_ttl: int
    config_id: str


# Helper functions moved to respective factory modules


# create_credential_provider moved to data_fetcher_core.credentials.factory


# KV store factory functions moved to data_fetcher_core.kv_store.factory


# create_storage_config_instance moved to data_fetcher_core.storage.factory


@dataclass
class FetcherConfig:
    """Fetcher configuration container."""

    credential_provider: CredentialProvider
    kv_store: KeyValueStore
    storage: Storage


async def create_fetcher_config(
    credentials_provider_type: str | None = None,
    storage_type: str | None = None,
    kv_store_type: str | None = None,
    **kwargs: Unpack[ConfigKwargs],
) -> FetcherConfig:
    """Create a complete fetcher configuration.

    Args:
        credentials_provider_type: Credential provider type ("aws" or "env").
        storage_type: Storage type ("s3" or "file").
        kv_store_type: Key-value store type ("redis" or "memory").
        **kwargs: Additional configuration parameters passed to individual factory functions.

    Returns:
        Complete fetcher configuration with all components.
    """
    # Create credential provider
    credential_kwargs = {
        k: v for k, v in kwargs.items() if k.startswith(("aws_", "env_"))
    }
    credential_provider = create_credential_provider(
        provider_type=credentials_provider_type,
        **credential_kwargs,  # type: ignore[arg-type]
    )

    # Create key-value store
    kv_kwargs = {
        k: v
        for k, v in kwargs.items()
        if k.startswith(("redis_", "serializer", "default_ttl", "config_id"))
    }
    kv_store = create_kv_store(
        store_type=kv_store_type,
        **kv_kwargs,  # type: ignore[arg-type]
    )

    # Create storage instance
    storage_kwargs = {
        k: v for k, v in kwargs.items() if k.startswith(("s3_", "file_", "use_"))
    }
    storage_config = create_storage_config_instance(
        storage_type=storage_type,
        **storage_kwargs,  # type: ignore[arg-type]
    )

    # Build the actual storage instance
    storage = cast("Storage", storage_config.build())
    if not storage:
        raise StorageCreationError(storage_type or "unknown")

    return FetcherConfig(
        credential_provider=credential_provider,
        kv_store=kv_store,
        storage=storage,
    )


# Backward compatibility aliases
AppConfig = FetcherConfig
create_app_config = create_fetcher_config
