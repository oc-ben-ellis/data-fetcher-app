"""Factory functions for creating HTTP API components.

This module provides factory functions to create and configure HTTP API
components including bundle locators and loaders.
"""

from collections.abc import Callable
from typing import Any

from data_fetcher_core.kv_store import KeyValueStore
from data_fetcher_core.kv_store.factory import create_kv_store
from data_fetcher_http.http_config import HttpProtocolConfig
from data_fetcher_http_api.api_bundle_locators import (
    PaginationHttpBundleLocator,
    SingleHttpBundleLocator,
)
from data_fetcher_http_api.api_loader import HttpBundleLoader, TrackingHttpBundleLoader
from data_fetcher_http_api.api_pagination_bundle_locators import (
    ComplexPaginationHttpBundleLocator,
    CursorPaginationStrategy,
    ReversePaginationHttpBundleLocator,
)


def create_pagination_http_bundle_locator(
    http_config: HttpProtocolConfig,
    store: KeyValueStore,
    base_url: str,
    date_start: str,
    date_end: str | None = None,
    max_records_per_page: int = 1000,
    rate_limit_requests_per_second: float = 2.0,
    query_params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    query_builder: Callable[[str], str] | None = None,
) -> PaginationHttpBundleLocator:
    """Create a generic API pagination bundle locator.

    Args:
        http_config: HTTP protocol configuration.
        store: Key-value store for state management.
        base_url: Base URL for the API.
        date_start: Start date for data fetching.
        date_end: End date for data fetching. Defaults to None.
        max_records_per_page: Maximum records per page. Defaults to 1000.
        rate_limit_requests_per_second: Rate limit for requests. Defaults to 2.0.
        query_params: Additional query parameters. Defaults to None.
        headers: HTTP headers. Defaults to None.
        query_builder: Function to build query strings. Defaults to None.

    Returns:
        Configured PaginationHttpBundleLocator instance.
    """
    return PaginationHttpBundleLocator(
        http_config=http_config,
        store=store,
        base_url=base_url,
        date_start=date_start,
        date_end=date_end,
        max_records_per_page=max_records_per_page,
        rate_limit_requests_per_second=rate_limit_requests_per_second,
        query_params=query_params,
        headers=headers,
        query_builder=query_builder,
    )


def create_single_http_bundle_locator(
    http_config: HttpProtocolConfig,
    urls: list[str],
    headers: dict[str, str] | None = None,
    state_management_prefix: str = "single_http_bundle_locator",
    store: KeyValueStore | None = None,
) -> SingleHttpBundleLocator:
    """Create a single HTTP bundle locator for processing specific URLs.

    Args:
        http_config: HTTP protocol configuration.
        urls: List of URLs to process.
        headers: HTTP headers. Defaults to None.
        state_management_prefix: Prefix for state management. Defaults to "single_http_bundle_locator".
        store: Key-value store for state management. Defaults to None.

    Returns:
        Configured SingleHttpBundleLocator instance.
    """
    # Create a temporary in-memory store if none provided
    if store is None:
        store = create_kv_store(store_type="memory")

    return SingleHttpBundleLocator(
        http_config=http_config,
        urls=urls,
        headers=headers,
        store=store,
        persistence_prefix=state_management_prefix,
    )


def create_complex_pagination_http_bundle_locator(
    http_config: HttpProtocolConfig,
    base_url: str,
    date_start: str,
    date_end: str | None = None,
    max_records_per_page: int = 1000,
    rate_limit_requests_per_second: float = 2.0,
    query_params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    query_builder: Callable[[str, str | None], str] | None = None,
    pagination_strategy: CursorPaginationStrategy | None = None,
    narrowing_strategy: Callable[[str], str] | None = None,
    state_management_prefix: str = "complex_pagination_http_bundle_locator",
    store: KeyValueStore | None = None,
) -> ComplexPaginationHttpBundleLocator:
    """Create a complex pagination bundle locator with configurable strategies.

    Args:
        http_config: HTTP protocol configuration.
        base_url: Base URL for the API.
        date_start: Start date for data fetching.
        date_end: End date for data fetching. Defaults to None.
        max_records_per_page: Maximum records per page. Defaults to 1000.
        rate_limit_requests_per_second: Rate limit for requests. Defaults to 2.0.
        query_params: Additional query parameters. Defaults to None.
        headers: HTTP headers. Defaults to None.
        query_builder: Function to build query strings. Defaults to None.
        pagination_strategy: Pagination strategy. Defaults to None.
        narrowing_strategy: Narrowing strategy. Defaults to None.
        state_management_prefix: Prefix for state management. Defaults to "complex_pagination_http_bundle_locator".
        store: Key-value store for state management. Defaults to None.

    Returns:
        Configured ComplexPaginationHttpBundleLocator instance.
    """
    # Create a temporary in-memory store if none provided
    if store is None:
        store = create_kv_store(store_type="memory")

    return ComplexPaginationHttpBundleLocator(
        http_config=http_config,
        store=store,
        base_url=base_url,
        date_start=date_start,
        date_end=date_end,
        max_records_per_page=max_records_per_page,
        rate_limit_requests_per_second=rate_limit_requests_per_second,
        query_params=query_params,
        headers=headers,
        query_builder=query_builder,
        pagination_strategy=pagination_strategy,
        narrowing_strategy=narrowing_strategy,
        state_management_prefix=state_management_prefix,
    )


