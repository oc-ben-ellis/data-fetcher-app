"""Factory functions for creating framework components.

This module provides factory functions to create and configure various framework
components including SFTP managers, loaders, and data providers.
"""

from collections.abc import Callable
from typing import Any

from data_fetcher_core.credentials import CredentialProvider, SftpCredentialsWrapper
from data_fetcher_core.global_credential_provider import get_default_credential_provider
from data_fetcher_http.http_manager import HttpManager
from data_fetcher_http_api.api_bundle_locators import (
    ApiPaginationBundleLocator,
    SingleApiBundleLocator,
)
from data_fetcher_http_api.api_generic_bundle_locators import (
    GenericDirectoryBundleLocator,
    GenericFileBundleLocator,
)
from data_fetcher_http_api.api_loader import ApiLoader, TrackingApiLoader
from data_fetcher_http_api.api_pagination_bundle_locators import (
    ComplexPaginationBundleLocator,
    CursorPaginationStrategy,
    ReversePaginationBundleLocator,
)
from data_fetcher_sftp.authentication import (
    AuthenticationMechanism,
)
from data_fetcher_sftp.sftp_loader import SFTPLoader
from data_fetcher_sftp.sftp_manager import SftpManager

"""
Factory methods for creating fetcher components.
"""


def create_sftp_manager(
    config_name: str,
    connect_timeout: float = 20.0,
    rate_limit_requests_per_second: float = 2.0,
    credential_provider: CredentialProvider | None = None,
) -> SftpManager:
    """Create an SFTP manager with dynamic credentials."""
    if credential_provider is None:
        credential_provider = get_default_credential_provider()

    credentials_provider = SftpCredentialsWrapper(config_name, credential_provider)

    return SftpManager(
        credentials_provider=credentials_provider,
        connect_timeout=connect_timeout,
        rate_limit_requests_per_second=rate_limit_requests_per_second,
    )


def create_sftp_loader(
    sftp_manager: SftpManager,
    meta_load_name: str = "sftp_loader",
) -> SFTPLoader:
    """Create an SFTP loader with the given SFTP manager."""
    return SFTPLoader(
        sftp_manager=sftp_manager,
        meta_load_name=meta_load_name,
    )


def create_directory_provider(
    sftp_manager: SftpManager,
    remote_dir: str,
    filename_pattern: str = "*",
    max_files: int | None = None,
    file_filter: Callable[[str], bool] | None = None,
    sort_key: Callable[[str, float | int | None], Any] | None = None,
    *,
    sort_reverse: bool = True,
) -> GenericDirectoryBundleLocator:
    """Create a generic directory bundle locator."""
    return GenericDirectoryBundleLocator(
        sftp_manager=sftp_manager,
        remote_dir=remote_dir,
        filename_pattern=filename_pattern,
        max_files=max_files,
        file_filter=file_filter,
        sort_key=sort_key,
        sort_reverse=sort_reverse,
    )


def create_file_provider(
    sftp_manager: SftpManager,
    file_paths: list[str],
) -> GenericFileBundleLocator:
    """Create a generic file bundle locator."""
    return GenericFileBundleLocator(
        sftp_manager=sftp_manager,
        file_paths=file_paths,
    )


def create_http_manager(
    timeout: float = 30.0,
    rate_limit_requests_per_second: float = 10.0,
    max_retries: int = 3,
    default_headers: dict[str, str] | None = None,
    authentication_mechanism: AuthenticationMechanism | None = None,
) -> HttpManager:
    """Create an HTTP manager with the given configuration."""
    return HttpManager(
        timeout=timeout,
        rate_limit_requests_per_second=rate_limit_requests_per_second,
        max_retries=max_retries,
        default_headers=default_headers,
        authentication_mechanism=authentication_mechanism,
    )


def create_api_loader(
    http_manager: HttpManager,
    meta_load_name: str = "api_loader",
    error_handler: Callable[[str, int], bool] | None = None,
) -> ApiLoader:
    """Create a generic API loader."""
    return ApiLoader(
        http_manager=http_manager,
        meta_load_name=meta_load_name,
        error_handler=error_handler,
    )


def create_tracking_api_loader(
    http_manager: HttpManager,
    meta_load_name: str = "tracking_api_loader",
    error_handler: Callable[[str, int], bool] | None = None,
) -> TrackingApiLoader:
    """Create a tracking API loader that tracks failed requests."""
    return TrackingApiLoader(
        http_manager=http_manager,
        meta_load_name=meta_load_name,
        error_handler=error_handler,
    )


def create_api_pagination_provider(
    http_manager: HttpManager,
    base_url: str,
    date_start: str,
    date_end: str | None = None,
    max_records_per_page: int = 1000,
    rate_limit_requests_per_second: float = 2.0,
    query_params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    query_builder: Callable[[str], str] | None = None,
) -> ApiPaginationBundleLocator:
    """Create a generic API pagination bundle locator."""
    return ApiPaginationBundleLocator(
        http_manager=http_manager,
        base_url=base_url,
        date_start=date_start,
        date_end=date_end,
        max_records_per_page=max_records_per_page,
        rate_limit_requests_per_second=rate_limit_requests_per_second,
        query_params=query_params,
        headers=headers,
        query_builder=query_builder,
    )


def create_single_api_provider(
    http_manager: HttpManager,
    urls: list[str],
    headers: dict[str, str] | None = None,
    persistence_prefix: str = "single_api_provider",
) -> SingleApiBundleLocator:
    """Create a single API bundle locator for specific URLs."""
    return SingleApiBundleLocator(
        http_manager=http_manager,
        urls=urls,
        headers=headers,
        persistence_prefix=persistence_prefix,
    )


def create_complex_pagination_provider(
    http_manager: HttpManager,
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
    persistence_prefix: str = "complex_pagination_provider",
) -> ComplexPaginationBundleLocator:
    """Create a complex pagination bundle locator with configurable strategies."""
    return ComplexPaginationBundleLocator(
        http_manager=http_manager,
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
        persistence_prefix=persistence_prefix,
    )


def create_reverse_pagination_provider(
    http_manager: HttpManager,
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
    persistence_prefix: str = "reverse_pagination_provider",
) -> ReversePaginationBundleLocator:
    """Create a reverse pagination bundle locator for gap filling."""
    return ReversePaginationBundleLocator(
        http_manager=http_manager,
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
        persistence_prefix=persistence_prefix,
    )
