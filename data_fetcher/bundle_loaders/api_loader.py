"""HTTP API data loader implementation."""

from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Union, cast

import structlog

from data_fetcher.core import BundleRef, FetchRunContext, RequestMeta
from data_fetcher.protocols import HttpManager

if TYPE_CHECKING:
    from data_fetcher.storage.file_storage import FileStorage
    from data_fetcher.storage.lineage_storage import LineageStorage
    from data_fetcher.storage.s3_storage import S3Storage

# Type alias for storage classes
Storage = Union["FileStorage", "S3Storage", "LineageStorage"]

# Get logger for this module
logger = structlog.get_logger(__name__)


@dataclass
class ApiLoader:
    """Generic API loader for HTTP-based APIs."""

    http_manager: HttpManager
    meta_load_name: str = "api_loader"
    follow_redirects: bool = True
    max_redirects: int = 5
    error_handler: Callable[[str, int], bool] | None = None

    async def load(
        self,
        request: RequestMeta,
        storage: Storage | None,
        ctx: FetchRunContext,  # noqa: ARG002
    ) -> list[BundleRef]:
        """Load data from API endpoint.

        Args:
            request: The request to process
            storage: Storage backend for saving data
            ctx: Fetch run context

        Returns:
            List of bundle references
        """
        try:
            logger.debug(
                "Loading API request",
                url=request.url,
                meta_load_name=self.meta_load_name,
            )

            # Make HTTP request (authentication is handled by HttpManager)
            response = await self.http_manager.request(
                "GET",
                request.url,
                headers=request.headers,
                follow_redirects=self.follow_redirects,
            )

            logger.debug(
                "Received HTTP response",
                url=request.url,
                status_code=response.status_code,
                content_type=response.headers.get("content-type"),
                content_length=response.headers.get("content-length"),
            )

            # Handle errors if custom error handler is provided
            if self.error_handler and not self.error_handler(
                request.url, response.status_code
            ):
                logger.warning(
                    "Request rejected by error handler",
                    url=request.url,
                    status_code=response.status_code,
                )
                return []

            # Create bundle reference
            bundle_ref = BundleRef(
                primary_url=request.url,
                resources_count=1,
                meta={
                    "status_code": response.status_code,
                    "content_type": response.headers.get("content-type"),
                    "content_length": response.headers.get("content-length"),
                },
            )

            # Stream to storage
            if storage:
                logger.debug("Streaming response to storage", url=request.url)
                async with storage.open_bundle(bundle_ref) as bundle:
                    # Write primary resource
                    await bundle.write_resource(
                        url=request.url,
                        content_type=response.headers.get("content-type"),
                        status_code=response.status_code,
                        stream=cast(
                            "AsyncGenerator[bytes, None]", response.aiter_bytes()
                        ),
                    )
                logger.debug("Successfully streamed to storage", url=request.url)
            else:
                logger.debug(
                    "No storage configured, skipping storage write", url=request.url
                )

            logger.info(
                "API request loaded successfully",
                url=request.url,
                status_code=response.status_code,
                bundle_ref=bundle_ref,
            )

        except Exception as e:
            logger.exception("Error loading request", url=request.url, error=str(e))
            return []
        else:
            return [bundle_ref]


@dataclass
class TrackingApiLoader(ApiLoader):
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
