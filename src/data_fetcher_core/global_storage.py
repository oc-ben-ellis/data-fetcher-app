"""Application storage configuration and management.

This module manages the application-wide default storage instance, providing
data storage capabilities including S3 integration and local file storage.

Environment Variables:
    OC_STORAGE_TYPE: Storage type to use ("s3" or "file"). Default: "s3"
    OC_S3_BUCKET: S3 bucket name. Default: "oc-fetcher-data"
    OC_S3_PREFIX: S3 key prefix. Default: ""
    OC_S3_REGION: AWS region for S3. Default: "eu-west-2"
    OC_S3_ENDPOINT_URL: Custom S3 endpoint URL (for LocalStack, etc.). Default: None
    AWS_REGION: Standard AWS region environment variable (takes precedence over OC_S3_REGION)
    OC_STORAGE_USE_UNZIP: Enable unzip decorator ("true"/"false"). Default: "true"

    OC_STORAGE_USE_BUNDLER: Enable bundler decorator ("true"/"false"). Default: "true"
    OC_STORAGE_FILE_PATH: File storage path (when using file storage). Default: "default_capture"
"""

import os

from .storage.builder import create_storage_config, set_global_storage


def _get_env_bool(key: str, *, default: bool = False) -> bool:
    """Get boolean value from environment variable."""
    value = os.getenv(key, "").lower()
    if value in ("true", "1", "yes", "on"):
        return True
    if value in ("false", "0", "no", "off"):
        return False
    return default


def _get_aws_region() -> str:
    """Get AWS region with proper precedence: AWS_REGION > OC_S3_REGION > default."""
    return (
        os.getenv("OC_S3_REGION") or os.getenv("AWS_REGION", "eu-west-2") or "eu-west-2"
    )


def configure_application_storage() -> None:
    """Configure the application storage with environment variables and sensible defaults."""
    # Get storage type
    storage_type = os.getenv("OC_STORAGE_TYPE", "s3").lower()

    # Create storage config
    storage_config = create_storage_config()

    if storage_type == "s3":
        # S3 storage configuration
        bucket = os.getenv("OC_S3_BUCKET", "oc-fetcher-data")
        prefix = os.getenv("OC_S3_PREFIX", "")
        region = _get_aws_region()

        # Get endpoint URL for LocalStack support
        endpoint_url = os.getenv("OC_S3_ENDPOINT_URL")

        storage_config = storage_config.pipeline_storage(
            bucket=bucket, prefix=prefix, region=region, endpoint_url=endpoint_url
        )
    elif storage_type == "file":
        # File storage configuration
        file_path = os.getenv("OC_STORAGE_FILE_PATH", "default_capture")
        storage_config = storage_config.file_storage(file_path)
    else:
        raise ValueError(f"Unknown storage: {storage_type}")  # noqa: TRY003

    # Configure decorators
    use_unzip = _get_env_bool("OC_STORAGE_USE_UNZIP", default=True)
    use_bundler = _get_env_bool("OC_STORAGE_USE_BUNDLER", default=True)

    storage_config = storage_config.storage_decorators(
        use_unzip=use_unzip, use_bundler=use_bundler
    )

    set_global_storage(storage_config)


def configure_global_storage() -> None:
    """Alias: Configure global storage.

    This is an alias for ``configure_application_storage`` to maintain backward compatibility.
    """
    configure_application_storage()


# Configure application storage when this module is imported
configure_application_storage()
