"""AWS S3 storage implementation.

This module provides the S3Storage class for storing data to AWS S3,
including bucket management, object operations, and S3-specific features.
"""

import os
import tempfile
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from ..core import BundleRef


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

        try:
            import boto3

            # Declare the attribute once to avoid mypy no-redef complaints
            self.s3_client: Any

            # Create S3 client with optional custom endpoint
            if self.endpoint_url:
                # For LocalStack, we need to set these credentials
                self.s3_client = boto3.client(
                    "s3",
                    region_name=self.region,
                    endpoint_url=self.endpoint_url,
                    aws_access_key_id="test",
                    aws_secret_access_key="test",
                )
            else:
                self.s3_client = boto3.client("s3", region_name=self.region)
        except ImportError as err:
            raise ImportError("boto3 is required for S3 storage") from err

    @asynccontextmanager
    async def open_bundle(
        self, bundle_ref: BundleRef
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
        self, s3_client: Any, bucket_name: str, prefix: str, bundle_ref: BundleRef
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
        import boto3
        from botocore.config import Config

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
        transfer_s3_client: Any
        try:
            # botocore exposes _endpoint.host and meta.region_name
            endpoint_url = self.s3_client._endpoint.host
        except Exception:
            endpoint_url = None

        region_name = getattr(
            getattr(self.s3_client, "meta", None), "region_name", None
        )

        session = boto3.session.Session()
        transfer_s3_client = session.client(
            "s3",
            region_name=region_name,
            endpoint_url=endpoint_url,
            aws_access_key_id=os.getenv(
                "AWS_ACCESS_KEY_ID", "test" if endpoint_url else None
            ),
            aws_secret_access_key=os.getenv(
                "AWS_SECRET_ACCESS_KEY", "test" if endpoint_url else None
            ),
            config=transfer_config,
        )
        # Use the correct import path for S3Transfer
        from boto3.s3.transfer import S3Transfer

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
                try:
                    os.unlink(temp_file.name)
                except OSError:
                    pass

    def _create_s3_key(self, url: str) -> str:
        """Create an S3 key from a URL."""
        import hashlib
        from urllib.parse import urlparse

        # Parse URL
        parsed = urlparse(url)

        # Create a hash of the URL for uniqueness
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]

        # Create key with prefix
        key = f"{self.prefix}/resources/{url_hash}"

        # Add file extension based on content type
        if parsed.path:
            _, ext = os.path.splitext(parsed.path)
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

        import json

        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=bundle_key,
            Body=json.dumps(metadata, indent=2),
            ContentType="application/json",
        )
