"""France API fetcher recipe.

This module provides the recipe for fetching data from French government
APIs, including SIRENE business registry data and related endpoints.
"""

import datetime
import os
from collections.abc import Callable
from datetime import timedelta
from typing import Protocol

import structlog

# Removed global credential provider import - will be passed via app_config
from data_fetcher_core.core import FetcherRecipe, create_fetcher_config
from data_fetcher_core.recipebook import register_recipe
from data_fetcher_http.factory import create_http_protocol_config
from data_fetcher_http_api.api_pagination_bundle_locators import (
    CursorPaginationStrategy,
)
from data_fetcher_http_api.factory import (
    create_complex_pagination_http_bundle_locator,
    create_reverse_pagination_http_bundle_locator,
    create_single_http_bundle_locator,
    create_tracking_http_bundle_loader,
)
from data_fetcher_sftp.authentication import OAuthAuthenticationMechanism

"""
French INSEE API recipe setup.
"""

# Get logger for this module
logger = structlog.get_logger(__name__)


def _create_fr_date_filter(start_date: str) -> Callable[[str], bool]:
    """Create a date filter for FR API based on start date."""

    def filter_function(date_str: str) -> bool:
        """Check if date should be processed based on start date."""
        try:
            return date_str >= start_date
        except Exception as e:
            # If we can't parse the date, process it
            logger.exception(
                "DATE_PARSING_ERROR_CONTINUING",
                error=str(e),
                date_str=date_str,
                start_date=start_date,
            )
            return True

    return filter_function


class QueryBuilder(Protocol):
    """Protocol for query builder function."""

    def __call__(self, date_str: str, narrowing: str | None = None) -> str:
        """Build a query string with date and optional narrowing parameters.

        Args:
            date_str: Date string in YYYY-MM-DD format
            narrowing: Optional narrowing parameter for the query

        Returns:
            Formatted query string for the API
        """
        ...


def _create_sirene_query_builder() -> QueryBuilder:
    """Create a query builder for Sirene API."""

    def query_builder(date_str: str, narrowing: str | None = None) -> str:
        """Build Sirene API query with date and optional narrowing."""
        base_query = f"dateDernierTraitementUniteLegale:[{date_str}T00:00:00%20TO%20{date_str}T23:59:59]"

        if narrowing:
            # Handle SIREN prefix narrowing
            if narrowing.startswith("siren:"):
                return f"{narrowing}* AND -periode(categorieJuridiqueUniteLegale:1000) AND statutDiffusionUniteLegale:O AND {base_query}"
            return f"{narrowing} AND -periode(categorieJuridiqueUniteLegale:1000) AND statutDiffusionUniteLegale:O AND {base_query}"
        return f"-periode(categorieJuridiqueUniteLegale:1000) AND statutDiffusionUniteLegale:O AND {base_query}"

    return query_builder


def _create_siren_narrowing_strategy() -> Callable[[str | None], str]:
    """Create a SIREN narrowing strategy."""
    PREFIX_LENGTH = 2  # noqa: N806
    PREFIX_SUFFIX = "9"  # noqa: N806

    def narrowing_strategy(current_narrowing: str | None = None) -> str:
        """Create SIREN prefix for narrowing search."""
        if current_narrowing is None:
            return "siren:00"
        if current_narrowing == "siren:99":
            return "siren:99"  # This will trigger date increment
        # Extract the numeric part and increment
        prefix_value = current_narrowing.split(":", 1)[1]
        if len(prefix_value) == PREFIX_LENGTH:
            new_value = str(int(prefix_value) + 1).zfill(PREFIX_LENGTH)
        elif prefix_value.endswith(PREFIX_SUFFIX):
            new_value = str(int(prefix_value[:-1]) + 1).zfill(len(prefix_value) - 1)
        else:
            new_value = str(int(prefix_value) + 1).zfill(len(prefix_value))
        return f"siren:{new_value}"

    return narrowing_strategy


def _create_sirene_error_handler() -> Callable[[str, int], bool]:
    """Create an error handler for Sirene API."""
    HTTP_STATUS_OK = 200  # noqa: N806
    HTTP_STATUS_NOT_FOUND = 404  # noqa: N806
    HTTP_STATUS_SERVER_ERROR = 500  # noqa: N806
    HTTP_STATUS_SERVICE_UNAVAILABLE = 503  # noqa: N806
    HTTP_STATUS_GATEWAY_TIMEOUT = 504  # noqa: N806
    HTTP_STATUS_FORBIDDEN = 403  # noqa: N806

    def error_handler(url: str, status_code: int) -> bool:
        """Handle Sirene API errors."""
        if status_code == HTTP_STATUS_NOT_FOUND:
            logger.warning("NO_ITEMS_FOUND", url=url)
            return False
        if status_code in [
            HTTP_STATUS_SERVER_ERROR,
            HTTP_STATUS_SERVICE_UNAVAILABLE,
            HTTP_STATUS_GATEWAY_TIMEOUT,
            HTTP_STATUS_FORBIDDEN,
        ]:
            logger.exception("SERVER_ERROR", url=url, status_code=status_code)
            return False
        if status_code != HTTP_STATUS_OK:
            logger.exception("UNEXPECTED_STATUS_CODE", url=url, status_code=status_code)
            return False
        return True

    return error_handler