def create_reverse_pagination_http_bundle_locator(
    http_config: HttpProtocolConfig,
    base_url: str,
    date_start: str,
    date_end: str | None = None,
    max_records_per_page: int = 1000,
    rate_limit_requests_per_second: float = 2.0,
    query_params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    query_builder: Callable[[str, str | None], str] | None = None,
    pagination_strategy: CursorPaginationStrategy | None = None,
    narrowing_strategy: Callable[[str], str] | None = None,
    state_management_prefix: str = "reverse_pagination_http_bundle_locator",
    store: KeyValueStore | None = None,
) -> ReversePaginationHttpBundleLocator:
    """Create a reverse pagination bundle locator with configurable strategies.

    Args:
        http_config: HTTP protocol configuration.
        base_url: Base URL for the API.
        date_start: Start date for data fetching.
        date_end: End date for data fetching. Defaults to None.
        max_records_per_page: Maximum records per page. Defaults to 1000.
        rate_limit_requests_per_second: Rate limit for requests. Defaults to 2.0.
        query_params: Additional query parameters. Defaults to None.
        headers: HTTP headers. Defaults to None.
        query_builder: Function to build query strings. Defaults to None.
        pagination_strategy: Pagination strategy. Defaults to None.
        narrowing_strategy: Narrowing strategy. Defaults to None.
        state_management_prefix: Prefix for state management. Defaults to "reverse_pagination_http_bundle_locator".
        store: Key-value store for state management. Defaults to None.

    Returns:
        Configured ReversePaginationHttpBundleLocator instance.
    """
    # Create a temporary in-memory store if none provided
    if store is None:
        store = create_kv_store(store_type="memory")

    return ReversePaginationHttpBundleLocator(
        http_config=http_config,
        store=store,
        base_url=base_url,
        date_start=date_start,
        date_end=date_end,
        max_records_per_page=max_records_per_page,
        rate_limit_requests_per_second=rate_limit_requests_per_second,
        query_params=query_params,
        headers=headers,
        query_builder=query_builder,
        pagination_strategy=pagination_strategy,
        narrowing_strategy=narrowing_strategy,
        state_management_prefix=state_management_prefix,
    )


def create_http_bundle_loader(
    http_config: HttpProtocolConfig,
    meta_load_name: str = "http_bundle_loader",
) -> HttpBundleLoader:
    """Create a basic HTTP bundle loader.

    Args:
        http_config: HTTP protocol configuration.
        meta_load_name: Name for metadata tracking. Defaults to "http_bundle_loader".

    Returns:
        Configured HttpBundleLoader instance.
    """
    return HttpBundleLoader(
        http_config=http_config,
        meta_load_name=meta_load_name,
    )


def create_tracking_http_bundle_loader(
    http_config: HttpProtocolConfig,
    meta_load_name: str = "tracking_http_bundle_loader",
    error_handler: Callable[[str, int], bool] | None = None,
) -> TrackingHttpBundleLoader:
    """Create a tracking HTTP bundle loader with error handling capabilities.

    Args:
        http_config: HTTP protocol configuration.
        meta_load_name: Name for metadata tracking. Defaults to "tracking_http_bundle_loader".
        error_handler: Function to handle HTTP errors. Defaults to None.

    Returns:
        Configured TrackingHttpBundleLoader instance.
    """
    return TrackingHttpBundleLoader(
        http_config=http_config,
        meta_load_name=meta_load_name,
        error_handler=error_handler,
    )
