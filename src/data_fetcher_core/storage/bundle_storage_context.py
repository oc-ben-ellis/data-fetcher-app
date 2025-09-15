"""Bundle storage context for managing bundle lifecycle and resource uploads.

This module provides the BundleStorageContext class that manages the lifecycle
of a bundle during storage operations, including resource uploads and completion.
"""

import asyncio
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from data_fetcher_core.core import BundleRef, DataRegistryFetcherConfig
    from data_fetcher_core.storage import Storage

# Get logger for this module
logger = structlog.get_logger(__name__)


class BundleStorageContext:
    """Context for managing bundle lifecycle and resource uploads.

    This class provides a stateful interface for managing bundle creation,
    resource addition, and completion. It ensures proper sequencing of
    operations and handles upload coordination.
    """

    def __init__(
        self,
        bundle_ref: "BundleRef",
        recipe: "DataRegistryFetcherConfig",
        storage: "Storage",
    ) -> None:
        """Initialize the bundle storage context.

        Args:
            bundle_ref: Reference to the bundle being created.
            recipe: The fetcher recipe containing callback information.
            storage: The storage implementation to delegate operations to.
        """
        self.bundle_ref = bundle_ref
        self.recipe = recipe
        self.storage = storage
        self._pending_uploads: set[str] = set()
        self._completed_uploads: set[str] = set()
        self._upload_lock = asyncio.Lock()
        self._completion_event = asyncio.Event()
        self._is_completed = False
        # Set the event initially since there are no pending uploads
        self._completion_event.set()

    async def add_resource(
        self,
        resource_name: str,
        metadata: dict[str, Any],
        stream: AsyncGenerator[bytes],
    ) -> None:
        """Add a resource to the bundle.

        Args:
            resource_name: The name of the resource (e.g., filename, or "original.tar.gz/path/to/file.csv").
            metadata: Dictionary containing metadata about the resource (url, content_type, status_code, etc.).
            stream: Async generator yielding the resource content.

        Raises:
            ValueError: If the bundle is not found in storage.
            Exception: If the resource upload fails.
        """
        upload_id = f"{resource_name}_{id(stream)}"  # Unique identifier for this upload

        async with self._upload_lock:
            self._pending_uploads.add(upload_id)
            # Clear the completion event since we now have pending uploads
            if len(self._pending_uploads) == 1:
                self._completion_event.clear()

        try:
            # Delegate to storage implementation
            await self.storage._add_resource_to_bundle(  # type: ignore[attr-defined]  # noqa: SLF001
                self.bundle_ref, resource_name, metadata, stream
            )

            # Mark upload as completed
            async with self._upload_lock:
                self._pending_uploads.discard(upload_id)
                self._completed_uploads.add(upload_id)

                # Signal completion if no more pending uploads
                if not self._pending_uploads:
                    self._completion_event.set()

        except Exception:
            async with self._upload_lock:
                self._pending_uploads.discard(upload_id)
                # Signal completion even on error if no more pending uploads
                if not self._pending_uploads:
                    self._completion_event.set()
            raise

    async def complete(self, metadata: dict[str, Any]) -> None:
        """Complete the bundle after all uploads are finished.

        This method waits for all pending uploads to complete, then delegates
        to the storage implementation to finalize the bundle and execute
        completion callbacks.

        Args:
            metadata: Additional metadata to include with the bundle.

        Raises:
            Exception: If bundle completion fails.
        """
        # Wait for all pending uploads to complete using proper synchronization
        await self._completion_event.wait()

        # Check if already completed to ensure idempotency
        if self._is_completed:
            return

        # Mark as completed before calling storage method
        self._is_completed = True

        # Delegate completion to storage (including callbacks)
        await self.storage.complete_bundle_with_callbacks_hook(  # type: ignore[attr-defined]
            self.bundle_ref, self.recipe, metadata
        )
