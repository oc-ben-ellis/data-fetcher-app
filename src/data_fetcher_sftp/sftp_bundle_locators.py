"""SFTP-based bundle locator implementations.

This module provides bundle locators that work with SFTP servers, including
file pattern matching, date-based filtering, and remote directory traversal.
"""

import fnmatch
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import structlog

from data_fetcher_core.core import BundleRef, FetchRunContext
from data_fetcher_core.strategy_types import (
    FileSortStrategyBase,
    FilterStrategyBase,
    LocatorStrategy,
)
from data_fetcher_sftp.sftp_config import SftpProtocolConfig
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
class DirectorySftpBundleLocator(LocatorStrategy):
    """Directory bundle locator for SFTP directories with custom filtering."""

    sftp_manager: SftpManager
    sftp_config: SftpProtocolConfig
    remote_dir: str = "/"
    filename_pattern: str = "*"
    max_files: int | None = None
    file_filter: FilterStrategyBase | None = None
    file_sort: FileSortStrategyBase | None = None
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
        bundle: BundleRef,
        context: FetchRunContext,
        *,
        success: bool = True,
    ) -> None:
        """Save processing result to kvstore."""
        if not context.app_config or not context.app_config.kv_store:
            error_message = "No kv_store available in context - persistence is required for this locator"
            raise ValueError(error_message)
        store = context.app_config.kv_store

        remote_path = str(bundle.request_meta.get("url", "")).replace("sftp://", "")
        result_key = f"{self.state_management_prefix}:results:{self.remote_dir}:{hash(remote_path)}"
        result_data = {
            "remote_path": remote_path,
            "timestamp": datetime.now(UTC).isoformat(),
            "success": success,
            "bundle_bid": str(bundle.bid),
        }
        await store.put(result_key, result_data, ttl=timedelta(days=30))

    async def _save_error_state(
        self, bundle: BundleRef, error: str, context: FetchRunContext
    ) -> None:
        """Save error state for retry logic."""
        if not context.app_config or not context.app_config.kv_store:
            error_message = "No kv_store available in context - error state saving is required for this locator"
            raise ValueError(error_message)
        store = context.app_config.kv_store

        remote_path = str(bundle.request_meta.get("url", "")).replace("sftp://", "")
        error_key = f"{self.state_management_prefix}:errors:{self.remote_dir}:{hash(remote_path)}"
        error_data = {
            "remote_path": remote_path,
            "error": error,
            "timestamp": datetime.now(UTC).isoformat(),
            "retry_count": 0,
        }
        await store.put(error_key, error_data, ttl=timedelta(hours=24))

    async def get_next_bundle_refs(
        self, ctx: FetchRunContext, bundle_refs_needed: int
    ) -> list[BundleRef]:
        """Get the next batch of SFTP URLs to process."""
        logger.info(
            "GET_NEXT_BUNDLE_REFS_STARTING",
            initialized=self._initialized,
            bundle_refs_needed=bundle_refs_needed,
        )

        if not self._initialized:
            await self._load_persistence_state(ctx)
            if not self._initialized:
                await self._initialize(ctx)

        logger.info(
            "FILE_QUEUE_STATUS",
            file_queue_size=len(self._file_queue),
            processed_files_size=len(self._processed_files),
            processed_files_contents=list(self._processed_files),
        )

        urls: list[BundleRef] = []
        while self._file_queue and len(urls) < bundle_refs_needed:
            if self.max_files and len(self._processed_files) >= self.max_files:
                logger.info("MAX_FILES_LIMIT_HIT", max_files=self.max_files)
                break

            file_path = self._file_queue.pop(0)
            logger.info("FILE_POPPED_FROM_QUEUE", file_path=file_path)

            if file_path not in self._processed_files:
                logger.info("NEW_FILE_ADDED_TO_PROCESSING", file_path=file_path)
                if not ctx.app_config or not ctx.app_config.storage:
                    raise ValueError(
                        "Storage is required in app_config for BID minting"
                    )
                storage = ctx.app_config.storage
                bid_str = storage.bundle_found(
                    {
                        "source": "sftp",
                        "primary_url": f"sftp://{file_path}",
                        "config_id": getattr(ctx.app_config, "config_id", "sftp"),
                    }
                )
                urls.append(
                    BundleRef(
                        bid=bid_str,
                        request_meta={
                            "url": f"sftp://{file_path}",
                            "resources_count": 0,
                        },
                    )
                )
                self._processed_files.add(file_path)
            else:
                logger.info("ALREADY_PROCESSED_FILE_SKIPPED", file_path=file_path)

        logger.info("RETURNING_BUNDLE_REFS_FOR_PROCESSING", bundle_ref_count=len(urls))

        # Save state after generating URLs
        await self._save_persistence_state(ctx)
        return urls

    async def handle_url_processed(
        self, bundle: BundleRef, result: object, ctx: FetchRunContext
    ) -> None:
        """Handle when a URL has been processed."""
        # Mark as processed
        remote_path = str(bundle.request_meta.get("url", "")).replace("sftp://", "")
        self._processed_files.add(remote_path)

        # Save processing result
        await self._save_processing_result(bundle, ctx, success=True)

        # Save state after processing
        await self._save_persistence_state(ctx)

    async def handle_url_error(
        self, bundle: BundleRef, error: str, context: FetchRunContext
    ) -> None:
        """Handle when a URL processing fails."""
        await self._save_error_state(bundle, error, context)
        await self._save_persistence_state(context)

    async def _initialize(self, context: FetchRunContext) -> None:
        """Initialize by listing files in the remote directory."""
        try:
            # List files in directory using SFTP manager
            async with await self.sftp_manager.get_connection(
                self.sftp_config, context
            ) as conn:
                files = await conn.listdir(self.remote_dir)

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
                if self.file_filter is not None and not self.file_filter.filter(
                    filename
                ):
                    continue

                # Get file stats for sorting using SFTP manager
                stat = await conn.stat(file_path)
                file_info.append((file_path, stat.st_mtime))

            # Sort files using strategy if provided
            if self.file_sort is not None:
                file_info = self.file_sort.sort(file_info)

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
            # Fail-fast: bubble the error so the fetcher can terminate
            raise

    def _matches_pattern(self, filename: str) -> bool:
        """Check if filename matches the pattern."""
        return fnmatch.fnmatch(filename, self.filename_pattern)


