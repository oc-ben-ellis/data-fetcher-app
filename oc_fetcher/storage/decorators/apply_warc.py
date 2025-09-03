"""WARC file creation and metadata decorator.

This module provides decorators for creating WARC (Web ARChive) files during
storage operations, preserving web content and metadata in standard format.
"""

import os
import tempfile
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from ...core import BundleRef


class ApplyWARCDecorator:
    """Decorator that formats resources as WARC records."""

    def __init__(self, base_storage: Any) -> None:
        """Initialize the WARC decorator with base storage.

        Args:
            base_storage: The underlying storage to decorate.
        """
        self.base_storage = base_storage

    @asynccontextmanager
    async def open_bundle(self, bundle_ref: BundleRef) -> Any:
        """Open a bundle with WARC formatting."""
        async with self.base_storage.open_bundle(bundle_ref) as base_bundle:
            warc_bundle = WARCBundle(base_bundle)
            try:
                yield warc_bundle
            finally:
                await warc_bundle.close()


class WARCBundle:
    """WARC bundle for writing WARC records."""

    def __init__(self, base_bundle: Any) -> None:
        """Initialize the WARC bundle with base bundle.

        Args:
            base_bundle: The underlying bundle to decorate.
        """
        self.base_bundle = base_bundle
        self.warc_records: list[bytes] = []

    async def write_resource(
        self,
        url: str,
        content_type: str | None,
        status_code: int,
        stream: AsyncGenerator[bytes, None],
    ) -> None:
        """Write a resource as a WARC record using streaming."""
        # Stream to temporary file instead of memory
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            try:
                # Stream content to temp file
                async for chunk in stream:
                    temp_file.write(chunk)
                temp_file.flush()

                # Create WARC record from temp file
                warc_record = await self._create_warc_record_from_file(
                    url, content_type, status_code, temp_file.name
                )

                # Write to base storage
                await self.base_bundle.write_resource(
                    url=f"{url}.warc",
                    content_type="application/warc",
                    status_code=status_code,
                    stream=self._stream_from_bytes(warc_record),
                )

                self.warc_records.append(warc_record)

            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_file.name)
                except OSError:
                    pass

    async def _create_warc_record_from_file(
        self, url: str, content_type: str | None, status_code: int, filepath: str
    ) -> bytes:
        """Create a WARC record from a file."""
        # Get file size without loading into memory
        file_size = os.path.getsize(filepath)

        # Create WARC header
        now = datetime.utcnow()
        warc_date = now.strftime("%Y-%m-%dT%H:%M:%SZ")

        warc_header = f"""WARC/1.0\r
WARC-Type: response\r
WARC-Date: {warc_date}\r
WARC-Target-URI: {url}\r
Content-Type: application/http; msgtype=response\r
Content-Length: {file_size + 200}\r
\r
HTTP/1.1 {status_code} OK\r
Content-Type: {content_type or 'application/octet-stream'}\r
Content-Length: {file_size}\r
\r
""".encode()

        # Read file in chunks and append to header
        result = bytearray(warc_header)
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(8192)  # 8KB chunks
                if not chunk:
                    break
                result.extend(chunk)

        return bytes(result)

    async def _create_warc_record(
        self,
        url: str,
        content_type: str | None,
        status_code: int,
        stream: AsyncGenerator[bytes, None],
    ) -> bytes:
        """Create a WARC record from a resource."""
        # Collect content
        content = b""
        async for chunk in stream:
            content += chunk

        # Create WARC header
        now = datetime.utcnow()
        warc_date = now.strftime("%Y-%m-%dT%H:%M:%SZ")

        warc_header = f"""WARC/1.0\r
WARC-Type: response\r
WARC-Date: {warc_date}\r
WARC-Target-URI: {url}\r
Content-Type: application/http; msgtype=response\r
Content-Length: {len(content) + 200}\r
\r
HTTP/1.1 {status_code} OK\r
Content-Type: {content_type or 'application/octet-stream'}\r
Content-Length: {len(content)}\r
\r
""".encode()

        return warc_header + content

    async def _stream_from_bytes(self, data: bytes) -> AsyncGenerator[bytes, None]:
        """Create a stream from bytes."""
        yield data

    async def close(self) -> None:
        """Close the WARC bundle."""
        await self.base_bundle.close()
