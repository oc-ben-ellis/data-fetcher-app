"""Pipeline Bus storage implementation.

This module provides the DataPipelineBusStorage class that uses the pipeline-bus module
for standardized S3 layout, BID generation, event emission, and CDC with hash storage.
"""

import hashlib
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import structlog
from oc_pipeline_bus import DataPipelineBus

from data_fetcher_core.storage.bundle_storage_context import BundleStorageContext

if TYPE_CHECKING:
    from data_fetcher_core.core import BundleRef, DataRegistryFetcherConfig

# Get logger for this module
logger = structlog.get_logger(__name__)


@dataclass
class DataPipelineBusStorage:
    """Pipeline Bus storage implementation using the oc_pipeline_bus module."""

    pipeline_bus: DataPipelineBus | None = None
    _skip_validation: bool = False

    def __post_init__(self) -> None:
        """Initialize the Pipeline Bus storage."""
        if self.pipeline_bus is None:
            self.pipeline_bus = DataPipelineBus(_skip_validation=self._skip_validation)
        self._active_bundles: dict[str, str] = {}  # bid -> bundle_id mapping

    async def start_bundle(
        self, bundle_ref: "BundleRef", recipe: "DataRegistryFetcherConfig"
    ) -> "BundleStorageContext":
        """Initialize a new bundle and return a BundleStorageContext."""
        # Create bundle metadata for the pipeline bus
        bundle_metadata = {
            "primary_url": bundle_ref.request_meta.get("url"),
            "resources_count": bundle_ref.request_meta.get("resources_count"),
            "meta": dict(bundle_ref.request_meta),
            "config_id": recipe.config_id,
        }

        # Notify pipeline bus that bundle was found and get the BID
        bid = self.pipeline_bus.bundle_found(bundle_metadata)

        # Store the mapping between our bundle_ref.bid and the pipeline bus bid
        self._active_bundles[str(bundle_ref.bid)] = bid

        # Create and return BundleStorageContext
        context = BundleStorageContext(bundle_ref, recipe, self)
        logger.debug(
            "Bundle started with pipeline bus",
            bid=str(bundle_ref.bid),
            pipeline_bid=bid,
            config_id=recipe.config_id,
        )
        return context

    def bundle_found(self, metadata: dict[str, Any]) -> str:
        """Mint a BID using the underlying pipeline bus and return it.

        Adds clearer error context if the underlying SQS queue is missing.
        """
        return self.pipeline_bus.bundle_found(metadata)

    async def _add_resource_to_bundle(
        self,
        bundle_ref: "BundleRef",
        resource_name: str,
        metadata: dict[str, Any],
        stream: AsyncGenerator[bytes],
    ) -> None:
        """Internal method to add a resource to a bundle."""
        bid = self._active_bundles.get(str(bundle_ref.bid))
        if not bid:
            error_message = "Bundle not found in active bundles"
            raise ValueError(error_message)

        # Progress callback for logging
        async def progress_callback(bytes_uploaded: int) -> None:
            logger.debug(
                "Uploading resource",
                bid=str(bundle_ref.bid),
                pipeline_bid=bid,
                resource_name=resource_name,
                bytes_uploaded=bytes_uploaded,
            )

        # Stream directly to pipeline bus
        await self.pipeline_bus.add_bundle_resource_streaming(
            bid=bid,
            resource_name=resource_name,
            metadata=metadata,
            async_stream=stream,
            progress_callback=progress_callback,
        )

        logger.debug(
            "Resource added to bundle",
            bid=str(bundle_ref.bid),
            pipeline_bid=bid,
            resource_name=resource_name,
        )

    async def complete_bundle_with_callbacks_hook(
        self,
        bundle_ref: "BundleRef",
        recipe: "DataRegistryFetcherConfig",
        metadata: dict[str, Any],
    ) -> None:
        """Complete bundle and execute all completion callbacks."""
        bid = self._active_bundles.get(str(bundle_ref.bid))
        if not bid:
            error_message = "Bundle not found in active bundles"
            raise ValueError(error_message)

        # Execute completion callbacks using the recipe
        await self._execute_completion_callbacks(bundle_ref, recipe)

        # Complete the bundle using pipeline bus
        self.pipeline_bus.complete_bundle(bid, metadata)

        # Clean up
        del self._active_bundles[str(bundle_ref.bid)]

        logger.debug(
            "Bundle completed with pipeline bus",
            bid=str(bundle_ref.bid),
            pipeline_bid=bid,
            config_id=recipe.config_id,
        )

    async def _execute_completion_callbacks(
        self, bundle_ref: "BundleRef", recipe: "DataRegistryFetcherConfig"
    ) -> None:
        """Execute completion callbacks from recipe components."""
        # Execute loader completion callback
        loader = recipe.loader
        if loader is not None and getattr(loader, "on_bundle_complete_hook", None):
            try:
                await loader.on_bundle_complete_hook(bundle_ref)
                logger.debug(
                    "Loader completion callback executed",
                    bid=str(bundle_ref.bid),
                    config_id=recipe.config_id,
                    loader_type=type(recipe.loader).__name__,
                )
            except Exception as e:
                logger.exception(
                    "Error executing loader completion callback",
                    error=str(e),
                    bid=str(bundle_ref.bid),
                    config_id=recipe.config_id,
                )

        # Execute locator completion callbacks
        for locator in recipe.locators:
            if locator is not None and getattr(
                locator, "on_bundle_complete_hook", None
            ):
                try:
                    await locator.on_bundle_complete_hook(bundle_ref)
                    logger.debug(
                        "Locator completion callback executed",
                        bid=str(bundle_ref.bid),
                        config_id=recipe.config_id,
                        locator_type=type(locator).__name__,
                    )
                except Exception as e:
                    logger.exception(
                        "Error executing locator completion callback",
                        error=str(e),
                        bid=str(bundle_ref.bid),
                        config_id=recipe.config_id,
                    )

    def _create_resource_name(self, url: str) -> str:
        """Create a resource name from a URL."""
        parsed = urlparse(url)
        if parsed.path:
            filename = Path(parsed.path).name
            if filename:
                return filename

        # Fallback: use hash of URL to ensure uniqueness
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:8]
        return f"resource_{url_hash}"
