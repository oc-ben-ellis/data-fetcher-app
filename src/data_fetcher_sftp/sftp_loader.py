"""SFTP data loader implementation."""

import fnmatch
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, Union

import structlog

from data_fetcher_core.core import (
    BundleLoadResult,
    BundleRef,
    DataRegistryFetcherConfig,
    FetchRunContext,
)
from data_fetcher_core.strategy_types import LoaderStrategy
from data_fetcher_sftp.sftp_config import SftpProtocolConfig
from data_fetcher_sftp.sftp_manager import SftpManager


class StorageRequiredError(Exception):
    """Raised when storage is required but not provided."""

    def __init__(self) -> None:
        """Initialize the error."""
        super().__init__("Storage is required but was None")


def _raise_storage_required() -> None:
    """Raise StorageRequiredError."""
    raise StorageRequiredError


if TYPE_CHECKING:
    from data_fetcher_core.storage import DataPipelineBusStorage, FileStorage, S3Storage

# Type alias for storage classes
Storage = Union["FileStorage", "S3Storage", "DataPipelineBusStorage"]


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
class SftpBundleLoader(LoaderStrategy):
    """SFTP loader with AWS integration and file pattern support."""

    sftp_manager: SftpManager
    sftp_config: SftpProtocolConfig
    remote_dir: str = "/"
    filename_pattern: str = "*"
    meta_load_name: str = "sftp_loader"

    async def load(
        self,
        bundle: BundleRef,
        storage: Storage,
        ctx: FetchRunContext,
        recipe: DataRegistryFetcherConfig,
    ) -> BundleLoadResult:
        """Load data from SFTP endpoint.

        Args:
            request: The request to process
            storage: Storage backend for saving data
            ctx: Fetch run context
            recipe: The fetcher recipe configuration

        Returns:
            List of bundle references
        """
        try:
            # List files in remote directory
            remote_path = str(bundle.request_meta.get("url", "")).replace("sftp://", "")
            # If the path doesn't start with /, it's relative to the home directory
            # Don't prefix with remote_dir for relative paths

            # Check if it's a file or directory
            try:
                stat = await self.sftp_manager.stat(self.sftp_config, ctx, remote_path)
                if stat.st_mode is not None and stat.st_mode & 0o40000:  # Directory
                    return await self._load_directory(
                        self.sftp_manager,
                        self.sftp_config,
                        remote_path,
                        bundle,
                        storage,
                        ctx,
                        recipe,
                    )
                # File
                return await self._load_file(
                    self.sftp_manager,
                    self.sftp_config,
                    remote_path,
                    bundle,
                    storage,
                    ctx,
                    recipe,
                )
            except Exception as e:
                logger.exception(
                    "ERROR_ACCESSING_REMOTE_PATH",
                    remote_path=remote_path,
                    error=str(e),
                )
                raise

        except Exception as e:
            logger.exception(
                "ERROR_LOADING_SFTP_REQUEST",
                url=str(bundle.meta.get("primary_url", "unknown")),
                error=str(e),
            )
            raise

    async def _load_file(
        self,
        sftp_manager: SftpManager,
        sftp_config: SftpProtocolConfig,
        remote_path: str,
        bundle: BundleRef,
        storage: Storage,
        _ctx: FetchRunContext,
        recipe: DataRegistryFetcherConfig,
    ) -> BundleLoadResult:
        """Load a single file from SFTP."""
        try:
            # Get file info
            stat = await sftp_manager.stat(sftp_config, _ctx, remote_path)

            # Update incoming bundle request_meta with file details
            bundle.request_meta.update({
                "url": f"sftp://{self.remote_dir}/{remote_path}",
                "resources_count": 1,
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "permissions": (oct(stat.st_mode) if stat.st_mode is not None else None),
            })

            # Create logger with BID context for tracing
            bid_logger = logger.bind(bid=str(bundle.bid))

            # Stream to storage using new BundleStorageContext interface
            if not storage:
                _raise_storage_required()

            bid_logger.debug("STREAMING_FILE_TO_STORAGE", remote_path=remote_path)

            # 1. Start bundle and get context
            bundle_context = await storage.start_bundle(bundle, recipe)

            try:
                # 2. Add file resource
                with await sftp_manager.open(  # type: ignore[attr-defined]
                    sftp_config, _ctx, remote_path, "rb"
                ) as remote_file:
                    await bundle_context.add_resource(
                        resource_name=remote_path,  # Use the file path as resource name
                        metadata={
                            "url": f"sftp://{self.remote_dir}/{remote_path}",
                            "content_type": "application/octet-stream",
                            "status_code": 200,
                        },
                        stream=self._stream_from_file(remote_file),
                    )

                # 3. Complete bundle
                await bundle_context.complete(
                    {"source": "sftp", "run_id": _ctx.run_id, "resources_count": 1}
                )

            except Exception as e:
                # BundleStorageContext will handle cleanup
                bid_logger.exception("Error in bundle processing", error=str(e))
                raise

            bid_logger.debug(
                "SUCCESSFULLY_STREAMED_FILE_TO_STORAGE", remote_path=remote_path
            )

        except Exception as e:
            logger.exception(
                "ERROR_LOADING_FILE",
                remote_path=remote_path,
                error=str(e),
            )
            raise
        else:
            return BundleLoadResult(
                bundle=bundle,
                bundle_meta=bundle.request_meta,
                resources=[
                    {
                        "url": f"sftp://{self.remote_dir}/{remote_path}",
                        "content_type": "application/octet-stream",
                        "status_code": 200,
                    }
                ],
            )

    async def _load_directory(
        self,
        sftp_manager: SftpManager,
        sftp_config: SftpProtocolConfig,
        remote_path: str,
        bundle: BundleRef,
        storage: Storage,
        ctx: FetchRunContext,
        recipe: DataRegistryFetcherConfig,
    ) -> BundleLoadResult:
        """Load all files in a directory from SFTP."""
        resources_meta: list[dict[str, object]] = []

        try:
            # List files in directory
            files = await sftp_manager.listdir(sftp_config, ctx, remote_path)

            for filename in files:
                if filename in [".", ".."]:
                    continue

                file_path = f"{remote_path}/{filename}"

                # Check if file matches pattern
                if not self._matches_pattern(filename):
                    continue

                # Load the file
                file_result = await self._load_file(
                    sftp_manager, sftp_config, file_path, bundle, storage, ctx, recipe
                )
                resources_meta.extend(file_result.resources)

        except Exception as e:
            logger.exception(
                "ERROR_LOADING_DIRECTORY",
                remote_path=remote_path,
                error=str(e),
            )

        if not resources_meta:
            raise RuntimeError("No files matched pattern in directory")
        return BundleLoadResult(
            bundle=bundle, bundle_meta=bundle.request_meta, resources=resources_meta
        )

    def _matches_pattern(self, filename: str) -> bool:
        """Check if filename matches the pattern."""
        return fnmatch.fnmatch(filename, self.filename_pattern)

    async def _stream_from_file(self, file_obj: ReadableFile) -> AsyncGenerator[bytes]:
        """Create an async stream from a file object."""
        while True:
            chunk = file_obj.read(8192)  # 8KB chunks
            if not chunk:
                break
            yield chunk
