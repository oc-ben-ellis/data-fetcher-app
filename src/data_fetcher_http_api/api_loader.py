"""HTTP API data loader implementation."""

from collections.abc import AsyncGenerator, Callable
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


class StorageRequiredError(Exception):
    """Raised when storage is required but not provided."""

    def __init__(self) -> None:
        """Initialize the error."""
        super().__init__("Storage is required but was None")


if TYPE_CHECKING:
    from data_fetcher_core.storage.file_storage import FileStorage
    from data_fetcher_core.storage.pipeline_bus_storage import DataPipelineBusStorage
    from data_fetcher_core.storage.s3_storage import S3Storage

# Type alias for storage classes
Storage = Union["FileStorage", "S3Storage", "DataPipelineBusStorage"]

# Get logger for this module
logger = structlog.get_logger(__name__)


@dataclass
class HttpBundleLoader:
    """Generic API loader for HTTP-based APIs."""

    http_manager: HttpManager
    http_config: HttpProtocolConfig
    meta_load_name: str = "api_loader"
    follow_redirects: bool = True
    max_redirects: int = 5
    error_handler: Callable[[str, int], bool] | None = None

    async def load(
        self,
        bundle: BundleRef,
        storage: Storage,
        ctx: FetchRunContext,
        recipe: DataRegistryFetcherConfig,
    ) -> BundleLoadResult:
        """Load data from API endpoint using BundleStorageContext.

        Args:
            request: The request to process
            storage: Storage backend for saving data
            ctx: Fetch run context
            recipe: The fetcher recipe

        Returns:
            List of bundle references
        """
        if not storage:
            raise StorageRequiredError

        try:
            url = str(bundle.request_meta.get("url", ""))
            logger.debug(
                "LOADING_API_REQUEST", url=url, meta_load_name=self.meta_load_name
            )

            # Make HTTP request (authentication is handled by HttpManager)
            response = await self.http_manager.request(
                self.http_config,
                ctx.app_config,
                "GET",
                url,
                headers={},
                follow_redirects=self.follow_redirects,
            )

            logger.debug(
                "RECEIVED_HTTP_RESPONSE",
                url=url,
                status_code=response.status_code,
                content_type=response.headers.get("content-type"),
                content_length=response.headers.get("content-length"),
            )

            # Handle errors if custom error handler is provided
            if self.error_handler and not self.error_handler(url, response.status_code):
                logger.warning(
                    "REQUEST_REJECTED_BY_ERROR_HANDLER",
                    url=url,
                    status_code=response.status_code,
                )
                raise RuntimeError("Error handler rejected response")

            # Update bundle request_meta
            bundle.request_meta.update({
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type"),
                "content_length": response.headers.get("content-length"),
                "resources_count": 1,
            })

            # Create logger with BID context for tracing
            bid_logger = logger.bind(bid=str(bundle.bid))

            # Use new BundleStorageContext interface
            bid_logger.debug("STREAMING_RESPONSE_TO_STORAGE", url=url)

            # 1. Start bundle and get context
            bundle_context = await storage.start_bundle(bundle, recipe)

            try:
                # 2. Add primary resource
                primary_meta = {
                    "url": url,
                    "content_type": response.headers.get("content-type"),
                    "status_code": response.status_code,
                }
                await bundle_context.add_resource(
                    resource_name=url,
                    metadata=primary_meta,
                    stream=cast("AsyncGenerator[bytes]", response.aiter_bytes()),
                )

                # 3. Complete bundle
                await bundle_context.complete(
                    {"source": "http_api", "run_id": ctx.run_id, "resources_count": 1}
                )

            except Exception as e:
                # BundleStorageContext will handle cleanup
                bid_logger.exception("Error in bundle processing", error=str(e))
                raise

            bid_logger.debug("SUCCESSFULLY_STREAMED_TO_STORAGE", url=url)

            bid_logger.info(
                "API_REQUEST_LOADED_SUCCESSFULLY",
                url=url,
                status_code=response.status_code,
                bundle_ref=bundle,
            )

        except Exception as e:
            logger.exception(
                "REQUEST_LOADING_ERROR",
                url=str(bundle.request_meta.get("url", "unknown")),
                error=str(e),
            )
            raise
        else:
            return BundleLoadResult(
                bundle=bundle,
                 bundle_meta=bundle.request_meta,
                resources=[
                    {
                        "url": url,
                        "content_type": response.headers.get("content-type"),
                        "status_code": response.status_code,
                    }
                ],
            )


@dataclass
class TrackingHttpBundleLoader(HttpBundleLoader):
    """API loader that tracks failed requests for retry purposes."""

    def __post_init__(self) -> None:
        """Initialize the tracking state for failed identifiers."""
        self._failed_identifiers: set[str] = set()

    def get_failed_identifiers(self) -> set[str]:
        """Get the set of failed identifiers."""
        return self._failed_identifiers.copy()

    def add_failed_identifier(self, identifier: str) -> None:
        """Add an identifier to the failed set."""
        self._failed_identifiers.add(identifier)