@dataclass
class FileSftpBundleLocator(LocatorStrategy):
    """File bundle locator for specific SFTP files."""

    sftp_manager: SftpManager
    sftp_config: SftpProtocolConfig
    file_paths: list[str]
    state_management_prefix: str = "sftp_file_provider"

    def __post_init__(self) -> None:
        """Initialize the file SFTP bundle locator state and internal variables."""
        self._processed_files: dict[
            str, float
        ] = {}  # file_path -> last_processed_mtime
        self._file_queue: list[str] = self.file_paths.copy()

        # Validate required dependencies
        if not self.sftp_manager:
            raise ValueError("sftp_manager is required for FileSftpBundleLocator")
        if not self.sftp_config:
            raise ValueError("sftp_config is required for FileSftpBundleLocator")

    async def _load_persistence_state(self, context: FetchRunContext) -> None:
        """Load persistence state from kvstore."""
        if not context.app_config or not context.app_config.kv_store:
            raise NoKeyValueStoreError
        store = context.app_config.kv_store

        # Load processed files with their modification times
        processed_files_key = f"{self.state_management_prefix}:processed_files"
        processed_files_data = await store.get(processed_files_key, {})
        if isinstance(processed_files_data, dict):
            self._processed_files = processed_files_data
        else:
            self._processed_files = {}

        # Note: We don't filter the queue here anymore since we need to check
        # modification times dynamically in get_next_bundle_refs

    async def _should_process_file(self, file_path: str, ctx: FetchRunContext) -> bool:
        """Check if a file should be processed based on modification time."""
        try:
            # Check if file exists on SFTP server
            async with await self.sftp_manager.get_connection(
                self.sftp_config, ctx
            ) as conn:
                file_exists = await conn.exists(file_path)
            if not file_exists:
                logger.warning(
                    "FILE_NOT_FOUND_ON_SFTP_SERVER",
                    file_path=file_path,
                )
                return False

            # Get current file modification time
            stat = await conn.stat(file_path)
            current_mtime = stat.st_mtime

            # Check if we've processed this file before
            last_processed_mtime = self._processed_files.get(file_path)

            if last_processed_mtime is None:
                # File has never been processed
                logger.info(
                    "FILE_NEVER_PROCESSED",
                    file_path=file_path,
                    current_mtime=current_mtime,
                )
                return True

            if current_mtime > last_processed_mtime:
                # File has been modified since last processing
                logger.info(
                    "FILE_MODIFIED_SINCE_LAST_PROCESSING",
                    file_path=file_path,
                    current_mtime=current_mtime,
                    last_processed_mtime=last_processed_mtime,
                )
                return True
            # File hasn't changed since last processing
            logger.debug(
                "FILE_UNCHANGED_SINCE_LAST_PROCESSING",
                file_path=file_path,
                current_mtime=current_mtime,
                last_processed_mtime=last_processed_mtime,
            )
            return False

        except Exception as e:
            logger.exception(
                "ERROR_CHECKING_FILE_MODIFICATION_TIME",
                file_path=file_path,
                error=str(e),
            )
            # On error, raise to avoid silent failures
            raise RuntimeError(
                f"Failed to check file modification time for '{file_path}': {e}"
            ) from e

    async def _save_persistence_state(self, context: FetchRunContext) -> None:
        """Save persistence state to kvstore."""
        if not context.app_config or not context.app_config.kv_store:
            error_message = "No kv_store available in context - persistence is required for this locator"
            raise ValueError(error_message)
        store = context.app_config.kv_store

        # Save processed files with their modification times
        processed_files_key = f"{self.state_management_prefix}:processed_files"
        await store.put(
            processed_files_key, self._processed_files, ttl=timedelta(days=7)
        )

    async def _save_processing_result(
        self,
        bundle: BundleRef,
        context: FetchRunContext,
        *,
        success: bool = True,
    ) -> None:
        """Save processing result to kvstore."""
        if not context.app_config or not context.app_config.kv_store:
            error_message = "No kv_store available in context - persistence is required for this locator"
            raise ValueError(error_message)
        store = context.app_config.kv_store

        remote_path = bundle.request_meta["url"].replace("sftp://", "")
        result_key = f"{self.state_management_prefix}:results:{hash(remote_path)}"
        result_data = {
            "remote_path": remote_path,
            "timestamp": datetime.now(UTC).isoformat(),
            "success": success,
            "bundle_bid": str(bundle.bid),
        }
        await store.put(result_key, result_data, ttl=timedelta(days=30))

    async def get_next_bundle_refs(
        self, ctx: FetchRunContext, bundle_refs_needed: int
    ) -> list[BundleRef]:
        """Get the next batch of SFTP URLs to process."""
        # Load persistence state on first call
        if not self._processed_files:
            await self._load_persistence_state(ctx)

        urls: list[BundleRef] = []
        while self._file_queue and len(urls) < bundle_refs_needed:
            file_path = self._file_queue.pop(0)

            # Check if file needs processing based on modification time
            should_process = await self._should_process_file(file_path, ctx)

            if should_process:
                if not ctx.app_config or not ctx.app_config.storage:
                    raise ValueError(
                        "Storage is required in app_config for BID minting"
                    )
                storage = ctx.app_config.storage
                bid_str = storage.bundle_found(
                    {
                        "source": "sftp",
                        "primary_url": f"sftp://{file_path}",
                        "config_id": getattr(ctx.app_config, "config_id", "sftp"),
                    }
                )
                urls.append(
                    BundleRef(bid=bid_str, request_meta={"url": f"sftp://{file_path}"})
                )
                logger.info(
                    "FILE_ADDED_FOR_PROCESSING",
                    file_path=file_path,
                )

        # Save state after generating URLs
        await self._save_persistence_state(ctx)
        return urls

    async def handle_url_processed(
        self, bundle: BundleRef, result: object, ctx: FetchRunContext
    ) -> None:
        """Handle when a URL has been processed."""
        remote_path = bundle.request_meta["url"].replace("sftp://", "")

        # Get current file modification time and store it
        try:
            async with await self.sftp_manager.get_connection(
                self.sftp_config, ctx
            ) as conn:
                stat = await conn.stat(remote_path)
            current_mtime = stat.st_mtime
            self._processed_files[remote_path] = current_mtime

            logger.info(
                "FILE_PROCESSING_COMPLETED", file_path=remote_path, mtime=current_mtime
            )
        except Exception as e:
            logger.exception(
                "ERROR_GETTING_FILE_MODIFICATION_TIME_AFTER_PROCESSING",
                file_path=remote_path,
                error=str(e),
            )
            # On error, raise to avoid silent failures
            raise RuntimeError(
                f"Failed to get file modification time after processing '{remote_path}': {e}"
            ) from e

        # Save processing result
        await self._save_processing_result(bundle, ctx, success=True)

        # Save state after processing
        await self._save_persistence_state(ctx)

    async def handle_url_error(
        self, bundle: BundleRef, error: str, context: FetchRunContext
    ) -> None:
        """Handle when a URL processing fails."""
        if not context.app_config or not context.app_config.kv_store:
            error_message = "No kv_store available in context - error state saving is required for this locator"
            raise ValueError(error_message)
        store = context.app_config.kv_store

        remote_path = bundle.request_meta["url"].replace("sftp://", "")
        error_key = f"{self.state_management_prefix}:errors:{hash(remote_path)}"
        error_data = {
            "remote_path": remote_path,
            "error": error,
            "timestamp": datetime.now(UTC).isoformat(),
            "retry_count": 0,
        }
        await store.put(error_key, error_data, ttl=timedelta(hours=24))
