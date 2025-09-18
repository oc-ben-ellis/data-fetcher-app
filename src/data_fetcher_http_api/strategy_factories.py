"""Strategy factories for HTTP API components.

This module provides strategy factories that can be registered with the
StrategyFactoryRegistry to enable YAML-based configuration loading.
"""

from dataclasses import dataclass
from typing import Annotated, Any

from oc_pipeline_bus.strategy_registry import (
    InvalidArgumentStrategyException,
    StrategyFactory,
)

from data_fetcher_core.strategy_types import LoaderStrategy, LocatorStrategy
from data_fetcher_http.http_config import HttpProtocolConfig
from data_fetcher_http.http_manager import HttpManager
from data_fetcher_http_api.api_bundle_locators import (
    PaginationHttpBundleLocator,
)
from data_fetcher_http_api.api_loader import HttpBundleLoader


@dataclass
class HttpLoaderConfig:
    """Configuration for HTTP bundle loader."""

    meta_load_name: str
    # value is an alias like "test_http" → resolve to filename via protocols.http.{value} → load into HttpProtocolConfig
    http_config: Annotated[
        HttpProtocolConfig, "path:protocols.http.{value}", "relative_config"
    ]
    follow_redirects: bool = True
    max_redirects: int = 5
    error_handler: Any = None


@dataclass
class HttpPaginationLocatorConfig:
    """Configuration for HTTP pagination bundle locator."""

    # value is an alias like "test_http" → resolve to filename via protocols.http.{value} → load into HttpProtocolConfig
    http_config: Annotated[
        HttpProtocolConfig, "path:protocols.http.{value}", "relative_config"
    ]
    base_url: str
    date_start: str
    date_end: str | None = None
    max_records_per_page: int = 1000
    rate_limit_requests_per_second: float = 2.0
    date_filter: Any = None
    query_params: dict[str, Any] | None = None
    headers: dict[str, str] | None = None
    query_builder: Any = None
    pagination_strategy: Any = None
    narrowing_strategy: Any = None
    state_management_prefix: str = "pagination_http_bundle_locator"


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

    def create(self, params: Any) -> HttpBundleLoader:
        """Create an HttpBundleLoader instance.

        Args:
            params: Dictionary of parameters for loader creation (may be processed config object)

        Returns:
            Created HttpBundleLoader instance
        """
        # The http_config parameter will be resolved by DataPipelineConfig
        # and passed as an actual HttpProtocolConfig object
        if hasattr(params, 'http_config'):
            # params is a dataclass instance
            http_config = params.http_config
            meta_load_name = params.meta_load_name
            follow_redirects = getattr(params, 'follow_redirects', True)
            max_redirects = getattr(params, 'max_redirects', 5)
            error_handler = getattr(params, 'error_handler', None)
        else:
            # params is a dictionary
            http_config = params["http_config"]
            meta_load_name = params["meta_load_name"]
            follow_redirects = params.get("follow_redirects", True)
            max_redirects = params.get("max_redirects", 5)
            error_handler = params.get("error_handler")

        return HttpBundleLoader(
            http_manager=self.http_manager,
            http_config=http_config,
            meta_load_name=meta_load_name,
            follow_redirects=follow_redirects,
            max_redirects=max_redirects,
            error_handler=error_handler,
        )

    def get_config_type(self, params: dict[str, Any]) -> type | None:
        """Get the configuration type for further processing.

        Args:
            params: Dictionary of parameters that may contain nested configurations

        Returns:
            HttpLoaderConfig - for processing http_config relative config
        """
        return HttpLoaderConfig


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

    def create(self, params: Any) -> PaginationHttpBundleLocator:
        """Create a PaginationHttpBundleLocator instance.

        Args:
            params: Dictionary of parameters for locator creation (may be processed config object)

        Returns:
            Created PaginationHttpBundleLocator instance
        """
        # The http_config parameter will be resolved by DataPipelineConfig
        # and passed as an actual HttpProtocolConfig object
        if hasattr(params, 'http_config'):
            # params is a dataclass instance
            http_config = params.http_config
            base_url = params.base_url
            date_start = params.date_start
            date_end = getattr(params, 'date_end', None)
            max_records_per_page = getattr(params, 'max_records_per_page', 1000)
            rate_limit_requests_per_second = getattr(params, 'rate_limit_requests_per_second', 2.0)
            date_filter = getattr(params, 'date_filter', None)
            query_params = getattr(params, 'query_params', None)
            headers = getattr(params, 'headers', None)
        else:
            # params is a dictionary
            http_config = params["http_config"]
            base_url = params["base_url"]
            date_start = params["date_start"]
            date_end = params.get("date_end")
            max_records_per_page = params.get("max_records_per_page", 1000)
            rate_limit_requests_per_second = params.get("rate_limit_requests_per_second", 2.0)
            date_filter = params.get("date_filter")
            query_params = params.get("query_params")
            headers = params.get("headers")

        # Note: store will be provided by the context during execution
        # For now, we'll use None and it will be set later
        return PaginationHttpBundleLocator(
            http_manager=self.http_manager,
            http_config=http_config,
            store=None,  # Will be set from context
            base_url=base_url,
            date_start=date_start,
            date_end=date_end,
            max_records_per_page=max_records_per_page,
            rate_limit_requests_per_second=rate_limit_requests_per_second,
            date_filter=date_filter,  # Will be processed by DataPipelineConfig
            query_params=query_params,
            headers=headers,
        )

    def get_config_type(self, params: dict[str, Any]) -> type | None:
        """Get the configuration type for further processing.

        Args:
            params: Dictionary of parameters that may contain nested configurations

        Returns:
            HttpPaginationLocatorConfig - for processing http_config relative config
        """
        return HttpPaginationLocatorConfig


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
