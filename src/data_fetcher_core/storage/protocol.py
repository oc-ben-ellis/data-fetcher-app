"""Storage protocol definitions.

This module defines the Storage protocol that all storage implementations
must follow for bundle lifecycle management.
"""

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from data_fetcher_core.core import BundleRef, DataRegistryFetcherConfig
    from data_fetcher_core.storage.bundle_storage_context import BundleStorageContext


class Storage(Protocol):
    """Storage protocol for bundle lifecycle management.

    This protocol defines the interface that all storage implementations
    must follow for managing bundle creation and resource storage.
    """

    async def start_bundle(
        self, bundle_ref: "BundleRef", recipe: "DataRegistryFetcherConfig"
    ) -> "BundleStorageContext":
        """Initialize a new bundle and return a BundleStorageContext for managing it.

        Args:
            bundle_ref: Reference to the bundle being created.
            recipe: The fetcher recipe containing callback information.

        Returns:
            A BundleStorageContext for managing the bundle lifecycle.

        Raises:
            Exception: If bundle initialization fails.
        """
        ...

    def bundle_found(self, metadata: dict[str, Any]) -> str:
        """Mint or return a BID for a newly discovered bundle.

        Implementations may persist discovery metadata or simply return a stub value.
        """
        ...
