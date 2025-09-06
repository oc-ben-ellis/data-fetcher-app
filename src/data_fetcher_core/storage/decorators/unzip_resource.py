"""File decompression and extraction decorator.

This module provides decorators for automatically decompressing compressed
files during storage operations, including ZIP, GZIP, and other formats.
"""

import gzip
import tempfile
import zipfile
from collections.abc import AsyncGenerator
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from data_fetcher_core.core import BundleRef, FetcherRecipe
    from data_fetcher_core.storage.bundle_storage_context import BundleStorageContext

# Get logger for this module
logger = structlog.get_logger(__name__)


class UnzipResourceDecorator:
    """Decorator that decompresses zipped resources."""

    def __init__(self, base_storage: object) -> None:
        """Initialize the unzip resource decorator with base storage.

        Args:
            base_storage: The underlying storage to decorate.
        """
        self.base_storage = base_storage

    async def start_bundle(
        self, bundle_ref: "BundleRef", recipe: "FetcherRecipe"
    ) -> "BundleStorageContext":
        """Initialize a new bundle and return a BundleStorageContext for managing it.

        Args:
            bundle_ref: Reference to the bundle being created.
            recipe: The fetcher recipe containing callback information.

        Returns:
            A BundleStorageContext for managing the bundle lifecycle.
        """
        # Get the base storage context
        base_context = await self.base_storage.start_bundle(bundle_ref, recipe)  # type: ignore[attr-defined]

        # Return a wrapped context that applies decompression
        return UnzipResourceBundleStorageContext(base_context, self)  # type: ignore[return-value]

    def _is_gzipped_file(self, filepath: str) -> bool:
        """Check if file is gzipped by reading first 2 bytes."""
        with Path(filepath).open("rb") as f:
            header = f.read(2)
        return header.startswith(b"\x1f\x8b")

    def _is_zipped_file(self, filepath: str) -> bool:
        """Check if file is a zip file by reading first 2 bytes."""
        with Path(filepath).open("rb") as f:
            header = f.read(2)
        return header.startswith(b"PK")

    def _strip_compression_suffix(self, url: str) -> str:
        """Strip common compression suffixes from the URL path.

        This helps produce expected filenames like `page.html` when the input
        URL is `page.html.gz`, regardless of whether decompression actually
        happened (e.g., in error fallbacks).

        Args:
            url: Original resource URL that may end with a compression suffix.

        Returns:
            URL string with trailing `.gz`/`.gzip` removed from the path.
        """
        try:
            from urllib.parse import urlparse, urlunparse  # noqa: PLC0415

            parsed = urlparse(url)
            path = parsed.path
            for suffix in (".gz", ".gzip"):
                if path.endswith(suffix):
                    path = path[: -len(suffix)]
                    break
            parsed = parsed._replace(path=path)
            return urlunparse(parsed)
        except Exception as e:
            # Safe fallback: best-effort suffix strip
            logger.exception(
                "ERROR_PARSING_URL_FOR_COMPRESSION_DETECTION_USING_FALLBACK",
                error=str(e),
                url=url,
            )
            if url.endswith(".gz"):
                return url[:-3]
            if url.endswith(".gzip"):
                return url[:-5]
            return url

    def _should_bypass_decompression(self, url: str, content_type: str | None) -> bool:
        """Determine whether to bypass decompression for this resource.

        We avoid decompressing when the URL indicates a final bundle artifact
        (e.g., ends with .zip) so that higher-level decorators can persist
        archives without this layer extracting them.

        Args:
            url: Resource URL.
            content_type: Optional content type.

        Returns:
            True if decompression should be bypassed.
        """
        try:
            from urllib.parse import urlparse  # noqa: PLC0415

            path = urlparse(url).path or ""
            if path.endswith(".zip"):
                return True
            # Respect explicit zip content-type as an additional signal
            if content_type and "application/zip" in content_type:
                return True
        except Exception as e:
            logger.exception(
                "ERROR_CHECKING_IF_DECOMPRESSION_SHOULD_BE_BYPASSED",
                error=str(e),
                url=url,
                content_type=content_type,
            )
        return False


