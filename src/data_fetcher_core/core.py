"""Core framework components and base classes.

This module provides the fundamental building blocks of the OC Fetcher framework,
including the base DataRegistryFetcherConfigBuilder and configuration creation utilities.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Mapping
from types import MappingProxyType

from oc_pipeline_bus.config import Annotated

from data_fetcher_core.strategy_types import LoaderStrategy, LocatorStrategy

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
    request_meta: "RequestMeta"

    def __init__(
        self,
        bid: Bid | str | None = None,
        request_meta: "RequestMeta | None" = None,
        **kwargs: object,
    ) -> None:
        # Enforce that bid is provided
        if bid is None:
            raise TypeError("BundleRef requires a 'bid' (str or Bid)")
        self.bid = bid if isinstance(bid, Bid) else Bid(bid)
        # Start with provided request_meta or empty
        rm_dict: dict[str, Any] = dict(request_meta or {})
        # Back-compat: fold legacy kwargs into request_meta
        if "primary_url" in kwargs and kwargs["primary_url"] is not None:
            rm_dict.setdefault("url", kwargs["primary_url"])  # type: ignore[index]
        if "resources_count" in kwargs and kwargs["resources_count"] is not None:
            rm_dict.setdefault("resources_count", kwargs["resources_count"])  # type: ignore[index]
        if "storage_key" in kwargs and kwargs["storage_key"] is not None:
            rm_dict.setdefault("storage_key", kwargs["storage_key"])  # type: ignore[index]
        # Freeze request metadata to prevent mutation after construction
        self.request_meta = MappingProxyType(rm_dict)

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

        # Accept either 'request_meta' (preferred) or 'meta' (legacy)
        if "request_meta" in data:
            meta = data["request_meta"]
        elif "meta" in data:
            meta = data["meta"]
        else:
            error_message = "BundleRef data must contain 'request_meta' (or legacy 'meta') field"
            raise BundleRefValidationError(error_message)
        if not isinstance(meta, dict):
            error_message = "request_meta must be a dictionary"
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
            request_meta=meta,
        )


@dataclass
class BundleLoadResult:
    """Result of loading a bundle.

    Contains the original `BundleRef`, aggregate bundle metadata, and
    per-resource metadata entries produced during loading.
    """

    bundle: BundleRef
    bundle_meta: Mapping[str, Any]
    resources: list[dict[str, Any]]


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

    loader: Annotated[LoaderStrategy, "strategy"]
    locators: list[Annotated[LocatorStrategy, "strategy"]]
    concurrency: int = 10
    target_queue_size: int = 100
    # Optional fields for backward compatibility with storage hooks
    config_id: str = ""
    # Protocol configurations for resolving relative configs
    # protocols: dict[str, dict[str, str]] = field(default_factory=dict)


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
