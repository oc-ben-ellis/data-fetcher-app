"""Storage factory functions for creating storage configurations.

This module provides factory functions to create storage instances based on
environment variables and CLI arguments.
"""

import os

from .builder import StorageBuilder, create_storage_config


class UnknownStorageTypeError(ValueError):
    """Raised when an unknown storage type is specified."""

    def __init__(self, storage_type: str) -> None:
        """Initialize the unknown storage type error.

        Args:
            storage_type: The unknown storage type that was specified.
        """
        super().__init__(f"Unknown storage type: {storage_type}")
        self.storage_type = storage_type


def _get_env_bool(key: str, *, default: bool = False) -> bool:
    """Get boolean value from environment variable."""
    value = os.getenv(key, "").lower()
    if value in ("true", "1", "yes", "on"):
        return True
    if value in ("false", "0", "no", "off"):
        return False
    return default


def _get_aws_region() -> str:
    """Get AWS region with proper precedence: AWS_REGION > OC_*_REGION > default."""
    return (
        os.getenv("AWS_REGION", "eu-west-2")
        or os.getenv("OC_CREDENTIAL_PROVIDER_AWS_REGION", "eu-west-2")
        or os.getenv("OC_S3_REGION", "eu-west-2")
        or "eu-west-2"
    )


def create_storage_config_instance(
    storage_type: str | None = None,
    s3_bucket: str | None = None,
    s3_prefix: str | None = None,
    s3_region: str | None = None,
    s3_endpoint_url: str | None = None,
    file_path: str | None = None,
    *,
    use_unzip: bool | None = None,
    use_tar_gz: bool | None = None,
) -> StorageBuilder:
    """Create a storage configuration instance.

    Args:
        storage_type: Storage type to use ("pipeline_bus", "s3", or "file").
                     If None, uses OC_STORAGE_TYPE env var or "pipeline_bus".
        s3_bucket: S3 bucket name.
                  If None, uses OC_S3_BUCKET env var or "data-fetcher-app-data".
        s3_prefix: S3 key prefix.
                  If None, uses OC_S3_PREFIX env var or "".
        s3_region: AWS region for S3.
                  If None, uses AWS_REGION or OC_S3_REGION env vars.
        s3_endpoint_url: Custom S3 endpoint URL (for LocalStack, etc.).
                        If None, uses OC_S3_ENDPOINT_URL env var.
        file_path: File storage path (when using file storage).
                  If None, uses OC_STORAGE_FILE_PATH env var or "tmp/file_storage".
        use_unzip: Enable unzip decorator.
                  If None, uses OC_STORAGE_USE_UNZIP env var or True.
        use_tar_gz: Enable tar/gz decorator.
                   If None, uses OC_STORAGE_USE_TAR_GZ env var or True.

    Returns:
        Configured storage configuration instance.
    """
    # Get storage type
    if storage_type is None:
        storage_type = os.getenv("OC_STORAGE_TYPE", "pipeline_bus").lower()
    else:
        storage_type = storage_type.lower()

    # Normalize known aliases
    if storage_type in ("pipeline", "pipeline-bus", "pipeline_bus", "bus"):
        storage_type = "pipeline_bus"

    # Create storage config
    storage_config = create_storage_config()

    if storage_type == "pipeline_bus":
        # Pipeline Bus storage configuration
        storage_config = storage_config.pipeline_bus_storage()
    elif storage_type == "s3":
        # S3 storage configuration
        if s3_bucket is None:
            s3_bucket = os.getenv("OC_S3_BUCKET", "data-fetcher-app-data")
        if s3_prefix is None:
            s3_prefix = os.getenv("OC_S3_PREFIX", "")
        if s3_region is None:
            s3_region = _get_aws_region()
        if s3_endpoint_url is None:
            s3_endpoint_url = os.getenv("OC_S3_ENDPOINT_URL")

        storage_config = storage_config.s3_storage(
            bucket=s3_bucket,
            prefix=s3_prefix,
            region=s3_region,
            endpoint_url=s3_endpoint_url,
        )
    elif storage_type == "file":
        # File storage configuration
        if file_path is None:
            file_path = os.getenv("OC_STORAGE_FILE_PATH", "tmp/file_storage")
        storage_config = storage_config.file_storage(file_path)
    else:
        raise UnknownStorageTypeError(storage_type)

    # Configure decorators
    if use_unzip is None:
        use_unzip = _get_env_bool("OC_STORAGE_USE_UNZIP", default=True)
    if use_tar_gz is None:
        use_tar_gz = _get_env_bool("OC_STORAGE_USE_TAR_GZ", default=True)

    return storage_config.storage_decorators(use_unzip=use_unzip, use_tar_gz=use_tar_gz)
