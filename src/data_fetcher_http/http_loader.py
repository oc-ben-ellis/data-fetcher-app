"""HTTP data loader implementation."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Union, cast

import structlog

from data_fetcher_core.core import (
    BundleRef,
    DataRegistryFetcherConfig,
    FetchRunContext,
    RequestMeta,
)
from data_fetcher_http.http_config import HttpProtocolConfig
from data_fetcher_http.http_manager import HttpManager

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from data_fetcher_core.storage.file_storage import FileStorage
    from data_fetcher_core.storage.pipeline_bus_storage import DataPipelineBusStorage
    from data_fetcher_core.storage.s3_storage import S3Storage

# Type alias for storage classes
Storage = Union["FileStorage", "S3Storage", "DataPipelineBusStorage"]

# Get logger for this module
logger = structlog.get_logger(__name__)


@dataclass
class StreamingHttpBundleLoader:
    """HTTP streaming loader with support for related resources."""

    http_manager: HttpManager
    http_config: HttpProtocolConfig
    max_related: int = 2
    follow_redirects: bool = True
    max_redirects: int = 5

    async def load(
        self,
        request: RequestMeta,
        storage: Storage | None,
        ctx: FetchRunContext,
        recipe: DataRegistryFetcherConfig,
    ) -> list[BundleRef]:
        """Load data from HTTP endpoint with streaming support.

        Args:
            request: The request to process
            storage: Storage backend for saving data
            ctx: Fetch run context
            recipe: The fetcher recipe configuration

        Returns:
            List of bundle references
        """
        try:
            # Make HTTP request
            response = await self.http_manager.request(
                self.http_config,
                ctx.app_config,
                "GET",
                request["url"],
                headers=request.get("headers", {}),
                follow_redirects=self.follow_redirects,
            )

            # Create bundle reference
            bundle_ref = BundleRef(
                primary_url=request["url"],
                resources_count=1,
                meta={
                    "status_code": response.status_code,
                    "content_type": response.headers.get("content-type"),
                    "content_length": response.headers.get("content-length"),
                },
            )

            # Create logger with BID context for tracing
            bid_logger = logger.bind(bid=str(bundle_ref.bid))

            # Stream to storage
            if storage:
                bid_logger.debug(
                    "STREAMING_HTTP_RESPONSE_TO_STORAGE", url=request["url"]
                )
                bundle_context = await storage.start_bundle(bundle_ref, recipe)
                # BundleStorageContext doesn't support async with, so we use it directly
                bundle = bundle_context

                # Write primary resource
                await bundle.add_resource(
                    resource_name=request["url"],
                    metadata={
                        "url": request["url"],
                        "content_type": response.headers.get("content-type"),
                        "status_code": response.status_code,
                    },
                    stream=cast("AsyncGenerator[bytes]", response.aiter_bytes()),
                )

                # Handle related resources (e.g., CSS, JS, images)
                if self.max_related > 0:
                    related_urls = self._extract_related_urls(response)
                    for _i, related_url in enumerate(related_urls[: self.max_related]):
                        try:
                            related_response = await self.http_manager.request(
                                self.http_config,
                                ctx.app_config,
                                "GET",
                                related_url,
                            )
                            await bundle.add_resource(
                                resource_name=related_url,
                                metadata={
                                    "url": related_url,
                                    "content_type": related_response.headers.get(
                                        "content-type"
                                    ),
                                    "status_code": related_response.status_code,
                                },
                                stream=cast(
                                    "AsyncGenerator[bytes]",
                                    related_response.aiter_bytes(),
                                ),
                            )
                            # Increment resources_count if tracked in meta
                            try:
                                current = int(bundle_ref.meta.get("resources_count", 0))
                            except (TypeError, ValueError):
                                current = 0
                            bundle_ref.meta["resources_count"] = current + 1
                        except Exception as e:  # noqa: BLE001
                            bid_logger.warning(
                                "ERROR_FETCHING_RELATED_RESOURCE",
                                related_url=related_url,
                                error=str(e),
                            )
                bid_logger.debug(
                    "SUCCESSFULLY_STREAMED_HTTP_RESPONSE_TO_STORAGE", url=request["url"]
                )

        except Exception as e:
            logger.exception(
                "ERROR_LOADING_HTTP_REQUEST",
                url=request.get("url", "unknown"),
                error=str(e),
            )
            return []
        else:
            return [bundle_ref]

    def _extract_related_urls(self, response: object) -> list[str]:  # noqa: ARG002
        """Extract related URLs from HTML content."""
        # This is a simplified implementation
        # In a real implementation, you would parse HTML and extract links
        return []
