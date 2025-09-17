"""S3 storage implementation.

This module provides the S3Storage class for storing data to AWS S3,
including bucket management and object operations.
"""

import hashlib
import json
import os
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import boto3
import structlog

from data_fetcher_core.storage.bundle_storage_context import BundleStorageContext

if TYPE_CHECKING:
    from data_fetcher_core.core import BundleRef, DataRegistryFetcherConfig

# Get logger for this module
logger = structlog.get_logger(__name__)


class MissingAWSCredentialsError(ValueError):
    """Raised when AWS credentials are required but not provided."""

    def __init__(self) -> None:
        """Initialize the error with a descriptive message."""
        super().__init__(
            "AWS credentials are required when using a custom endpoint. "
            "Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables."
        )


@dataclass
class S3Storage:
    """S3 storage implementation for basic S3 operations without SQS notifications."""

    bucket_name: str
    prefix: str = ""
    region: str | None = None
    endpoint_url: str | None = None

    def __post_init__(self) -> None:
        """Initialize the S3 storage and create S3 client."""
        # Use AWS_REGION environment variable if region is not specified
        if self.region is None:
            self.region = os.getenv("AWS_REGION", "eu-west-2")

        # Declare the attribute once to avoid mypy no-redef complaints
        self.s3_client: Any = None
        self._active_bundles: dict[str, Any] = {}

        # Create S3 client with optional custom endpoint and profile
        profile_name = os.getenv(
            "OC_STORAGE_PIPELINE_AWS_PROFILE", os.getenv("AWS_PROFILE")
        )
        session = (
            boto3.session.Session(profile_name=profile_name)
            if profile_name
            else boto3.session.Session()
        )
        if self.endpoint_url:
            # For LocalStack, we need to set these credentials
            aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
            aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")

            if not aws_access_key_id or not aws_secret_access_key:
                raise MissingAWSCredentialsError

            self.s3_client = session.client(
                "s3",
                region_name=self.region,
                endpoint_url=self.endpoint_url,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
            )
        else:
            self.s3_client = session.client("s3", region_name=self.region)

    # New interface methods
    async def start_bundle(
        self, bundle_ref: "BundleRef", config: "DataRegistryFetcherConfig"
    ) -> "BundleStorageContext":
        """Initialize a new bundle and return a BundleStorageContext."""
        # Create S3 bundle
        bundle = S3StorageBundle(
            self.s3_client, self.bucket_name, self.prefix, bundle_ref
        )
        self._active_bundles[str(bundle_ref.bid)] = bundle

        # Create and return BundleStorageContext
        context = BundleStorageContext(bundle_ref, config, self)
        logger.debug(
            "Bundle started", bid=str(bundle_ref.bid), config_id=config.config_id
        )
        return context

    def bundle_found(self, metadata: dict[str, Any]) -> str:
        """Return a stub/mock BID value for S3 storage (no event emission)."""
        from datetime import UTC, datetime
        from secrets import token_hex

        ts = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        reg = str(metadata.get("config_id", "s3")).lower().replace(" ", "-")
        rnd = token_hex(4)
        return f"bid:v1:{reg}:{ts}:{rnd}"

    async def _add_resource_to_bundle(
        self,
        bundle_ref: "BundleRef",
        resource_name: str,
        metadata: dict[str, Any],
        stream: AsyncGenerator[bytes],
    ) -> None:
        """Internal method to add a resource to a bundle."""
        bundle = self._active_bundles.get(str(bundle_ref.bid))
        if not bundle:
            error_message = "Bundle not found"
            raise ValueError(error_message)

        await bundle.write_resource(resource_name, metadata, stream)

    async def complete_bundle_with_callbacks_hook(
        self,
        bundle_ref: "BundleRef",
        config: "DataRegistryFetcherConfig",
        metadata: dict[str, Any],
    ) -> None:
        """Complete bundle and execute all completion callbacks."""
        # Finalize the bundle
        await self._finalize_bundle(bundle_ref)

        # Execute completion callbacks using the config
        await self._execute_completion_callbacks(bundle_ref, config)

        logger.debug(
            "Bundle completed", bid=str(bundle_ref.bid), config_id=config.config_id
        )

    async def _finalize_bundle(
        self,
        bundle_ref: "BundleRef",
    ) -> None:
        """Internal method to finalize a bundle."""
        bundle = self._active_bundles.get(str(bundle_ref.bid))
        if not bundle:
            error_message = "Bundle not found"
            raise ValueError(error_message)

        # Finalize the S3 bundle (upload metadata, etc.)
        await bundle.close()

        # Clean up
        del self._active_bundles[str(bundle_ref.bid)]

    async def _execute_completion_callbacks(
        self, bundle_ref: "BundleRef", config: "DataRegistryFetcherConfig"
    ) -> None:
        """Execute completion callbacks from config components."""
        # Execute loader completion callback
        loader = config.loader
        if loader is not None and getattr(loader, "on_bundle_complete_hook", None):
            try:
                await loader.on_bundle_complete_hook(bundle_ref)
                logger.debug(
                    "Loader completion callback executed",
                    bid=str(bundle_ref.bid),
                    config_id=config.config_id,
                    loader_type=type(config.loader).__name__,
                )
            except Exception as e:
                logger.exception(
                    "Error executing loader completion callback",
                    error=str(e),
                    bid=str(bundle_ref.bid),
                    config_id=config.config_id,
                )

        # Execute locator completion callbacks
        for locator in config.locators:
            if locator is not None and getattr(
                locator, "on_bundle_complete_hook", None
            ):
                try:
                    await locator.on_bundle_complete_hook(bundle_ref)
                    logger.debug(
                        "Locator completion callback executed",
                        bid=str(bundle_ref.bid),
                        config_id=config.config_id,
                        locator_type=type(locator).__name__,
                    )
                except Exception as e:
                    logger.exception(
                        "Error executing locator completion callback",
                        error=str(e),
                        bid=str(bundle_ref.bid),
                        config_id=config.config_id,
                    )


