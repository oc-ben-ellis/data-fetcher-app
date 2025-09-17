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
        self._use_pipeline_bus: bool = False
        self._use_unzip: bool = True  # Enable by default
        self._use_tar_gz: bool = True  # Enable by default
        self._pipeline_bus: object | None = None  # For dependency injection

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

    def pipeline_bus_storage(
        self, pipeline_bus: object | None = None
    ) -> "StorageBuilder":
        """Configure Pipeline Bus storage."""
        self._use_pipeline_bus = True
        self._pipeline_bus = pipeline_bus
        return self

    def file_storage(self, path: str) -> "StorageBuilder":
        """Configure file storage."""
        self._file_path = path
        return self

    def storage_decorators(
        self, *, use_unzip: bool = True, use_tar_gz: bool = True
    ) -> "StorageBuilder":
        """Configure storage decorators."""
        self._use_unzip = use_unzip
        self._use_tar_gz = use_tar_gz
        return self

    def build(self) -> object:
        """Build the storage configuration."""
        # Import here to avoid circular imports
        from . import (  # noqa: PLC0415
            DataPipelineBusStorage,
            FileStorage,
            S3Storage,
            TarGzResourceDecorator,
            UnzipResourceDecorator,
        )

        # Create base storage
        if self._use_pipeline_bus:
            # Use Pipeline Bus storage
            if self._pipeline_bus is not None:
                # Use injected pipeline bus
                base_storage: object = DataPipelineBusStorage(
                    pipeline_bus=self._pipeline_bus
                )
            else:
                base_storage = DataPipelineBusStorage()
        elif self._s3_bucket:
            # Use S3 storage without SQS
            base_storage = S3Storage(
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
            base_storage = FileStorage("tmp/file_storage")

        # Apply decorators in order
        storage: object = base_storage

        if self._use_tar_gz:
            storage = TarGzResourceDecorator(storage)

        if self._use_unzip:
            storage = UnzipResourceDecorator(storage)

        return storage


def create_storage_config() -> StorageBuilder:
    """Create a new storage configuration builder."""
    return StorageBuilder()


# Global storage functions removed - use config_factory.create_app_config() instead
