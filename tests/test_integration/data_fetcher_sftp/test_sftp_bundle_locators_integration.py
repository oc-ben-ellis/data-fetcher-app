"""Integration tests for SFTP bundle locators.

This module contains integration tests that test the full workflow of the
SFTP bundle locators with real KV store interactions and end-to-end scenarios.
"""

import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from data_fetcher_core.strategy_types import BundleRef, FetchRunContext
from data_fetcher_sftp.sftp_bundle_locators import (
    DirectorySftpBundleLocator,
    FileSftpBundleLocator,
)
from data_fetcher_sftp.sftp_config import SftpProtocolConfig
from data_fetcher_sftp.sftp_manager import SftpManager


class TestDirectorySftpBundleLocatorIntegration:
    """Integration tests for DirectorySftpBundleLocator."""

    @pytest.fixture
    def mock_sftp_manager(self) -> MagicMock:
        """Create a mock SFTP manager."""
        manager = MagicMock(spec=SftpManager)
        manager.get_connection = AsyncMock()
        return manager

    @pytest.fixture
    def mock_sftp_config(self) -> SftpProtocolConfig:
        """Create a mock SFTP config."""
        return SftpProtocolConfig(
            host="test.example.com",
            port=22,
            username="testuser",
            password="testpass"
        )

    @pytest.fixture
    def mock_kv_store(self) -> AsyncMock:
        """Create a mock KV store."""
        store = AsyncMock()
        store.exists = AsyncMock(return_value=False)
        store.put = AsyncMock()
        store.get = AsyncMock(return_value=None)
        return store

    @pytest.fixture
    def mock_context(self, mock_kv_store) -> FetchRunContext:
        """Create a mock fetch run context."""
        context = MagicMock(spec=FetchRunContext)
        context.app_config = MagicMock()
        context.app_config.kv_store = mock_kv_store
        context.app_config.storage = MagicMock()
        context.app_config.storage.bundle_found = MagicMock(return_value="test-bid-123")
        context.app_config.config_id = "test-config"
        return context

    @pytest.fixture
    def locator(self, mock_sftp_manager, mock_sftp_config) -> DirectorySftpBundleLocator:
        """Create a DirectorySftpBundleLocator instance."""
        return DirectorySftpBundleLocator(
            sftp_manager=mock_sftp_manager,
            sftp_config=mock_sftp_config,
            remote_dir="/test/dir",
            filename_pattern="*.txt",
            processed_files_ttl=timedelta(days=7),
            processing_results_ttl=timedelta(days=30),
            error_state_ttl=timedelta(hours=24),
        )

    @pytest.mark.asyncio
    async def test_full_workflow_new_files(self, locator, mock_context, mock_kv_store):
        """Test the full workflow with new files."""
        # Mock SFTP connection and file listing
        mock_conn = AsyncMock()
        mock_conn.listdir = AsyncMock(return_value=["file1.txt", "file2.txt", "file3.log"])
        mock_conn.stat = AsyncMock()
        mock_conn.stat.return_value.st_mtime = 1234567890
        
        locator.sftp_manager.get_connection.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        locator.sftp_manager.get_connection.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Mock all files as not processed initially
        mock_kv_store.exists = AsyncMock(return_value=False)
        
        # Test getting bundle refs (should initialize and process files)
        bundle_refs = await locator.get_next_bundle_refs(mock_context, 5)
        
        # Should have processed 2 files (file1.txt and file2.txt, but not file3.log due to pattern)
        assert len(bundle_refs) == 2
        assert all(isinstance(ref, BundleRef) for ref in bundle_refs)
        
        # Verify KV store calls for file processing checks
        assert mock_kv_store.exists.call_count == 2  # Called for each .txt file
        
        # Test handling bundle processed
        bundle = bundle_refs[0]
        await locator.handle_bundle_processed(bundle, "result", mock_context)
        
        # Verify file was marked as processed
        mock_kv_store.put.assert_called()
        put_calls = mock_kv_store.put.call_args_list
        
        # Should have calls for marking file as processed and saving processing result
        processed_calls = [call for call in put_calls if "processed:" in call[0][0]]
        result_calls = [call for call in put_calls if "results:" in call[0][0]]
        
        assert len(processed_calls) == 1
        assert len(result_calls) == 1
        
        # Verify TTL values were used
        processed_call = processed_calls[0]
        assert processed_call[1]["ttl"] == timedelta(days=7)
        
        result_call = result_calls[0]
        assert result_call[1]["ttl"] == timedelta(days=30)

    @pytest.mark.asyncio
    async def test_full_workflow_with_processed_files(self, locator, mock_context, mock_kv_store):
        """Test the full workflow with some files already processed."""
        # Mock SFTP connection and file listing
        mock_conn = AsyncMock()
        mock_conn.listdir = AsyncMock(return_value=["file1.txt", "file2.txt"])
        mock_conn.stat = AsyncMock()
        mock_conn.stat.return_value.st_mtime = 1234567890
        
        locator.sftp_manager.get_connection.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        locator.sftp_manager.get_connection.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Mock file1.txt as already processed, file2.txt as not processed
        def mock_exists(key):
            return "file1.txt" in key
        
        mock_kv_store.exists = AsyncMock(side_effect=mock_exists)
        
        # Test getting bundle refs
        bundle_refs = await locator.get_next_bundle_refs(mock_context, 5)
        
        # Should only process file2.txt (file1.txt is already processed)
        assert len(bundle_refs) == 1
        assert bundle_refs[0].request_meta["url"] == "sftp:///test/dir/file2.txt"

    @pytest.mark.asyncio
    async def test_error_handling(self, locator, mock_context, mock_kv_store):
        """Test error handling workflow."""
        # Pre-populate queue with a file
        locator._file_queue = ["/test/dir/file1.txt"]
        
        # Test getting bundle refs
        bundle_refs = await locator.get_next_bundle_refs(mock_context, 1)
        assert len(bundle_refs) == 1
        
        # Test handling bundle error
        bundle = bundle_refs[0]
        await locator.handle_bundle_error(bundle, "Test error", mock_context)
        
        # Verify error state was saved
        mock_kv_store.put.assert_called()
        put_calls = mock_kv_store.put.call_args_list
        
        error_calls = [call for call in put_calls if "errors:" in call[0][0]]
        assert len(error_calls) == 1
        
        # Verify TTL value was used
        error_call = error_calls[0]
        assert error_call[1]["ttl"] == timedelta(hours=24)

    @pytest.mark.asyncio
    async def test_max_files_limit(self, locator, mock_context):
        """Test max_files limit functionality."""
        locator.max_files = 1
        
        # Mock SFTP connection and file listing
        mock_conn = AsyncMock()
        mock_conn.listdir = AsyncMock(return_value=["file1.txt", "file2.txt", "file3.txt"])
        mock_conn.stat = AsyncMock()
        mock_conn.stat.return_value.st_mtime = 1234567890
        
        locator.sftp_manager.get_connection.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        locator.sftp_manager.get_connection.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Mock all files as not processed
        mock_context.app_config.kv_store.exists = AsyncMock(return_value=False)
        
        # Test getting bundle refs
        bundle_refs = await locator.get_next_bundle_refs(mock_context, 5)
        
        # Should respect max_files limit
        assert len(bundle_refs) == 1


