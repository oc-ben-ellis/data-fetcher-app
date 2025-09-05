"""SFTP-based bundle locator implementations.

This module provides bundle locators that work with SFTP servers, including
file pattern matching, date-based filtering, and remote directory traversal.
"""

import fnmatch
from dataclasses import dataclass

import structlog

from data_fetcher_core.core import BundleRef, FetchRunContext, RequestMeta
from data_fetcher_sftp.sftp_manager import SftpManager

# Get logger for this module
logger = structlog.get_logger(__name__)


@dataclass
class SFTPDirectoryBundleLocator:
    """Bundle locator that generates SFTP URLs for directories."""

    sftp_manager: SftpManager
    remote_dir: str = "/"
    filename_pattern: str = "*"
    max_files: int | None = None

    def __post_init__(self) -> None:
        """Initialize the SFTP directory bundle locator state and internal variables."""
        self._processed_files: set[str] = set()
        self._file_queue: list[str] = []
        self._initialized: bool = False

    async def get_next_urls(self, _ctx: FetchRunContext) -> list[RequestMeta]:
        """Get the next batch of SFTP URLs to process."""
        if not self._initialized:
            await self._initialize()

        BATCH_SIZE = 10  # noqa: N806
        urls: list[RequestMeta] = []
        while self._file_queue and len(urls) < BATCH_SIZE:  # Batch size
            if self.max_files and len(self._processed_files) >= self.max_files:
                break

            file_path = self._file_queue.pop(0)
            if file_path not in self._processed_files:
                urls.append(RequestMeta(url=f"sftp://{file_path}"))
                self._processed_files.add(file_path)

        return urls

    async def handle_url_processed(
        self, request: RequestMeta, _bundle_refs: list[BundleRef], _ctx: FetchRunContext
    ) -> None:
        """Handle when a URL has been processed."""
        # Mark as processed
        remote_path = request.url.replace("sftp://", "")
        self._processed_files.add(remote_path)

    async def _initialize(self) -> None:
        """Initialize by listing files in the remote directory."""
        try:
            conn = await self.sftp_manager.get_connection()

            # List files in directory
            files = conn.listdir(self.remote_dir)

            for filename in files:
                if filename in [".", ".."]:
                    continue

                file_path = f"{self.remote_dir}/{filename}"

                # Check if file matches pattern
                if self._matches_pattern(filename):
                    self._file_queue.append(file_path)

            self._initialized = True

        except Exception as e:
            logger.exception(
                "Error initializing SFTP directory locator",
                remote_dir=self.remote_dir,
                error=str(e),
            )

    def _matches_pattern(self, filename: str) -> bool:
        """Check if filename matches the pattern."""
        return fnmatch.fnmatch(filename, self.filename_pattern)


@dataclass
class SFTPFileBundleLocator:
    """Bundle locator that generates SFTP URLs for individual files."""

    sftp_manager: SftpManager
    file_paths: list[str]

    def __post_init__(self) -> None:
        """Initialize the SFTP file bundle locator state and internal variables."""
        self._processed_files: set[str] = set()
        self._file_queue: list[str] = self.file_paths.copy()

    async def get_next_urls(self, _ctx: FetchRunContext) -> list[RequestMeta]:
        """Get the next batch of SFTP URLs to process."""
        urls: list[RequestMeta] = []

        BATCH_SIZE = 10  # noqa: N806
        while self._file_queue and len(urls) < BATCH_SIZE:  # Batch size
            file_path = self._file_queue.pop(0)
            if file_path not in self._processed_files:
                urls.append(RequestMeta(url=f"sftp://{file_path}"))
                self._processed_files.add(file_path)

        return urls

    async def handle_url_processed(
        self, request: RequestMeta, _bundle_refs: list[BundleRef], _ctx: FetchRunContext
    ) -> None:
        """Handle when a URL has been processed."""
        # Mark as processed
        remote_path = request.url.replace("sftp://", "")
        self._processed_files.add(remote_path)
