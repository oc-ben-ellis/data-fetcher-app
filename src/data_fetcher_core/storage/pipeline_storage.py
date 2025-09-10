"""Pipeline storage implementation.

This module provides the PipelineStorage class for storing data to AWS S3,
including bucket management, object operations, and S3-specific features.
"""

import hashlib
import json
import os
import tempfile
from collections.abc import AsyncGenerator
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import urlparse

import boto3
import structlog
from boto3.s3.transfer import S3Transfer
from botocore.config import Config

from data_fetcher_core.core import BundleRef
from data_fetcher_core.storage.bundle_storage_context import BundleStorageContext

if TYPE_CHECKING:
    from data_fetcher_core.core import FetcherRecipe, FetchRunContext
    from data_fetcher_core.notifications.sqs_publisher import SqsPublisher

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
class PipelineStorage:
    """Pipeline storage implementation with mandatory SQS notifications and pending completion processing."""

    bucket_name: str
    sqs_publisher: "SqsPublisher"
    prefix: str = ""
    region: str | None = None
    endpoint_url: str | None = None

    def __post_init__(self) -> None:
        """Initialize the S3 storage and create S3 client."""
        # Validate that SQS publisher is provided
        if not self.sqs_publisher:
            error_message = "SQS publisher is required for PipelineStorage but was None"
            raise ValueError(error_message)

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
        self, bundle_ref: "BundleRef", recipe: "FetcherRecipe"
    ) -> "BundleStorageContext":
        """Initialize a new bundle and return a BundleStorageContext."""
        # Create S3 bundle
        bundle = S3StorageBundle(
            self.s3_client, self.bucket_name, self.prefix, bundle_ref
        )
        self._active_bundles[str(bundle_ref.bid)] = bundle

        # Create and return BundleStorageContext
        context = BundleStorageContext(bundle_ref, recipe, self)
        logger.debug(
            "Bundle started", bid=str(bundle_ref.bid), recipe_id=recipe.recipe_id
        )
        return context

    async def _add_resource_to_bundle(
        self,
        bundle_ref: "BundleRef",
        url: str,
        content_type: str | None,
        status_code: int,
        stream: AsyncGenerator[bytes],
    ) -> None:
        """Internal method to add a resource to a bundle."""
        bundle = self._active_bundles.get(str(bundle_ref.bid))
        if not bundle:
            error_message = "Bundle not found"
            raise ValueError(error_message)

        await bundle.write_resource(url, content_type, status_code, stream)

    async def complete_bundle_with_callbacks_hook(
        self,
        bundle_ref: "BundleRef",
        recipe: "FetcherRecipe",
        metadata: dict[str, Any],
    ) -> None:
        """Complete bundle and execute all completion callbacks."""
        # Finalize the bundle
        await self._finalize_bundle(bundle_ref)

        # Execute completion callbacks using the recipe
        await self._execute_completion_callbacks(bundle_ref, recipe)

        # Send SQS notification (mandatory)
        await self.sqs_publisher.publish_bundle_completion(
            bundle_ref, metadata, recipe.recipe_id
        )

        logger.debug(
            "Bundle completed", bid=str(bundle_ref.bid), recipe_id=recipe.recipe_id
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
        self, bundle_ref: "BundleRef", recipe: "FetcherRecipe"
    ) -> None:
        """Execute completion callbacks from recipe components."""
        # Execute loader completion callback
        if hasattr(recipe.bundle_loader, "on_bundle_complete_hook"):
            try:
                await recipe.bundle_loader.on_bundle_complete_hook(bundle_ref)
                logger.debug(
                    "Loader completion callback executed",
                    bid=str(bundle_ref.bid),
                    recipe_id=recipe.recipe_id,
                    loader_type=type(recipe.bundle_loader).__name__,
                )
            except Exception as e:
                logger.exception(
                    "Error executing loader completion callback",
                    error=str(e),
                    bid=str(bundle_ref.bid),
                    recipe_id=recipe.recipe_id,
                )

        # Execute locator completion callbacks
        for locator in recipe.bundle_locators:
            if hasattr(locator, "on_bundle_complete_hook"):
                try:
                    await locator.on_bundle_complete_hook(bundle_ref)
                    logger.debug(
                        "Locator completion callback executed",
                        bid=str(bundle_ref.bid),
                        recipe_id=recipe.recipe_id,
                        locator_type=type(locator).__name__,
                    )
                except Exception as e:
                    logger.exception(
                        "Error executing locator completion callback",
                        error=str(e),
                        bid=str(bundle_ref.bid),
                        recipe_id=recipe.recipe_id,
                    )

    # Optional hook - not part of protocol
    async def on_run_start(
        self, context: "FetchRunContext", recipe: "FetcherRecipe"
    ) -> None:
        """Hook called at the start of a fetcher run to process pending completions."""
        await self._process_pending_completions(context, recipe)

    async def _process_pending_completions(
        self, context: "FetchRunContext", recipe: "FetcherRecipe"
    ) -> None:
        """Process any pending SQS notifications from previous runs."""
        if not context.app_config or not context.app_config.kv_store:
            logger.debug(
                "No kv_store available - skipping pending completion processing"
            )
            return

        # Find all pending completion keys for this recipe
        pending_keys = await context.app_config.kv_store.scan(  # type: ignore[attr-defined]
            f"sqs_notifications:pending:{recipe.recipe_id}:*"
        )

        if not pending_keys:
            logger.debug("No pending completions found", recipe_id=recipe.recipe_id)
            return

        logger.info(
            "Processing pending completions",
            recipe_id=recipe.recipe_id,
            pending_count=len(pending_keys),
        )

        for key in pending_keys:
            pending_data = await context.app_config.kv_store.get(key)
            if pending_data:
                try:
                    # Reconstruct bundle_ref
                    bundle_ref = BundleRef.from_dict(pending_data["bundle_ref"])  # type: ignore[index]
                    metadata = pending_data["metadata"]  # type: ignore[index]

                    # Re-execute completion callbacks
                    await self._execute_completion_callbacks(bundle_ref, recipe)

                    # Re-send SQS notification
                    await self.sqs_publisher.publish_bundle_completion(
                        bundle_ref, metadata, recipe.recipe_id
                    )

                    # Remove pending key
                    await context.app_config.kv_store.delete(key)

                    logger.debug(
                        "Processed pending completion",
                        bid=str(bundle_ref.bid),
                        recipe_id=recipe.recipe_id,
                    )

                except Exception as e:
                    logger.exception(
                        "Error processing pending completion",
                        error=str(e),
                        key=key,
                        recipe_id=recipe.recipe_id,
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
        url: str,
        content_type: str | None,
        status_code: int,
        stream: AsyncGenerator[bytes],
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
            endpoint_url = (
                cast(  # noqa: SLF001  # SLF001: Accessing private member for endpoint URL extraction
                    "Any", self.s3_client
                )._endpoint.host
            )  # SLF001: Accessing private member for endpoint URL extraction
        except Exception as e:
            logger.exception(
                "Could not extract endpoint URL from S3 client",
                error=str(e),
            )
            endpoint_url = None

        region_name = getattr(
            getattr(self.s3_client, "meta", None), "region_name", None
        )

        profile_name = os.getenv(
            "OC_STORAGE_PIPELINE_AWS_PROFILE", os.getenv("AWS_PROFILE")
        )
        session = (
            boto3.session.Session(profile_name=profile_name)
            if profile_name
            else boto3.session.Session()
        )

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
        """Create an S3 key from a URL using BID for time-based organization."""
        # Parse URL
        parsed = urlparse(url)

        # Use BID for key generation to enable time-based organization
        # BID contains timestamp information from UUIDv7
        bid_str = str(self.bundle_ref.bid)

        # Create key with prefix and BID
        key = f"{self.prefix}/bundles/{bid_str}/resources"

        # Add filename to ensure uniqueness for multiple resources
        if parsed.path:
            filename = Path(parsed.path).name
            if filename:
                # Use the full filename to ensure uniqueness
                key += f"_{filename}"
            else:
                # Fallback: use hash of URL to ensure uniqueness
                url_hash = hashlib.sha256(url.encode()).hexdigest()[:8]
                key += f"_{url_hash}"

        return key

    async def close(self) -> None:
        """Close the bundle and upload metadata."""
        # Create bundle metadata using BID for time-based organization
        bid_str = str(self.bundle_ref.bid)
        bundle_key = f"{self.prefix}/bundles/{bid_str}/metadata.json"

        metadata = {
            "bid": bid_str,
            "primary_url": self.bundle_ref.primary_url,
            "resources_count": self.bundle_ref.resources_count,
            "storage_key": bundle_key,
            "uploaded_keys": self.uploaded_keys,
            "meta": self.bundle_ref.meta,
        }

        self.s3_client.put_object(  # type: ignore[attr-defined]
            Bucket=self.bucket_name,
            Key=bundle_key,
            Body=json.dumps(metadata, indent=2),
            ContentType="application/json",
        )
