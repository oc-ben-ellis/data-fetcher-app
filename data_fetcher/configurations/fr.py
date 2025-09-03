"""France API fetcher configuration.

This module provides the configuration for fetching data from French government
APIs, including SIRENE business registry data and related endpoints.
"""

from collections.abc import Callable
from datetime import date, timedelta
from typing import Protocol

import structlog

from ..bundle_locators.api_pagination_bundle_locators import CursorPaginationStrategy
from ..core import FetchContext, create_fetcher_config
from ..factory import (
    create_complex_pagination_provider,
    create_http_manager,
    create_reverse_pagination_provider,
    create_single_api_provider,
    create_tracking_api_loader,
)
from ..global_credential_provider import get_default_credential_provider
from ..protocols.authentication import OAuthAuthenticationMechanism
from ..registry import register_configuration

"""
French INSEE API configuration setup.
"""

# Get logger for this module
logger = structlog.get_logger(__name__)


def _create_fr_date_filter(start_date: str) -> Callable[[str], bool]:
    """Create a date filter for FR API based on start date."""

    def filter_function(date_str: str) -> bool:
        """Check if date should be processed based on start date."""
        try:
            return date_str >= start_date
        except Exception:
            # If we can't parse the date, process it
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
            else:
                return f"{narrowing} AND -periode(categorieJuridiqueUniteLegale:1000) AND statutDiffusionUniteLegale:O AND {base_query}"
        else:
            return f"-periode(categorieJuridiqueUniteLegale:1000) AND statutDiffusionUniteLegale:O AND {base_query}"

    return query_builder


def _create_siren_narrowing_strategy() -> Callable[[str | None], str]:
    """Create a SIREN narrowing strategy."""

    def narrowing_strategy(current_narrowing: str | None = None) -> str:
        """Create SIREN prefix for narrowing search."""
        if current_narrowing is None:
            return "siren:00"
        elif current_narrowing == "siren:99":
            return "siren:99"  # This will trigger date increment
        else:
            # Extract the numeric part and increment
            prefix_value = current_narrowing.split(":", 1)[1]
            if len(prefix_value) == 2:
                new_value = str(int(prefix_value) + 1).zfill(2)
            else:
                if prefix_value.endswith("9"):
                    new_value = str(int(prefix_value[:-1]) + 1).zfill(
                        len(prefix_value) - 1
                    )
                else:
                    new_value = str(int(prefix_value) + 1).zfill(len(prefix_value))
            return f"siren:{new_value}"

    return narrowing_strategy


def _create_sirene_error_handler() -> Callable[[str, int], bool]:
    """Create an error handler for Sirene API."""

    def error_handler(url: str, status_code: int) -> bool:
        """Handle Sirene API errors."""
        if status_code == 404:
            logger.warning("No items found for query", url=url)
            return False
        elif status_code in [500, 503, 504, 403]:
            logger.error("Server error", url=url, status_code=status_code)
            return False
        elif status_code != 200:
            logger.error("Unexpected status code", url=url, status_code=status_code)
            return False
        return True

    return error_handler


def _setup_fr_api_fetcher(
    token_url: str | None = None,
    base_url: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> FetchContext:
    """French INSEE API fetcher using generic API providers with OAuth authentication."""
    # Get credential provider
    credential_provider = get_default_credential_provider()

    # Use provided token URL or default to INSEE API
    if token_url is None:
        token_url = "https://api.insee.fr/token"

    # Use provided base URL or default to INSEE API
    if base_url is None:
        base_url = "https://api.insee.fr/entreprises/sirene/V3.11/siren"

    # Create OAuth authentication mechanism
    oauth_auth = OAuthAuthenticationMechanism(
        token_url=token_url,
        credential_provider=credential_provider,
        config_name="fr-api",
    )

    # Create HTTP manager with OAuth authentication
    http_manager = create_http_manager(
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
    loader = create_tracking_api_loader(
        http_manager=http_manager,
        meta_load_name="fr_sirene_api_loader",
        error_handler=_create_sirene_error_handler(),
    )

    # Calculate date range (use provided dates or default to last 5 days)
    if end_date is None:
        end_date = date.today().strftime("%Y-%m-%d")
    if start_date is None:
        end_date_obj = date.today() if isinstance(end_date, str) else end_date
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
    siren_provider = create_complex_pagination_provider(
        http_manager=http_manager,
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
        persistence_prefix="fr_siren_provider",
    )

    # Create gap-filling provider for historical data
    # This would be used to fill gaps in data collection
    # For testing, use a very short range; for production, this could be much longer
    gap_start_date = start_date
    gap_end_date = end_date

    gap_provider = create_reverse_pagination_provider(
        http_manager=http_manager,
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
        persistence_prefix="fr_gap_provider",
    )

    # Create provider for failed company numbers (if any)
    # This would be populated with company numbers that failed to process
    failed_companies_provider = create_single_api_provider(
        http_manager=http_manager,
        urls=[],  # Empty initially, would be populated with failed company URLs
        headers={
            "Accept": "application/json",
        },
        persistence_prefix="fr_failed_companies_provider",
    )

    # Build configuration
    return (
        create_fetcher_config()
        .use_bundle_loader(loader)
        .add_bundle_locator(siren_provider)
        .add_bundle_locator(gap_provider)
        .add_bundle_locator(failed_companies_provider)
        .build()
    )


# Register the configuration
register_configuration("fr-api", _setup_fr_api_fetcher)
