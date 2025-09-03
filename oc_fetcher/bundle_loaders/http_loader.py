"""HTTP data loader implementation."""

__author__ = "Ben Ellis <ben.ellis@opencorporates.com>"
__copyright__ = "Copyright (c) 2024 OpenCorporates Ltd"

from dataclasses import dataclass
from typing import Any

import structlog

from ..core import BundleRef, FetchRunContext, RequestMeta
from ..protocols import HttpManager

# Get logger for this module
logger = structlog.get_logger(__name__)


@dataclass
class HttpxStreamingLoader:
    """HTTP streaming loader with support for related resources."""

    http_manager: HttpManager
    max_related: int = 2
    follow_redirects: bool = True
    max_redirects: int = 5

    async def load(
        self, request: RequestMeta, storage: Any, ctx: FetchRunContext
    ) -> list[BundleRef]:
        """Load data from HTTP endpoint with streaming support.

        Args:
            request: The request to process
            storage: Storage backend for saving data
            ctx: Fetch run context

        Returns:
            List of bundle references
        """
        try:
            # Make HTTP request
            response = await self.http_manager.request(
                "GET",
                request.url,
                headers=request.headers,
                follow_redirects=self.follow_redirects,
            )

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
                async with storage.open_bundle(bundle_ref) as bundle:
                    # Write primary resource
                    await bundle.write_resource(
                        url=request.url,
                        content_type=response.headers.get("content-type"),
                        status_code=response.status_code,
                        stream=response.aiter_bytes(),
                    )

                    # Handle related resources (e.g., CSS, JS, images)
                    if self.max_related > 0:
                        related_urls = self._extract_related_urls(response)
                        for _i, related_url in enumerate(
                            related_urls[: self.max_related]
                        ):
                            try:
                                related_response = await self.http_manager.request(
                                    "GET", related_url
                                )
                                await bundle.write_resource(
                                    url=related_url,
                                    content_type=related_response.headers.get(
                                        "content-type"
                                    ),
                                    status_code=related_response.status_code,
                                    stream=related_response.aiter_bytes(),
                                )
                                bundle_ref.resources_count += 1
                            except Exception as e:
                                logger.warning(
                                    "Error fetching related resource",
                                    related_url=related_url,
                                    error=str(e),
                                )

            return [bundle_ref]

        except Exception as e:
            logger.error(
                "Error loading HTTP request",
                url=request.url,
                error=str(e),
                exc_info=True,
            )
            return []

    def _extract_related_urls(self, response: Any) -> list[str]:
        """Extract related URLs from HTML content."""
        # This is a simplified implementation
        # In a real implementation, you would parse HTML and extract links
        return []
