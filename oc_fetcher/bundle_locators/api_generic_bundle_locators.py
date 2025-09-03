"""Generic bundle locator implementations.

This module provides generic bundle locators that can work with various data
sources, including file systems, databases, and custom data providers.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import structlog

from ..core import BundleRef, FetchRunContext, RequestMeta
from ..kv_store import KeyValueStore, get_global_store
from ..protocols import SftpManager

# Get logger for this module
logger = structlog.get_logger(__name__)


@dataclass
class GenericDirectoryBundleLocator:
    """Generic bundle locator for SFTP directories with custom filtering."""

    sftp_manager: SftpManager
    remote_dir: str = "/"
    filename_pattern: str = "*"
    max_files: int | None = None
    file_filter: Callable[[str], bool] | None = None
    sort_key: Callable[[str, float | int | None], Any] | None = None
    sort_reverse: bool = True
    persistence_prefix: str = "sftp_directory_provider"

    def __post_init__(self) -> None:
        """Initialize the generic directory bundle locator state and internal variables."""
        self._processed_files: set[str] = set()
        self._file_queue: list[str] = []
        self._initialized: bool = False
        self._store: KeyValueStore | None = None

    async def _get_store(self) -> KeyValueStore:
        """Get the key-value store instance."""
        if self._store is None:
            self._store = await get_global_store()
        return self._store

    async def _load_persistence_state(self) -> None:
        """Load persistence state from kvstore."""
        store = await self._get_store()

        # Load processed files
        processed_files_key = (
            f"{self.persistence_prefix}:processed_files:{self.remote_dir}"
        )
        processed_files_data = await store.get(processed_files_key, [])
        if isinstance(processed_files_data, list):
            self._processed_files = set(processed_files_data)
        else:
            self._processed_files = set()

        # Load file queue if available
        queue_key = f"{self.persistence_prefix}:file_queue:{self.remote_dir}"
        queue_data = await store.get(queue_key, [])
        if queue_data and isinstance(queue_data, list):
            self._file_queue = queue_data
            self._initialized = True

    async def _save_persistence_state(self) -> None:
        """Save persistence state to kvstore."""
        store = await self._get_store()

        # Save processed files
        processed_files_key = (
            f"{self.persistence_prefix}:processed_files:{self.remote_dir}"
        )
        await store.put(
            processed_files_key, list(self._processed_files), ttl=timedelta(days=7)
        )

        # Save file queue
        queue_key = f"{self.persistence_prefix}:file_queue:{self.remote_dir}"
        await store.put(queue_key, self._file_queue, ttl=timedelta(days=7))

        # Save initialization state
        init_key = f"{self.persistence_prefix}:initialized:{self.remote_dir}"
        await store.put(init_key, self._initialized, ttl=timedelta(days=7))

    async def _save_processing_result(
        self, request: RequestMeta, bundle_refs: list[BundleRef], success: bool = True
    ) -> None:
        """Save processing result to kvstore."""
        store = await self._get_store()

        remote_path = request.url.replace("sftp://", "")
        result_key = (
            f"{self.persistence_prefix}:results:{self.remote_dir}:{hash(remote_path)}"
        )
        result_data = {
            "remote_path": remote_path,
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "bundle_count": len(bundle_refs),
            "bundle_refs": [str(ref) for ref in bundle_refs],
        }
        await store.put(result_key, result_data, ttl=timedelta(days=30))

    async def _save_error_state(self, request: RequestMeta, error: str) -> None:
        """Save error state for retry logic."""
        store = await self._get_store()

        remote_path = request.url.replace("sftp://", "")
        error_key = (
            f"{self.persistence_prefix}:errors:{self.remote_dir}:{hash(remote_path)}"
        )
        error_data = {
            "remote_path": remote_path,
            "error": error,
            "timestamp": datetime.now().isoformat(),
            "retry_count": 0,
        }
        await store.put(error_key, error_data, ttl=timedelta(hours=24))

    async def get_next_urls(self, ctx: FetchRunContext) -> list[RequestMeta]:
        """Get the next batch of SFTP URLs to process."""
        if not self._initialized:
            await self._load_persistence_state()
            if not self._initialized:
                await self._initialize()

        urls: list[RequestMeta] = []
        while self._file_queue and len(urls) < 10:  # Batch size
            if self.max_files and len(self._processed_files) >= self.max_files:
                break

            file_path = self._file_queue.pop(0)
            if file_path not in self._processed_files:
                urls.append(RequestMeta(url=f"sftp://{file_path}"))
                self._processed_files.add(file_path)

        # Save state after generating URLs
        await self._save_persistence_state()
        return urls

    async def handle_url_processed(
        self, request: RequestMeta, bundle_refs: list[BundleRef], ctx: FetchRunContext
    ) -> None:
        """Handle when a URL has been processed."""
        # Mark as processed
        remote_path = request.url.replace("sftp://", "")
        self._processed_files.add(remote_path)

        # Save processing result
        await self._save_processing_result(request, bundle_refs, success=True)

        # Save state after processing
        await self._save_persistence_state()

    async def handle_url_error(self, request: RequestMeta, error: str) -> None:
        """Handle when a URL processing fails."""
        await self._save_error_state(request, error)
        await self._save_persistence_state()

    async def _initialize(self) -> None:
        """Initialize by listing files in the remote directory."""
        try:
            conn = await self.sftp_manager.get_connection()

            # List files in directory
            files = conn.listdir(self.remote_dir)

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

                # Get file stats for sorting
                try:
                    stat = conn.stat(file_path)
                    file_info.append((file_path, stat.st_mtime))
                except Exception as e:
                    logger.warning(
                        "Error getting stats for file",
                        file_path=file_path,
                        error=str(e),
                    )
                    continue

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
                "Initialized directory provider",
                file_count=len(self._file_queue),
                directory=self.remote_dir,
            )

        except Exception as e:
            logger.error(
                "Error initializing directory provider",
                directory=self.remote_dir,
                error=str(e),
                exc_info=True,
            )

    def _matches_pattern(self, filename: str) -> bool:
        """Check if filename matches the pattern."""
        import fnmatch

        return fnmatch.fnmatch(filename, self.filename_pattern)


@dataclass
class GenericFileBundleLocator:
    """Generic bundle locator for specific SFTP files."""

    sftp_manager: SftpManager
    file_paths: list[str]
    persistence_prefix: str = "sftp_file_provider"

    def __post_init__(self) -> None:
        """Initialize the generic file bundle locator state and internal variables."""
        self._processed_files: set[str] = set()
        self._file_queue: list[str] = self.file_paths.copy()
        self._store: KeyValueStore | None = None

    async def _get_store(self) -> KeyValueStore:
        """Get the key-value store instance."""
        if self._store is None:
            self._store = await get_global_store()
        return self._store

    async def _load_persistence_state(self) -> None:
        """Load persistence state from kvstore."""
        store = await self._get_store()

        # Load processed files
        processed_files_key = f"{self.persistence_prefix}:processed_files"
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

    async def _save_persistence_state(self) -> None:
        """Save persistence state to kvstore."""
        store = await self._get_store()

        # Save processed files
        processed_files_key = f"{self.persistence_prefix}:processed_files"
        await store.put(
            processed_files_key, list(self._processed_files), ttl=timedelta(days=7)
        )

    async def _save_processing_result(
        self, request: RequestMeta, bundle_refs: list[BundleRef], success: bool = True
    ) -> None:
        """Save processing result to kvstore."""
        store = await self._get_store()

        remote_path = request.url.replace("sftp://", "")
        result_key = f"{self.persistence_prefix}:results:{hash(remote_path)}"
        result_data = {
            "remote_path": remote_path,
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "bundle_count": len(bundle_refs),
            "bundle_refs": [str(ref) for ref in bundle_refs],
        }
        await store.put(result_key, result_data, ttl=timedelta(days=30))

    async def get_next_urls(self, ctx: FetchRunContext) -> list[RequestMeta]:
        """Get the next batch of SFTP URLs to process."""
        # Load persistence state on first call
        if not self._processed_files:
            await self._load_persistence_state()

        urls: list[RequestMeta] = []
        while self._file_queue and len(urls) < 10:  # Batch size
            file_path = self._file_queue.pop(0)
            if file_path not in self._processed_files:
                urls.append(RequestMeta(url=f"sftp://{file_path}"))
                self._processed_files.add(file_path)

        # Save state after generating URLs
        await self._save_persistence_state()
        return urls

    async def handle_url_processed(
        self, request: RequestMeta, bundle_refs: list[BundleRef], ctx: FetchRunContext
    ) -> None:
        """Handle when a URL has been processed."""
        # Mark as processed
        remote_path = request.url.replace("sftp://", "")
        self._processed_files.add(remote_path)

        # Save processing result
        await self._save_processing_result(request, bundle_refs, success=True)

        # Save state after processing
        await self._save_persistence_state()

    async def handle_url_error(self, request: RequestMeta, error: str) -> None:
        """Handle when a URL processing fails."""
        store = await self._get_store()

        remote_path = request.url.replace("sftp://", "")
        error_key = f"{self.persistence_prefix}:errors:{hash(remote_path)}"
        error_data = {
            "remote_path": remote_path,
            "error": error,
            "timestamp": datetime.now().isoformat(),
            "retry_count": 0,
        }
        await store.put(error_key, error_data, ttl=timedelta(hours=24))
