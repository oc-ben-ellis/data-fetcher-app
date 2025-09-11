"""SFTP-based bundle locator implementations.

This module provides bundle locators that work with SFTP servers, including
file pattern matching, date-based filtering, and remote directory traversal.
"""

import fnmatch
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from data_fetcher_core.core import BundleRef, FetchRunContext, RequestMeta
from data_fetcher_core.protocol_config import SftpProtocolConfig
from data_fetcher_sftp.sftp_manager import SftpManager

# Get logger for this module
logger = structlog.get_logger(__name__)


class NoKeyValueStoreError(ValueError):
    """Raised when no key-value store is available in context."""

    def __init__(self) -> None:
        """Initialize the no key-value store error.

        This error is raised when a bundle locator requires persistence
        but no key-value store is available in the context.
        """
        super().__init__(
            "No kv_store available in context - persistence is required for this locator"
        )


@dataclass
class DirectorySftpBundleLocator:
    """Directory bundle locator for SFTP directories with custom filtering."""

    sftp_config: SftpProtocolConfig
    remote_dir: str = "/"
    filename_pattern: str = "*"
    max_files: int | None = None
    file_filter: Callable[[str], bool] | None = None
    sort_key: Callable[[str, float | int | None], Any] | None = None
    sort_reverse: bool = True
    state_management_prefix: str = "sftp_directory_provider"

    def __post_init__(self) -> None:
        """Initialize the directory SFTP bundle locator state and internal variables."""
        self._processed_files: set[str] = set()
        self._file_queue: list[str] = []
        self._initialized: bool = False

    async def _load_persistence_state(self, context: FetchRunContext) -> None:
        """Load persistence state from kvstore."""
        if not context.app_config or not context.app_config.kv_store:
            error_message = "No kv_store available in context - persistence is required for this locator"
            raise ValueError(error_message)
        store = context.app_config.kv_store

        # Load processed files
        processed_files_key = (
            f"{self.state_management_prefix}:processed_files:{self.remote_dir}"
        )
        processed_files_data = await store.get(processed_files_key, [])
        if isinstance(processed_files_data, list):
            self._processed_files = set(processed_files_data)
        else:
            self._processed_files = set()

        # Load file queue if available
        queue_key = f"{self.state_management_prefix}:file_queue:{self.remote_dir}"
        queue_data = await store.get(queue_key, [])
        if queue_data and isinstance(queue_data, list):
            self._file_queue = queue_data
            self._initialized = True

    async def _save_persistence_state(self, context: FetchRunContext) -> None:
        """Save persistence state to kvstore."""
        if not context.app_config or not context.app_config.kv_store:
            error_message = "No kv_store available in context - persistence is required for this locator"
            raise ValueError(error_message)
        store = context.app_config.kv_store

        # Save processed files
        processed_files_key = (
            f"{self.state_management_prefix}:processed_files:{self.remote_dir}"
        )
        await store.put(
            processed_files_key, list(self._processed_files), ttl=timedelta(days=7)
        )

        # Save file queue
        queue_key = f"{self.state_management_prefix}:file_queue:{self.remote_dir}"
        await store.put(queue_key, self._file_queue, ttl=timedelta(days=7))

        # Save initialization state
        init_key = f"{self.state_management_prefix}:initialized:{self.remote_dir}"
        await store.put(init_key, self._initialized, ttl=timedelta(days=7))

    async def _save_processing_result(
        self,
        request: RequestMeta,
        bundle_refs: list[BundleRef],
        context: FetchRunContext,
        *,
        success: bool = True,
    ) -> None:
        """Save processing result to kvstore."""
        if not context.app_config or not context.app_config.kv_store:
            error_message = "No kv_store available in context - persistence is required for this locator"
            raise ValueError(error_message)
        store = context.app_config.kv_store

        remote_path = request.url.replace("sftp://", "")
        result_key = f"{self.state_management_prefix}:results:{self.remote_dir}:{hash(remote_path)}"
        result_data = {
            "remote_path": remote_path,
            "timestamp": datetime.now(UTC).isoformat(),
            "success": success,
            "bundle_count": len(bundle_refs),
            "bundle_refs": [str(ref) for ref in bundle_refs],
        }
        await store.put(result_key, result_data, ttl=timedelta(days=30))

    async def _save_error_state(
        self, request: RequestMeta, error: str, context: FetchRunContext
    ) -> None:
        """Save error state for retry logic."""
        if not context.app_config or not context.app_config.kv_store:
            error_message = "No kv_store available in context - error state saving is required for this locator"
            raise ValueError(error_message)
        store = context.app_config.kv_store

        remote_path = request.url.replace("sftp://", "")
        error_key = f"{self.state_management_prefix}:errors:{self.remote_dir}:{hash(remote_path)}"
        error_data = {
            "remote_path": remote_path,
            "error": error,
            "timestamp": datetime.now(UTC).isoformat(),
            "retry_count": 0,
        }
        await store.put(error_key, error_data, ttl=timedelta(hours=24))

    async def get_next_urls(self, ctx: FetchRunContext) -> list[RequestMeta]:
        """Get the next batch of SFTP URLs to process."""
        logger.info("GET_NEXT_URLS_STARTING", initialized=self._initialized)

        if not self._initialized:
            await self._load_persistence_state(ctx)
            if not self._initialized:
                await self._initialize(ctx)

        logger.info(
            "FILE_QUEUE_STATUS",
            file_queue_size=len(self._file_queue),
            processed_files_size=len(self._processed_files),
            processed_files_contents=list(self._processed_files)
        )

        urls: list[RequestMeta] = []
        BATCH_SIZE = 10  # noqa: N806
        while self._file_queue and len(urls) < BATCH_SIZE:  # Batch size
            if self.max_files and len(self._processed_files) >= self.max_files:
                logger.info("MAX_FILES_LIMIT_HIT", max_files=self.max_files)
                break

            file_path = self._file_queue.pop(0)
            logger.info("FILE_POPPED_FROM_QUEUE", file_path=file_path)

            if file_path not in self._processed_files:
                logger.info("NEW_FILE_ADDED_TO_PROCESSING", file_path=file_path)
                urls.append(RequestMeta(url=f"sftp://{file_path}"))
                self._processed_files.add(file_path)
            else:
                logger.info("ALREADY_PROCESSED_FILE_SKIPPED", file_path=file_path)

        logger.info(
            "RETURNING_URLS_FOR_PROCESSING",
            url_count=len(urls),
            urls=[u.url for u in urls]
        )

        # Save state after generating URLs
        await self._save_persistence_state(ctx)
        return urls

    async def handle_url_processed(
        self, request: RequestMeta, bundle_refs: list[BundleRef], ctx: FetchRunContext
    ) -> None:
        """Handle when a URL has been processed."""
        # Mark as processed
        remote_path = request.url.replace("sftp://", "")
        self._processed_files.add(remote_path)

        # Save processing result
        await self._save_processing_result(request, bundle_refs, ctx, success=True)

        # Save state after processing
        await self._save_persistence_state(ctx)

    async def handle_url_error(
        self, request: RequestMeta, error: str, context: FetchRunContext
    ) -> None:
        """Handle when a URL processing fails."""
        await self._save_error_state(request, error, context)
        await self._save_persistence_state(context)

    async def _initialize(self, context: FetchRunContext) -> None:
        """Initialize by listing files in the remote directory."""
        try:
            # Get SFTP manager from context
            sftp_manager = SftpManager()

            # List files in directory using SFTP manager
            files = await sftp_manager.listdir(
                self.sftp_config, context, self.remote_dir
            )

            # Collect file information
            file_info: list[tuple[str, float | int | None]] = []
            for filename in files:
                if filename in [".", ".."]:
                    continue

                file_path = f"{self.remote_dir}/{filename}"

                # Check if file matches pattern
                if not self._matches_pattern(filename):
                    continue

                # Apply custom filter if provided
                if self.file_filter and not self.file_filter(filename):
                    continue

                # Get file stats for sorting using SFTP manager
                stat = await sftp_manager.stat(self.sftp_config, context, file_path)
                file_info.append((file_path, stat.st_mtime))

            # Sort files if sort_key is provided
            sort_key_func = self.sort_key
            if sort_key_func is not None:
                file_info.sort(
                    key=lambda x: sort_key_func(x[0], x[1]), reverse=self.sort_reverse
                )

            # Add to queue
            for file_path, _ in file_info:
                self._file_queue.append(file_path)

            self._initialized = True
            logger.info(
                "DIRECTORY_PROVIDER_INITIALIZED",
                file_count=len(self._file_queue),
                directory=self.remote_dir,
            )

        except Exception as e:
            logger.exception(
                "Error initializing directory provider",
                directory=self.remote_dir,
                error=str(e),
            )

    def _matches_pattern(self, filename: str) -> bool:
        """Check if filename matches the pattern."""
        return fnmatch.fnmatch(filename, self.filename_pattern)