class S3StorageBundle:
    """S3 bundle for writing resources to S3."""

    def __init__(
        self, s3_client: object, bucket_name: str, prefix: str, bundle_ref: "BundleRef"
    ) -> None:
        """Initialize the S3 bundle with S3 client, bucket, and bundle reference.

        Args:
            s3_client: The S3 client to use for uploads.
            bucket_name: Name of the S3 bucket.
            prefix: Prefix for S3 keys.
            bundle_ref: Reference to the bundle being created.
        """
        self.s3_client = s3_client
        self.bucket_name = bucket_name
        self.prefix = prefix
        self.bundle_ref = bundle_ref
        self.uploaded_keys: list[str] = []

    async def write_resource(
        self,
        resource_name: str,
        metadata: dict[str, Any],
        stream: AsyncGenerator[bytes],
    ) -> None:
        """Write a resource to S3 using true streaming with multipart uploads."""
        key = self._create_s3_key(resource_name)

        # Extract metadata with defaults
        url = metadata.get("url", "")
        content_type = metadata.get("content_type")
        status_code = metadata.get("status_code", 200)

        logger.info(
            "S3_UPLOAD_STARTING",
            s3_bucket=self.bucket_name,
            s3_key=key,
            resource_name=resource_name,
            url=url,
            content_type=content_type,
            bundle_id=str(self.bundle_ref.bid),
        )

        try:
            # Use true streaming with multipart uploads
            await self._stream_to_s3_with_multipart(
                stream=stream,
                key=key,
                content_type=content_type,
                metadata={
                    "resource_name": resource_name,
                    "url": url,
                    "content_type": content_type or "application/octet-stream",
                    "status_code": str(status_code),
                },
            )

            self.uploaded_keys.append(key)

        except Exception as e:
            logger.exception(
                "S3_UPLOAD_FAILED",
                s3_bucket=self.bucket_name,
                s3_key=key,
                url=url,
                error=str(e),
            )
            raise

    async def _stream_to_s3_with_multipart(
        self,
        stream: AsyncGenerator[bytes],
        key: str,
        content_type: str | None,
        metadata: dict[str, str],
        chunk_size: int = 8 * 1024 * 1024,  # 8MB
    ) -> None:
        """Stream data to S3 using multipart uploads with minimal memory usage.

        This implementation uses S3 multipart uploads with bounded memory usage:
        - Only accumulates data up to chunk_size (default 8MB) at a time
        - Uploads each part immediately when chunk_size is reached
        - Memory usage is bounded by chunk_size, not total file size
        """
        import aioboto3

        session = aioboto3.Session()
        async with session.client("s3") as s3:
            # Initialize multipart upload
            response = await s3.create_multipart_upload(
                Bucket=self.bucket_name,
                Key=key,
                ContentType=content_type or "application/octet-stream",
                Metadata=metadata,
            )
            upload_id = response["UploadId"]

            parts = []
            part_number = 1

            # Memory-bounded streaming: only hold up to chunk_size in memory
            current_part_chunks = []
            current_part_size = 0

            try:
                async for chunk in stream:
                    # Add chunk to current part
                    current_part_chunks.append(chunk)
                    current_part_size += len(chunk)

                    # If we've reached the chunk size, upload this part immediately
                    if current_part_size >= chunk_size:
                        # Combine chunks for this part (memory usage: max chunk_size)
                        part_data = b"".join(current_part_chunks)

                        # Upload the part to S3
                        response = await s3.upload_part(
                            Bucket=self.bucket_name,
                            Key=key,
                            PartNumber=part_number,
                            UploadId=upload_id,
                            Body=part_data,
                        )

                        parts.append(
                            {"ETag": response["ETag"], "PartNumber": part_number}
                        )
                        part_number += 1

                        # Reset for next part (immediately free memory)
                        current_part_chunks = []
                        current_part_size = 0

                # Upload any remaining data (final part)
                if current_part_size > 0:
                    part_data = b"".join(current_part_chunks)

                    response = await s3.upload_part(
                        Bucket=self.bucket_name,
                        Key=key,
                        PartNumber=part_number,
                        UploadId=upload_id,
                        Body=part_data,
                    )

                    parts.append({"ETag": response["ETag"], "PartNumber": part_number})

                # Complete multipart upload
                await s3.complete_multipart_upload(
                    Bucket=self.bucket_name,
                    Key=key,
                    UploadId=upload_id,
                    MultipartUpload={"Parts": parts},
                )

            except Exception:
                # Abort multipart upload on error
                await s3.abort_multipart_upload(
                    Bucket=self.bucket_name, Key=key, UploadId=upload_id
                )
                raise

    def _create_s3_key(self, url: str) -> str:
        """Create an S3 key from a URL using BID for time-based organization."""
        # Parse URL
        parsed = urlparse(url)

        # Use BID for key generation to enable time-based organization
        # BID contains timestamp information for chronological sorting
        bid_str = str(self.bundle_ref.bid)

        key = f"{self.prefix}/{bid_str}" if self.prefix else bid_str

        if parsed.path:
            filename = Path(parsed.path).name
            if filename:
                key += f"/{filename}"
            else:
                # Fallback: use hash of URL to ensure uniqueness
                url_hash = hashlib.sha256(url.encode()).hexdigest()[:8]
                key += f"/{url_hash}"

        return key

    async def close(self) -> None:
        """Close the bundle and upload metadata."""
        # Create bundle metadata using BID for time-based organization
        bid_str = str(self.bundle_ref.bid)
        bundle_key = f"{self.prefix}/bundles/{bid_str}/metadata.json"

        metadata = {
            "bid": bid_str,
            "primary_url": self.bundle_ref.request_meta.get("url"),
            "resources_count": self.bundle_ref.request_meta.get("resources_count"),
            "storage_key": bundle_key,
            "uploaded_keys": self.uploaded_keys,
            "meta": dict(self.bundle_ref.request_meta),
        }

        self.s3_client.put_object(  # type: ignore[attr-defined]
            Bucket=self.bucket_name,
            Key=bundle_key,
            Body=json.dumps(metadata, indent=2),
            ContentType="application/json",
        )
