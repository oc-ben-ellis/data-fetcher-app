"""Strategy type definitions for the data fetcher service.

This module defines the abstract base classes and protocols for different
strategy types used in the data fetcher service, providing proper type
annotations instead of using generic Callable types.
"""

from abc import ABC
from typing import Any, AsyncGenerator, Protocol, runtime_checkable

from data_fetcher_core.kv_store import KeyValueStore


@runtime_checkable
class BundleLoader(Protocol):
    """Protocol for bundle loader strategies.
    
    Bundle loaders are responsible for loading data bundles from various sources.
    """
    
    async def load(self, bundle_id: str) -> AsyncGenerator[bytes, None]:
        """Load a bundle by its identifier.
        
        Args:
            bundle_id: The identifier of the bundle to load
            
        Yields:
            Chunks of data from the bundle
        """
        ...


@runtime_checkable
class BundleLocator(Protocol):
    """Protocol for bundle locator strategies.
    
    Bundle locators are responsible for discovering and enumerating available
    bundles from various sources.
    """
    
    async def locate(self) -> AsyncGenerator[str, None]:
        """Locate and enumerate available bundles.
        
        Yields:
            Bundle identifiers that can be loaded
        """
        ...


@runtime_checkable
class FilterStrategy(Protocol):
    """Protocol for filter strategies.
    
    Filter strategies are used to filter or transform data during processing.
    """
    
    def filter(self, data: Any) -> bool:
        """Filter data based on the strategy's criteria.
        
        Args:
            data: The data to filter
            
        Returns:
            True if the data should be included, False otherwise
        """
        ...


class LoaderStrategy(ABC):
    """Marker base class for loader strategies.
    
    Implementations may define their own `load` signatures compatible with the runtime.
    This class exists purely for isinstance checks in the strategy registry.
    """


class LocatorStrategy(ABC):
    """Marker base class for locator strategies (isinstance only)."""


class FilterStrategyBase(ABC):
    """Marker base class for filter strategies (isinstance only)."""


# Type aliases for common strategy types
LoaderStrategyType = type[LoaderStrategy]
LocatorStrategyType = type[LocatorStrategy]
FilterStrategyType = type[FilterStrategyBase]

# Strategy configuration types (for YAML config)
LoaderStrategyConfig = dict[str, Any]  # Configuration dict for loader strategies
LocatorStrategyConfig = dict[str, Any]  # Configuration dict for locator strategies
FilterStrategyConfig = dict[str, Any]  # Configuration dict for filter strategies
