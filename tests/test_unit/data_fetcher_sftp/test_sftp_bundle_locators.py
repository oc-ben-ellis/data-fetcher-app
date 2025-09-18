"""Tests for SFTP bundle locators.

This module contains unit tests for DirectorySftpBundleLocator and FileSftpBundleLocator,
covering all the recent changes including TTL configuration, memory efficiency improvements,
and queue management.
"""

import asyncio
import unittest
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

from data_fetcher_core.core import BundleRef, FetchRunContext
from data_fetcher_sftp.sftp_bundle_locators import (
    DirectorySftpBundleLocator,
    FileSftpBundleLocator,
)
from data_fetcher_sftp.sftp_config import SftpProtocolConfig
from data_fetcher_sftp.sftp_manager import SftpManager


class TestDirectorySftpBundleLocator(unittest.TestCase):
    """Test DirectorySftpBundleLocator functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_sftp_manager = MagicMock(spec=SftpManager)
        self.mock_sftp_manager.get_connection = AsyncMock()
        
        self.mock_sftp_config = SftpProtocolConfig(
            host="test.example.com",
            port=22,
            username="testuser",
            password="testpass"
        )
        
        self.mock_context = MagicMock(spec=FetchRunContext)
        self.mock_context.app_config = MagicMock()
        self.mock_context.app_config.kv_store = AsyncMock()
        self.mock_context.app_config.storage = MagicMock()
        self.mock_context.app_config.storage.bundle_found = MagicMock(return_value="test-bid-123")
        self.mock_context.app_config.config_id = "test-config"
        
        self.locator = DirectorySftpBundleLocator(
            sftp_manager=self.mock_sftp_manager,
            sftp_config=self.mock_sftp_config,
            remote_dir="/test/dir",
            filename_pattern="*.txt",
            processed_files_ttl=timedelta(days=7),
            processing_results_ttl=timedelta(days=30),
            error_state_ttl=timedelta(hours=24),
        )

    def test_initialization(self):
        """Test locator initialization."""
        self.assertEqual(self.locator.remote_dir, "/test/dir")
        self.assertEqual(self.locator.filename_pattern, "*.txt")
        self.assertEqual(self.locator.processed_files_ttl, timedelta(days=7))
        self.assertEqual(self.locator.processing_results_ttl, timedelta(days=30))
        self.assertEqual(self.locator.error_state_ttl, timedelta(hours=24))
        self.assertEqual(self.locator._file_queue, [])

    def test_initialization_default_ttl(self):
        """Test locator initialization with default TTL values."""
        locator = DirectorySftpBundleLocator(
            sftp_manager=self.mock_sftp_manager,
            sftp_config=self.mock_sftp_config,
            remote_dir="/test/dir",
        )
        self.assertIsNone(locator.processed_files_ttl)
        self.assertIsNone(locator.processing_results_ttl)
        self.assertIsNone(locator.error_state_ttl)

    def test_is_file_processed_true(self):
        """Test checking if a file is processed (returns True)."""
        async def run_test():
            self.mock_context.app_config.kv_store.exists = AsyncMock(return_value=True)
            
            result = await self.locator._is_file_processed("/test/dir/file.txt", self.mock_context)
            
            self.assertTrue(result)
            self.mock_context.app_config.kv_store.exists.assert_called_once_with(
                "sftp_directory_provider:processed:/test/dir:/test/dir/file.txt"
            )
        
        asyncio.run(run_test())

    def test_is_file_processed_false(self):
        """Test checking if a file is processed (returns False)."""
        async def run_test():
            self.mock_context.app_config.kv_store.exists = AsyncMock(return_value=False)
            
            result = await self.locator._is_file_processed("/test/dir/file.txt", self.mock_context)
            
            self.assertFalse(result)
        
        asyncio.run(run_test())

    def test_is_file_processed_no_kv_store(self):
        """Test checking if a file is processed when no KV store is available."""
        async def run_test():
            context = MagicMock(spec=FetchRunContext)
            context.app_config = None
            
            result = await self.locator._is_file_processed("/test/dir/file.txt", context)
            
            self.assertFalse(result)
        
        asyncio.run(run_test())

    def test_mark_file_processed(self):
        """Test marking a file as processed."""
        async def run_test():
            await self.locator._mark_file_processed("/test/dir/file.txt", self.mock_context)
            
            self.mock_context.app_config.kv_store.put.assert_called_once_with(
                "sftp_directory_provider:processed:/test/dir:/test/dir/file.txt",
                True,
                ttl=timedelta(days=7)
            )
        
        asyncio.run(run_test())

    def test_mark_file_processed_no_ttl(self):
        """Test marking a file as processed with no TTL."""
        async def run_test():
            locator = DirectorySftpBundleLocator(
                sftp_manager=self.mock_sftp_manager,
                sftp_config=self.mock_sftp_config,
                remote_dir="/test/dir",
                processed_files_ttl=None,
            )
            
            await locator._mark_file_processed("/test/dir/file.txt", self.mock_context)
            
            self.mock_context.app_config.kv_store.put.assert_called_once_with(
                "sftp_directory_provider:processed:/test/dir:/test/dir/file.txt",
                True,
                ttl=None
            )
        
        asyncio.run(run_test())

    def test_save_processing_result(self):
        """Test saving processing result."""
        async def run_test():
            bundle = BundleRef(
                bid="test-bid-123",
                request_meta={"url": "sftp:///test/dir/file.txt"}
            )
            
            await self.locator._save_processing_result(bundle, self.mock_context, success=True)
            
            self.mock_context.app_config.kv_store.put.assert_called_once()
            call_args = self.mock_context.app_config.kv_store.put.call_args
            self.assertTrue(call_args[0][0].startswith("sftp_directory_provider:results:/test/dir:"))
            self.assertTrue(call_args[0][1]["success"])
            self.assertEqual(call_args[0][1]["bundle_bid"], "test-bid-123")
            self.assertEqual(call_args[1]["ttl"], timedelta(days=30))
        
        asyncio.run(run_test())

    def test_save_error_state(self):
        """Test saving error state."""
        async def run_test():
            bundle = BundleRef(
                bid="test-bid-123",
                request_meta={"url": "sftp:///test/dir/file.txt"}
            )
            
            await self.locator._save_error_state(bundle, "Test error", self.mock_context)
            
            self.mock_context.app_config.kv_store.put.assert_called_once()
            call_args = self.mock_context.app_config.kv_store.put.call_args
            self.assertTrue(call_args[0][0].startswith("sftp_directory_provider:errors:/test/dir:"))
            self.assertEqual(call_args[0][1]["error"], "Test error")
            self.assertEqual(call_args[0][1]["retry_count"], 0)
            self.assertEqual(call_args[1]["ttl"], timedelta(hours=24))
        
        asyncio.run(run_test())

    def test_get_next_bundle_refs_empty_queue(self):
        """Test getting bundle refs when queue is empty."""
        async def run_test():
            # Mock initialization
            self.locator._initialize = AsyncMock()
            
            result = await self.locator.get_next_bundle_refs(self.mock_context, 5)
            
            self.assertEqual(result, [])
            self.locator._initialize.assert_called_once_with(self.mock_context)
        
        asyncio.run(run_test())

    def test_get_next_bundle_refs_with_files(self):
        """Test getting bundle refs when queue has files."""
        async def run_test():
            # Pre-populate queue
            self.locator._file_queue = ["/test/dir/file1.txt", "/test/dir/file2.txt"]
            
            result = await self.locator.get_next_bundle_refs(self.mock_context, 2)
            
            self.assertEqual(len(result), 2)
            self.assertTrue(all(isinstance(ref, BundleRef) for ref in result))
            self.assertEqual(result[0].request_meta["url"], "sftp:///test/dir/file1.txt")
            self.assertEqual(result[1].request_meta["url"], "sftp:///test/dir/file2.txt")
            self.assertEqual(len(self.locator._file_queue), 0)  # Queue should be empty after processing
        
        asyncio.run(run_test())

    def test_get_next_bundle_refs_max_files_limit(self):
        """Test getting bundle refs with max_files limit."""
        async def run_test():
            self.locator.max_files = 1
            self.locator._file_queue = ["/test/dir/file1.txt", "/test/dir/file2.txt"]
            
            result = await self.locator.get_next_bundle_refs(self.mock_context, 5)
            
            self.assertEqual(len(result), 1)  # Should respect max_files limit
            self.assertEqual(result[0].request_meta["url"], "sftp:///test/dir/file1.txt")
        
        asyncio.run(run_test())

    def test_handle_bundle_processed(self):
        """Test handling bundle processed."""
        async def run_test():
            bundle = BundleRef(
                bid="test-bid-123",
                request_meta={"url": "sftp:///test/dir/file.txt"}
            )
            
            self.locator._mark_file_processed = AsyncMock()
            self.locator._save_processing_result = AsyncMock()
            
            await self.locator.handle_bundle_processed(bundle, "result", self.mock_context)
            
            self.locator._mark_file_processed.assert_called_once_with("/test/dir/file.txt", self.mock_context)
            self.locator._save_processing_result.assert_called_once_with(bundle, self.mock_context, success=True)
        
        asyncio.run(run_test())

    def test_handle_bundle_error(self):
        """Test handling bundle error."""
        async def run_test():
            bundle = BundleRef(
                bid="test-bid-123",
                request_meta={"url": "sftp:///test/dir/file.txt"}
            )
            
            self.locator._save_error_state = AsyncMock()
            
            await self.locator.handle_bundle_error(bundle, "Test error", self.mock_context)
            
            self.locator._save_error_state.assert_called_once_with(bundle, "Test error", self.mock_context)
        
        asyncio.run(run_test())


class TestFileSftpBundleLocator(unittest.TestCase):
    """Test FileSftpBundleLocator functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_sftp_manager = MagicMock(spec=SftpManager)
        self.mock_sftp_manager.get_connection = AsyncMock()
        
        self.mock_sftp_config = SftpProtocolConfig(
            host="test.example.com",
            port=22,
            username="testuser",
            password="testpass"
        )
        
        self.mock_context = MagicMock(spec=FetchRunContext)
        self.mock_context.app_config = MagicMock()
        self.mock_context.app_config.kv_store = AsyncMock()
        self.mock_context.app_config.storage = MagicMock()
        self.mock_context.app_config.storage.bundle_found = MagicMock(return_value="test-bid-123")
        self.mock_context.app_config.config_id = "test-config"
        
        self.locator = FileSftpBundleLocator(
            sftp_manager=self.mock_sftp_manager,
            sftp_config=self.mock_sftp_config,
            file_paths=["/test/file1.txt", "/test/file2.txt"],
            processed_files_ttl=timedelta(days=7),
            processing_results_ttl=timedelta(days=30),
            error_state_ttl=timedelta(hours=24),
        )

    def test_initialization(self):
        """Test locator initialization."""
        self.assertEqual(self.locator.file_paths, ["/test/file1.txt", "/test/file2.txt"])
        self.assertEqual(self.locator.processed_files_ttl, timedelta(days=7))
        self.assertEqual(self.locator.processing_results_ttl, timedelta(days=30))
        self.assertEqual(self.locator.error_state_ttl, timedelta(hours=24))
        self.assertEqual(self.locator._file_queue, [])

    def test_initialization_default_ttl(self):
        """Test locator initialization with default TTL values."""
        locator = FileSftpBundleLocator(
            sftp_manager=self.mock_sftp_manager,
            sftp_config=self.mock_sftp_config,
            file_paths=["/test/file1.txt"],
        )
        self.assertIsNone(locator.processed_files_ttl)
        self.assertIsNone(locator.processing_results_ttl)
        self.assertIsNone(locator.error_state_ttl)

    def test_get_file_processed_mtime(self):
        """Test getting file processed modification time."""
        async def run_test():
            self.mock_context.app_config.kv_store.get = AsyncMock(return_value=1234567890.0)
            
            result = await self.locator._get_file_processed_mtime("/test/file.txt", self.mock_context)
            
            self.assertEqual(result, 1234567890.0)
            self.mock_context.app_config.kv_store.get.assert_called_once_with(
                "sftp_file_provider:processed_mtime:/test/file.txt"
            )
        
        asyncio.run(run_test())

    def test_get_file_processed_mtime_none(self):
        """Test getting file processed modification time when not found."""
        async def run_test():
            self.mock_context.app_config.kv_store.get = AsyncMock(return_value=None)
            
            result = await self.locator._get_file_processed_mtime("/test/file.txt", self.mock_context)
            
            self.assertIsNone(result)
        
        asyncio.run(run_test())

    def test_mark_file_processed_with_mtime(self):
        """Test marking a file as processed with modification time."""
        async def run_test():
            await self.locator._mark_file_processed_with_mtime("/test/file.txt", 1234567890.0, self.mock_context)
            
            self.mock_context.app_config.kv_store.put.assert_called_once_with(
                "sftp_file_provider:processed_mtime:/test/file.txt",
                1234567890.0,
                ttl=timedelta(days=7)
            )
        
        asyncio.run(run_test())

    def test_should_process_file_never_processed(self):
        """Test should_process_file when file has never been processed."""
        async def run_test():
            # Mock SFTP connection
            mock_conn = AsyncMock()
            mock_conn.exists = AsyncMock(return_value=True)
            mock_conn.stat = AsyncMock()
            mock_conn.stat.return_value.st_mtime = 1234567890.0
            
            self.locator.sftp_manager.get_connection.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            self.locator.sftp_manager.get_connection.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Mock no previous processing
            self.locator._get_file_processed_mtime = AsyncMock(return_value=None)
            
            result = await self.locator._should_process_file("/test/file.txt", self.mock_context)
            
            self.assertTrue(result)
        
        asyncio.run(run_test())

    def test_should_process_file_modified(self):
        """Test should_process_file when file has been modified."""
        async def run_test():
            # Mock SFTP connection
            mock_conn = AsyncMock()
            mock_conn.exists = AsyncMock(return_value=True)
            mock_conn.stat = AsyncMock()
            mock_conn.stat.return_value.st_mtime = 1234567890.0  # Current time
            
            self.locator.sftp_manager.get_connection.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            self.locator.sftp_manager.get_connection.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Mock previous processing with older time
            self.locator._get_file_processed_mtime = AsyncMock(return_value=1234567800.0)  # Older time
            
            result = await self.locator._should_process_file("/test/file.txt", self.mock_context)
            
            self.assertTrue(result)
        
        asyncio.run(run_test())

    def test_should_process_file_not_modified(self):
        """Test should_process_file when file has not been modified."""
        async def run_test():
            # Mock SFTP connection
            mock_conn = AsyncMock()
            mock_conn.exists = AsyncMock(return_value=True)
            mock_conn.stat = AsyncMock()
            mock_conn.stat.return_value.st_mtime = 1234567890.0  # Current time
            
            self.locator.sftp_manager.get_connection.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            self.locator.sftp_manager.get_connection.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Mock previous processing with same time
            self.locator._get_file_processed_mtime = AsyncMock(return_value=1234567890.0)  # Same time
            
            result = await self.locator._should_process_file("/test/file.txt", self.mock_context)
            
            self.assertFalse(result)
        
        asyncio.run(run_test())

    def test_should_process_file_not_exists(self):
        """Test should_process_file when file does not exist."""
        async def run_test():
            # Mock SFTP connection
            mock_conn = AsyncMock()
            mock_conn.exists = AsyncMock(return_value=False)
            
            self.locator.sftp_manager.get_connection.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            self.locator.sftp_manager.get_connection.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await self.locator._should_process_file("/test/file.txt", self.mock_context)
            
            self.assertFalse(result)
        
        asyncio.run(run_test())

    def test_get_next_bundle_refs_empty_queue(self):
        """Test getting bundle refs when queue is empty."""
        async def run_test():
            # Mock initialization
            self.locator._initialize = AsyncMock()
            
            result = await self.locator.get_next_bundle_refs(self.mock_context, 5)
            
            self.assertEqual(result, [])
            self.locator._initialize.assert_called_once_with(self.mock_context)
        
        asyncio.run(run_test())

    def test_get_next_bundle_refs_with_files(self):
        """Test getting bundle refs when queue has files."""
        async def run_test():
            # Pre-populate queue
            self.locator._file_queue = ["/test/file1.txt", "/test/file2.txt"]
            
            result = await self.locator.get_next_bundle_refs(self.mock_context, 2)
            
            self.assertEqual(len(result), 2)
            self.assertTrue(all(isinstance(ref, BundleRef) for ref in result))
            self.assertEqual(result[0].request_meta["url"], "sftp:///test/file1.txt")
            self.assertEqual(result[1].request_meta["url"], "sftp:///test/file2.txt")
            self.assertEqual(len(self.locator._file_queue), 0)  # Queue should be empty after processing
        
        asyncio.run(run_test())

    def test_handle_bundle_processed(self):
        """Test handling bundle processed."""
        async def run_test():
            bundle = BundleRef(
                bid="test-bid-123",
                request_meta={"url": "sftp:///test/file.txt"}
            )
            
            # Mock SFTP connection for getting file modification time
            mock_conn = AsyncMock()
            mock_conn.stat = AsyncMock()
            mock_conn.stat.return_value.st_mtime = 1234567890.0
            
            self.locator.sftp_manager.get_connection.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            self.locator.sftp_manager.get_connection.return_value.__aexit__ = AsyncMock(return_value=None)
            
            self.locator._mark_file_processed_with_mtime = AsyncMock()
            self.locator._save_processing_result = AsyncMock()
            
            await self.locator.handle_bundle_processed(bundle, "result", self.mock_context)
            
            self.locator._mark_file_processed_with_mtime.assert_called_once_with("/test/file.txt", 1234567890.0, self.mock_context)
            self.locator._save_processing_result.assert_called_once_with(bundle, self.mock_context, success=True)
        
        asyncio.run(run_test())

    def test_handle_bundle_error(self):
        """Test handling bundle error."""
        async def run_test():
            bundle = BundleRef(
                bid="test-bid-123",
                request_meta={"url": "sftp:///test/file.txt"}
            )
            
            self.locator._save_error_state = AsyncMock()
            
            await self.locator.handle_bundle_error(bundle, "Test error", self.mock_context)
            
            self.locator._save_error_state.assert_called_once_with(bundle, "Test error", self.mock_context)
        
        asyncio.run(run_test())


if __name__ == '__main__':
    unittest.main()