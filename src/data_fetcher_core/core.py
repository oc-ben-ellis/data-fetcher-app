"""Core framework components and base classes.

This module provides the fundamental building blocks of the OC Fetcher framework,
including the base FetcherContextBuilder and configuration creation utilities.
"""

from dataclasses import dataclass, field
from typing import Any

from data_fetcher_core.storage.builder import get_global_storage

Url = str


@dataclass
class RequestMeta:
    """Metadata for a fetch request."""

    url: Url
    depth: int = 0
    referer: Url | None = None
    headers: dict[str, str] = field(default_factory=dict)
    flags: dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourceMeta:
    """Metadata for a fetched resource."""

    url: Url
    status: int | None = None
    content_type: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    note: str | None = None


@dataclass
class BundleRef:
    """Reference to a bundle of fetched resources."""

    primary_url: Url
    resources_count: int
    storage_key: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class FetchRunContext:
    """Context for a fetch run."""

    shared: dict[str, Any] = field(default_factory=dict)
    run_id: str | None = None


@dataclass
class FetchPlan:
    """Plan for fetching resources."""

    requests: list[RequestMeta]
    context: FetchRunContext
    concurrency: int = 1


@dataclass
class FetchContext:
    """Context for the entire fetch operation."""

    bundle_locators: list[Any] = field(default_factory=list)
    bundle_loader: object | None = None
    storage: object | None = None


class FetcherContextBuilder:
    """Builder for creating fetcher configurations."""

    def __init__(self) -> None:
        """Initialize the fetcher context builder."""
        self._bundle_loader: object = None
        self._bundle_locators: list[Any] = []

    def use_bundle_loader(
        self, bundle_loader_instance: object
    ) -> "FetcherContextBuilder":
        """Set the loader instance."""
        self._bundle_loader = bundle_loader_instance
        return self

    def add_bundle_locator(
        self, bundle_locator_instance: object
    ) -> "FetcherContextBuilder":
        """Add a bundle locator instance."""
        self._bundle_locators.append(bundle_locator_instance)
        return self

    def build(self) -> FetchContext:
        """Build the fetcher configuration."""
        if not self._bundle_loader:
            raise ValueError("Bundle loader required")  # noqa: TRY003

        # Get global storage
        storage = get_global_storage()

        return FetchContext(
            bundle_locators=self._bundle_locators,
            bundle_loader=self._bundle_loader,
            storage=storage,
        )


def create_fetcher_config() -> FetcherContextBuilder:
    """Create a new fetcher configuration builder."""
    return FetcherContextBuilder()
