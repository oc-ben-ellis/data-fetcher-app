"""Resource bundling and aggregation decorator.

This module provides decorators for bundling multiple resources together
during storage operations, creating logical groupings of related data.
"""

import gzip
import io
import os
import tempfile
import zipfile
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from ...core import BundleRef


class BundleResourcesDecorator:
    """Decorator that bundles resources into a single zip file."""

    def __init__(self, base_storage: Any) -> None:
        """Initialize the bundle resources decorator with base storage.

        Args:
            base_storage: The underlying storage to decorate.
        """
        self.base_storage = base_storage

    @asynccontextmanager
    async def open_bundle(self, bundle_ref: BundleRef) -> Any:
        """Open a bundle with resource bundling."""
        async with self.base_storage.open_bundle(bundle_ref) as base_bundle:
            bundle = BundleResourcesBundle(base_bundle)
            try:
                yield bundle
            finally:
                await bundle.close()


class BundleResourcesBundle:
    """Bundle that collects resources into a zip file."""

    def __init__(self, base_bundle: Any) -> None:
        """Initialize the bundle resources bundle with base bundle.

        Args:
            base_bundle: The underlying bundle to decorate.
        """
        self.base_bundle = base_bundle
        # Store temp file paths, not content
        self.temp_files: list[dict[str, Any]] = []

    async def write_resource(
        self,
        url: str,
        content_type: str | None,
        status_code: int,
        stream: AsyncGenerator[bytes, None],
    ) -> None:
        """Stream a resource to a temporary file."""
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        try:
            # Stream content to temp file
            async for chunk in stream:
                temp_file.write(chunk)
            temp_file.flush()
            temp_file.close()

            # If the resource appears to be gzipped (by magic bytes) or URL ends with .gz,
            # transparently decompress before adding to the bundle so that downstream
            # consumers see the actual payload (e.g., HTML) rather than the compressed blob.
            decompressed_path = self._maybe_decompress_gzip(url, temp_file.name)

            # Store temp file info (not content)
            self.temp_files.append(
                {
                    "url": url,
                    "content_type": content_type,
                    "status_code": status_code,
                    "temp_file": decompressed_path,
                }
            )
        except Exception:
            # Clean up on error
            try:
                os.unlink(temp_file.name)
            except OSError:
                pass
            raise

    async def close(self) -> None:
        """Close the bundle and create zip file from temp files."""
        if not self.temp_files:
            await self.base_bundle.close()
            return

        try:
            # Create zip file from temp files
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for i, resource in enumerate(self.temp_files):
                    # Create filename
                    filename = f"resource_{i:03d}"
                    if resource["content_type"]:
                        if "html" in resource["content_type"]:
                            filename += ".html"
                        elif "json" in resource["content_type"]:
                            filename += ".json"
                        elif "xml" in resource["content_type"]:
                            filename += ".xml"
                        elif "text" in resource["content_type"]:
                            filename += ".txt"
                        else:
                            filename += ".bin"

                    # Add temp file to zip (streams from disk) if it still exists.
                    # In some environments, intermediary temp files may be
                    # cleaned up by underlying layers; skip gracefully.
                    temp_path = resource["temp_file"]
                    if os.path.exists(temp_path):
                        zip_file.write(temp_path, filename)
                    else:
                        # TODO: Consider logging this occurrence for debugging
                        # rather than raising, to keep bundling robust.
                        continue

            # Write zip to base storage
            zip_data = zip_buffer.getvalue()
            await self.base_bundle.write_resource(
                url="bundle.zip",
                content_type="application/zip",
                status_code=200,
                stream=self._stream_from_bytes(zip_data),
            )

        finally:
            # Clean up all temp files
            for resource in self.temp_files:
                try:
                    os.unlink(resource["temp_file"])
                except OSError:
                    pass

        await self.base_bundle.close()

    async def _stream_from_bytes(self, data: bytes) -> AsyncGenerator[bytes, None]:
        """Create a stream from bytes."""
        yield data

    def _maybe_decompress_gzip(self, url: str, temp_path: str) -> str:
        """Decompress using gzip if required.

        If the given temp file is gzipped (or URL ends with .gz), return a path to a decompressed temp file; otherwise return the original path.

        Args:
            url: Original URL (used to detect .gz suffix).
            temp_path: Path to the streamed content.

        Returns:
            Path to a file containing the decompressed content (or original).
        """
        try:
            is_gz = False
            if url.endswith(".gz"):
                is_gz = True
            else:
                with open(temp_path, "rb") as f:
                    header = f.read(2)
                    is_gz = header.startswith(b"\x1f\x8b")

            if not is_gz:
                return temp_path

            # Decompress into a new temp file
            with open(temp_path, "rb") as src:
                with gzip.GzipFile(fileobj=src, mode="rb") as gz:
                    decompressed = gz.read()

            out = tempfile.NamedTemporaryFile(delete=False)
            out.write(decompressed)
            out.flush()
            out.close()

            # Keep original around for later cleanup; caller manages lifecycle
            return out.name
        except Exception:
            # On any failure, fall back to original content
            return temp_path
