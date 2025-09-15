"""FR-specific strategy factories for HTTP API components.

This module provides strategy factories for FR-specific HTTP API components
like complex pagination locators, reverse pagination locators, and single URL locators.
"""

from collections.abc import Callable
from typing import Any

from oc_pipeline_bus.strategy_registry import (
    InvalidArgumentStrategyException,
    StrategyFactory,
)

from data_fetcher_http_api.api_bundle_locators import (
    PaginationHttpBundleLocator,
)
from data_fetcher_http_api.api_pagination_bundle_locators import (
    CursorPaginationStrategy,
)
from data_fetcher_http.http_manager import HttpManager
from data_fetcher_core.strategy_types import BundleLocator


class SirenProviderFactory(StrategyFactory):
    """Factory for creating SIREN provider locators with complex pagination."""

    http_manager: HttpManager

    def __init__(self, http_manager: HttpManager) -> None:
        self.http_manager = http_manager

    def validate(self, params: dict[str, Any]) -> None:
        """Validate parameters for SIREN provider creation."""
        required_fields = ["http_config", "base_url", "date_start"]

        for field in required_fields:
            if field not in params:
                raise InvalidArgumentStrategyException(
                    f"Missing required parameter: {field}",
                    PaginationHttpBundleLocator,
                    "siren_provider",
                    params,
                )

    def create(self, params: dict[str, Any]) -> PaginationHttpBundleLocator:
        """Create a SIREN provider locator."""
        http_config = params["http_config"]

        # Create query builder
        query_builder = self._create_sirene_query_builder()

        # Create pagination strategy
        pagination_strategy = CursorPaginationStrategy(
            cursor_field="curseurSuivant",
            total_field="total",
            count_field="nombre",
            max_records=20000,
        )

        # Create narrowing strategy
        narrowing_strategy = self._create_siren_narrowing_strategy()

        return PaginationHttpBundleLocator(
            http_manager=self.http_manager,
            http_config=http_config,
            store=None,  # Will be set from context
            base_url=params["base_url"],
            date_start=params["date_start"],
            date_end=params.get("date_end"),
            max_records_per_page=params.get("max_records_per_page", 1000),
            rate_limit_requests_per_second=params.get(
                "rate_limit_requests_per_second", 2.0
            ),
            headers=params.get("headers", {}),
            query_builder=query_builder,
            pagination_strategy=pagination_strategy,
            narrowing_strategy=narrowing_strategy,
        )

    def _create_sirene_query_builder(self) -> Callable[[str, str | None], str]:
        """Create a query builder for Sirene API."""

        def query_builder(date_str: str, narrowing: str | None = None) -> str:
            base_query = f"dateDernierTraitementUniteLegale:[{date_str}T00:00:00%20TO%20{date_str}T23:59:59]"

            if narrowing:
                if narrowing.startswith("siren:"):
                    return f"{narrowing}* AND -periode(categorieJuridiqueUniteLegale:1000) AND statutDiffusionUniteLegale:O AND {base_query}"
                return f"{narrowing} AND -periode(categorieJuridiqueUniteLegale:1000) AND statutDiffusionUniteLegale:O AND {base_query}"
            return f"-periode(categorieJuridiqueUniteLegale:1000) AND statutDiffusionUniteLegale:O AND {base_query}"

        return query_builder

    def _create_siren_narrowing_strategy(self) -> Callable[[str | None], str]:
        """Create a SIREN narrowing strategy."""
        PREFIX_LENGTH = 2
        PREFIX_SUFFIX = "9"

        def narrowing_strategy(current_narrowing: str | None = None) -> str:
            if current_narrowing is None:
                return "siren:00"
            if current_narrowing == "siren:99":
                return "siren:99"  # This will trigger date increment

            prefix_value = current_narrowing.split(":", 1)[1]
            if len(prefix_value) == PREFIX_LENGTH:
                new_value = str(int(prefix_value) + 1).zfill(PREFIX_LENGTH)
            elif prefix_value.endswith(PREFIX_SUFFIX):
                new_value = str(int(prefix_value[:-1]) + 1).zfill(len(prefix_value) - 1)
            else:
                new_value = str(int(prefix_value) + 1).zfill(len(prefix_value))
            return f"siren:{new_value}"

        return narrowing_strategy


