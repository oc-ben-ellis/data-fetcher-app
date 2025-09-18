"""Tee stream utility for splitting async generators.

This module provides utilities for splitting a single async generator into multiple
streams, enabling parallel processing while maintaining low memory usage.
"""

import asyncio
import contextlib
from collections.abc import AsyncGenerator

import structlog

# Get logger for this module
logger = structlog.get_logger(__name__)


class TeeStream:
    """Splits an async generator into multiple streams for parallel processing.

    This implementation uses asyncio queues to buffer data between the source
    stream and multiple consumers, enabling true parallel streaming with
    bounded memory usage.
    """

    def __init__(
        self, source_stream: AsyncGenerator[bytes], max_queue_size: int = 10
    ) -> None:
        """Initialize the tee stream.

        Args:
            source_stream: The source async generator to split.
            max_queue_size: Maximum number of chunks to buffer per consumer.
        """
        self.source_stream = source_stream
        self.max_queue_size = max_queue_size
        self.consumers: list[asyncio.Queue[bytes | None]] = []
        self._source_task: asyncio.Task[None] | None = None
        self._closed = False

    def get_stream(self, consumer_id: int = 0) -> AsyncGenerator[bytes]:
        """Get a stream for a specific consumer.

        Args:
            consumer_id: Unique identifier for this consumer.

        Yields:
            Chunks of bytes from the source stream.
        """
        if consumer_id >= len(self.consumers):
            # Create new consumer queue
            queue: asyncio.Queue[bytes | None] = asyncio.Queue(
                maxsize=self.max_queue_size
            )
            self.consumers.append(queue)

            # Start source task if not already running
            if self._source_task is None:
                self._source_task = asyncio.create_task(self._feed_consumers())

        queue = self.consumers[consumer_id]

        async def _stream_generator() -> AsyncGenerator[bytes]:
            try:
                while True:
                    chunk = await queue.get()
                    if chunk is None:  # End of stream signal
                        break
                    yield chunk
            except GeneratorExit:
                # Consumer is closing, mark queue as closed
                with contextlib.suppress(asyncio.QueueFull):
                    queue.put_nowait(None)
                raise

        return _stream_generator()

    async def _feed_consumers(self) -> None:
        """Feed all consumer queues with data from the source stream."""
        try:
            async for chunk in self.source_stream:
                # Send chunk to all active consumers
                for queue in self.consumers:
                    max_retries = 10
                    retry_delay = 0.1  # 100ms

                    for attempt in range(max_retries):
                        try:
                            queue.put_nowait(chunk)
                            break  # Success, move to next queue
                        except asyncio.QueueFull:
                            if attempt == max_retries - 1:
                                # Final attempt failed, raise error
                                raise RuntimeError(
                                    f"Consumer queue full after {max_retries} retries. "
                                    f"Queue size: {queue.qsize()}, max size: {self.max_queue_size}. "
                                    f"Consumer may be stuck or too slow."
                                )
                            # Wait before retrying
                            await asyncio.sleep(retry_delay)

                # Small yield to prevent blocking
                await asyncio.sleep(0)

        except Exception as e:
            logger.exception("Error in tee stream source", error=str(e))
            raise
        finally:
            # Signal end of stream to all consumers
            for queue in self.consumers:
                with contextlib.suppress(asyncio.QueueFull):
                    queue.put_nowait(None)
            self._closed = True

    async def close(self) -> None:
        """Close the tee stream and clean up resources."""
        if self._source_task and not self._source_task.done():
            self._source_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._source_task


class StreamingZipReader:
    """Streaming ZIP file reader that processes ZIP files without loading entire content.

    This implementation reads ZIP files in a streaming fashion, extracting individual
    files as they are encountered without loading the entire ZIP into memory.
    """

    def __init__(self, file_path: str) -> None:
        """Initialize the streaming ZIP reader.

        Args:
            file_path: Path to the ZIP file to read.
        """
        self.file_path = file_path
        self.zip_file: zipfile.ZipFile | None = None

    async def __aenter__(self) -> "StreamingZipReader":
        """Async context manager entry."""
        self.zip_file = zipfile.ZipFile(self.file_path, "r")
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        type_: BaseException | None,
        traceback: object | None,
    ) -> None:
        """Async context manager exit."""
        if self.zip_file:
            self.zip_file.close()

    def get_file_stream(self, filename: str) -> AsyncGenerator[bytes]:
        """Get a stream for a specific file in the ZIP.

        Args:
            filename: Name of the file to stream from the ZIP.

        Yields:
            Chunks of bytes from the specified file.
        """
        if not self.zip_file:
            raise RuntimeError("ZIP file not opened")

        async def _file_stream() -> AsyncGenerator[bytes]:
            try:
                zipf = self.zip_file
                if zipf is None:
                    raise RuntimeError("ZIP file not opened")
                with zipf.open(filename) as zf:
                    while True:
                        chunk = zf.read(8192)  # 8KB chunks
                        if not chunk:
                            break
                        yield chunk
            except KeyError as e:
                logger.warning("File not found in ZIP", filename=filename)
                raise FileNotFoundError(
                    f"File '{filename}' not found in ZIP archive"
                ) from e
            except Exception as e:
                logger.exception(
                    "Error reading file from ZIP", filename=filename, error=str(e)
                )
                raise RuntimeError(
                    f"Failed to read file '{filename}' from ZIP archive: {e}"
                ) from e

        return _file_stream()

    def list_files(self) -> list[str]:
        """List all files in the ZIP archive.

        Returns:
            List of filenames in the ZIP archive.
        """
        if not self.zip_file:
            raise RuntimeError("ZIP file not opened")

        zipf = self.zip_file
        if zipf is None:
            raise RuntimeError("ZIP file not opened")
        return [info.filename for info in zipf.filelist if not info.is_dir()]


# Import zipfile at module level
import zipfile
