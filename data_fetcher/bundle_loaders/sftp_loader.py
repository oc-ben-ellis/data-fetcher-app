"""SFTP data loader implementation."""

import fnmatch
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, Union

import pysftp
import structlog

from data_fetcher.core import BundleRef, FetchRunContext, RequestMeta
from data_fetcher.protocols import SftpManager

if TYPE_CHECKING:
    from data_fetcher.storage import FileStorage, LineageStorage, S3Storage

# Type alias for storage classes
Storage = Union["FileStorage", "S3Storage", "LineageStorage"]


class ReadableFile(Protocol):
    """Protocol for file objects that can be read."""

    def read(self, size: int = -1) -> bytes:
        """Read data from the file."""


"""

SFTP loader with enterprise features.
"""


# Get logger for this module
logger = structlog.get_logger(__name__)


@dataclass
class SFTPLoader:
    """SFTP loader with AWS integration and file pattern support."""

    sftp_manager: SftpManager
    remote_dir: str = "/"
    filename_pattern: str = "*"
    meta_load_name: str = "sftp_loader"

    async def load(
        self, request: RequestMeta, storage: Storage | None, ctx: FetchRunContext
    ) -> list[BundleRef]:
        """Load data from SFTP endpoint.

        Args:
            request: The request to process
            storage: Storage backend for saving data
            ctx: Fetch run context

        Returns:
            List of bundle references
        """
        try:
            # Get SFTP connection
            conn = await self.sftp_manager.get_connection()

            # List files in remote directory
            remote_path = request.url.replace("sftp://", "")
            # If the path doesn't start with /, it's relative to the home directory
            # Don't prefix with remote_dir for relative paths

            # Check if it's a file or directory
            try:
                stat = conn.stat(remote_path)
                if stat.st_mode is not None and stat.st_mode & 0o40000:  # Directory
                    return await self._load_directory(conn, remote_path, storage, ctx)
                # File
                return await self._load_file(conn, remote_path, storage, ctx)
            except Exception as e:
                logger.exception(
                    "Error accessing remote path",
                    remote_path=remote_path,
                    error=str(e),
                )
                return []

        except Exception as e:
            logger.exception(
                "Error loading SFTP request",
                url=request.url,
                error=str(e),
            )
            return []

    async def _load_file(
        self,
        conn: pysftp.Connection,
        remote_path: str,
        storage: Storage | None,
        _ctx: FetchRunContext,
    ) -> list[BundleRef]:
        """Load a single file from SFTP."""
        try:
            # Get file info
            stat = conn.stat(remote_path)

            # Create bundle reference
            bundle_ref = BundleRef(
                primary_url=f"sftp://{self.remote_dir}/{remote_path}",
                resources_count=1,
                meta={
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "permissions": (
                        oct(stat.st_mode) if stat.st_mode is not None else None
                    ),
                },
            )

            # Stream to storage
            if storage:
                async with storage.open_bundle(bundle_ref) as bundle:
                    # Create a temporary file to stream from
                    with conn.open(remote_path, "rb") as remote_file:
                        await bundle.write_resource(
                            url=f"sftp://{self.remote_dir}/{remote_path}",
                            content_type="application/octet-stream",
                            status_code=200,
                            stream=self._stream_from_file(remote_file),
                        )

        except Exception as e:
            logger.exception(
                "Error loading file",
                remote_path=remote_path,
                error=str(e),
            )
            return []
        else:
            return [bundle_ref]

    async def _load_directory(
        self,
        conn: pysftp.Connection,
        remote_path: str,
        storage: Storage | None,
        ctx: FetchRunContext,
    ) -> list[BundleRef]:
        """Load all files in a directory from SFTP."""
        bundle_refs = []

        try:
            # List files in directory
            files = conn.listdir(remote_path)

            for filename in files:
                if filename in [".", ".."]:
                    continue

                file_path = f"{remote_path}/{filename}"

                # Check if file matches pattern
                if not self._matches_pattern(filename):
                    continue

                # Load the file
                file_bundles = await self._load_file(conn, file_path, storage, ctx)
                bundle_refs.extend(file_bundles)

        except Exception as e:
            logger.exception(
                "Error loading directory",
                remote_path=remote_path,
                error=str(e),
            )

        return bundle_refs

    def _matches_pattern(self, filename: str) -> bool:
        """Check if filename matches the pattern."""
        return fnmatch.fnmatch(filename, self.filename_pattern)

    async def _stream_from_file(
        self, file_obj: ReadableFile
    ) -> AsyncGenerator[bytes, None]:
        """Create an async stream from a file object."""
        while True:
            chunk = file_obj.read(8192)  # 8KB chunks
            if not chunk:
                break
            yield chunk