@dataclass
class FileSftpBundleLocator:
    """File bundle locator for specific SFTP files."""

    sftp_config: SftpProtocolConfig
    file_paths: list[str]
    state_management_prefix: str = "sftp_file_provider"

    def __post_init__(self) -> None:
        """Initialize the file SFTP bundle locator state and internal variables."""
        self._processed_files: set[str] = set()
        self._file_queue: list[str] = self.file_paths.copy()

    async def _load_persistence_state(self, context: FetchRunContext) -> None:
        """Load persistence state from kvstore."""
        if not context.app_config or not context.app_config.kv_store:
            raise NoKeyValueStoreError
        store = context.app_config.kv_store

        # Load processed files
        processed_files_key = f"{self.state_management_prefix}:processed_files"
        processed_files_data = await store.get(processed_files_key, [])
        if isinstance(processed_files_data, list):
            self._processed_files = set(processed_files_data)
        else:
            self._processed_files = set()

        # Filter out already processed files from queue
        self._file_queue = [
            file_path
            for file_path in self._file_queue
            if file_path not in self._processed_files
        ]

    async def _save_persistence_state(self, context: FetchRunContext) -> None:
        """Save persistence state to kvstore."""
        if not context.app_config or not context.app_config.kv_store:
            error_message = "No kv_store available in context - persistence is required for this locator"
            raise ValueError(error_message)
        store = context.app_config.kv_store

        # Save processed files
        processed_files_key = f"{self.state_management_prefix}:processed_files"
        await store.put(
            processed_files_key, list(self._processed_files), ttl=timedelta(days=7)
        )

    async def _save_processing_result(
        self,
        request: RequestMeta,
        bundle_refs: list[BundleRef],
        context: FetchRunContext,
        *,
        success: bool = True,
    ) -> None:
        """Save processing result to kvstore."""
        if not context.app_config or not context.app_config.kv_store:
            error_message = "No kv_store available in context - persistence is required for this locator"
            raise ValueError(error_message)
        store = context.app_config.kv_store

        remote_path = request.url.replace("sftp://", "")
        result_key = f"{self.state_management_prefix}:results:{hash(remote_path)}"
        result_data = {
            "remote_path": remote_path,
            "timestamp": datetime.now(UTC).isoformat(),
            "success": success,
            "bundle_count": len(bundle_refs),
            "bundle_refs": [str(ref) for ref in bundle_refs],
        }
        await store.put(result_key, result_data, ttl=timedelta(days=30))

    async def get_next_urls(self, ctx: FetchRunContext) -> list[RequestMeta]:
        """Get the next batch of SFTP URLs to process."""
        # Load persistence state on first call
        if not self._processed_files:
            await self._load_persistence_state(ctx)

        urls: list[RequestMeta] = []
        BATCH_SIZE = 10  # noqa: N806
        while self._file_queue and len(urls) < BATCH_SIZE:  # Batch size
            file_path = self._file_queue.pop(0)
            if file_path not in self._processed_files:
                urls.append(RequestMeta(url=f"sftp://{file_path}"))
                self._processed_files.add(file_path)

        # Save state after generating URLs
        await self._save_persistence_state(ctx)
        return urls

    async def handle_url_processed(
        self, request: RequestMeta, bundle_refs: list[BundleRef], ctx: FetchRunContext
    ) -> None:
        """Handle when a URL has been processed."""
        # Mark as processed
        remote_path = request.url.replace("sftp://", "")
        self._processed_files.add(remote_path)

        # Save processing result
        await self._save_processing_result(request, bundle_refs, ctx, success=True)

        # Save state after processing
        await self._save_persistence_state(ctx)

    async def handle_url_error(
        self, request: RequestMeta, error: str, context: FetchRunContext
    ) -> None:
        """Handle when a URL processing fails."""
        if not context.app_config or not context.app_config.kv_store:
            error_message = "No kv_store available in context - error state saving is required for this locator"
            raise ValueError(error_message)
        store = context.app_config.kv_store

        remote_path = request.url.replace("sftp://", "")
        error_key = f"{self.state_management_prefix}:errors:{hash(remote_path)}"
        error_data = {
            "remote_path": remote_path,
            "error": error,
            "timestamp": datetime.now(UTC).isoformat(),
            "retry_count": 0,
        }
        await store.put(error_key, error_data, ttl=timedelta(hours=24))
