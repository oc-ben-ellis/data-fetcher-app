"""Local file system storage implementation.

This module provides the FileStorage class for storing data to local file
systems, including directory management and file operations.
"""

import hashlib
import importlib.util
import re
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

if TYPE_CHECKING:
    from data_fetcher.core import BundleRef


@dataclass
class FileStorage:
    """File-based storage implementation."""

    output_dir: str
    create_dirs: bool = True

    def __post_init__(self) -> None:
        """Initialize the file storage and create output directory if needed."""
        if self.create_dirs:
            Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    @asynccontextmanager
    async def open_bundle(
        self, bundle_ref: "BundleRef"
    ) -> AsyncGenerator["FileBundle", None]:
        """Open a bundle for writing."""
        bundle = FileBundle(self.output_dir, bundle_ref)
        try:
            yield bundle
        finally:
            await bundle.close()


class FileBundle:
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
        # Create a unique directory name based on the primary URL
        url_hash = hashlib.sha256(self.bundle_ref.primary_url.encode()).hexdigest()[:8]
        bundle_dir = str(Path(self.output_dir) / f"bundle_{url_hash}")
        Path(bundle_dir).mkdir(parents=True, exist_ok=True)
        return bundle_dir

    async def write_resource(
        self,
        url: str,
        content_type: str | None,
        status_code: int,
        stream: AsyncGenerator[bytes, None],
    ) -> None:
        """Write a resource to the bundle."""
        # Create a safe filename from the URL
        filename = self._safe_filename(url)
        filepath = str(Path(self.bundle_dir) / filename)

        # Write the file
        async with aiofiles_module.open(filepath, "wb") as f:
            async for chunk in stream:
                await f.write(chunk)

        # Create metadata file
        meta_filepath = f"{filepath}.meta"
        metadata = {
            "url": url,
            "content_type": content_type,
            "status_code": status_code,
            "size": Path(filepath).stat().st_size,
        }

        async with aiofiles_module.open(meta_filepath, "w") as f:
            await f.write(str(metadata))

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
            "primary_url": self.bundle_ref.primary_url,
            "resources_count": self.bundle_ref.resources_count,
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
