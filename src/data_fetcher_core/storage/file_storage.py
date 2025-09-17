"""Local file system storage implementation.

This module provides the FileStorage class for storing data to local file
systems, including directory management and file operations.
"""

import importlib.util
import re
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import structlog

from data_fetcher_core.storage.bundle_storage_context import BundleStorageContext

if TYPE_CHECKING:
    from data_fetcher_core.core import BundleRef, DataRegistryFetcherConfig

# Get logger for this module
logger = structlog.get_logger(__name__)


@dataclass
class FileStorage:
    """File-based storage implementation."""

    output_dir: str
    create_dirs: bool = True

    def __post_init__(self) -> None:
        """Initialize the file storage and create output directory if needed."""
        if self.create_dirs:
            Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        self._active_bundles: dict[str, Any] = {}

    # New interface methods
    async def start_bundle(
        self, bundle_ref: "BundleRef", recipe: "DataRegistryFetcherConfig"
    ) -> "BundleStorageContext":
        """Initialize a new bundle and return a BundleStorageContext."""
        # Create file bundle
        bundle = FileStorageBundle(self.output_dir, bundle_ref)
        self._active_bundles[str(bundle_ref.bid)] = bundle

        # Create and return BundleStorageContext
        context = BundleStorageContext(bundle_ref, recipe, self)
        logger.debug(
            "Bundle started", bid=str(bundle_ref.bid), config_id=recipe.config_id
        )
        return context

    def bundle_found(self, metadata: dict[str, Any]) -> str:
        """Return a stub/mock BID value for local file storage."""
        # Generate a simple deterministic-looking stub BID without external deps
        from datetime import UTC, datetime
        from secrets import token_hex

        ts = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        reg = str(metadata.get("config_id", "local")).lower().replace(" ", "-")
        rnd = token_hex(4)
        return f"bid:v1:{reg}:{ts}:{rnd}"

    async def _add_resource_to_bundle(
        self,
        bundle_ref: "BundleRef",
        resource_name: str,
        metadata: dict[str, Any],
        stream: AsyncGenerator[bytes],
    ) -> None:
        """Internal method to add a resource to a bundle."""
        bundle = self._active_bundles.get(str(bundle_ref.bid))
        if not bundle:
            error_message = "Bundle not found"
            raise ValueError(error_message)

        await bundle.write_resource(resource_name, metadata, stream)

    async def complete_bundle_with_callbacks_hook(
        self,
        bundle_ref: "BundleRef",
        recipe: "DataRegistryFetcherConfig",
        _metadata: dict[str, "Any"],
    ) -> None:
        """Complete bundle and execute all completion callbacks."""
        # Finalize the bundle
        await self._finalize_bundle(bundle_ref)

        # Execute completion callbacks using the recipe
        await self._execute_completion_callbacks(bundle_ref, recipe)

        logger.debug(
            "Bundle completed", bid=str(bundle_ref.bid), config_id=recipe.config_id
        )

    async def _finalize_bundle(
        self,
        bundle_ref: "BundleRef",
    ) -> None:
        """Internal method to finalize a bundle."""
        bundle = self._active_bundles.get(str(bundle_ref.bid))
        if not bundle:
            error_message = "Bundle not found"
            raise ValueError(error_message)

        # Finalize the file bundle
        await bundle.close()

        # Clean up
        del self._active_bundles[str(bundle_ref.bid)]

    async def _execute_completion_callbacks(
        self, bundle_ref: "BundleRef", recipe: "DataRegistryFetcherConfig"
    ) -> None:
        """Execute completion callbacks from recipe components."""
        # Execute loader completion callback
        loader = recipe.loader
        if loader is not None and getattr(loader, "on_bundle_complete_hook", None):
            try:
                await loader.on_bundle_complete_hook(bundle_ref)
                logger.debug(
                    "Loader completion callback executed",
                    bid=str(bundle_ref.bid),
                    config_id=recipe.config_id,
                    loader_type=type(recipe.loader).__name__,
                )
            except Exception as e:
                logger.exception(
                    "Error executing loader completion callback",
                    error=str(e),
                    bid=str(bundle_ref.bid),
                    config_id=recipe.config_id,
                )

        # Execute locator completion callbacks
        for locator in recipe.locators:
            if locator is not None and getattr(
                locator, "on_bundle_complete_hook", None
            ):
                try:
                    await locator.on_bundle_complete_hook(bundle_ref)
                    logger.debug(
                        "Locator completion callback executed",
                        bid=str(bundle_ref.bid),
                        config_id=recipe.config_id,
                        locator_type=type(locator).__name__,
                    )
                except Exception as e:
                    logger.exception(
                        "Error executing locator completion callback",
                        error=str(e),
                        bid=str(bundle_ref.bid),
                        config_id=recipe.config_id,
                    )


