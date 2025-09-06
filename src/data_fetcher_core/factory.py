"""Factory functions for creating framework components.

This module provides factory functions to create and configure various framework
components including SFTP managers, loaders, and data providers.
"""

from collections.abc import Callable
from typing import Any

# Removed global credential provider import - will be passed explicitly
from data_fetcher_core.protocol_config import SftpProtocolConfig
from data_fetcher_sftp.sftp_bundle_locators import (
    DirectorySftpBundleLocator,
    FileSftpBundleLocator,
)
from data_fetcher_sftp.sftp_loader import SftpBundleLoader
from data_fetcher_sftp.sftp_manager import SftpManager

"""
Factory methods for creating fetcher components.
"""


def create_sftp_protocol_config(
    config_name: str,
    connect_timeout: float = 20.0,
    rate_limit_requests_per_second: float = 2.0,
    max_retries: int = 3,
    base_retry_delay: float = 1.0,
    max_retry_delay: float = 60.0,
    retry_exponential_base: float = 2.0,
) -> SftpProtocolConfig:
    """Create an SFTP protocol configuration with the given settings.

    Args:
        config_name: Configuration name for credentials.
        connect_timeout: Connection timeout in seconds.
        rate_limit_requests_per_second: Rate limit for requests.
        max_retries: Maximum number of retries.
        base_retry_delay: Base delay for retries.
        max_retry_delay: Maximum delay for retries.
        retry_exponential_base: Exponential base for retry delays.
    """
    return SftpProtocolConfig(
        config_name=config_name,
        connect_timeout=connect_timeout,
        rate_limit_requests_per_second=rate_limit_requests_per_second,
        max_retries=max_retries,
        base_retry_delay=base_retry_delay,
        max_retry_delay=max_retry_delay,
        retry_exponential_base=retry_exponential_base,
    )


def create_sftp_manager() -> SftpManager:
    """Create an SFTP manager instance."""
    return SftpManager()


def create_sftp_loader(
    sftp_config: SftpProtocolConfig,
    meta_load_name: str = "sftp_loader",
) -> SftpBundleLoader:
    """Create an SFTP loader with the given SFTP protocol configuration."""
    return SftpBundleLoader(
        sftp_config=sftp_config,
        meta_load_name=meta_load_name,
    )


def create_directory_provider(
    sftp_config: SftpProtocolConfig,
    remote_dir: str,
    filename_pattern: str = "*",
    max_files: int | None = None,
    file_filter: Callable[[str], bool] | None = None,
    sort_key: Callable[[str, float | int | None], Any] | None = None,
    *,
    sort_reverse: bool = True,
) -> DirectorySftpBundleLocator:
    """Create a directory SFTP bundle locator."""
    return DirectorySftpBundleLocator(
        sftp_config=sftp_config,
        remote_dir=remote_dir,
        filename_pattern=filename_pattern,
        max_files=max_files,
        file_filter=file_filter,
        sort_key=sort_key,
        sort_reverse=sort_reverse,
    )


def create_file_provider(
    sftp_config: SftpProtocolConfig,
    file_paths: list[str],
) -> FileSftpBundleLocator:
    """Create a file SFTP bundle locator."""
    return FileSftpBundleLocator(
        sftp_config=sftp_config,
        file_paths=file_paths,
    )