class TestFileSftpBundleLocatorIntegration:
    """Integration tests for FileSftpBundleLocator."""

    @pytest.fixture
    def mock_sftp_manager(self) -> MagicMock:
        """Create a mock SFTP manager."""
        manager = MagicMock(spec=SftpManager)
        manager.get_connection = AsyncMock()
        return manager

    @pytest.fixture
    def mock_sftp_config(self) -> SftpProtocolConfig:
        """Create a mock SFTP config."""
        return SftpProtocolConfig(
            host="test.example.com",
            port=22,
            username="testuser",
            password="testpass"
        )

    @pytest.fixture
    def mock_kv_store(self) -> AsyncMock:
        """Create a mock KV store."""
        store = AsyncMock()
        store.get = AsyncMock(return_value=None)
        store.put = AsyncMock()
        return store

    @pytest.fixture
    def mock_context(self, mock_kv_store) -> FetchRunContext:
        """Create a mock fetch run context."""
        context = MagicMock(spec=FetchRunContext)
        context.app_config = MagicMock()
        context.app_config.kv_store = mock_kv_store
        context.app_config.storage = MagicMock()
        context.app_config.storage.bundle_found = MagicMock(return_value="test-bid-123")
        context.app_config.config_id = "test-config"
        return context

    @pytest.fixture
    def locator(self, mock_sftp_manager, mock_sftp_config) -> FileSftpBundleLocator:
        """Create a FileSftpBundleLocator instance."""
        return FileSftpBundleLocator(
            sftp_manager=mock_sftp_manager,
            sftp_config=mock_sftp_config,
            file_paths=["/test/file1.txt", "/test/file2.txt"],
            processed_files_ttl=timedelta(days=7),
            processing_results_ttl=timedelta(days=30),
            error_state_ttl=timedelta(hours=24),
        )

    @pytest.mark.asyncio
    async def test_full_workflow_new_files(self, locator, mock_context, mock_kv_store):
        """Test the full workflow with new files."""
        # Mock SFTP connection for file existence and stats
        mock_conn = AsyncMock()
        mock_conn.exists = AsyncMock(return_value=True)
        mock_conn.stat = AsyncMock()
        mock_conn.stat.return_value.st_mtime = 1234567890.0
        
        locator.sftp_manager.get_connection.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        locator.sftp_manager.get_connection.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Mock no previous processing (all files need processing)
        mock_kv_store.get = AsyncMock(return_value=None)
        
        # Test getting bundle refs (should initialize and process files)
        bundle_refs = await locator.get_next_bundle_refs(mock_context, 5)
        
        # Should have processed 2 files
        assert len(bundle_refs) == 2
        assert all(isinstance(ref, BundleRef) for ref in bundle_refs)
        
        # Verify KV store calls for modification time checks
        assert mock_kv_store.get.call_count == 2  # Called for each file
        
        # Test handling bundle processed
        bundle = bundle_refs[0]
        await locator.handle_bundle_processed(bundle, "result", mock_context)
        
        # Verify file was marked as processed with modification time
        mock_kv_store.put.assert_called()
        put_calls = mock_kv_store.put.call_args_list
        
        # Should have calls for marking file as processed and saving processing result
        processed_calls = [call for call in put_calls if "processed_mtime:" in call[0][0]]
        result_calls = [call for call in put_calls if "results:" in call[0][0]]
        
        assert len(processed_calls) == 1
        assert len(result_calls) == 1
        
        # Verify TTL values were used
        processed_call = processed_calls[0]
        assert processed_call[1]["ttl"] == timedelta(days=7)
        
        result_call = result_calls[0]
        assert result_call[1]["ttl"] == timedelta(days=30)

    @pytest.mark.asyncio
    async def test_full_workflow_with_modified_files(self, locator, mock_context, mock_kv_store):
        """Test the full workflow with some files modified since last processing."""
        # Mock SFTP connection for file existence and stats
        mock_conn = AsyncMock()
        mock_conn.exists = AsyncMock(return_value=True)
        mock_conn.stat = AsyncMock()
        mock_conn.stat.return_value.st_mtime = 1234567890.0  # Current time
        
        locator.sftp_manager.get_connection.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        locator.sftp_manager.get_connection.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Mock file1.txt as not modified (same mtime), file2.txt as modified (older mtime)
        def mock_get(key):
            if "file1.txt" in key:
                return 1234567890.0  # Same time - no processing needed
            elif "file2.txt" in key:
                return 1234567800.0  # Older time - processing needed
            return None
        
        mock_kv_store.get = AsyncMock(side_effect=mock_get)
        
        # Test getting bundle refs
        bundle_refs = await locator.get_next_bundle_refs(mock_context, 5)
        
        # Should only process file2.txt (file1.txt hasn't been modified)
        assert len(bundle_refs) == 1
        assert bundle_refs[0].request_meta["url"] == "sftp:///test/file2.txt"

    @pytest.mark.asyncio
    async def test_full_workflow_file_not_exists(self, locator, mock_context, mock_kv_store):
        """Test the full workflow when a file doesn't exist."""
        # Mock SFTP connection for file existence
        mock_conn = AsyncMock()
        mock_conn.exists = AsyncMock(return_value=False)  # File doesn't exist
        
        locator.sftp_manager.get_connection.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        locator.sftp_manager.get_connection.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Test getting bundle refs
        bundle_refs = await locator.get_next_bundle_refs(mock_context, 5)
        
        # Should not process any files (none exist)
        assert len(bundle_refs) == 0

    @pytest.mark.asyncio
    async def test_error_handling(self, locator, mock_context, mock_kv_store):
        """Test error handling workflow."""
        # Pre-populate queue with a file
        locator._file_queue = ["/test/file1.txt"]
        
        # Test getting bundle refs
        bundle_refs = await locator.get_next_bundle_refs(mock_context, 1)
        assert len(bundle_refs) == 1
        
        # Test handling bundle error
        bundle = bundle_refs[0]
        await locator.handle_bundle_error(bundle, "Test error", mock_context)
        
        # Verify error state was saved
        mock_kv_store.put.assert_called()
        put_calls = mock_kv_store.put.call_args_list
        
        error_calls = [call for call in put_calls if "errors:" in call[0][0]]
        assert len(error_calls) == 1
        
        # Verify TTL value was used
        error_call = error_calls[0]
        assert error_call[1]["ttl"] == timedelta(hours=24)