class FileStorageBundle:
    """File bundle for writing resources to disk."""

    def __init__(self, output_dir: str, bundle_ref: "BundleRef") -> None:
        """Initialize the file bundle with output directory and bundle reference.

        Args:
            output_dir: Directory where the bundle will be stored.
            bundle_ref: Reference to the bundle being created.
        """
        self.output_dir = output_dir
        self.bundle_ref = bundle_ref
        self.bundle_dir = self._create_bundle_dir()

    def _create_bundle_dir(self) -> str:
        """Create a directory for this bundle."""
        # Use BID for directory naming to enable time-based organization
        # BID contains timestamp information for chronological sorting
        bundle_dir = str(Path(self.output_dir) / f"bundle_{self.bundle_ref.bid}")
        Path(bundle_dir).mkdir(parents=True, exist_ok=True)
        return bundle_dir

    async def write_resource(
        self,
        resource_name: str,
        metadata: dict[str, Any],
        stream: AsyncGenerator[bytes],
    ) -> None:
        """Write a resource to the bundle."""
        # Create a safe filename from the resource name
        filename = self._safe_filename(resource_name)
        filepath = str(Path(self.bundle_dir) / filename)

        # Write the file
        async with aiofiles_module.open(filepath, "wb") as f:
            async for chunk in stream:
                await f.write(chunk)

        # Create metadata file
        meta_filepath = f"{filepath}.meta"
        # Merge provided metadata with file size
        file_metadata = {
            "resource_name": resource_name,
            "size": Path(filepath).stat().st_size,
            **metadata,  # Include all provided metadata
        }

        async with aiofiles_module.open(meta_filepath, "w") as f:
            await f.write(str(file_metadata))

    def _safe_filename(self, url: str) -> str:
        """Create a safe filename from a URL."""
        # Parse URL
        parsed = urlparse(url)

        # Get the path and filename
        path = parsed.path
        if not path or path == "/":
            path = "index.html"

        # Remove leading slash
        if path.startswith("/"):
            path = path[1:]

        # Replace unsafe characters
        safe_path = re.sub(r"[^\w\-_.]", "_", path)

        # Ensure it's not empty
        if not safe_path:
            safe_path = "index.html"

        return safe_path

    async def close(self) -> None:
        """Close the bundle."""
        # Update bundle metadata
        meta_filepath = str(Path(self.bundle_dir) / "bundle.meta")
        metadata = {
            "bid": str(self.bundle_ref.bid),
            "primary_url": self.bundle_ref.meta.get("primary_url"),
            "resources_count": self.bundle_ref.meta.get("resources_count"),
            "storage_key": self.bundle_dir,
            "meta": self.bundle_ref.meta,
        }

        async with aiofiles_module.open(meta_filepath, "w") as f:
            await f.write(str(metadata))


# Import aiofiles for async file operations
aiofiles_module: Any
if importlib.util.find_spec("aiofiles") is not None:
    import aiofiles

    aiofiles_module = aiofiles
else:
    # Fallback to synchronous file operations
    class _AioFilesFallback:
        class AsyncFile:
            def __init__(self, filepath: str, mode: str) -> None:
                self.filepath = filepath
                self.mode = mode
                self.file: Any = None

            async def __aenter__(self) -> "_AioFilesFallback.AsyncFile":
                # Use context manager to open file, then keep reference
                # This satisfies the linter while maintaining the async context manager pattern
                self.file = Path(self.filepath).open(self.mode)  # noqa: SIM115
                return self

            async def __aexit__(
                self, exc_type: object, exc_val: object, exc_tb: object
            ) -> None:
                if self.file is not None:
                    self.file.close()

            async def write(self, data: object) -> None:
                if self.file is not None:
                    self.file.write(data)

            async def read(self, size: int = -1) -> object:
                if self.file is not None:
                    return self.file.read(size)
                return None

        @staticmethod
        async def open(filepath: str, mode: str) -> "_AioFilesFallback.AsyncFile":
            return _AioFilesFallback.AsyncFile(filepath, mode)

    aiofiles_module = _AioFilesFallback()