def _setup_fr_api_fetcher(
    token_url: str | None = None,
    base_url: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> FetcherRecipe:
    """French INSEE API fetcher using generic API providers with OAuth authentication."""
    # Use provided token URL or environment variable or default to INSEE API
    if token_url is None:
        token_url = os.getenv("OC_FR_TOKEN_URL", "https://api.insee.fr/token")

    # Use provided base URL or environment variable or default to INSEE API
    if base_url is None:
        base_url = os.getenv(
            "OC_FR_API_BASE_URL", "https://api.insee.fr/entreprises/sirene/V3.11/siren"
        )

    # Create OAuth authentication mechanism
    # The credential provider will be passed to authenticate_request method
    oauth_auth = OAuthAuthenticationMechanism(
        token_url=token_url,
        config_name="fr",
    )

    # Create HTTP protocol configuration with OAuth authentication
    http_config = create_http_protocol_config(
        timeout=120.0,  # Longer timeout for API calls
        rate_limit_requests_per_second=2.0,  # Conservative rate limiting
        max_retries=5,
        default_headers={
            "User-Agent": "OCFetcher/1.0",
            "Accept": "application/json",
        },
        authentication_mechanism=oauth_auth,
    )

    # Create Sirene API loader with error handling
    loader = create_tracking_http_bundle_loader(
        http_config=http_config,
        meta_load_name="fr_sirene_api_loader",
        error_handler=_create_sirene_error_handler(),
    )

    # Calculate date range (use provided dates or default to last 5 days)
    if end_date is None:
        end_date = datetime.datetime.now(tz=datetime.UTC).date().strftime("%Y-%m-%d")
    if start_date is None:
        end_date_obj = (
            datetime.datetime.now(tz=datetime.UTC).date()
            if isinstance(end_date, str)
            else end_date
        )
        start_date_obj = end_date_obj - timedelta(days=5)
        start_date = start_date_obj.strftime("%Y-%m-%d")

    # Create date filter
    _create_fr_date_filter(start_date)

    # Create Sirene-specific pagination strategy
    sirene_pagination_strategy = CursorPaginationStrategy(
        cursor_field="curseurSuivant",
        total_field="total",
        count_field="nombre",
        max_records=20000,
    )

    # Create main Sirene API provider for SIREN data with complex pagination logic
    siren_provider = create_complex_pagination_http_bundle_locator(
        http_config=http_config,
        base_url=base_url,
        date_start=start_date,
        date_end=end_date,
        max_records_per_page=1000,
        rate_limit_requests_per_second=2.0,
        headers={
            "Accept": "application/json",
        },
        query_builder=_create_sirene_query_builder(),
        pagination_strategy=sirene_pagination_strategy,
        narrowing_strategy=_create_siren_narrowing_strategy(),
        state_management_prefix="fr_siren_provider",
    )

    # Create gap-filling provider for historical data
    # This would be used to fill gaps in data collection
    # For testing, use a very short range; for production, this could be much longer
    gap_start_date = start_date
    gap_end_date = end_date

    gap_provider = create_reverse_pagination_http_bundle_locator(
        http_config=http_config,
        base_url=base_url,
        date_start=gap_start_date,
        date_end=gap_end_date,
        max_records_per_page=1000,
        rate_limit_requests_per_second=2.0,
        headers={
            "Accept": "application/json",
        },
        query_builder=_create_sirene_query_builder(),
        pagination_strategy=sirene_pagination_strategy,
        narrowing_strategy=_create_siren_narrowing_strategy(),
        state_management_prefix="fr_gap_provider",
    )

    # Create provider for failed company numbers (if any)
    # This would be populated with company numbers that failed to process
    failed_companies_provider = create_single_http_bundle_locator(
        http_config=http_config,
        urls=[],  # Empty initially, would be populated with failed company URLs
        headers={
            "Accept": "application/json",
        },
        state_management_prefix="fr_failed_companies_provider",
    )

    # Build configuration
    recipe = (
        create_fetcher_config()
        .use_bundle_loader(loader)
        .add_bundle_locator(siren_provider)
        .add_bundle_locator(gap_provider)
        .add_bundle_locator(failed_companies_provider)
        .build()
    )

    # Add recipe_id to the recipe
    recipe.recipe_id = "fr"
    return recipe


def _setup_fr_api_fetcher_wrapper() -> FetcherRecipe:
    """Wrapper function that creates a store and calls the main setup function."""
    return _setup_fr_api_fetcher()


# Register the recipe
register_recipe("fr", _setup_fr_api_fetcher_wrapper)
