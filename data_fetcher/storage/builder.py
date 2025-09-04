"""Storage configuration builder and factory.

This module provides the StorageBuilder class for creating and configuring
storage instances, including S3 and local file storage with various options.
"""

import os


class StorageBuilder:
    """Builder for creating storage configurations."""

    def __init__(self) -> None:
        """Initialize the storage builder with default configuration."""
        self._s3_bucket: str | None = None
        self._s3_prefix: str = ""
        self._s3_region: str = self._get_default_aws_region()
        self._s3_endpoint_url: str | None = None
        self._file_path: str | None = None
        self._use_bundler: bool = True
        self._use_unzip: bool = False

    def _get_default_aws_region(self) -> str:
        """Get default AWS region with proper precedence: AWS_REGION > hard-coded default."""
        return os.getenv("AWS_REGION", "eu-west-2")

    def s3_storage(
        self,
        bucket: str,
        prefix: str = "",
        region: str | None = None,
        endpoint_url: str | None = None,
    ) -> "StorageBuilder":
        """Configure S3 storage."""
        self._s3_bucket = bucket
        self._s3_prefix = prefix
        self._s3_region = region or self._get_default_aws_region()
        self._s3_endpoint_url = endpoint_url
        return self

    def file_storage(self, path: str) -> "StorageBuilder":
        """Configure file storage."""
        self._file_path = path
        return self

    def storage_decorators(
        self, *, use_unzip: bool = False, use_bundler: bool = True
    ) -> "StorageBuilder":
        """Configure storage decorators."""
        self._use_unzip = use_unzip
        self._use_bundler = use_bundler
        return self

    def build(self) -> object:
        """Build the storage configuration."""
        # Import here to avoid circular imports
        from . import (  # noqa: PLC0415
            BundleResourcesDecorator,
            FileStorage,
            S3Storage,
            UnzipResourceDecorator,
        )

        # Create base storage
        if self._s3_bucket:
            # Use S3 storage
            base_storage: object = S3Storage(
                bucket_name=self._s3_bucket,
                prefix=self._s3_prefix,
                region=self._s3_region,
                endpoint_url=self._s3_endpoint_url,
            )
        elif self._file_path:
            # Use explicit file storage
            base_storage = FileStorage(self._file_path)
        else:
            # Use file storage as fallback
            base_storage = FileStorage("default_capture")

        # Apply decorators in order
        storage: object = base_storage

        if self._use_unzip:
            storage = UnzipResourceDecorator(storage)

        if self._use_bundler:
            storage = BundleResourcesDecorator(storage)

        return storage


def create_storage_config() -> StorageBuilder:
    """Create a new storage configuration builder."""
    return StorageBuilder()


class GlobalStorageManager:
    """Manager for the global storage instance."""

    def __init__(self) -> None:
        """Initialize the global storage manager."""
        self._storage: object | None = None

    def set(self, storage_builder: StorageBuilder) -> None:
        """Set the global storage configuration."""
        self._storage = storage_builder.build()

    def get(self) -> object:
        """Get the global storage instance."""
        if self._storage is None:
            # Create default storage if none is set
            self._storage = create_storage_config().build()
        return self._storage


# Global storage manager instance
_global_storage_manager = GlobalStorageManager()


def set_global_storage(storage_builder: StorageBuilder) -> None:
    """Set the global storage configuration."""
    _global_storage_manager.set(storage_builder)


def get_global_storage() -> object:
    """Get the global storage instance."""
    return _global_storage_manager.get()
