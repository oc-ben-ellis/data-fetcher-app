"""Tests for SFTP strategy factories.

This module contains unit tests for the SFTP strategy factories, covering
the new TTL parameter handling and configuration processing.
"""

import unittest
from datetime import timedelta
from unittest.mock import MagicMock

from data_fetcher_sftp.sftp_bundle_locators import (
    DirectorySftpBundleLocator,
    FileSftpBundleLocator,
)
from data_fetcher_sftp.sftp_config import SftpProtocolConfig
from data_fetcher_sftp.sftp_manager import SftpManager
from data_fetcher_sftp.strategy_factories import (
    DirectorySftpBundleLocatorFactory,
    FileSftpBundleLocatorFactory,
    SftpDirectoryLocatorConfig,
    SftpFileLocatorConfig,
)


class TestDirectorySftpBundleLocatorFactory(unittest.TestCase):
    """Test DirectorySftpBundleLocatorFactory functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_sftp_manager = MagicMock(spec=SftpManager)
        self.factory = DirectorySftpBundleLocatorFactory(self.mock_sftp_manager)
        self.mock_sftp_config = SftpProtocolConfig(
            host="test.example.com",
            port=22,
            username="testuser",
            password="testpass"
        )

    def test_validate_required_fields(self):
        """Test validation with required fields."""
        params = {
            "sftp_config": MagicMock(),
            "remote_dir": "/test/dir"
        }
        
        # Should not raise any exception
        try:
            self.factory.validate(params)
        except Exception as e:
            self.fail(f"validate() raised {type(e).__name__} unexpectedly: {e}")

    def test_validate_missing_sftp_config(self):
        """Test validation with missing sftp_config."""
        params = {
            "remote_dir": "/test/dir"
        }
        
        with self.assertRaises(Exception):  # InvalidArgumentStrategyException
            self.factory.validate(params)

    def test_validate_missing_remote_dir(self):
        """Test validation with missing remote_dir."""
        params = {
            "sftp_config": MagicMock()
        }
        
        with self.assertRaises(Exception):  # InvalidArgumentStrategyException
            self.factory.validate(params)

    def test_validate_invalid_remote_dir_type(self):
        """Test validation with invalid remote_dir type."""
        params = {
            "sftp_config": MagicMock(),
            "remote_dir": 123  # Should be string
        }
        
        with self.assertRaises(Exception):  # InvalidArgumentStrategyException
            self.factory.validate(params)

    def test_create_with_dict_params(self):
        """Test creating locator with dictionary parameters."""
        params = {
            "sftp_config": self.mock_sftp_config,
            "remote_dir": "/test/dir",
            "filename_pattern": "*.txt",
            "max_files": 100,
            "processed_files_ttl": timedelta(days=7),
            "processing_results_ttl": timedelta(days=30),
            "error_state_ttl": timedelta(hours=24),
        }
        
        locator = self.factory.create(params)
        
        self.assertIsInstance(locator, DirectorySftpBundleLocator)
        self.assertEqual(locator.remote_dir, "/test/dir")
        self.assertEqual(locator.filename_pattern, "*.txt")
        self.assertEqual(locator.max_files, 100)
        self.assertEqual(locator.processed_files_ttl, timedelta(days=7))
        self.assertEqual(locator.processing_results_ttl, timedelta(days=30))
        self.assertEqual(locator.error_state_ttl, timedelta(hours=24))

    def test_create_with_dict_params_defaults(self):
        """Test creating locator with dictionary parameters using defaults."""
        params = {
            "sftp_config": self.mock_sftp_config,
            "remote_dir": "/test/dir",
        }
        
        locator = self.factory.create(params)
        
        self.assertIsInstance(locator, DirectorySftpBundleLocator)
        self.assertEqual(locator.remote_dir, "/test/dir")
        self.assertEqual(locator.filename_pattern, "*")  # Default
        self.assertIsNone(locator.max_files)  # Default
        self.assertIsNone(locator.processed_files_ttl)  # Default
        self.assertIsNone(locator.processing_results_ttl)  # Default
        self.assertIsNone(locator.error_state_ttl)  # Default

    def test_create_with_dataclass_params(self):
        """Test creating locator with dataclass parameters."""
        config = SftpDirectoryLocatorConfig(
            sftp_config=self.mock_sftp_config,
            remote_dir="/test/dir",
            filename_pattern="*.txt",
            max_files=100,
            processed_files_ttl=timedelta(days=7),
            processing_results_ttl=timedelta(days=30),
            error_state_ttl=timedelta(hours=24),
        )
        
        locator = self.factory.create(config)
        
        self.assertIsInstance(locator, DirectorySftpBundleLocator)
        self.assertEqual(locator.remote_dir, "/test/dir")
        self.assertEqual(locator.filename_pattern, "*.txt")
        self.assertEqual(locator.max_files, 100)
        self.assertEqual(locator.processed_files_ttl, timedelta(days=7))
        self.assertEqual(locator.processing_results_ttl, timedelta(days=30))
        self.assertEqual(locator.error_state_ttl, timedelta(hours=24))

    def test_create_with_dataclass_params_defaults(self):
        """Test creating locator with dataclass parameters using defaults."""
        config = SftpDirectoryLocatorConfig(
            sftp_config=self.mock_sftp_config,
            remote_dir="/test/dir",
        )
        
        locator = self.factory.create(config)
        
        self.assertIsInstance(locator, DirectorySftpBundleLocator)
        self.assertEqual(locator.remote_dir, "/test/dir")
        self.assertEqual(locator.filename_pattern, "*")  # Default
        self.assertIsNone(locator.max_files)  # Default
        self.assertIsNone(locator.processed_files_ttl)  # Default
        self.assertIsNone(locator.processing_results_ttl)  # Default
        self.assertIsNone(locator.error_state_ttl)  # Default

    def test_get_config_type(self):
        """Test getting config type."""
        params = {"some": "params"}
        
        config_type = self.factory.get_config_type(params)
        
        self.assertEqual(config_type, SftpDirectoryLocatorConfig)


class TestFileSftpBundleLocatorFactory(unittest.TestCase):
    """Test FileSftpBundleLocatorFactory functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_sftp_manager = MagicMock(spec=SftpManager)
        self.factory = FileSftpBundleLocatorFactory(self.mock_sftp_manager)
        self.mock_sftp_config = SftpProtocolConfig(
            host="test.example.com",
            port=22,
            username="testuser",
            password="testpass"
        )

    def test_validate_required_fields(self):
        """Test validation with required fields."""
        params = {
            "sftp_config": MagicMock(),
            "file_paths": ["/test/file1.txt", "/test/file2.txt"]
        }
        
        # Should not raise any exception
        try:
            self.factory.validate(params)
        except Exception as e:
            self.fail(f"validate() raised {type(e).__name__} unexpectedly: {e}")

    def test_validate_missing_sftp_config(self):
        """Test validation with missing sftp_config."""
        params = {
            "file_paths": ["/test/file1.txt"]
        }
        
        with self.assertRaises(Exception):  # InvalidArgumentStrategyException
            self.factory.validate(params)

    def test_validate_missing_file_paths(self):
        """Test validation with missing file_paths."""
        params = {
            "sftp_config": MagicMock()
        }
        
        with self.assertRaises(Exception):  # InvalidArgumentStrategyException
            self.factory.validate(params)

    def test_validate_invalid_file_paths_type(self):
        """Test validation with invalid file_paths type."""
        params = {
            "sftp_config": MagicMock(),
            "file_paths": "not_a_list"  # Should be list
        }
        
        with self.assertRaises(Exception):  # InvalidArgumentStrategyException
            self.factory.validate(params)

    def test_validate_invalid_file_path_item_type(self):
        """Test validation with invalid file_paths item type."""
        params = {
            "sftp_config": MagicMock(),
            "file_paths": ["/test/file1.txt", 123]  # Second item should be string
        }
        
        with self.assertRaises(Exception):  # InvalidArgumentStrategyException
            self.factory.validate(params)

    def test_create_with_dict_params(self):
        """Test creating locator with dictionary parameters."""
        params = {
            "sftp_config": self.mock_sftp_config,
            "file_paths": ["/test/file1.txt", "/test/file2.txt"],
            "state_management_prefix": "custom_prefix",
            "processed_files_ttl": timedelta(days=7),
            "processing_results_ttl": timedelta(days=30),
            "error_state_ttl": timedelta(hours=24),
        }
        
        locator = self.factory.create(params)
        
        self.assertIsInstance(locator, FileSftpBundleLocator)
        self.assertEqual(locator.file_paths, ["/test/file1.txt", "/test/file2.txt"])
        self.assertEqual(locator.state_management_prefix, "custom_prefix")
        self.assertEqual(locator.processed_files_ttl, timedelta(days=7))
        self.assertEqual(locator.processing_results_ttl, timedelta(days=30))
        self.assertEqual(locator.error_state_ttl, timedelta(hours=24))

    def test_create_with_dict_params_defaults(self):
        """Test creating locator with dictionary parameters using defaults."""
        params = {
            "sftp_config": self.mock_sftp_config,
            "file_paths": ["/test/file1.txt"],
        }
        
        locator = self.factory.create(params)
        
        self.assertIsInstance(locator, FileSftpBundleLocator)
        self.assertEqual(locator.file_paths, ["/test/file1.txt"])
        self.assertEqual(locator.state_management_prefix, "sftp_file_provider")  # Default
        self.assertIsNone(locator.processed_files_ttl)  # Default
        self.assertIsNone(locator.processing_results_ttl)  # Default
        self.assertIsNone(locator.error_state_ttl)  # Default

    def test_create_with_dataclass_params(self):
        """Test creating locator with dataclass parameters."""
        config = SftpFileLocatorConfig(
            sftp_config=self.mock_sftp_config,
            file_paths=["/test/file1.txt", "/test/file2.txt"],
            state_management_prefix="custom_prefix",
            processed_files_ttl=timedelta(days=7),
            processing_results_ttl=timedelta(days=30),
            error_state_ttl=timedelta(hours=24),
        )
        
        locator = self.factory.create(config)
        
        self.assertIsInstance(locator, FileSftpBundleLocator)
        self.assertEqual(locator.file_paths, ["/test/file1.txt", "/test/file2.txt"])
        self.assertEqual(locator.state_management_prefix, "custom_prefix")
        self.assertEqual(locator.processed_files_ttl, timedelta(days=7))
        self.assertEqual(locator.processing_results_ttl, timedelta(days=30))
        self.assertEqual(locator.error_state_ttl, timedelta(hours=24))

    def test_create_with_dataclass_params_defaults(self):
        """Test creating locator with dataclass parameters using defaults."""
        config = SftpFileLocatorConfig(
            sftp_config=self.mock_sftp_config,
            file_paths=["/test/file1.txt"],
        )
        
        locator = self.factory.create(config)
        
        self.assertIsInstance(locator, FileSftpBundleLocator)
        self.assertEqual(locator.file_paths, ["/test/file1.txt"])
        self.assertEqual(locator.state_management_prefix, "sftp_file_provider")  # Default
        self.assertIsNone(locator.processed_files_ttl)  # Default
        self.assertIsNone(locator.processing_results_ttl)  # Default
        self.assertIsNone(locator.error_state_ttl)  # Default

    def test_get_config_type(self):
        """Test getting config type."""
        params = {"some": "params"}
        
        config_type = self.factory.get_config_type(params)
        
        self.assertEqual(config_type, SftpFileLocatorConfig)