class TestTTLConfigurationIntegration:
    """Integration tests for TTL configuration."""

    @pytest.fixture
    def mock_sftp_manager(self) -> MagicMock:
        """Create a mock SFTP manager."""
        manager = MagicMock(spec=SftpManager)
        manager.get_connection = AsyncMock()
        return manager

    @pytest.fixture
    def mock_sftp_config(self) -> SftpProtocolConfig:
        """Create a mock SFTP config."""
        return SftpProtocolConfig(
            host="test.example.com",
            port=22,
            username="testuser",
            password="testpass"
        )

    @pytest.fixture
    def mock_kv_store(self) -> AsyncMock:
        """Create a mock KV store."""
        store = AsyncMock()
        store.exists = AsyncMock(return_value=False)
        store.put = AsyncMock()
        store.get = AsyncMock(return_value=None)
        return store

    @pytest.fixture
    def mock_context(self, mock_kv_store) -> FetchRunContext:
        """Create a mock fetch run context."""
        context = MagicMock(spec=FetchRunContext)
        context.app_config = MagicMock()
        context.app_config.kv_store = mock_kv_store
        context.app_config.storage = MagicMock()
        context.app_config.storage.bundle_found = MagicMock(return_value="test-bid-123")
        context.app_config.config_id = "test-config"
        return context

    @pytest.mark.asyncio
    async def test_no_ttl_configuration(self, mock_sftp_manager, mock_sftp_config, mock_context, mock_kv_store):
        """Test locator with no TTL configuration (None values)."""
        locator = DirectorySftpBundleLocator(
            sftp_manager=mock_sftp_manager,
            sftp_config=mock_sftp_config,
            remote_dir="/test/dir",
            processed_files_ttl=None,
            processing_results_ttl=None,
            error_state_ttl=None,
        )
        
        # Pre-populate queue
        locator._file_queue = ["/test/dir/file1.txt"]
        
        # Test getting bundle refs
        bundle_refs = await locator.get_next_bundle_refs(mock_context, 1)
        assert len(bundle_refs) == 1
        
        # Test handling bundle processed
        bundle = bundle_refs[0]
        await locator.handle_bundle_processed(bundle, "result", mock_context)
        
        # Verify TTL values were None
        put_calls = mock_kv_store.put.call_args_list
        for call in put_calls:
            assert call[1]["ttl"] is None

    @pytest.mark.asyncio
    async def test_custom_ttl_configuration(self, mock_sftp_manager, mock_sftp_config, mock_context, mock_kv_store):
        """Test locator with custom TTL configuration."""
        locator = DirectorySftpBundleLocator(
            sftp_manager=mock_sftp_manager,
            sftp_config=mock_sftp_config,
            remote_dir="/test/dir",
            processed_files_ttl=timedelta(hours=1),
            processing_results_ttl=timedelta(hours=2),
            error_state_ttl=timedelta(hours=3),
        )
        
        # Pre-populate queue
        locator._file_queue = ["/test/dir/file1.txt"]
        
        # Test getting bundle refs
        bundle_refs = await locator.get_next_bundle_refs(mock_context, 1)
        assert len(bundle_refs) == 1
        
        # Test handling bundle processed
        bundle = bundle_refs[0]
        await locator.handle_bundle_processed(bundle, "result", mock_context)
        
        # Test handling bundle error
        await locator.handle_bundle_error(bundle, "Test error", mock_context)
        
        # Verify custom TTL values were used
        put_calls = mock_kv_store.put.call_args_list
        
        processed_calls = [call for call in put_calls if "processed:" in call[0][0]]
        result_calls = [call for call in put_calls if "results:" in call[0][0]]
        error_calls = [call for call in put_calls if "errors:" in call[0][0]]
        
        assert len(processed_calls) == 1
        assert len(result_calls) == 1
        assert len(error_calls) == 1
        
        assert processed_calls[0][1]["ttl"] == timedelta(hours=1)
        assert result_calls[0][1]["ttl"] == timedelta(hours=2)
        assert error_calls[0][1]["ttl"] == timedelta(hours=3)
