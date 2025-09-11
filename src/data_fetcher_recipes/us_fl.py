"""US Florida SFTP fetcher recipe.

This module provides the recipe for fetching data from the US Florida
SFTP server, including business registration and licensing data.
"""

from collections.abc import Callable

import structlog

from data_fetcher_core.core import FetcherRecipe, create_fetcher_config
from data_fetcher_core.factory import create_sftp_loader, create_sftp_protocol_config
from data_fetcher_core.recipebook import register_recipe
from data_fetcher_sftp.sftp_bundle_locators import (
    DirectorySftpBundleLocator,
    FileSftpBundleLocator,
)

# Get logger for this module
logger = structlog.get_logger(__name__)

"""
US Florida SFTP recipe setup.
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
                    logger.info("FILE_PASSED_DATE_FILTER", filename=filename, date_str=date_str)
                    return True
                return False
        except Exception as e:
            # If we can't parse the date, process the file
            logger.exception(
                "ERROR_PARSING_DATE_IN_FILENAME_SKIPPING_FILE",
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


def _setup_us_fl_sftp_fetcher() -> FetcherRecipe:
    """US Florida SFTP fetcher using generic providers with US FL specific logic."""
    # Create SFTP protocol configuration
    sftp_config = create_sftp_protocol_config(
        config_name="us-fl",
        connect_timeout=20.0,
        rate_limit_requests_per_second=2.0,
    )

    # Create loader
    loader = create_sftp_loader(
        sftp_config=sftp_config,
        meta_load_name="us_fl_sftp_loader",
    )

    # Create US FL specific file filter
    daily_file_filter = _create_us_fl_daily_file_filter("20230728")

    # Create bundle locators using generic locators with persistence
    # The store will be obtained from FetchRunContext during execution
    daily_provider = DirectorySftpBundleLocator(
        sftp_config=sftp_config,
        remote_dir="doc/cor",
        filename_pattern="*.txt",
        max_files=None,
        file_filter=daily_file_filter,
        # Sort by modification time (newest first)
        sort_key=lambda _file_path, mtime: mtime,
        sort_reverse=True,
        state_management_prefix="us_fl_daily_provider",
    )

    quarterly_provider = FileSftpBundleLocator(
        sftp_config=sftp_config,
        file_paths=["doc/Quarterly/Cor/cordata.zip"],
        state_management_prefix="us_fl_quarterly_provider",
    )

    # Build configuration
    return (
        create_fetcher_config()
        .with_recipe_id("us-fl")
        .use_bundle_loader(loader)
        .add_bundle_locator(daily_provider)
        .add_bundle_locator(quarterly_provider)
        .build()
    )

# Register the recipe
register_recipe("us-fl", _setup_us_fl_sftp_fetcher)
