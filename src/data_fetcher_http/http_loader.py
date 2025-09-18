"""HTTP data loader implementation."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Union, cast

import structlog

from data_fetcher_core.core import (
    BundleLoadResult,
    BundleRef,
    DataRegistryFetcherConfig,
    FetchRunContext,
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
        bundle: BundleRef,
        storage: Storage | None,
        ctx: FetchRunContext,
        recipe: DataRegistryFetcherConfig,
    ) -> BundleLoadResult:
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
            url = str(bundle.request_meta.get("url", ""))
            async with await self.http_manager.get_connection(
                self.http_config, ctx.app_config
            ) as http:
                response = await http.get(
                    url,
                    headers={},
                    follow_redirects=self.follow_redirects,
                )

            # Build immutable bundle_meta for the result (do not mutate request_meta)
            bundle_meta = {
                **dict(bundle.request_meta),
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type"),
                "content_length": response.headers.get("content-length"),
                "resources_count": 1,
            }

            # Create logger with BID context for tracing
            bid_logger = logger.bind(bid=str(bundle.bid))

            # Stream to storage
            resources_meta: list[dict[str, object]] = []
            if storage:
                bid_logger.debug("STREAMING_HTTP_RESPONSE_TO_STORAGE", url=url)
                bundle_context = await storage.start_bundle(bundle, recipe)
                # BundleStorageContext doesn't support async with, so we use it directly
                bundle = bundle_context

                # Write primary resource
                resource_meta = {
                    "url": url,
                    "content_type": response.headers.get("content-type"),
                    "status_code": response.status_code,
                }
                await bundle.add_resource(
                    resource_name=url,
                    metadata={
                        **resource_meta,
                    },
                    stream=cast("AsyncGenerator[bytes]", response.aiter_bytes()),
                )
                resources_meta.append(resource_meta)

                # Handle related resources (e.g., CSS, JS, images)
                if self.max_related > 0:
                    related_urls = self._extract_related_urls(response)
                    for _i, related_url in enumerate(related_urls[: self.max_related]):
                        try:
                            async with await self.http_manager.get_connection(
                                self.http_config, ctx.app_config
                            ) as http:
                                related_response = await http.get(related_url)
                            related_meta = {
                                "url": related_url,
                                "content_type": related_response.headers.get(
                                    "content-type"
                                ),
                                "status_code": related_response.status_code,
                            }
                            await bundle.add_resource(
                                resource_name=related_url,
                                metadata=related_meta,
                                stream=cast(
                                    "AsyncGenerator[bytes]",
                                    related_response.aiter_bytes(),
                                ),
                            )
                            resources_meta.append(related_meta)
                            # Increment resources_count if tracked in meta
                            # Track resource count in local bundle_meta only
                            try:
                                current = int(bundle_meta.get("resources_count", 0))
                            except (TypeError, ValueError):
                                current = 0
                            bundle_meta["resources_count"] = current + 1
                        except Exception as e:
                            bid_logger.warning(
                                "ERROR_FETCHING_RELATED_RESOURCE",
                                related_url=related_url,
                                error=str(e),
                            )
                            raise RuntimeError(
                                f"Failed to fetch related resource '{related_url}': {e}"
                            ) from e
                bid_logger.debug(
                    "SUCCESSFULLY_STREAMED_HTTP_RESPONSE_TO_STORAGE", url=url
                )

        except Exception as e:
            logger.exception(
                "ERROR_LOADING_HTTP_REQUEST",
                url=str(bundle.request_meta.get("url", "unknown")),
                error=str(e),
            )
            raise
        else:
            return BundleLoadResult(
                bundle=bundle, bundle_meta=bundle_meta, resources=resources_meta
            )

    def _extract_related_urls(self, response: object) -> list[str]:  # noqa: ARG002
        """Extract related URLs from HTML content."""
        # This is a simplified implementation
        # In a real implementation, you would parse HTML and extract links
        return []