class GapProviderFactory(StrategyFactory):
    """Factory for creating gap-filling provider locators."""

    http_manager: HttpManager

    def __init__(self, http_manager: HttpManager) -> None:
        self.http_manager = http_manager

    def validate(self, params: dict[str, Any]) -> None:
        """Validate parameters for gap provider creation."""
        required_fields = ["http_config", "base_url", "date_start"]

        for field in required_fields:
            if field not in params:
                raise InvalidArgumentStrategyException(
                    f"Missing required parameter: {field}",
                    PaginationHttpBundleLocator,
                    "gap_provider",
                    params,
                )

    def create(self, params: dict[str, Any]) -> PaginationHttpBundleLocator:
        """Create a gap provider locator."""
        http_config = params["http_config"]

        # Create query builder
        query_builder = self._create_sirene_query_builder()

        # Create pagination strategy
        pagination_strategy = CursorPaginationStrategy(
            cursor_field="curseurSuivant",
            total_field="total",
            count_field="nombre",
            max_records=20000,
        )

        # Create narrowing strategy
        narrowing_strategy = self._create_siren_narrowing_strategy()

        return PaginationHttpBundleLocator(
            http_manager=self.http_manager,
            http_config=http_config,
            store=None,  # Will be set from context
            base_url=params["base_url"],
            date_start=params["date_start"],
            date_end=params.get("date_end"),
            max_records_per_page=params.get("max_records_per_page", 1000),
            rate_limit_requests_per_second=params.get(
                "rate_limit_requests_per_second", 2.0
            ),
            headers=params.get("headers", {}),
            query_builder=query_builder,
            pagination_strategy=pagination_strategy,
            narrowing_strategy=narrowing_strategy,
        )

    def _create_sirene_query_builder(self) -> Callable[[str, str | None], str]:
        """Create a query builder for Sirene API."""

        def query_builder(date_str: str, narrowing: str | None = None) -> str:
            base_query = f"dateDernierTraitementUniteLegale:[{date_str}T00:00:00%20TO%20{date_str}T23:59:59]"

            if narrowing:
                if narrowing.startswith("siren:"):
                    return f"{narrowing}* AND -periode(categorieJuridiqueUniteLegale:1000) AND statutDiffusionUniteLegale:O AND {base_query}"
                return f"{narrowing} AND -periode(categorieJuridiqueUniteLegale:1000) AND statutDiffusionUniteLegale:O AND {base_query}"
            return f"-periode(categorieJuridiqueUniteLegale:1000) AND statutDiffusionUniteLegale:O AND {base_query}"

        return query_builder

    def _create_siren_narrowing_strategy(self) -> Callable[[str | None], str]:
        """Create a SIREN narrowing strategy."""
        PREFIX_LENGTH = 2
        PREFIX_SUFFIX = "9"

        def narrowing_strategy(current_narrowing: str | None = None) -> str:
            if current_narrowing is None:
                return "siren:00"
            if current_narrowing == "siren:99":
                return "siren:99"  # This will trigger date increment

            prefix_value = current_narrowing.split(":", 1)[1]
            if len(prefix_value) == PREFIX_LENGTH:
                new_value = str(int(prefix_value) + 1).zfill(PREFIX_LENGTH)
            elif prefix_value.endswith(PREFIX_SUFFIX):
                new_value = str(int(prefix_value[:-1]) + 1).zfill(len(prefix_value) - 1)
            else:
                new_value = str(int(prefix_value) + 1).zfill(len(prefix_value))
            return f"siren:{new_value}"

        return narrowing_strategy


class FailedCompaniesProviderFactory(StrategyFactory):
    """Factory for creating failed companies provider locators."""

    http_manager: HttpManager

    def __init__(self, http_manager: HttpManager) -> None:
        self.http_manager = http_manager

    def validate(self, params: dict[str, Any]) -> None:
        """Validate parameters for failed companies provider creation."""
        required_fields = ["http_config"]

        for field in required_fields:
            if field not in params:
                raise InvalidArgumentStrategyException(
                    f"Missing required parameter: {field}",
                    PaginationHttpBundleLocator,
                    "failed_companies_provider",
                    params,
                )

    def create(self, params: dict[str, Any]) -> PaginationHttpBundleLocator:
        """Create a failed companies provider locator."""
        http_config = params["http_config"]

        return PaginationHttpBundleLocator(
            http_manager=self.http_manager,
            http_config=http_config,
            store=None,  # Will be set from context
            base_url="",  # Not used for single URL locators
            date_start="",  # Not used for single URL locators
            urls=params.get("urls", []),
            headers=params.get("headers", {}),
        )


def register_fr_strategies(registry, http_manager) -> None:
    """Register all FR-specific strategy factories with the registry.

    Args:
        registry: StrategyFactoryRegistry instance to register with
    """
    from data_fetcher_http_api.api_bundle_locators import PaginationHttpBundleLocator

    # Register FR-specific locator factories against base interface
    registry.register(
        BundleLocator, "siren_provider", SirenProviderFactory(http_manager=http_manager)
    )

    registry.register(BundleLocator, "gap_provider", GapProviderFactory(http_manager=http_manager))

    registry.register(
        BundleLocator,
        "failed_companies_provider",
        FailedCompaniesProviderFactory(http_manager=http_manager),
    )
