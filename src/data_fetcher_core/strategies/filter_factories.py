"""Filter factories for creating file filters from YAML configuration.

This module provides factories for creating filter functions that can be used
by bundle locators to filter files based on various criteria.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from oc_pipeline_bus.strategy_registry import (
    InvalidArgumentStrategyException,
    StrategyFactory,
)

from data_fetcher_core.strategies.types import FileFilter


@dataclass
class DateFilterConfig:
    start_date: str
    date_pattern: str = "YYYYMMDD"


class DateFilterFactory(StrategyFactory):
    """Factory for creating date-based file filters."""

    def validate(self, params: dict[str, Any]) -> None:
        """Validate parameters for date filter creation.

        Args:
            params: Dictionary of parameters to validate

        Raises:
            InvalidArgumentStrategyException: If validation fails
        """
        required_fields = ["start_date"]

        for field in required_fields:
            if field not in params:
                raise InvalidArgumentStrategyException(
                    f"Missing required parameter: {field}",
                    Callable,
                    "date_filter",
                    params,
                )

        # Validate start_date is a string
        if not isinstance(params["start_date"], str):
            raise InvalidArgumentStrategyException(
                "start_date must be a string", Callable, "date_filter", params
            )

    def create(self, params: DateFilterConfig) -> Callable[[str], bool]:
        """Create a date-based file filter function.

        Args:
            params: Dictionary of parameters for filter creation

        Returns:
            Filter function that takes a filename and returns True if it should be processed
        """
        start_date = params.start_date
        _date_pattern = params.date_pattern  # Reserved for future use

        def date_filter(filename: str) -> bool:
            """Check if daily file should be processed based on start date."""
            DATE_LENGTH = 8  # YYYYMMDD format

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
                return False
            except Exception as e:
                # If we can't parse the date, raise an error to avoid silent failures
                raise ValueError(
                    f"Failed to parse date from filename '{filename}': {e}"
                ) from e

        return date_filter


@dataclass
class PatternFilterConfig:
    pattern: str
    case_sensitive: bool = True


class PatternFilterFactory(StrategyFactory):
    """Factory for creating pattern-based file filters."""

    def validate(self, params: dict[str, Any]) -> None:
        """Validate parameters for pattern filter creation.

        Args:
            params: Dictionary of parameters to validate

        Raises:
            InvalidArgumentStrategyException: If validation fails
        """
        required_fields = ["pattern"]

        for field in required_fields:
            if field not in params:
                raise InvalidArgumentStrategyException(
                    f"Missing required parameter: {field}",
                    Callable,
                    "pattern_filter",
                    params,
                )

        # Validate pattern is a string
        if not isinstance(params["pattern"], str):
            raise InvalidArgumentStrategyException(
                "pattern must be a string", Callable, "pattern_filter", params
            )

    def create(self, params: PatternFilterConfig) -> Callable[[str], bool]:
        """Create a pattern-based file filter function.

        Args:
            params: Dictionary of parameters for filter creation

        Returns:
            Filter function that takes a filename and returns True if it matches the pattern
        """
        import fnmatch

        pattern = params.pattern
        case_sensitive = params.case_sensitive

        def pattern_filter(filename: str) -> bool:
            """Check if filename matches the pattern."""
            if not case_sensitive:
                return fnmatch.fnmatch(filename.lower(), pattern.lower())
            return fnmatch.fnmatch(filename, pattern)

        return pattern_filter


@dataclass
class CompositeFilterConfig:
    filters: list[dict[str, Any]]
    operation: str = "AND"


class CompositeFilterFactory(StrategyFactory):
    """Factory for creating composite filters that combine multiple filter types."""

    def validate(self, params: dict[str, Any]) -> None:
        """Validate parameters for composite filter creation.

        Args:
            params: Dictionary of parameters to validate

        Raises:
            InvalidArgumentStrategyException: If validation fails
        """
        required_fields = ["filters"]

        for field in required_fields:
            if field not in params:
                raise InvalidArgumentStrategyException(
                    f"Missing required parameter: {field}",
                    Callable,
                    "composite_filter",
                    params,
                )

        # Validate filters is a list
        if not isinstance(params["filters"], list):
            raise InvalidArgumentStrategyException(
                "filters must be a list", Callable, "composite_filter", params
            )

        # Validate each filter has required fields
        for i, filter_config in enumerate(params["filters"]):
            if not isinstance(filter_config, dict):
                raise InvalidArgumentStrategyException(
                    f"filters[{i}] must be a dictionary",
                    Callable,
                    "composite_filter",
                    params,
                )

            if "type" not in filter_config:
                raise InvalidArgumentStrategyException(
                    f"filters[{i}] must have a 'type' field",
                    Callable,
                    "composite_filter",
                    params,
                )

    def create(self, params: CompositeFilterConfig) -> Callable[[str], bool]:
        """Create a composite filter function.

        Args:
            params: Dictionary of parameters for filter creation

        Returns:
            Filter function that combines multiple filters
        """
        filters = params.filters
        operation = params.operation  # AND or OR

        # Create individual filters
        filter_functions = []
        for filter_config in filters:
            filter_type = filter_config["type"]
            filter_params = {k: v for k, v in filter_config.items() if k != "type"}

            if filter_type == "date_filter":
                factory = DateFilterFactory()
                filter_func = factory.create(DateFilterConfig(**filter_params))
            elif filter_type == "pattern_filter":
                factory = PatternFilterFactory()
                filter_func = factory.create(PatternFilterConfig(**filter_params))
            else:
                raise InvalidArgumentStrategyException(
                    f"Unknown filter type: {filter_type}",
                    Callable,
                    "composite_filter",
                    params,
                )

            filter_functions.append(filter_func)

        def composite_filter(filename: str) -> bool:
            """Apply all filters with the specified operation."""
            if operation == "AND":
                return all(f(filename) for f in filter_functions)
            if operation == "OR":
                return any(f(filename) for f in filter_functions)
            raise ValueError(f"Unknown operation: {operation}")

        return composite_filter


def register_filter_strategies(registry) -> None:
    """Register all filter strategy factories with the registry.

    Args:
        registry: StrategyFactoryRegistry instance to register with
    """
    # Register filter factories
    registry.register(FileFilter, "date_filter", DateFilterFactory())

    registry.register(FileFilter, "pattern_filter", PatternFilterFactory())

    registry.register(FileFilter, "composite_filter", CompositeFilterFactory())
