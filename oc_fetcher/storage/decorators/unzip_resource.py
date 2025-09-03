"""File decompression and extraction decorator.

This module provides decorators for automatically decompressing compressed
files during storage operations, including ZIP, GZIP, and other formats.
"""

import gzip
import io
import os
import tempfile
import zipfile
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import structlog

from ...core import BundleRef

# Get logger for this module
logger = structlog.get_logger(__name__)


class UnzipResourceDecorator:
    """Decorator that decompresses zipped resources."""

    def __init__(self, base_storage: Any) -> None:
        """Initialize the unzip resource decorator with base storage.

        Args:
            base_storage: The underlying storage to decorate.
        """
        self.base_storage = base_storage

    @asynccontextmanager
    async def open_bundle(self, bundle_ref: BundleRef) -> Any:
        """Open a bundle with decompression."""
        async with self.base_storage.open_bundle(bundle_ref) as base_bundle:
            unzip_bundle = UnzipResourceBundle(base_bundle)
            try:
                yield unzip_bundle
            finally:
                await unzip_bundle.close()


class UnzipResourceBundle:
    """Bundle that decompresses resources."""

    def __init__(self, base_bundle: Any) -> None:
        """Initialize the unzip resource bundle with base bundle.

        Args:
            base_bundle: The underlying bundle to decorate.
        """
        self.base_bundle = base_bundle

    async def write_resource(
        self,
        url: str,
        content_type: str | None,
        status_code: int,
        stream: AsyncGenerator[bytes, None],
    ) -> None:
        """Write a resource with decompression using streaming."""
        # Stream to temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            try:
                # Stream content to temp file
                async for chunk in stream:
                    temp_file.write(chunk)
                temp_file.flush()
                temp_file.close()

                # Check if content is compressed
                if self._is_gzipped_file(temp_file.name):
                    await self._write_decompressed_gzip_file(
                        url, content_type, status_code, temp_file.name
                    )
                elif self._is_zipped_file(temp_file.name):
                    await self._write_decompressed_zip_file(
                        url, content_type, status_code, temp_file.name
                    )
                else:
                    # Stream original content from temp file
                    await self._stream_temp_file_to_storage(
                        url, content_type, status_code, temp_file.name
                    )

            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_file.name)
                except OSError:
                    pass

    def _is_gzipped_file(self, filepath: str) -> bool:
        """Check if file is gzipped by reading first 2 bytes."""
        with open(filepath, "rb") as f:
            header = f.read(2)
        return header.startswith(b"\x1f\x8b")

    def _is_zipped_file(self, filepath: str) -> bool:
        """Check if file is a zip file by reading first 2 bytes."""
        with open(filepath, "rb") as f:
            header = f.read(2)
        return header.startswith(b"PK")

    async def _stream_temp_file_to_storage(
        self, url: str, content_type: str | None, status_code: int, filepath: str
    ) -> None:
        """Stream a temp file to storage without loading into memory."""

        async def file_stream() -> AsyncGenerator[bytes, None]:
            with open(filepath, "rb") as f:
                while True:
                    chunk = f.read(8192)  # 8KB chunks
                    if not chunk:
                        break
                    yield chunk

        await self.base_bundle.write_resource(
            url=url,
            content_type=content_type,
            status_code=status_code,
            stream=file_stream(),
        )

    async def _write_decompressed_gzip_file(
        self, url: str, content_type: str | None, status_code: int, filepath: str
    ) -> None:
        """Decompress gzip file and stream to storage."""
        try:
            # Stream decompressed content
            async def gzip_stream() -> AsyncGenerator[bytes, None]:
                with gzip.open(filepath, "rb") as gz_file:
                    while True:
                        chunk = gz_file.read(8192)  # 8KB chunks
                        if not chunk:
                            break
                        yield chunk

            await self.base_bundle.write_resource(
                url=f"{url}.decompressed",
                content_type=content_type,
                status_code=status_code,
                stream=gzip_stream(),
            )
        except Exception as e:
            logger.error(
                "Error decompressing gzip", url=url, error=str(e), exc_info=True
            )
            # Stream original content as fallback
            await self._stream_temp_file_to_storage(
                url, content_type, status_code, filepath
            )

    async def _write_decompressed_zip_file(
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
                    ) -> AsyncGenerator[bytes, None]:
                        with zip_file.open(filename) as zf:
                            while True:
                                chunk = zf.read(8192)  # 8KB chunks
                                if not chunk:
                                    break
                                yield chunk

                    # Write extracted file
                    extracted_url = f"{url}/{filename}"
                    await self.base_bundle.write_resource(
                        url=extracted_url,
                        content_type="application/octet-stream",
                        status_code=status_code,
                        stream=create_zip_stream(zip_file, filename),
                    )
        except Exception as e:
            logger.error(
                "Error decompressing zip", url=url, error=str(e), exc_info=True
            )
            # Stream original content as fallback
            await self._stream_temp_file_to_storage(
                url, content_type, status_code, filepath
            )

    async def _write_decompressed_gzip(
        self, url: str, content_type: str | None, status_code: int, content: bytes
    ) -> None:
        """Write decompressed gzip content."""
        try:
            decompressed = gzip.decompress(content)
            await self.base_bundle.write_resource(
                url=f"{url}.decompressed",
                content_type=content_type,
                status_code=status_code,
                stream=self._stream_from_bytes(decompressed),
            )
        except Exception as e:
            logger.error(
                "Error decompressing gzip", url=url, error=str(e), exc_info=True
            )
            # Write original content as fallback
            await self.base_bundle.write_resource(
                url=url,
                content_type=content_type,
                status_code=status_code,
                stream=self._stream_from_bytes(content),
            )

    async def _write_decompressed_zip(
        self, url: str, content_type: str | None, status_code: int, content: bytes
    ) -> None:
        """Write decompressed zip content."""
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zip_file:
                for zip_info in zip_file.filelist:
                    if zip_info.is_dir():
                        continue

                    # Extract file
                    filename = zip_info.filename
                    extracted_content = zip_file.read(filename)

                    # Write extracted file
                    extracted_url = f"{url}/{filename}"
                    await self.base_bundle.write_resource(
                        url=extracted_url,
                        content_type="application/octet-stream",
                        status_code=status_code,
                        stream=self._stream_from_bytes(extracted_content),
                    )
        except Exception as e:
            logger.error(
                "Error decompressing zip", url=url, error=str(e), exc_info=True
            )
            # Write original content as fallback
            await self.base_bundle.write_resource(
                url=url,
                content_type=content_type,
                status_code=status_code,
                stream=self._stream_from_bytes(content),
            )

    async def _stream_from_bytes(self, data: bytes) -> AsyncGenerator[bytes, None]:
        """Create a stream from bytes."""
        yield data

    async def close(self) -> None:
        """Close the unzip bundle."""
        await self.base_bundle.close()
