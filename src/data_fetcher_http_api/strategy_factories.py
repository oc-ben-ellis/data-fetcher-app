"""Strategy factories for HTTP API components.

This module provides strategy factories that can be registered with the
StrategyFactoryRegistry to enable YAML-based configuration loading.
"""

from typing import Any

from oc_pipeline_bus.strategy_registry import (
    InvalidArgumentStrategyException,
    StrategyFactory,
)

from data_fetcher_core.strategy_types import LoaderStrategy, LocatorStrategy
from data_fetcher_http.http_manager import HttpManager
from data_fetcher_http_api.api_bundle_locators import (
    PaginationHttpBundleLocator,
)
from data_fetcher_http_api.api_loader import HttpBundleLoader


class HttpBundleLoaderFactory(StrategyFactory):
    """Factory for creating HttpBundleLoader instances."""

    http_manager: HttpManager

    def __init__(self, http_manager: HttpManager) -> None:
        self.http_manager = http_manager

    def validate(self, params: dict[str, Any]) -> None:
        """Validate parameters for HttpBundleLoader creation.

        Args:
            params: Dictionary of parameters to validate

        Raises:
            InvalidArgumentStrategyException: If validation fails
        """
        required_fields = ["meta_load_name", "http_config"]

        for field in required_fields:
            if field not in params:
                raise InvalidArgumentStrategyException(
                    f"Missing required parameter: {field}",
                    HttpBundleLoader,
                    "http_loader",
                    params,
                )

        # Validate http_config is a string (relative config path)
        if not isinstance(params["http_config"], str):
            raise InvalidArgumentStrategyException(
                "http_config must be a string path to configuration file",
                HttpBundleLoader,
                "http_loader",
                params,
            )

    def create(self, params: dict[str, Any]) -> HttpBundleLoader:
        """Create an HttpBundleLoader instance.

        Args:
            params: Dictionary of parameters for loader creation

        Returns:
            Created HttpBundleLoader instance
        """
        # The http_config parameter will be resolved by DataPipelineConfig
        # and passed as an actual HttpProtocolConfig object
        http_config = params["http_config"]

        return HttpBundleLoader(
            http_manager=self.http_manager,
            http_config=http_config,
            meta_load_name=params["meta_load_name"],
            follow_redirects=params.get("follow_redirects", True),
            max_redirects=params.get("max_redirects", 5),
            error_handler=params.get("error_handler"),
        )


class PaginationHttpBundleLocatorFactory(StrategyFactory):
    """Factory for creating PaginationHttpBundleLocator instances."""

    http_manager: HttpManager

    def __init__(self, http_manager: HttpManager) -> None:
        self.http_manager = http_manager

    def validate(self, params: dict[str, Any]) -> None:
        """Validate parameters for PaginationHttpBundleLocator creation.

        Args:
            params: Dictionary of parameters to validate

        Raises:
            InvalidArgumentStrategyException: If validation fails
        """
        required_fields = ["http_config", "base_url", "date_start"]

        for field in required_fields:
            if field not in params:
                raise InvalidArgumentStrategyException(
                    f"Missing required parameter: {field}",
                    PaginationHttpBundleLocator,
                    "pagination_locator",
                    params,
                )

        # Validate http_config is a string (relative config path)
        if not isinstance(params["http_config"], str):
            raise InvalidArgumentStrategyException(
                "http_config must be a string path to configuration file",
                PaginationHttpBundleLocator,
                "pagination_locator",
                params,
            )

        # Validate base_url is a string
        if not isinstance(params["base_url"], str):
            raise InvalidArgumentStrategyException(
                "base_url must be a string",
                PaginationHttpBundleLocator,
                "pagination_locator",
                params,
            )

        # Validate date_start is a string
        if not isinstance(params["date_start"], str):
            raise InvalidArgumentStrategyException(
                "date_start must be a string",
                PaginationHttpBundleLocator,
                "pagination_locator",
                params,
            )

    def create(self, params: dict[str, Any]) -> PaginationHttpBundleLocator:
        """Create a PaginationHttpBundleLocator instance.

        Args:
            params: Dictionary of parameters for locator creation

        Returns:
            Created PaginationHttpBundleLocator instance
        """
        # The http_config parameter will be resolved by DataPipelineConfig
        # and passed as an actual HttpProtocolConfig object
        http_config = params["http_config"]

        # Note: store will be provided by the context during execution
        # For now, we'll use None and it will be set later
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
            date_filter=params.get(
                "date_filter"
            ),  # Will be processed by DataPipelineConfig
            query_params=params.get("query_params"),
            headers=params.get("headers"),
        )


def register_http_strategies(registry, http_manager) -> None:
    """Register all HTTP strategy factories with the registry.

    Args:
        registry: StrategyFactoryRegistry instance to register with
    """
    # Register loader factory against base interface
    registry.register(
        LoaderStrategy,
        "http_loader",
        HttpBundleLoaderFactory(http_manager=http_manager),
    )

    # Register locator factories
    registry.register(
        LocatorStrategy,
        "pagination_locator",
        PaginationHttpBundleLocatorFactory(http_manager=http_manager),
    )
