"""Storage configuration builder and factory.

This module provides the StorageBuilder class for creating and configuring
storage instances, including S3 and local file storage with various options.
"""

import os

from data_fetcher_core.notifications import SqsPublisher


class SqsQueueUrlRequiredError(Exception):
    """Raised when SQS queue URL is required but not provided."""

    def __init__(self) -> None:
        """Initialize the error."""
        super().__init__(
            "OC_SQS_QUEUE_URL environment variable is required for PipelineStorage"
        )


class StorageBuilder:
    """Builder for creating storage configurations."""

    def __init__(self) -> None:
        """Initialize the storage builder with default configuration."""
        self._s3_bucket: str | None = None
        self._s3_prefix: str = ""
        self._s3_region: str = self._get_default_aws_region()
        self._s3_endpoint_url: str | None = None
        self._file_path: str | None = None
        self._use_unzip: bool = False

    def _get_default_aws_region(self) -> str:
        """Get default AWS region with proper precedence: AWS_REGION > hard-coded default."""
        return os.getenv("AWS_REGION", "eu-west-2")

    def pipeline_storage(
        self,
        bucket: str,
        prefix: str = "",
        region: str | None = None,
        endpoint_url: str | None = None,
    ) -> "StorageBuilder":
        """Configure pipeline storage."""
        self._s3_bucket = bucket
        self._s3_prefix = prefix
        self._s3_region = region or self._get_default_aws_region()
        self._s3_endpoint_url = endpoint_url
        return self

    def file_storage(self, path: str) -> "StorageBuilder":
        """Configure file storage."""
        self._file_path = path
        return self

    def storage_decorators(self, *, use_unzip: bool = False) -> "StorageBuilder":
        """Configure storage decorators."""
        self._use_unzip = use_unzip
        return self

    def build(self) -> object:
        """Build the storage configuration."""
        # Import here to avoid circular imports
        from . import (  # noqa: PLC0415
            FileStorage,
            PipelineStorage,
            UnzipResourceDecorator,
        )

        # Create base storage
        if self._s3_bucket:
            # Create SQS publisher for PipelineStorage
            # Get SQS configuration from environment variables
            sqs_queue_url = os.getenv("OC_SQS_QUEUE_URL")
            if not sqs_queue_url:
                raise SqsQueueUrlRequiredError

            sqs_publisher = SqsPublisher(
                queue_url=sqs_queue_url,
                region=self._s3_region,
                endpoint_url=self._s3_endpoint_url,
            )

            # Use pipeline storage with mandatory SQS publisher
            base_storage: object = PipelineStorage(
                bucket_name=self._s3_bucket,
                sqs_publisher=sqs_publisher,
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

        if self._use_unzip:
            storage = UnzipResourceDecorator(storage)

        return storage


def create_storage_config() -> StorageBuilder:
    """Create a new storage configuration builder."""
    return StorageBuilder()


# Global storage functions removed - use config_factory.create_app_config() instead
