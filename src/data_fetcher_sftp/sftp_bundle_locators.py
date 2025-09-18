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
    processed_files_ttl: timedelta | None = None
    processing_results_ttl: timedelta | None = None
    error_state_ttl: timedelta | None = None

    def __post_init__(self) -> None:
        """Initialize the directory SFTP bundle locator state and internal variables."""
        self._file_queue: list[str] = []

    async def _is_file_processed(self, file_path: str, context: FetchRunContext) -> bool:
        """Check if a single file is processed without loading all files into memory."""
        if not context.app_config or not context.app_config.kv_store:
            return False
        
        store = context.app_config.kv_store
        processed_key = f"{self.state_management_prefix}:processed:{self.remote_dir}:{file_path}"
        return await store.exists(processed_key)

    async def _mark_file_processed(self, file_path: str, context: FetchRunContext) -> None:
        """Mark a single file as processed."""
        if not context.app_config or not context.app_config.kv_store:
            return
        
        store = context.app_config.kv_store
        processed_key = f"{self.state_management_prefix}:processed:{self.remote_dir}:{file_path}"
        await store.put(processed_key, True, ttl=self.processed_files_ttl)




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
        await store.put(result_key, result_data, ttl=self.processing_results_ttl)

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
        await store.put(error_key, error_data, ttl=self.error_state_ttl)

    async def get_next_bundle_refs(
        self, ctx: FetchRunContext, bundle_refs_needed: int
    ) -> list[BundleRef]:
        """Get the next batch of SFTP URLs to process."""
        logger.info(
            "GET_NEXT_BUNDLE_REFS_STARTING",
            initialized=len(self._file_queue) > 0,
            bundle_refs_needed=bundle_refs_needed,
        )

        if not self._file_queue:
            await self._initialize(ctx)
        
        logger.info(
            "FILE_QUEUE_STATUS",
            file_queue_size=len(self._file_queue),
        )

        bundle_refs: list[BundleRef] = []
        while self._file_queue and len(bundle_refs) < bundle_refs_needed:
            if self.max_files and len(bundle_refs) >= self.max_files:
                logger.info("MAX_FILES_LIMIT_HIT", max_files=self.max_files)
                break

            file_path = self._file_queue.pop(0)
            logger.info("FILE_POPPED_FROM_QUEUE", file_path=file_path)

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
            bundle_refs.append(
                BundleRef(
                    bid=bid_str,
                    request_meta={
                        "url": f"sftp://{file_path}",
                        "resources_count": 0,
                    },
                )
            )

        logger.info("RETURNING_BUNDLE_REFS_FOR_PROCESSING", bundle_ref_count=len(bundle_refs))

        return bundle_refs

    async def handle_bundle_processed(
        self, bundle: BundleRef, result: object, ctx: FetchRunContext
    ) -> None:
        """Handle when a bundle has been processed."""
        # Mark as processed
        remote_path = str(bundle.request_meta.get("url", "")).replace("sftp://", "")
        await self._mark_file_processed(remote_path, ctx)

        # Save processing result
        await self._save_processing_result(bundle, ctx, success=True)

    async def handle_bundle_error(
        self, bundle: BundleRef, error: str, context: FetchRunContext
    ) -> None:
        """Handle when a bundle processing fails."""
        await self._save_error_state(bundle, error, context)

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

            # Add unprocessed files to in-memory queue
            for file_path, _ in file_info:
                if not await self._is_file_processed(file_path, context):
                    self._file_queue.append(file_path)

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
    processed_files_ttl: timedelta | None = None
    processing_results_ttl: timedelta | None = None
    error_state_ttl: timedelta | None = None

    def __post_init__(self) -> None:
        """Initialize the file SFTP bundle locator state and internal variables."""
        self._file_queue: list[str] = []
        
        # Validate required dependencies
        if not self.sftp_manager:
            raise ValueError("sftp_manager is required for FileSftpBundleLocator")
        if not self.sftp_config:
            raise ValueError("sftp_config is required for FileSftpBundleLocator")

    async def _get_file_processed_mtime(self, file_path: str, context: FetchRunContext) -> float | None:
        """Get the last processed modification time for a file from KV store."""
        if not context.app_config or not context.app_config.kv_store:
            return None
        
        store = context.app_config.kv_store
        processed_key = f"{self.state_management_prefix}:processed_mtime:{file_path}"
        mtime_data = await store.get(processed_key)
        return mtime_data if isinstance(mtime_data, (int, float)) else None

    async def _mark_file_processed_with_mtime(self, file_path: str, mtime: float, context: FetchRunContext) -> None:
        """Mark a file as processed with its modification time in KV store."""
        if not context.app_config or not context.app_config.kv_store:
            return
        
        store = context.app_config.kv_store
        processed_key = f"{self.state_management_prefix}:processed_mtime:{file_path}"
        await store.put(processed_key, mtime, ttl=self.processed_files_ttl)



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
            last_processed_mtime = await self._get_file_processed_mtime(file_path, ctx)

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

    async def _initialize(self, context: FetchRunContext) -> None:
        """Initialize by building queue with unprocessed files."""
        # Add unprocessed files to in-memory queue
        for file_path in self.file_paths:
            if await self._should_process_file(file_path, context):
                self._file_queue.append(file_path)

        logger.info(
            "FILE_PROVIDER_INITIALIZED",
            file_count=len(self._file_queue),
            total_files=len(self.file_paths),
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
        await store.put(result_key, result_data, ttl=self.processing_results_ttl)

    async def get_next_bundle_refs(
        self, ctx: FetchRunContext, bundle_refs_needed: int
    ) -> list[BundleRef]:
        """Get the next batch of SFTP URLs to process."""
        logger.info(
            "GET_NEXT_BUNDLE_REFS_STARTING",
            initialized=len(self._file_queue) > 0,
            bundle_refs_needed=bundle_refs_needed,
        )

        if not self._file_queue:
            await self._initialize(ctx)
        
        logger.info(
            "FILE_QUEUE_STATUS",
            file_queue_size=len(self._file_queue),
        )

        bundle_refs: list[BundleRef] = []
        while self._file_queue and len(bundle_refs) < bundle_refs_needed:
            file_path = self._file_queue.pop(0)
            logger.info("FILE_POPPED_FROM_QUEUE", file_path=file_path)

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
            bundle_refs.append(
                BundleRef(bid=bid_str, request_meta={"url": f"sftp://{file_path}"})
            )

        logger.info("RETURNING_BUNDLE_REFS_FOR_PROCESSING", bundle_ref_count=len(bundle_refs))

        return bundle_refs

    async def handle_bundle_processed(
        self, bundle: BundleRef, result: object, ctx: FetchRunContext
    ) -> None:
        """Handle when a bundle has been processed."""
        remote_path = bundle.request_meta["url"].replace("sftp://", "")

        # Get current file modification time and store it
        try:
            async with await self.sftp_manager.get_connection(
                self.sftp_config, ctx
            ) as conn:
                stat = await conn.stat(remote_path)
            current_mtime = stat.st_mtime
            await self._mark_file_processed_with_mtime(remote_path, current_mtime, ctx)

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

    async def handle_bundle_error(
        self, bundle: BundleRef, error: str, context: FetchRunContext
    ) -> None:
        """Handle when a bundle processing fails."""
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
        await store.put(error_key, error_data, ttl=self.error_state_ttl)