class TestSftpDirectoryLocatorConfig(unittest.TestCase):
    """Test SftpDirectoryLocatorConfig functionality."""

    def test_config_creation_with_ttl(self):
        """Test creating config with TTL values."""
        config = SftpDirectoryLocatorConfig(
            sftp_config=MagicMock(),
            remote_dir="/test/dir",
            processed_files_ttl=timedelta(days=7),
            processing_results_ttl=timedelta(days=30),
            error_state_ttl=timedelta(hours=24),
        )
        
        self.assertEqual(config.remote_dir, "/test/dir")
        self.assertEqual(config.processed_files_ttl, timedelta(days=7))
        self.assertEqual(config.processing_results_ttl, timedelta(days=30))
        self.assertEqual(config.error_state_ttl, timedelta(hours=24))

    def test_config_creation_defaults(self):
        """Test creating config with default values."""
        config = SftpDirectoryLocatorConfig(
            sftp_config=MagicMock(),
            remote_dir="/test/dir",
        )
        
        self.assertEqual(config.remote_dir, "/test/dir")
        self.assertEqual(config.filename_pattern, "*")  # Default
        self.assertIsNone(config.max_files)  # Default
        self.assertIsNone(config.processed_files_ttl)  # Default
        self.assertIsNone(config.processing_results_ttl)  # Default
        self.assertIsNone(config.error_state_ttl)  # Default


