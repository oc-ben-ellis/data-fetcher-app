"""API-based bundle locator implementations.

This module provides bundle locators that work with REST APIs and web services,
including support for pagination, filtering, and dynamic data discovery.
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

import structlog

from data_fetcher.core import BundleRef, FetchRunContext, RequestMeta
from data_fetcher.kv_store import KeyValueStore, get_global_store
from data_fetcher.protocols import HttpManager

# Get logger for this module
logger = structlog.get_logger(__name__)


@dataclass
class ApiPaginationBundleLocator:
    """Generic API bundle locator with pagination support."""

    http_manager: HttpManager
    base_url: str
    date_start: str
    date_end: str | None = None
    max_records_per_page: int = 1000
    rate_limit_requests_per_second: float = 2.0
    date_filter: Callable[[str], bool] | None = None
    query_params: dict[str, Any] | None = None
    headers: dict[str, str] | None = None
    query_builder: Callable[[str], str] | None = None
    persistence_prefix: str = "api_provider"

    def __post_init__(self) -> None:
        """Initialize the bundle locator state and internal variables."""
        self._processed_urls: set[str] = set()
        self._url_queue: list[str] = []
        self._current_date: date | None = None
        self._current_cursor: str = "*"
        self._initialized: bool = False
        self._last_request_time: float = 0.0
        self._rate_limit_lock: asyncio.Lock = asyncio.Lock()
        self._store: KeyValueStore | None = None

    async def _get_store(self) -> KeyValueStore:
        """Get the key-value store instance."""
        if self._store is None:
            self._store = await get_global_store()
        return self._store

    async def _load_persistence_state(self) -> None:
        """Load persistence state from kvstore."""
        store = await self._get_store()

        # Load processed URLs
        processed_urls_key = f"{self.persistence_prefix}:processed_urls:{self.base_url}"
        processed_urls_data = await store.get(processed_urls_key, [])
        if isinstance(processed_urls_data, list):
            self._processed_urls = set(processed_urls_data)
        else:
            self._processed_urls = set()

        # Load current state
        state_key = f"{self.persistence_prefix}:state:{self.base_url}"
        state_data = await store.get(state_key, {})

        if state_data:
            self._current_date = datetime.strptime(  # noqa: DTZ007
                state_data.get("current_date", self.date_start),  # type: ignore[attr-defined]
                "%Y-%m-%d",
            ).date()
            self._current_cursor = state_data.get("current_cursor", "*")  # type: ignore[attr-defined]
            self._initialized = state_data.get("initialized", False)  # type: ignore[attr-defined]
            self._last_request_time = state_data.get("last_request_time", 0.0)  # type: ignore[attr-defined]

    async def _save_persistence_state(self) -> None:
        """Save persistence state to kvstore."""
        store = await self._get_store()

        # Save processed URLs
        processed_urls_key = f"{self.persistence_prefix}:processed_urls:{self.base_url}"
        await store.put(
            processed_urls_key, list(self._processed_urls), ttl=timedelta(days=7)
        )

        # Save current state
        state_key = f"{self.persistence_prefix}:state:{self.base_url}"
        state_data = {
            "current_date": (
                self._current_date.strftime("%Y-%m-%d")
                if self._current_date
                else self.date_start
            ),
            "current_cursor": self._current_cursor,
            "initialized": self._initialized,
            "last_request_time": self._last_request_time,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        await store.put(state_key, state_data, ttl=timedelta(days=7))

    async def _save_processing_result(
        self,
        request: RequestMeta,
        bundle_refs: list[BundleRef],
        *,
        success: bool = True,
    ) -> None:
        """Save processing result to kvstore."""
        store = await self._get_store()

        result_key = (
            f"{self.persistence_prefix}:results:{self.base_url}:{hash(request.url)}"
        )
        result_data = {
            "url": request.url,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success": success,
            "bundle_count": len(bundle_refs),
            "bundle_refs": [str(ref) for ref in bundle_refs],
        }
        await store.put(result_key, result_data, ttl=timedelta(days=30))

    async def _save_error_state(self, request: RequestMeta, error: str) -> None:
        """Save error state for retry logic."""
        store = await self._get_store()

        error_key = (
            f"{self.persistence_prefix}:errors:{self.base_url}:{hash(request.url)}"
        )
        error_data = {
            "url": request.url,
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "retry_count": 0,
        }
        await store.put(error_key, error_data, ttl=timedelta(hours=24))

    async def get_next_urls(self, _ctx: FetchRunContext) -> list[RequestMeta]:
        """Get the next batch of API URLs to process."""
        if not self._initialized:
            await self._load_persistence_state()
            await self._initialize()

        urls: list[RequestMeta] = []
        BATCH_SIZE = 5  # noqa: N806
        while self._url_queue and len(urls) < BATCH_SIZE:  # Batch size
            url = self._url_queue.pop(0)
            if url not in self._processed_urls:
                urls.append(RequestMeta(url=url, headers=self.headers or {}))
                self._processed_urls.add(url)

        # Save state after generating URLs
        await self._save_persistence_state()
        return urls

    async def handle_url_processed(
        self, request: RequestMeta, bundle_refs: list[BundleRef], _ctx: FetchRunContext
    ) -> None:
        """Handle when a URL has been processed and potentially generate next URLs."""
        # Mark as processed
        self._processed_urls.add(request.url)

        # Save processing result
        await self._save_processing_result(request, bundle_refs, success=True)

        # Check if we need to generate more URLs based on response
        if bundle_refs and len(bundle_refs) > 0:
            # Extract cursor from response if available
            # This would need to be implemented based on the actual API response format
            await self._generate_next_urls(_ctx)

        # If no more URLs in queue and we haven't finished the date range, generate more
        if not self._url_queue and self._current_date and self.date_end:
            end_date = datetime.strptime(  # noqa: DTZ007
                self.date_end, "%Y-%m-%d"
            ).date()
            if self._current_date < end_date:
                self._current_date += timedelta(days=1)
                self._current_cursor = "*"  # Reset cursor for new date
                await self._generate_urls_for_current_date()

        # Save state after processing
        await self._save_persistence_state()

    async def handle_url_error(self, request: RequestMeta, error: str) -> None:
        """Handle when a URL processing fails."""
        await self._save_error_state(request, error)
        await self._save_persistence_state()

    async def _initialize(self) -> None:
        """Initialize the provider with the date range."""
        try:
            start_date = datetime.strptime(  # noqa: DTZ007
                self.date_start, "%Y-%m-%d"
            ).date()
            end_date = (
                datetime.strptime(self.date_end, "%Y-%m-%d").date()  # noqa: DTZ007
                if self.date_end
                else datetime.now(tz=timezone.utc).date()
            )

            if self._current_date is None:
                self._current_date = start_date

            # Generate initial URLs for the date range
            await self._generate_urls_for_current_date()

            self._initialized = True
            logger.info(
                "Initialized API provider",
                date_start=start_date,
                date_end=end_date,
                base_url=self.base_url,
            )

        except Exception as e:
            logger.exception(
                "Error initializing API provider", base_url=self.base_url, error=str(e)
            )
            raise

    async def _generate_urls_for_current_date(self) -> None:
        """Generate URLs for the current date."""
        if not self._current_date:
            return

        date_str = self._current_date.strftime("%Y-%m-%d")

        # Apply date filter if provided
        if self.date_filter and not self.date_filter(date_str):
            return

        # Build query parameters
        params = {
            "nombre": str(self.max_records_per_page),
            "curseur": self._current_cursor,
        }

        # Use custom query builder if provided, otherwise use default
        if self.query_builder:
            params["q"] = self.query_builder(date_str)
        else:
            # Default query format
            params["q"] = f"date:[{date_str}T00:00:00%20TO%20{date_str}T23:59:59]"

        # Add additional query parameters
        if self.query_params:
            params.update(self.query_params)

        # Build URL
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        url = f"{self.base_url}?{query_string}"

        self._url_queue.append(url)

    async def _generate_next_urls(self, _ctx: FetchRunContext) -> None:
        """Generate next URLs based on pagination or date progression."""
        # This would be called after processing a response to determine if we need more URLs
        # For now, we'll implement a simple date progression
        if (
            self._current_date
            and self.date_end
            and self._current_date
            < datetime.strptime(self.date_end, "%Y-%m-%d").date()  # noqa: DTZ007
        ):
            self._current_date += timedelta(days=1)
            self._current_cursor = "*"  # Reset cursor for new date
            await self._generate_urls_for_current_date()

    async def _wait_for_rate_limit(self) -> None:
        """Wait if rate limit would be exceeded."""
        async with self._rate_limit_lock:
            now = asyncio.get_event_loop().time()
            time_since_last = now - self._last_request_time
            min_interval = 1.0 / self.rate_limit_requests_per_second

            if time_since_last < min_interval:
                await asyncio.sleep(min_interval - time_since_last)

            self._last_request_time = asyncio.get_event_loop().time()


@dataclass
class SingleApiBundleLocator:
    """Bundle locator for single API endpoints."""

    http_manager: HttpManager
    urls: list[str]
    headers: dict[str, str] | None = None
    persistence_prefix: str = "single_api_provider"

    def __post_init__(self) -> None:
        """Initialize the single API bundle locator state and internal variables."""
        self._processed_urls: set[str] = set()
        self._url_queue: list[str] = self.urls.copy()
        self._store: KeyValueStore | None = None

    async def _get_store(self) -> KeyValueStore:
        """Get the key-value store instance."""
        if self._store is None:
            self._store = await get_global_store()
        return self._store

    async def _load_persistence_state(self) -> None:
        """Load persistence state from kvstore."""
        store = await self._get_store()

        # Load processed URLs
        processed_urls_key = f"{self.persistence_prefix}:processed_urls"
        processed_urls_data = await store.get(processed_urls_key, [])
        if isinstance(processed_urls_data, list):
            self._processed_urls = set(processed_urls_data)
        else:
            self._processed_urls = set()

        # Filter out already processed URLs from queue
        self._url_queue = [
            url for url in self._url_queue if url not in self._processed_urls
        ]

    async def _save_persistence_state(self) -> None:
        """Save persistence state to kvstore."""
        store = await self._get_store()

        # Save processed URLs
        processed_urls_key = f"{self.persistence_prefix}:processed_urls"
        await store.put(
            processed_urls_key, list(self._processed_urls), ttl=timedelta(days=7)
        )

    async def _save_processing_result(
        self,
        request: RequestMeta,
        bundle_refs: list[BundleRef],
        *,
        success: bool = True,
    ) -> None:
        """Save processing result to kvstore."""
        store = await self._get_store()

        result_key = f"{self.persistence_prefix}:results:{hash(request.url)}"
        result_data = {
            "url": request.url,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success": success,
            "bundle_count": len(bundle_refs),
            "bundle_refs": [str(ref) for ref in bundle_refs],
        }
        await store.put(result_key, result_data, ttl=timedelta(days=30))

    async def get_next_urls(self, _ctx: FetchRunContext) -> list[RequestMeta]:
        """Get the next batch of API URLs to process."""
        # Load persistence state on first call
        if not self._processed_urls:
            await self._load_persistence_state()

        urls: list[RequestMeta] = []
        BATCH_SIZE = 10  # noqa: N806
        while self._url_queue and len(urls) < BATCH_SIZE:  # Batch size
            url = self._url_queue.pop(0)
            if url not in self._processed_urls:
                urls.append(RequestMeta(url=url, headers=self.headers or {}))
                self._processed_urls.add(url)

        # Save state after generating URLs
        await self._save_persistence_state()
        return urls

    async def handle_url_processed(
        self, request: RequestMeta, bundle_refs: list[BundleRef], _ctx: FetchRunContext
    ) -> None:
        """Handle when a URL has been processed."""
        # Mark as processed
        self._processed_urls.add(request.url)

        # Save processing result
        await self._save_processing_result(request, bundle_refs, success=True)

        # Save state after processing
        await self._save_persistence_state()

    async def handle_url_error(self, request: RequestMeta, error: str) -> None:
        """Handle when a URL processing fails."""
        store = await self._get_store()

        error_key = f"{self.persistence_prefix}:errors:{hash(request.url)}"
        error_data = {
            "url": request.url,
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "retry_count": 0,
        }
        await store.put(error_key, error_data, ttl=timedelta(hours=24))
