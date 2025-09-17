"""Tar and GZ file decompression and extraction decorator.

This module provides decorators for automatically decompressing and extracting
tar and gzip files during storage operations, with different behaviors based
on file type.
"""

import asyncio
import gzip
import tarfile
import tempfile
from collections.abc import AsyncGenerator
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

from data_fetcher_core.storage.streaming.tee_stream import TeeStream

if TYPE_CHECKING:
    from data_fetcher_core.core import BundleRef, DataRegistryFetcherConfig
    from data_fetcher_core.storage.bundle_storage_context import BundleStorageContext

# Get logger for this module
logger = structlog.get_logger(__name__)


class TarGzResourceDecorator:
    """Decorator that decompresses and extracts tar and gzip resources."""

    def __init__(self, base_storage: object) -> None:
        """Initialize the tar/gz resource decorator with base storage.

        Args:
            base_storage: The underlying storage to decorate.
        """
        self.base_storage = base_storage

    def bundle_found(self, metadata: dict[str, Any]) -> str:
        """Passthrough BID minting to the underlying storage."""
        return self.base_storage.bundle_found(metadata)  # type: ignore[attr-defined]

    async def start_bundle(
        self, bundle_ref: "BundleRef", config: "DataRegistryFetcherConfig"
    ) -> "BundleStorageContext":
        """Initialize a new bundle and return a BundleStorageContext for managing it.

        Args:
            bundle_ref: Reference to the bundle being created.
            config: The fetcher config containing callback information.

        Returns:
            A BundleStorageContext for managing the bundle lifecycle.
        """
        # Get the base storage context
        base_context = await self.base_storage.start_bundle(bundle_ref, config)  # type: ignore[attr-defined]

        # Return a wrapped context that applies decompression/extraction
        return TarGzResourceBundleStorageContext(base_context, self)  # type: ignore[return-value]

    def _is_gzipped_file(self, filepath: str) -> bool:
        """Check if file is gzipped by reading first 2 bytes."""
        with Path(filepath).open("rb") as f:
            header = f.read(2)
        return header.startswith(b"\x1f\x8b")

    def _is_tar_file(self, filepath: str) -> bool:
        """Check if file is a tar file by reading first 2 bytes."""
        with Path(filepath).open("rb") as f:
            header = f.read(2)
        return header.startswith((b"ustar", b"tar"))

    def _is_tar_gz_file(self, filepath: str) -> bool:
        """Check if file is a tar.gz file by checking if it's gzipped and contains tar."""
        if not self._is_gzipped_file(filepath):
            return False

        try:
            with gzip.open(filepath, "rb") as gz_file:
                # Read first few bytes to check for tar signature
                header = gz_file.read(2)
                return header.startswith((b"ustar", b"tar"))
        except Exception:
            return False

    def _strip_compression_suffix(self, url: str) -> str:
        """Strip common compression suffixes from the URL path.

        Args:
            url: Original resource URL that may end with a compression suffix.

        Returns:
            URL string with trailing `.gz`, `.tar`, `.tar.gz` removed from the path.
        """
        try:
            from urllib.parse import urlparse, urlunparse

            parsed = urlparse(url)
            path = parsed.path
            for suffix in (".tar.gz", ".tgz", ".gz", ".tar"):
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
            for suffix in (".tar.gz", ".tgz", ".gz", ".tar"):
                if url.endswith(suffix):
                    return url[: -len(suffix)]
            return url

    def _should_bypass_processing(self, url: str, content_type: str | None) -> bool:
        """Determine whether to bypass processing for this resource.

        Args:
            url: Resource URL.
            content_type: Optional content type.

        Returns:
            True if processing should be bypassed.
        """
        try:
            from urllib.parse import urlparse

            path = urlparse(url).path or ""
            # Bypass if it's a final archive artifact
            if any(
                path.endswith(suffix) for suffix in (".tar.gz", ".tgz", ".tar", ".gz")
            ):
                return True
            # Respect explicit content types
            if content_type and any(
                ct in content_type
                for ct in (
                    "application/gzip",
                    "application/x-tar",
                    "application/x-gtar",
                )
            ):
                return True
        except Exception as e:
            logger.exception(
                "ERROR_CHECKING_IF_PROCESSING_SHOULD_BE_BYPASSED",
                error=str(e),
                url=url,
                content_type=content_type,
            )
        return False


