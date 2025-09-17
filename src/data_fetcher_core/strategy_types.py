"""Strategy type definitions for the data fetcher service.

This module defines the abstract base classes and protocols for different
strategy types used in the data fetcher service, providing proper type
annotations instead of using generic Callable types.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # Only for static typing; avoids runtime circular imports
    from data_fetcher_core.core import (
        BundleLoadResult,
        BundleRef,
        DataRegistryFetcherConfig,
        FetchRunContext,
    )


class LoaderStrategy(ABC):
    """Abstract base class for loader strategies.

    This provides a concrete base class for loader implementations that
    need to be instantiated as dataclasses.
    """

    @abstractmethod
    async def load(
        self,
        bundle: "BundleRef",
        storage: "object",
        ctx: "FetchRunContext",
        recipe: "DataRegistryFetcherConfig",
    ) -> "BundleLoadResult":
        """Load resources for the provided BundleRef and return a BundleLoadResult."""


class LocatorStrategy(ABC):
    """Abstract base class for locator strategies.

    This provides a concrete base class for locator implementations that
    need to be instantiated as dataclasses.
    """

    @abstractmethod
    async def get_next_bundle_refs(
        self, ctx: "FetchRunContext", bundle_refs_needed: int
    ) -> list["BundleRef"]:
        """Locate and enumerate available bundle references."""


class FilterStrategyBase(ABC):
    """Abstract base class for filter strategies.

    Implementations must provide a `filter` method.
    """

    @abstractmethod
    def filter(self, data: "object") -> bool:
        """Return True if the data should be included, False otherwise."""


# Type aliases for common strategy types
LoaderStrategyType = type[LoaderStrategy]
LocatorStrategyType = type[LocatorStrategy]
# Kept for backward compatibility where referenced, but prefer using FilterStrategyBase directly
FilterStrategyType = type[FilterStrategyBase]


class FileSortStrategyBase(ABC):
    """Abstract base class for file sorting strategies.

    Implementations receive a list of (path, mtime) tuples and return a sorted list.
    """

    @abstractmethod
    def sort(
        self, items: list[tuple[str, float | int | None]]
    ) -> list[tuple[str, float | int | None]]:
        """Return a sorted list of (path, mtime) tuples according to strategy."""


# Strategy configuration types (for YAML config)
LoaderStrategyConfig = dict[str, Any]  # Configuration dict for loader strategies
LocatorStrategyConfig = dict[str, Any]  # Configuration dict for locator strategies
FilterStrategyConfig = dict[str, Any]  # Configuration dict for filter strategies
