"""Core framework components and base classes.

This module provides the fundamental building blocks of the OC Fetcher framework,
including the base DataRegistryFetcherConfigBuilder and configuration creation utilities.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from oc_pipeline_bus.config import Strategy, Annotated
from data_fetcher_core.strategy_types import BundleLoader, BundleLocator

if TYPE_CHECKING:
    from data_fetcher_core.core_config.config_factory import FetcherConfig

# Import pipeline-bus config types
from oc_pipeline_bus.identifiers import Bid

from data_fetcher_core.exceptions import BundleRefValidationError


@dataclass(init=False)
class BundleRef:
    """Reference to a bundle of fetched resources.

    Backwards-compatible initializer: allows passing legacy keyword arguments
    like primary_url/resources_count, which are stored in meta.
    """

    bid: Bid
    meta: dict[str, Any]

    def __init__(
        self,
        bid: Bid | None = None,
        meta: dict[str, Any] | None = None,
        **kwargs: object,
    ) -> None:
        self.bid = bid or Bid()  # Default construct when not provided
        self.meta = dict(meta or {})
        # Fold any legacy kwargs into meta for compatibility
        for key in ("primary_url", "resources_count", "storage_key"):
            if key in kwargs and kwargs[key] is not None:
                self.meta[key] = kwargs[key]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BundleRef:
        """Create a BundleRef from a dictionary.

        Args:
            data: Dictionary containing bundle reference data.

        Returns:
            A new BundleRef instance.

        Raises:
            BundleRefValidationError: If required fields are missing or invalid.
        """
        if not isinstance(data, dict):
            error_message = "Data must be a dictionary"  # type: ignore[unreachable]
            raise BundleRefValidationError(error_message)

        # Validate required fields
        if "bid" not in data:
            error_message = "BundleRef data must contain 'bid' field"
            raise BundleRefValidationError(error_message)

        # Validate meta dict is present; specific keys are optional and may include
        # 'primary_url' and 'resources_count'
        if "meta" not in data:
            error_message = "BundleRef data must contain 'meta' field"
            raise BundleRefValidationError(error_message)
        meta = data["meta"]
        if not isinstance(meta, dict):
            error_message = "meta must be a dictionary"
            raise BundleRefValidationError(error_message)

        # Validate BID format
        try:
            bid = Bid(data["bid"])
        except ValueError as e:
            error_message = "Invalid BID format"
            raise BundleRefValidationError(error_message) from e

        # meta already validated above; we do not enforce specific keys here

        return cls(
            bid=bid,
            meta=meta,
        )


@dataclass
class FetchRunContext:
    """Context for a fetch run."""

    run_id: str
    shared: dict[str, Any] = field(default_factory=dict)
    processed_count: int = 0
    errors: list[str] = field(default_factory=list)
    app_config: FetcherConfig | None = None


@dataclass
class ProtocolConfig(ABC):
    """Base class for protocol-specific configurations.

    This abstract base class defines the interface that all protocol configurations
    must implement. Each protocol configuration contains the settings needed to
    establish and manage connections for that specific protocol.
    """

    @abstractmethod
    def get_connection_key(self) -> str:
        """Get a unique key for this configuration.

        This key is used to identify and reuse connection pools that match
        this configuration. Configurations with the same key will share
        the same connection pool.

        Returns:
            A unique string identifier for this configuration.
        """

    @abstractmethod
    def get_protocol_type(self) -> str:
        """Get the protocol type identifier.

        Returns:
            A string identifying the protocol type (e.g., 'http', 'sftp').
        """


@dataclass
class DataRegistryFetcherConfig:
    """YAML-based fetcher configuration using strategy factory registry."""

    loader: Annotated[BundleLoader, "strategy"]
    locators: list[ Annotated[BundleLocator, "strategy"]]
    concurrency: int = 10
    target_queue_size: int = 100
    # Optional fields for backward compatibility with storage hooks
    config_id: str = ""
    # Protocol configurations for resolving relative configs
    protocols: dict[str, dict[str, str]] = field(default_factory=dict)


@dataclass
class FetchPlan:
    """Plan for fetching resources."""

    config: DataRegistryFetcherConfig
    context: FetchRunContext
    concurrency: int = 1
    target_queue_size: int = 100


# Lightweight public type aliases retained for backward compatibility with tests
# RequestMeta/ResourceMeta are dictionaries passed through the queue and loader
RequestMeta = dict[str, Any]
ResourceMeta = dict[str, Any]
