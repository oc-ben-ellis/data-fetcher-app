"""AWS S3 storage implementation.

This module provides the S3Storage class for storing data to AWS S3,
including bucket management, object operations, and S3-specific features.
"""

import hashlib
import json
import os
import tempfile
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import urlparse

import boto3
import structlog
from boto3.s3.transfer import S3Transfer
from botocore.config import Config

if TYPE_CHECKING:
    from data_fetcher.core import BundleRef

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
    """S3 storage implementation."""

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

        # Create S3 client with optional custom endpoint
        if self.endpoint_url:
            # For LocalStack, we need to set these credentials
            aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
            aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")

            if not aws_access_key_id or not aws_secret_access_key:
                raise MissingAWSCredentialsError

            self.s3_client = boto3.client(
                "s3",
                region_name=self.region,
                endpoint_url=self.endpoint_url,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
            )
        else:
            self.s3_client = boto3.client("s3", region_name=self.region)

    @asynccontextmanager
    async def open_bundle(
        self, bundle_ref: "BundleRef"
    ) -> AsyncGenerator["S3Bundle", None]:
        """Open a bundle for writing to S3."""
        bundle = S3Bundle(self.s3_client, self.bucket_name, self.prefix, bundle_ref)
        try:
            yield bundle
        finally:
            await bundle.close()


class S3Bundle:
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
        url: str,
        content_type: str | None,
        status_code: int,
        stream: AsyncGenerator[bytes, None],
    ) -> None:
        """Write a resource to S3 using S3 Transfer Manager for streaming."""
        key = self._create_s3_key(url)

        # Create transfer manager with streaming config
        # Note: The actual transfer configuration is handled by S3Transfer, not Config
        transfer_config = Config(
            # Use only valid Config parameters
            max_pool_connections=10,
        )

        # Reuse the pre-configured client (includes endpoint/credentials for LocalStack)
        # but apply transfer-related config via a new session client using the same parameters
        # to ensure connection pooling settings are respected.
        # If the existing client has a custom endpoint, we must carry that forward.
        try:
            # botocore exposes _endpoint.host and meta.region_name
            # Accessing private member for endpoint URL extraction
            endpoint_url = cast(  # noqa: SLF001  # SLF001: Accessing private member for endpoint URL extraction
                "Any", self.s3_client
            )._endpoint.host  # SLF001: Accessing private member for endpoint URL extraction
        except Exception as e:
            logger.exception(
                "Could not extract endpoint URL from S3 client",
                error=str(e),
            )
            endpoint_url = None

        region_name = getattr(
            getattr(self.s3_client, "meta", None), "region_name", None
        )

        session = boto3.session.Session()

        # Get AWS credentials - require them when using custom endpoint
        aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")

        if endpoint_url and (not aws_access_key_id or not aws_secret_access_key):
            raise MissingAWSCredentialsError

        transfer_s3_client = session.client(
            "s3",
            region_name=region_name,
            endpoint_url=endpoint_url,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            config=transfer_config,
        )
        # Create transfer manager
        transfer = S3Transfer(transfer_s3_client)

        # Create a temporary file for streaming
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            try:
                # Stream to temporary file
                async for chunk in stream:
                    temp_file.write(chunk)
                temp_file.flush()

                # Upload using transfer manager (handles multipart automatically)
                transfer.upload_file(
                    temp_file.name,
                    self.bucket_name,
                    key,
                    extra_args={
                        "ContentType": content_type or "application/octet-stream",
                        "Metadata": {
                            "url": url,
                            "content_type": content_type or "application/octet-stream",
                            "status_code": str(status_code),
                        },
                    },
                )

                self.uploaded_keys.append(key)

            finally:
                # Clean up temporary file
                with suppress(OSError):
                    Path(temp_file.name).unlink()

    def _create_s3_key(self, url: str) -> str:
        """Create an S3 key from a URL."""
        # Parse URL
        parsed = urlparse(url)

        # Create a hash of the URL for uniqueness
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:8]

        # Create key with prefix
        key = f"{self.prefix}/resources/{url_hash}"

        # Add file extension based on content type
        if parsed.path:
            ext = Path(parsed.path).suffix
            if ext:
                key += ext

        return key

    async def close(self) -> None:
        """Close the bundle and upload metadata."""
        # Create bundle metadata
        bundle_key = f"{self.prefix}/bundles/{self.bundle_ref.primary_url.replace('://', '_').replace('/', '_')}.json"

        metadata = {
            "primary_url": self.bundle_ref.primary_url,
            "resources_count": self.bundle_ref.resources_count,
            "storage_key": bundle_key,
            "uploaded_keys": self.uploaded_keys,
        }

        self.s3_client.put_object(  # type: ignore[attr-defined]
            Bucket=self.bucket_name,
            Key=bundle_key,
            Body=json.dumps(metadata, indent=2),
            ContentType="application/json",
        )
