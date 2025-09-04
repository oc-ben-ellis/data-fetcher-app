"""US Florida SFTP fetcher configuration.

This module provides the configuration for fetching data from the US Florida
SFTP server, including business registration and licensing data.
"""

from collections.abc import Callable

import structlog

from data_fetcher.bundle_locators.api_generic_bundle_locators import (
    GenericDirectoryBundleLocator,
    GenericFileBundleLocator,
)
from data_fetcher.core import FetchContext, create_fetcher_config
from data_fetcher.factory import create_sftp_loader, create_sftp_manager
from data_fetcher.registry import register_configuration

# Get logger for this module
logger = structlog.get_logger(__name__)

"""
US Florida SFTP configuration setup.
"""


def _create_us_fl_daily_file_filter(start_date: str) -> Callable[[str], bool]:
    """Create a file filter for US FL daily files based on start date."""
    DATE_LENGTH = 8  # noqa: N806

    def filter_function(filename: str) -> bool:
        """Check if daily file should be processed based on start date."""
        # Extract date from filename (assuming format like YYYYMMDD_*.txt)
        try:
            # Look for date pattern in filename
            for i in range(len(filename) - (DATE_LENGTH - 1)):
                date_str = filename[i : i + DATE_LENGTH]
                if (
                    date_str.isdigit()
                    and len(date_str) == DATE_LENGTH
                    and date_str >= start_date
                ):
                    return True
        except Exception as e:
            # If we can't parse the date, process the file
            logger.exception(
                "Error parsing date in filename, skipping file",
                error=str(e),
                filename=filename,
                start_date=start_date,
            )
        else:
            # No date found or date is before start_date
            return False

        # If we get here, an exception occurred, so skip the file
        return False

    return filter_function


def _setup_us_fl_sftp_fetcher() -> FetchContext:
    """US Florida SFTP fetcher using generic providers with US FL specific logic."""
    # Create SFTP manager with dynamic credentials
    sftp_manager = create_sftp_manager(
        config_name="us-fl",
        connect_timeout=20.0,
        rate_limit_requests_per_second=2.0,
    )

    # Create loader
    loader = create_sftp_loader(
        sftp_manager=sftp_manager,
        meta_load_name="us_fl_sftp_loader",
    )

    # Create US FL specific file filter
    daily_file_filter = _create_us_fl_daily_file_filter("20230728")

    # Create bundle locators using generic locators with persistence
    daily_provider = GenericDirectoryBundleLocator(
        sftp_manager=sftp_manager,
        remote_dir="doc/cor",
        filename_pattern="*.txt",
        max_files=None,
        file_filter=daily_file_filter,
        # Sort by modification time (newest first)
        sort_key=lambda _file_path, mtime: mtime,
        sort_reverse=True,
        persistence_prefix="us_fl_daily_provider",
    )

    quarterly_provider = GenericFileBundleLocator(
        sftp_manager=sftp_manager,
        file_paths=["doc/Quarterly/Cor/cordata.zip"],
        persistence_prefix="us_fl_quarterly_provider",
    )

    # Build configuration
    return (
        create_fetcher_config()
        .use_bundle_loader(loader)
        .add_bundle_locator(daily_provider)
        .add_bundle_locator(quarterly_provider)
        .build()
    )


# Register the configuration
register_configuration("us-fl", _setup_us_fl_sftp_fetcher)
