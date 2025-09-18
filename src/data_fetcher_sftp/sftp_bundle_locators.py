"""SFTP-based bundle locator implementations.

This module provides bundle locators that work with SFTP servers, including
file pattern matching, date-based filtering, and remote directory traversal.
"""

import fnmatch
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import structlog

from data_fetcher_core.core import BundleRef, FetchRunContext
from data_fetcher_core.queue import BundleRefSerializer, KVStoreQueue
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
    in_flight_ttl: timedelta | None = None

    def __post_init__(self) -> None:
        """Initialize the directory SFTP bundle locator state and internal variables."""
        # No longer using in-memory queue - using kvstore instead

    def _get_queue(self, context: FetchRunContext) -> KVStoreQueue:
        """Get or create the KVStoreQueue for this locator."""
        if not context.app_config or not context.app_config.kv_store:
            raise NoKeyValueStoreError

        namespace = f"{self.state_management_prefix}:queue:{self.remote_dir}"
        return KVStoreQueue(
            kv_store=context.app_config.kv_store,
            namespace=namespace,
            serializer=BundleRefSerializer()
        )

    async def _is_known(self, file_path: str, context: FetchRunContext) -> bool:
        """Check if a file is processed, queued, or in-flight."""
        if not context.app_config or not context.app_config.kv_store:
            return False

        store = context.app_config.kv_store
        # Check if file is processed
        processed_key = f"{self.state_management_prefix}:processed:{self.remote_dir}:{file_path}"
        if await store.exists(processed_key):
            return True

        # Check if file is in-flight
        in_flight_key = f"{self.state_management_prefix}:in_flight:{self.remote_dir}:{file_path}"
        if await store.exists(in_flight_key):
            return True

        # Check if file is in queue by looking at queue contents
        queue = self._get_queue(context)
        queue_size = await queue.size()
        if queue_size > 0:
            # Peek at all items to check if our file is in the queue
            peeked_items = await queue.peek(max_items=queue_size)
            for bundle_ref in peeked_items:
                if isinstance(bundle_ref, BundleRef):
                    queue_file_path = str(bundle_ref.request_meta.get("url", "")).replace("sftp://", "")
                    if queue_file_path == file_path:
                        return True

        return False

    async def _add_bundle_ref_to_in_flight(self, bundle_ref: BundleRef, context: FetchRunContext) -> None:
        """Add a bundle ref to in-flight tracking."""
        if not context.app_config or not context.app_config.kv_store:
            raise NoKeyValueStoreError

        store = context.app_config.kv_store
        file_path = str(bundle_ref.request_meta.get("url", "")).replace("sftp://", "")
        in_flight_key = f"{self.state_management_prefix}:in_flight:{self.remote_dir}:{file_path}"

        # Store the bundle ref data
        bundle_data = {
            "bid": str(bundle_ref.bid),
            "request_meta": bundle_ref.request_meta,
            "file_path": file_path
        }
        await store.put(in_flight_key, bundle_data, ttl=self.in_flight_ttl)

    async def _remove_bundle_ref_from_in_flight(self, bundle_ref: BundleRef, context: FetchRunContext) -> None:
        """Remove a bundle ref from in-flight tracking."""
        if not context.app_config or not context.app_config.kv_store:
            return

        store = context.app_config.kv_store
        file_path = str(bundle_ref.request_meta.get("url", "")).replace("sftp://", "")
        in_flight_key = f"{self.state_management_prefix}:in_flight:{self.remote_dir}:{file_path}"
        await store.delete(in_flight_key)

    async def _recover_in_flight_bundles(self, context: FetchRunContext) -> None:
        """Re-queue any in-flight bundles (assume they failed)."""
        if not context.app_config or not context.app_config.kv_store:
            return

        store = context.app_config.kv_store
        in_flight_prefix = f"{self.state_management_prefix}:in_flight:{self.remote_dir}:"

        # Get all in-flight items
        in_flight_items = await store.range_get(in_flight_prefix)

        if in_flight_items:
            logger.info("RECOVERING_IN_FLIGHT_BUNDLES", count=len(in_flight_items))

            queue = self._get_queue(context)
            recovered_count = 0

            for _, bundle_data in in_flight_items:
                try:
                    # Reconstruct BundleRef
                    bundle_ref = BundleRef(
                        bid=bundle_data["bid"],
                        request_meta=bundle_data["request_meta"]
                    )

                    # Re-queue the bundle
                    await queue.enqueue([bundle_ref])
                    recovered_count += 1

                    # Remove from in-flight
                    file_path = bundle_data["file_path"]
                    in_flight_key = f"{self.state_management_prefix}:in_flight:{self.remote_dir}:{file_path}"
                    await store.delete(in_flight_key)

                except Exception as e:
                    logger.exception(
                        "ERROR_RECOVERING_IN_FLIGHT_BUNDLE",
                        bundle_data=bundle_data,
                        error=str(e)
                    )

            logger.info("IN_FLIGHT_BUNDLES_RECOVERED", recovered_count=recovered_count)

    async def _mark_file_processed(self, file_path: str, context: FetchRunContext) -> None:
        """Mark a single file as processed."""
        if not context.app_config or not context.app_config.kv_store:
            return

        store = context.app_config.kv_store
        processed_key = f"{self.state_management_prefix}:processed:{self.remote_dir}:{file_path}"
        await store.put(processed_key, value=True, ttl=self.processed_files_ttl)




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
        queue = self._get_queue(ctx)
        queue_size = await queue.size()
        logger.info(
            "GET_NEXT_BUNDLE_REFS_STARTING",
            initialized=queue_size > 0,
            bundle_refs_needed=bundle_refs_needed,
        )

        if queue_size == 0:
            await self._initialize(ctx)
            queue_size = await queue.size()

        logger.info(
            "FILE_QUEUE_STATUS",
            file_queue_size=queue_size,
        )

        bundle_refs: list[BundleRef] = []
        while len(bundle_refs) < bundle_refs_needed:
            if self.max_files and len(bundle_refs) >= self.max_files:
                logger.info("MAX_FILES_LIMIT_HIT", max_files=self.max_files)
                break

            # Peek at the head of the queue
            peeked_items = await queue.peek(max_items=1)
            if not peeked_items:
                logger.info("NO_MORE_BUNDLES_IN_QUEUE")
                break

            bundle_ref = peeked_items[0]
            if not isinstance(bundle_ref, BundleRef):
                logger.warning("INVALID_BUNDLE_REF_IN_QUEUE", bundle_ref=bundle_ref)
                # Remove the invalid item and continue
                await queue.dequeue(max_items=1)
                continue

            # Add to in-flight tracking
            await self._add_bundle_ref_to_in_flight(bundle_ref, ctx)

            # Dequeue from queue
            dequeued_items = await queue.dequeue(max_items=1)
            if not dequeued_items:
                # If dequeue failed, remove from in-flight
                await self._remove_bundle_ref_from_in_flight(bundle_ref, ctx)
                logger.warning("DEQUEUE_FAILED_AFTER_PEEK")
                continue

            file_path = str(bundle_ref.request_meta.get("url", "")).replace("sftp://", "")
            logger.info("BUNDLE_POPPED_FROM_QUEUE", file_path=file_path, bid=str(bundle_ref.bid))
            logger.info("NEW_BUNDLE_ADDED_TO_PROCESSING", file_path=file_path, bid=str(bundle_ref.bid))

            bundle_refs.append(bundle_ref)

        logger.info("RETURNING_BUNDLE_REFS_FOR_PROCESSING", bundle_ref_count=len(bundle_refs))

        return bundle_refs

    async def handle_bundle_processed(
        self, bundle: BundleRef, result: object, ctx: FetchRunContext
    ) -> None:
        """Handle when a bundle has been processed."""
        # Remove from in-flight tracking
        await self._remove_bundle_ref_from_in_flight(bundle, ctx)

        # Mark as processed
        remote_path = str(bundle.request_meta.get("url", "")).replace("sftp://", "")
        await self._mark_file_processed(remote_path, ctx)

        # Save processing result
        await self._save_processing_result(bundle, ctx, success=True)

    async def handle_bundle_error(
        self, bundle: BundleRef, error: str, context: FetchRunContext
    ) -> None:
        """Handle when a bundle processing fails."""
        # Remove from in-flight tracking
        await self._remove_bundle_ref_from_in_flight(bundle, context)

        # Save error state
        await self._save_error_state(bundle, error, context)

    async def _initialize(self, context: FetchRunContext) -> None:
        """Initialize by listing files in the remote directory and creating bundle refs."""
        try:
            # First, recover any in-flight bundles
            await self._recover_in_flight_bundles(context)

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

            # Create bundle refs for unprocessed files and add to persistent queue
            queue = self._get_queue(context)
            bundle_refs_to_enqueue = []

            for file_path, _ in file_info:
                if not await self._is_known(file_path, context):
                    # Create bundle ref
                    def _raise_storage_error() -> None:
                        msg = "Storage is required in app_config for BID minting"
                        raise ValueError(msg)
                    
                    if not context.app_config or not context.app_config.storage:
                        _raise_storage_error()
                    storage = context.app_config.storage
                    bid_str = storage.bundle_found(
                        {
                            "source": "sftp",
                            "primary_url": f"sftp://{file_path}",
                            "config_id": getattr(context.app_config, "config_id", "sftp"),
                        }
                    )
                    bundle_ref = BundleRef(
                        bid=bid_str,
                        request_meta={
                            "url": f"sftp://{file_path}",
                            "resources_count": 0,
                        },
                    )

                    bundle_refs_to_enqueue.append(bundle_ref)

            # Enqueue all bundle refs at once
            if bundle_refs_to_enqueue:
                await queue.enqueue(bundle_refs_to_enqueue)

            logger.info(
                "DIRECTORY_PROVIDER_INITIALIZED",
                file_count=len(bundle_refs_to_enqueue),
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
    in_flight_ttl: timedelta | None = None

    def __post_init__(self) -> None:
        """Initialize the file SFTP bundle locator state and internal variables."""
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
        return mtime_data if isinstance(mtime_data, int | float) else None

    async def _mark_file_processed_with_mtime(self, file_path: str, mtime: float, context: FetchRunContext) -> None:
        """Mark a file as processed with its modification time in KV store."""
        if not context.app_config or not context.app_config.kv_store:
            return

        store = context.app_config.kv_store
        processed_key = f"{self.state_management_prefix}:processed_mtime:{file_path}"
        await store.put(processed_key, mtime, ttl=self.processed_files_ttl)

    def _get_queue(self, context: FetchRunContext) -> KVStoreQueue:
        """Get the KVStore queue for this locator."""
        if not context.app_config or not context.app_config.kv_store:
            raise NoKeyValueStoreError()
        namespace = f"{self.state_management_prefix}:queue"
        return KVStoreQueue(
            kv_store=context.app_config.kv_store,
            namespace=namespace,
            serializer=BundleRefSerializer()
        )

    async def _is_known(self, file_path: str, context: FetchRunContext) -> bool:
        """Check if a file is known (processed, in-flight, or queued)."""
        # Check if file is already processed
        if await self._get_file_processed_mtime(file_path, context) is not None:
            return True

        # Check if file is in-flight
        if not context.app_config or not context.app_config.kv_store:
            return False
        store = context.app_config.kv_store
        in_flight_key = f"{self.state_management_prefix}:in_flight:{file_path}"
        in_flight_data = await store.get(in_flight_key)
        if in_flight_data is not None:
            return True

        # Check if file is in queue by peeking
        try:
            queue = self._get_queue(context)
            peeked_items = await queue.peek(max_items=100)  # Peek at more items to check
            for bundle_ref in peeked_items:
                if isinstance(bundle_ref, BundleRef):
                    bundle_file_path = bundle_ref.request_meta.get("url", "").replace("sftp://", "")
                    if bundle_file_path == file_path:
                        return True
        except Exception:
            # If we can't peek, assume not in queue
            pass

        return False

    async def _add_bundle_ref_to_in_flight(self, bundle_ref: BundleRef, context: FetchRunContext) -> None:
        """Add a bundle ref to the in-flight tracking."""
        if not context.app_config or not context.app_config.kv_store:
            return

        store = context.app_config.kv_store
        file_path = bundle_ref.request_meta["url"].replace("sftp://", "")
        in_flight_key = f"{self.state_management_prefix}:in_flight:{file_path}"
        await store.put(in_flight_key, bundle_ref, ttl=self.in_flight_ttl)

    async def _remove_bundle_ref_from_in_flight(self, bundle_ref: BundleRef, context: FetchRunContext) -> None:
        """Remove a bundle ref from the in-flight tracking."""
        if not context.app_config or not context.app_config.kv_store:
            return

        store = context.app_config.kv_store
        file_path = bundle_ref.request_meta["url"].replace("sftp://", "")
        in_flight_key = f"{self.state_management_prefix}:in_flight:{file_path}"
        await store.delete(in_flight_key)

    async def _recover_in_flight_bundles(self, context: FetchRunContext) -> None:
        """Recover in-flight bundles by re-queuing them."""
        if not context.app_config or not context.app_config.kv_store:
            return

        store = context.app_config.kv_store
        queue = self._get_queue(context)
        
        # Get all in-flight keys
        in_flight_prefix = f"{self.state_management_prefix}:in_flight:"
        in_flight_keys = await store.range_get(in_flight_prefix)
        
        if not in_flight_keys:
            return

        logger.info("RECOVERING_IN_FLIGHT_BUNDLES", count=len(in_flight_keys))
        
        # Re-queue in-flight bundles
        for key, bundle_ref_data in in_flight_keys.items():
            try:
                if isinstance(bundle_ref_data, BundleRef):
                    await queue.enqueue([bundle_ref_data])
                    logger.debug("RE_QUEUED_IN_FLIGHT_BUNDLE", file_path=bundle_ref_data.request_meta.get("url", ""))
            except Exception as e:
                logger.exception("FAILED_TO_RE_QUEUE_IN_FLIGHT_BUNDLE", key=key, error=str(e))

    async def _initialize(self, context: FetchRunContext) -> None:
        """Initialize the file locator by recovering in-flight bundles and enqueuing new files."""
        # First recover any in-flight bundles
        await self._recover_in_flight_bundles(context)
        
        # Get the queue
        queue = self._get_queue(context)
        
        # Create bundle refs for files that should be processed
        bundle_refs_to_enqueue = []
        
        for file_path in self.file_paths:
            if await self._should_process_file(file_path, context):
                # Create bundle ref
                def _raise_storage_error() -> None:
                    msg = "Storage is required in app_config for BID minting"
                    raise ValueError(msg)
                
                if not context.app_config or not context.app_config.storage:
                    _raise_storage_error()
                storage = context.app_config.storage
                bid_str = storage.bundle_found(
                    {
                        "source": "sftp",
                        "primary_url": f"sftp://{file_path}",
                        "config_id": getattr(context.app_config, "config_id", "sftp"),
                    }
                )
                bundle_ref = BundleRef(
                    bid=bid_str,
                    request_meta={
                        "url": f"sftp://{file_path}",
                        "resources_count": 0,
                    },
                )
                bundle_refs_to_enqueue.append(bundle_ref)
        
        # Enqueue all bundle refs
        if bundle_refs_to_enqueue:
            await queue.enqueue(bundle_refs_to_enqueue)
            logger.info(
                "ENQUEUED_BUNDLE_REFS",
                count=len(bundle_refs_to_enqueue),
                queue_size=await queue.size()
            )



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

            # Check if file is already known (processed, in-flight, or queued)
            if await self._is_known(file_path, ctx):
                logger.debug(
                    "FILE_ALREADY_KNOWN",
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
            bundle_refs_needed=bundle_refs_needed,
        )

        # Get the queue
        queue = self._get_queue(ctx)
        
        # Check if queue is empty and initialize if needed
        queue_size = await queue.size()
        if queue_size == 0:
            await self._initialize(ctx)
            queue_size = await queue.size()

        logger.info(
            "FILE_QUEUE_STATUS",
            queue_size=queue_size,
        )

        bundle_refs: list[BundleRef] = []
        while len(bundle_refs) < bundle_refs_needed:
            # Peek at the next item
            peeked_items = await queue.peek(max_items=1)
            if not peeked_items:
                break
                
            bundle_ref = peeked_items[0]
            
            # Add to in-flight tracking
            await self._add_bundle_ref_to_in_flight(bundle_ref, ctx)
            
            # Dequeue the item
            await queue.dequeue(max_items=1)
            
            bundle_refs.append(bundle_ref)
            logger.info("BUNDLE_REF_DEQUEUED", file_path=bundle_ref.request_meta.get("url", ""))

        logger.info("RETURNING_BUNDLE_REFS_FOR_PROCESSING", bundle_ref_count=len(bundle_refs))

        return bundle_refs

    async def handle_bundle_processed(
        self, bundle: BundleRef, result: object, ctx: FetchRunContext
    ) -> None:
        """Handle when a bundle has been processed."""
        # Remove from in-flight tracking
        await self._remove_bundle_ref_from_in_flight(bundle, ctx)
        
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
        # Remove from in-flight tracking
        await self._remove_bundle_ref_from_in_flight(bundle, context)
        
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