class UnzipResourceBundleStorageContext:
    """Bundle storage context that decompresses resources."""

    def __init__(
        self, base_context: "BundleStorageContext", decorator: "UnzipResourceDecorator"
    ) -> None:
        """Initialize the unzip resource bundle storage context.

        Args:
            base_context: The underlying bundle storage context to decorate.
            decorator: The decorator instance for accessing helper methods.
        """
        self.base_context = base_context
        self.decorator = decorator

    async def add_resource(
        self,
        url: str,
        content_type: str | None,
        status_code: int,
        stream: AsyncGenerator[bytes],
    ) -> None:
        """Add a resource to the bundle with decompression.

        Args:
            url: The URL of the resource being added.
            content_type: The content type of the resource.
            status_code: The HTTP status code of the resource.
            stream: Async generator yielding the resource content.
        """
        logger.debug(
            "UNZIPRESOURCEDECORATOR_ADD_RESOURCE_CALLED",
            url=url,
            content_type=content_type,
        )

        # If this looks like an intentional archive artifact (e.g., a final
        # bundle.zip), bypass decompression entirely and stream as-is.
        if self.decorator._should_bypass_decompression(url, content_type):  # noqa: SLF001
            await self.base_context.add_resource(
                self.decorator._strip_compression_suffix(url),  # noqa: SLF001
                content_type,
                status_code,
                stream,
            )
            return

        # Stream to temporary file for compression detection
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            try:
                # Stream content to temp file
                async for chunk in stream:
                    temp_file.write(chunk)
                temp_file.flush()
                temp_file.close()

                logger.debug(
                    "CONTENT_WRITTEN_TO_TEMP_FILE",
                    temp_file=temp_file.name,
                    size=Path(temp_file.name).stat().st_size,
                )

                # Check if content is compressed and process accordingly
                if self.decorator._is_gzipped_file(temp_file.name):  # noqa: SLF001
                    logger.debug("DETECTED_GZIPPED_CONTENT_DECOMPRESSING")
                    await self._add_decompressed_gzip_file(
                        url, content_type, status_code, temp_file.name
                    )
                elif self.decorator._is_zipped_file(temp_file.name):  # noqa: SLF001
                    logger.debug("DETECTED_ZIPPED_CONTENT_EXTRACTING")
                    await self._add_decompressed_zip_file(
                        url, content_type, status_code, temp_file.name
                    )
                else:
                    logger.debug("CONTENT_NOT_COMPRESSED_STREAMING_AS_IS")
                    # Stream original content from temp file
                    await self._add_temp_file_to_storage(
                        self.decorator._strip_compression_suffix(url),  # noqa: SLF001
                        content_type,
                        status_code,
                        temp_file.name,
                    )

            finally:
                # Clean up temp file
                with suppress(OSError):
                    Path(temp_file.name).unlink()

    async def complete(self, metadata: dict[str, object]) -> None:
        """Complete the bundle after all uploads are finished.

        Args:
            metadata: Additional metadata to include with the bundle.
        """
        await self.base_context.complete(metadata)

    async def _add_temp_file_to_storage(
        self, url: str, content_type: str | None, status_code: int, filepath: str
    ) -> None:
        """Stream a temp file to storage without loading into memory."""

        async def file_stream() -> AsyncGenerator[bytes]:
            with Path(filepath).open("rb") as f:
                while True:
                    chunk = f.read(8192)  # 8KB chunks
                    if not chunk:
                        break
                    yield chunk

        await self.base_context.add_resource(
            url=url,
            content_type=content_type,
            status_code=status_code,
            stream=file_stream(),
        )

    async def _add_decompressed_gzip_file(
        self, url: str, content_type: str | None, status_code: int, filepath: str
    ) -> None:
        """Decompress gzip file and stream to storage."""
        try:
            # Stream decompressed content
            async def gzip_stream() -> AsyncGenerator[bytes]:
                with gzip.open(filepath, "rb") as gz_file:
                    while True:
                        chunk = gz_file.read(8192)  # 8KB chunks
                        if not chunk:
                            break
                        yield chunk

            await self.base_context.add_resource(
                url=self.decorator._strip_compression_suffix(url),  # noqa: SLF001
                content_type=content_type,
                status_code=status_code,
                stream=gzip_stream(),
            )
        except Exception as e:
            logger.exception("GZIP_DECOMPRESSION_ERROR", url=url, error=str(e))
            # Stream original content as fallback
            await self._add_temp_file_to_storage(
                self.decorator._strip_compression_suffix(url),  # noqa: SLF001
                content_type,
                status_code,
                filepath,
            )

    async def _add_decompressed_zip_file(
        self, url: str, content_type: str | None, status_code: int, filepath: str
    ) -> None:
        """Decompress zip file and stream to storage."""
        try:
            with zipfile.ZipFile(filepath) as zip_file:
                for zip_info in zip_file.filelist:
                    if zip_info.is_dir():
                        continue

                    # Stream extracted file
                    filename = zip_info.filename

                    async def create_zip_stream(
                        zip_file: zipfile.ZipFile, filename: str
                    ) -> AsyncGenerator[bytes]:
                        with zip_file.open(filename) as zf:
                            while True:
                                chunk = zf.read(8192)  # 8KB chunks
                                if not chunk:
                                    break
                                yield chunk

                    # Add extracted file
                    extracted_url = (
                        f"{self.decorator._strip_compression_suffix(url)}/{filename}"  # noqa: SLF001
                    )
                    await self.base_context.add_resource(
                        url=extracted_url,
                        content_type="application/octet-stream",
                        status_code=status_code,
                        stream=create_zip_stream(zip_file, filename),
                    )
        except Exception as e:
            logger.exception("ZIP_DECOMPRESSION_ERROR", url=url, error=str(e))
            # Stream original content as fallback
            await self._add_temp_file_to_storage(
                self.decorator._strip_compression_suffix(url),  # noqa: SLF001
                content_type,
                status_code,
                filepath,
            )
