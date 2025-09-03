"""Local file system storage implementation.

This module provides the FileStorage class for storing data to local file
systems, including directory management and file operations.
"""

import importlib.util
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from ..core import BundleRef


@dataclass
class FileStorage:
    """File-based storage implementation."""

    output_dir: str
    create_dirs: bool = True

    def __post_init__(self) -> None:
        """Initialize the file storage and create output directory if needed."""
        if self.create_dirs:
            os.makedirs(self.output_dir, exist_ok=True)

    @asynccontextmanager
    async def open_bundle(
        self, bundle_ref: BundleRef
    ) -> AsyncGenerator["FileBundle", None]:
        """Open a bundle for writing."""
        bundle = FileBundle(self.output_dir, bundle_ref)
        try:
            yield bundle
        finally:
            await bundle.close()


class FileBundle:
    """File bundle for writing resources to disk."""

    def __init__(self, output_dir: str, bundle_ref: BundleRef) -> None:
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
        import hashlib

        url_hash = hashlib.md5(self.bundle_ref.primary_url.encode()).hexdigest()[:8]
        bundle_dir = os.path.join(self.output_dir, f"bundle_{url_hash}")
        os.makedirs(bundle_dir, exist_ok=True)
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
        filepath = os.path.join(self.bundle_dir, filename)

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
            "size": os.path.getsize(filepath),
        }

        async with aiofiles_module.open(meta_filepath, "w") as f:
            await f.write(str(metadata))

    def _safe_filename(self, url: str) -> str:
        """Create a safe filename from a URL."""
        import re
        from urllib.parse import urlparse

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
        meta_filepath = os.path.join(self.bundle_dir, "bundle.meta")
        metadata = {
            "primary_url": self.bundle_ref.primary_url,
            "resources_count": self.bundle_ref.resources_count,
            "storage_key": self.bundle_dir,
            "meta": self.bundle_ref.meta,
        }

        async with aiofiles_module.open(meta_filepath, "w") as f:
            await f.write(str(metadata))


# Import aiofiles for async file operations
if importlib.util.find_spec("aiofiles") is not None:
    import aiofiles

    aiofiles_module: Any = aiofiles
else:
    # Fallback to synchronous file operations
    class _AioFilesFallback:
        @staticmethod
        async def open(filepath: str, mode: str) -> Any:
            class AsyncFile:
                def __init__(self, filepath: str, mode: str) -> None:
                    self.file = open(filepath, mode)

                async def __aenter__(self) -> "AsyncFile":
                    return self

                async def __aexit__(
                    self, exc_type: Any, exc_val: Any, exc_tb: Any
                ) -> None:
                    self.file.close()

                async def write(self, data: Any) -> None:
                    self.file.write(data)

                async def read(self, size: int = -1) -> Any:
                    return self.file.read(size)

            return AsyncFile(filepath, mode)

    aiofiles_module = _AioFilesFallback()