class TestSftpFileLocatorConfig(unittest.TestCase):
    """Test SftpFileLocatorConfig functionality."""

    def test_config_creation_with_ttl(self):
        """Test creating config with TTL values."""
        config = SftpFileLocatorConfig(
            sftp_config=MagicMock(),
            file_paths=["/test/file1.txt", "/test/file2.txt"],
            processed_files_ttl=timedelta(days=7),
            processing_results_ttl=timedelta(days=30),
            error_state_ttl=timedelta(hours=24),
        )
        
        self.assertEqual(config.file_paths, ["/test/file1.txt", "/test/file2.txt"])
        self.assertEqual(config.processed_files_ttl, timedelta(days=7))
        self.assertEqual(config.processing_results_ttl, timedelta(days=30))
        self.assertEqual(config.error_state_ttl, timedelta(hours=24))

    def test_config_creation_defaults(self):
        """Test creating config with default values."""
        config = SftpFileLocatorConfig(
            sftp_config=MagicMock(),
            file_paths=["/test/file1.txt"],
        )
        
        self.assertEqual(config.file_paths, ["/test/file1.txt"])
        self.assertEqual(config.state_management_prefix, "sftp_file_provider")  # Default
        self.assertIsNone(config.processed_files_ttl)  # Default
        self.assertIsNone(config.processing_results_ttl)  # Default
        self.assertIsNone(config.error_state_ttl)  # Default


if __name__ == '__main__':
    unittest.main()