class TarGzResourceBundleStorageContext:
    """Bundle storage context that decompresses and extracts tar/gz resources."""

    def __init__(
        self, base_context: "BundleStorageContext", decorator: "TarGzResourceDecorator"
    ) -> None:
        """Initialize the tar/gz resource bundle storage context.

        Args:
            base_context: The underlying bundle storage context to decorate.
            decorator: The decorator instance for accessing helper methods.
        """
        self.base_context = base_context
        self.decorator = decorator

    async def add_resource(
        self,
        resource_name: str,
        metadata: dict[str, Any],
        stream: AsyncGenerator[bytes],
    ) -> None:
        """Add a resource to the bundle with decompression/extraction.

        Args:
            resource_name: The name of the resource being added.
            metadata: Dictionary containing metadata about the resource.
            stream: Async generator yielding the resource content.
        """
        # Extract metadata with defaults
        url = metadata.get("url", "")
        content_type = metadata.get("content_type")
        metadata.get("status_code", 200)

        logger.debug(
            "TARGZRESOURCEDECORATOR_ADD_RESOURCE_CALLED",
            resource_name=resource_name,
            url=url,
            content_type=content_type,
        )

        # If this looks like an intentional archive artifact, bypass processing
        if self.decorator._should_bypass_processing(url, content_type):  # noqa: SLF001
            await self.base_context.add_resource(
                self.decorator._strip_compression_suffix(resource_name),  # noqa: SLF001
                metadata,
                stream,
            )
            return

        # Create a tee stream to split the input into two streams
        tee_stream = TeeStream(stream)

        # Start streaming to wrapped storage immediately (non-blocking)
        wrapped_task = asyncio.create_task(
            self.base_context.add_resource(
                self.decorator._strip_compression_suffix(resource_name),  # noqa: SLF001
                metadata,
                tee_stream.get_stream(0),
            )
        )

        # Process the second stream to determine file type and handle accordingly
        await self._process_stream_for_compression(
            resource_name, metadata, tee_stream.get_stream(1)
        )

        # Wait for wrapped storage to complete
        await wrapped_task

        # Clean up tee stream
        await tee_stream.close()

    async def _process_stream_for_compression(
        self,
        resource_name: str,
        metadata: dict[str, Any],
        stream: AsyncGenerator[bytes],
    ) -> None:
        """Process the stream to determine compression type and handle accordingly."""
        # Extract metadata with defaults
        metadata.get("url", "")
        metadata.get("content_type")
        metadata.get("status_code", 200)

        # For gz files, we can try streaming decompression first
        # If it fails, fall back to temp file analysis
        try:
            # Try to stream decompress as gz first
            await self._try_stream_gz_decompression(resource_name, metadata, stream)
            return
        except Exception as e:
            logger.debug(
                "STREAM_GZ_DECOMPRESSION_FAILED_FALLING_BACK_TO_TEMP_FILE", error=str(e)
            )

        # Fall back to temp file analysis for tar files or if gz streaming failed
        temp_file_path = await self._stream_to_temp_file(stream)

        try:
            # Determine file type and process accordingly
            if self.decorator._is_tar_gz_file(temp_file_path):  # noqa: SLF001
                logger.debug("DETECTED_TAR_GZ_FILE_PROCESSING")
                await self._process_tar_gz_file(resource_name, metadata, temp_file_path)
            elif self.decorator._is_tar_file(temp_file_path):  # noqa: SLF001
                logger.debug("DETECTED_TAR_FILE_PROCESSING")
                await self._process_tar_file(resource_name, metadata, temp_file_path)
            else:
                logger.debug("FILE_NOT_COMPRESSED_OR_ARCHIVED_NO_ADDITIONAL_PROCESSING")
                # No additional processing needed - content already streamed to storage
        finally:
            # Clean up temp file
            with suppress(OSError):
                Path(temp_file_path).unlink()

    async def _stream_to_temp_file(self, stream: AsyncGenerator[bytes]) -> str:
        """Stream data to a temporary file and return the file path."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            try:
                async for chunk in stream:
                    temp_file.write(chunk)
                temp_file.flush()
                temp_file.close()

                logger.debug(
                    "CONTENT_WRITTEN_TO_TEMP_FILE",
                    temp_file=temp_file.name,
                    size=Path(temp_file.name).stat().st_size,
                )

                return temp_file.name
            except Exception:
                # Clean up temp file on error
                with suppress(OSError):
                    Path(temp_file.name).unlink()
                raise

    async def _try_stream_gz_decompression(
        self,
        resource_name: str,
        metadata: dict[str, Any],
        stream: AsyncGenerator[bytes],
    ) -> None:
        """Try to decompress gz stream directly without temp file.

        This method attempts to stream decompress a GZ file directly. If it's a plain GZ file,
        it will stream the decompressed content. If it's a tar.gz file, it will raise an
        exception to fall back to temp file processing.
        """
        # Check first chunk for GZ magic number
        first_chunk = None
        async for chunk in stream:
            first_chunk = chunk
            break

        if not first_chunk or len(first_chunk) < 2:
            raise ValueError("Stream too short to be a valid GZ file")

        # Check GZ magic number
        if not first_chunk.startswith(b"\x1f\x8b"):
            raise ValueError("Not a GZ file - missing magic number")

        # Create a stream that includes the first chunk
        async def gz_stream_with_header() -> AsyncGenerator[bytes]:
            yield first_chunk
            async for chunk in stream:
                yield chunk

        # Try to stream decompress using zlib for true streaming
        try:
            import zlib

            # Create a streaming decompressor
            decompressor = zlib.decompressobj(wbits=zlib.MAX_WBITS | 16)  # GZIP format

            async def decompressed_stream() -> AsyncGenerator[bytes]:
                # Process the stream in chunks
                async for chunk in gz_stream_with_header():
                    try:
                        # Decompress the chunk
                        decompressed_chunk = decompressor.decompress(chunk)
                        if decompressed_chunk:
                            yield decompressed_chunk
                    except zlib.error as e:
                        # If decompression fails, it might be a tar.gz file
                        raise ValueError(
                            f"GZ decompression failed, might be tar.gz: {e}"
                        )

                # Flush any remaining data
                final_chunk = decompressor.flush()
                if final_chunk:
                    yield final_chunk

            # Stream the decompressed content directly
            decompressed_metadata = {
                **metadata,  # Include all original metadata
                "derived_from": resource_name,  # Track the original resource
            }
            await self.base_context.add_resource(
                resource_name=self.decorator._strip_compression_suffix(resource_name),  # noqa: SLF001
                metadata=decompressed_metadata,
                stream=decompressed_stream(),
            )

            logger.debug("GZ_FILE_DECOMPRESSED_AND_STREAMED")

        except Exception as e:
            # If streaming decompression fails, it's likely a tar.gz file or corrupted
            raise ValueError(f"GZ decompression failed, might be tar.gz: {e}")

    async def _process_gz_file(
        self, resource_name: str, metadata: dict[str, Any], filepath: str
    ) -> None:
        """Process a gz file by streaming the decompressed content."""
        try:
            # Stream decompressed content directly (no temp file needed)
            async def gz_stream() -> AsyncGenerator[bytes]:
                with gzip.open(filepath, "rb") as gz_file:
                    while True:
                        chunk = gz_file.read(8192)  # 8KB chunks
                        if not chunk:
                            break
                        yield chunk

            decompressed_metadata = {
                **metadata,  # Include all original metadata
                "derived_from": resource_name,  # Track the original resource
            }
            await self.base_context.add_resource(
                resource_name=self.decorator._strip_compression_suffix(resource_name),  # noqa: SLF001
                metadata=decompressed_metadata,
                stream=gz_stream(),
            )

            logger.debug("GZ_FILE_DECOMPRESSED_AND_STREAMED")

        except Exception as e:
            logger.exception(
                "GZ_DECOMPRESSION_ERROR", resource_name=resource_name, error=str(e)
            )
            # Note: Original content already streamed to storage via tee stream

    async def _process_tar_file(
        self, resource_name: str, metadata: dict[str, Any], filepath: str
    ) -> None:
        """Process a tar file by extracting and streaming individual files."""
        try:
            with tarfile.open(filepath, "r") as tar_file:
                for tar_info in tar_file.getmembers():
                    if tar_info.isfile():
                        # Stream extracted file
                        async def create_tar_stream(
                            tar_file: tarfile.TarFile, tar_info: tarfile.TarInfo
                        ) -> AsyncGenerator[bytes]:
                            tf = tar_file.extractfile(tar_info)
                            if tf is None:
                                return
                            with tf as file_obj:
                                while True:
                                    chunk = file_obj.read(8192)  # 8KB chunks
                                    if not chunk:
                                        break
                                    yield chunk

                        # Add extracted file
                        extracted_url = f"{self.decorator._strip_compression_suffix(resource_name)}/{tar_info.name}"  # noqa: SLF001
                        extracted_metadata = {
                            "url": extracted_url,
                            "content_type": "application/octet-stream",
                            "status_code": metadata.get("status_code", 200),
                            "derived_from": resource_name,  # Track the original resource
                            **metadata,  # Include all original metadata
                        }
                        await self.base_context.add_resource(
                            resource_name=extracted_url,
                            metadata=extracted_metadata,
                            stream=create_tar_stream(tar_file, tar_info),
                        )

                        logger.debug(
                            "TAR_FILE_EXTRACTED",
                            original_resource_name=resource_name,
                            extracted_url=extracted_url,
                            filename=tar_info.name,
                        )

        except Exception as e:
            logger.exception(
                "TAR_EXTRACTION_ERROR", resource_name=resource_name, error=str(e)
            )
            # Note: Original content already streamed to storage via tee stream

    async def _process_tar_gz_file(
        self, resource_name: str, metadata: dict[str, Any], filepath: str
    ) -> None:
        """Process a tar.gz file by decompressing and extracting individual files."""
        try:
            with gzip.open(filepath, "rb") as gz_file:
                with tarfile.open(fileobj=gz_file, mode="r") as tar_file:
                    for tar_info in tar_file.getmembers():
                        if tar_info.isfile():
                            # Stream extracted file
                            async def create_tar_gz_stream(
                                tar_file: tarfile.TarFile, tar_info: tarfile.TarInfo
                            ) -> AsyncGenerator[bytes]:
                                tf = tar_file.extractfile(tar_info)
                                if tf is None:
                                    return
                                with tf as file_obj:
                                    while True:
                                        chunk = file_obj.read(8192)  # 8KB chunks
                                        if not chunk:
                                            break
                                        yield chunk

                            # Add extracted file
                            extracted_url = f"{self.decorator._strip_compression_suffix(resource_name)}/{tar_info.name}"  # noqa: SLF001
                            extracted_metadata = {
                                "url": extracted_url,
                                "content_type": "application/octet-stream",
                                "status_code": metadata.get("status_code", 200),
                                "derived_from": resource_name,  # Track the original resource
                                **metadata,  # Include all original metadata
                            }
                            await self.base_context.add_resource(
                                resource_name=extracted_url,
                                metadata=extracted_metadata,
                                stream=create_tar_gz_stream(tar_file, tar_info),
                            )

                            logger.debug(
                                "TAR_GZ_FILE_EXTRACTED",
                                original_resource_name=resource_name,
                                extracted_url=extracted_url,
                                filename=tar_info.name,
                            )

        except Exception as e:
            logger.exception(
                "TAR_GZ_EXTRACTION_ERROR", resource_name=resource_name, error=str(e)
            )
            # Note: Original content already streamed to storage via tee stream

    async def complete(self, metadata: dict[str, object]) -> None:
        """Complete the bundle after all uploads are finished.

        Args:
            metadata: Additional metadata to include with the bundle.
        """
        await self.base_context.complete(metadata)
