"""Tests for SFTP loader implementation.

This module contains unit tests for SFTP loader functionality.
"""

from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from data_fetcher_core.core import FetcherRecipe, FetchRunContext, RequestMeta
from data_fetcher_core.protocol_config import SftpProtocolConfig
from data_fetcher_core.storage import FileStorage
from data_fetcher_sftp.sftp_loader import SftpBundleLoader


def create_mock_storage() -> Mock:
    """Create a properly configured mock storage."""
    return Mock(spec=FileStorage)


def setup_storage_bundle_mock(mock_storage: Mock) -> AsyncMock:
    """Set up the storage bundle mock properly."""
    mock_bundle_context = AsyncMock()
    mock_bundle_context.add_resource = AsyncMock()
    mock_bundle_context.complete = AsyncMock()
    # start_bundle is awaited and returns the bundle context directly
    mock_storage.start_bundle = AsyncMock(return_value=mock_bundle_context)
    return mock_bundle_context


class TestSftpBundleLoader:
    """Test SftpBundleLoader class."""

    @pytest.fixture
    def mock_sftp_manager(self, monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
        """Provide a patched SftpManager instance used inside the loader."""
        mgr = AsyncMock()
        mgr.stat = AsyncMock()
        mgr.listdir = AsyncMock(return_value=[])
        # open() is awaited and returns a sync context manager
        file_ctx = MagicMock()
        file_ctx.__enter__.return_value = MagicMock()
        file_ctx.__exit__.return_value = None
        mgr.open = AsyncMock(return_value=file_ctx)

        # Patch constructor to return our mock manager
        monkeypatch.setattr(
            "data_fetcher_sftp.sftp_loader.SftpManager", lambda: mgr, raising=True
        )
        return mgr

    @pytest.fixture
    def mock_sftp_config(self) -> SftpProtocolConfig:
        """Create a mock SFTP protocol config."""
        return SftpProtocolConfig(
            config_name="test_config",
            connect_timeout=10.0,
            rate_limit_requests_per_second=5.0,
        )

    @pytest.fixture
    def loader(self, mock_sftp_config: SftpProtocolConfig) -> SftpBundleLoader:
        """Create a loader instance for testing."""
        return SftpBundleLoader(
            sftp_config=mock_sftp_config,
            remote_dir="/remote/path",
            filename_pattern="*.txt",
            meta_load_name="test_sftp_loader",
        )

    def test_loader_creation(
        self, loader: SftpBundleLoader, mock_sftp_config: SftpProtocolConfig
    ) -> None:
        """Test loader creation."""
        assert loader.sftp_config == mock_sftp_config
        assert loader.remote_dir == "/remote/path"
        assert loader.filename_pattern == "*.txt"
        assert loader.meta_load_name == "test_sftp_loader"

    @pytest.mark.asyncio
    async def test_load_sftp_file(
        self, loader: SftpBundleLoader, mock_sftp_manager: AsyncMock
    ) -> None:
        """Test loading SFTP file."""
        # Mock file stat (not a directory)
        mock_stat = Mock()
        mock_stat.st_mode = 0o644  # Regular file
        mock_stat.st_size = 1024
        mock_stat.st_mtime = 1234567890
        mock_sftp_manager.stat.return_value = mock_stat

        # Mock file stream
        mock_file = Mock()
        mock_file.read.return_value = b"file content"
        # Ensure the context manager yields our file-like
        mock_sftp_manager.open.return_value.__enter__.return_value = mock_file

        # Create request and context
        request = RequestMeta(url="sftp://example.com/remote/file.txt")
        ctx = FetchRunContext(run_id="test_run")
        recipe = FetcherRecipe(recipe_id="test_recipe")

        # Mock storage bundle
        mock_storage = Mock()
        # setup_storage_bundle_mock configures mock_storage.start_bundle but we don't need the returned mock_bundle
        setup_storage_bundle_mock(mock_storage)

        # Load the request
        bundle_refs = await loader.load(request, mock_storage, ctx, recipe)

        # Verify results
        assert len(bundle_refs) == 1
        assert (
            bundle_refs[0].primary_url
            == "sftp:///remote/path/example.com/remote/file.txt"
        )

        # Verify SFTP manager was used at least once for stat and open
        assert mock_sftp_manager.stat.call_count >= 1
        assert mock_sftp_manager.open.await_count == 1

    @pytest.mark.asyncio
    async def test_load_with_sftp_error(
        self, loader: SftpBundleLoader, mock_sftp_manager: AsyncMock
    ) -> None:
        """Test loading when SFTP manager raises an error."""
        # Mock SFTP manager to raise an exception on stat
        mock_sftp_manager.stat.side_effect = Exception("SFTP error")

        # Create request and context
        request = RequestMeta(url="sftp://example.com/remote/file.txt")
        ctx = FetchRunContext(run_id="test_run")
        recipe = FetcherRecipe(recipe_id="test_recipe")

        # Mock storage bundle
        mock_storage = Mock()
        # setup_storage_bundle_mock configures mock_storage.start_bundle but we don't need the returned mock_bundle
        setup_storage_bundle_mock(mock_storage)

        # Load the request - should handle error gracefully
        bundle_refs = await loader.load(request, mock_storage, ctx, recipe)

        # Should return empty list or handle error appropriately
        assert isinstance(bundle_refs, list)
