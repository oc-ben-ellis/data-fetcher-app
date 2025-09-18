"""Standalone tests for SFTP bundle locators.

This module contains basic unit tests for DirectorySftpBundleLocator and FileSftpBundleLocator,
importing modules directly without going through package __init__.py files.
"""

import sys
import unittest
from datetime import timedelta
from unittest.mock import MagicMock

# Add src to path
sys.path.insert(0, '/code/src')


class TestDirectorySftpBundleLocatorStandalone(unittest.TestCase):
    """Standalone tests for DirectorySftpBundleLocator functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_sftp_manager = MagicMock()
        self.mock_sftp_config = MagicMock()
        self.mock_sftp_config.host = "test.example.com"
        self.mock_sftp_config.port = 22
        self.mock_sftp_config.username = "testuser"
        self.mock_sftp_config.password = "testpass"

    def test_initialization_with_ttl(self):
        """Test locator initialization with TTL values."""
        # Import the module directly without going through __init__.py
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "sftp_bundle_locators", 
            "/code/src/data_fetcher_sftp/sftp_bundle_locators.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        locator = module.DirectorySftpBundleLocator(
            sftp_manager=self.mock_sftp_manager,
            sftp_config=self.mock_sftp_config,
            remote_dir="/test/dir",
            filename_pattern="*.txt",
            processed_files_ttl=timedelta(days=7),
            processing_results_ttl=timedelta(days=30),
            error_state_ttl=timedelta(hours=24),
        )
        
        self.assertEqual(locator.remote_dir, "/test/dir")
        self.assertEqual(locator.filename_pattern, "*.txt")
        self.assertEqual(locator.processed_files_ttl, timedelta(days=7))
        self.assertEqual(locator.processing_results_ttl, timedelta(days=30))
        self.assertEqual(locator.error_state_ttl, timedelta(hours=24))
        self.assertEqual(locator._file_queue, [])

    def test_initialization_default_ttl(self):
        """Test locator initialization with default TTL values."""
        # Import the module directly without going through __init__.py
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "sftp_bundle_locators", 
            "/code/src/data_fetcher_sftp/sftp_bundle_locators.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        locator = module.DirectorySftpBundleLocator(
            sftp_manager=self.mock_sftp_manager,
            sftp_config=self.mock_sftp_config,
            remote_dir="/test/dir",
        )
        
        self.assertIsNone(locator.processed_files_ttl)
        self.assertIsNone(locator.processing_results_ttl)
        self.assertIsNone(locator.error_state_ttl)

    def test_state_management_prefix(self):
        """Test that state management prefix is set correctly."""
        # Import the module directly without going through __init__.py
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "sftp_bundle_locators", 
            "/code/src/data_fetcher_sftp/sftp_bundle_locators.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        locator = module.DirectorySftpBundleLocator(
            sftp_manager=self.mock_sftp_manager,
            sftp_config=self.mock_sftp_config,
            remote_dir="/test/dir",
        )
        
        self.assertEqual(locator.state_management_prefix, "sftp_directory_provider")


class TestFileSftpBundleLocatorStandalone(unittest.TestCase):
    """Standalone tests for FileSftpBundleLocator functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_sftp_manager = MagicMock()
        self.mock_sftp_config = MagicMock()
        self.mock_sftp_config.host = "test.example.com"
        self.mock_sftp_config.port = 22
        self.mock_sftp_config.username = "testuser"
        self.mock_sftp_config.password = "testpass"

    def test_initialization_with_ttl(self):
        """Test locator initialization with TTL values."""
        # Import the module directly without going through __init__.py
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "sftp_bundle_locators", 
            "/code/src/data_fetcher_sftp/sftp_bundle_locators.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        locator = module.FileSftpBundleLocator(
            sftp_manager=self.mock_sftp_manager,
            sftp_config=self.mock_sftp_config,
            file_paths=["/test/file1.txt", "/test/file2.txt"],
            processed_files_ttl=timedelta(days=7),
            processing_results_ttl=timedelta(days=30),
            error_state_ttl=timedelta(hours=24),
        )
        
        self.assertEqual(locator.file_paths, ["/test/file1.txt", "/test/file2.txt"])
        self.assertEqual(locator.processed_files_ttl, timedelta(days=7))
        self.assertEqual(locator.processing_results_ttl, timedelta(days=30))
        self.assertEqual(locator.error_state_ttl, timedelta(hours=24))
        self.assertEqual(locator._file_queue, [])

    def test_initialization_default_ttl(self):
        """Test locator initialization with default TTL values."""
        # Import the module directly without going through __init__.py
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "sftp_bundle_locators", 
            "/code/src/data_fetcher_sftp/sftp_bundle_locators.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        locator = module.FileSftpBundleLocator(
            sftp_manager=self.mock_sftp_manager,
            sftp_config=self.mock_sftp_config,
            file_paths=["/test/file1.txt"],
        )
        
        self.assertIsNone(locator.processed_files_ttl)
        self.assertIsNone(locator.processing_results_ttl)
        self.assertIsNone(locator.error_state_ttl)

    def test_state_management_prefix(self):
        """Test that state management prefix is set correctly."""
        # Import the module directly without going through __init__.py
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "sftp_bundle_locators", 
            "/code/src/data_fetcher_sftp/sftp_bundle_locators.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        locator = module.FileSftpBundleLocator(
            sftp_manager=self.mock_sftp_manager,
            sftp_config=self.mock_sftp_config,
            file_paths=["/test/file1.txt"],
        )
        
        self.assertEqual(locator.state_management_prefix, "sftp_file_provider")

    def test_custom_state_management_prefix(self):
        """Test that custom state management prefix is set correctly."""
        # Import the module directly without going through __init__.py
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "sftp_bundle_locators", 
            "/code/src/data_fetcher_sftp/sftp_bundle_locators.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        locator = module.FileSftpBundleLocator(
            sftp_manager=self.mock_sftp_manager,
            sftp_config=self.mock_sftp_config,
            file_paths=["/test/file1.txt"],
            state_management_prefix="custom_prefix",
        )
        
        self.assertEqual(locator.state_management_prefix, "custom_prefix")


class TestSftpStrategyFactoriesStandalone(unittest.TestCase):
    """Standalone tests for SFTP strategy factories."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_sftp_manager = MagicMock()
        self.mock_sftp_config = MagicMock()
        self.mock_sftp_config.host = "test.example.com"
        self.mock_sftp_config.port = 22
        self.mock_sftp_config.username = "testuser"
        self.mock_sftp_config.password = "testpass"

    def test_directory_factory_creation(self):
        """Test DirectorySftpBundleLocatorFactory creation."""
        # Import the module directly without going through __init__.py
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "strategy_factories", 
            "/code/src/data_fetcher_sftp/strategy_factories.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        factory = module.DirectorySftpBundleLocatorFactory(self.mock_sftp_manager)
        self.assertIsNotNone(factory)

    def test_file_factory_creation(self):
        """Test FileSftpBundleLocatorFactory creation."""
        # Import the module directly without going through __init__.py
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "strategy_factories", 
            "/code/src/data_fetcher_sftp/strategy_factories.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        factory = module.FileSftpBundleLocatorFactory(self.mock_sftp_manager)
        self.assertIsNotNone(factory)

    def test_directory_factory_create_with_ttl(self):
        """Test DirectorySftpBundleLocatorFactory.create with TTL parameters."""
        # Import the module directly without going through __init__.py
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "strategy_factories", 
            "/code/src/data_fetcher_sftp/strategy_factories.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        factory = module.DirectorySftpBundleLocatorFactory(self.mock_sftp_manager)
        
        params = {
            "sftp_config": self.mock_sftp_config,
            "remote_dir": "/test/dir",
            "processed_files_ttl": timedelta(days=7),
            "processing_results_ttl": timedelta(days=30),
            "error_state_ttl": timedelta(hours=24),
        }
        
        locator = factory.create(params)
        
        self.assertEqual(locator.processed_files_ttl, timedelta(days=7))
        self.assertEqual(locator.processing_results_ttl, timedelta(days=30))
        self.assertEqual(locator.error_state_ttl, timedelta(hours=24))

    def test_file_factory_create_with_ttl(self):
        """Test FileSftpBundleLocatorFactory.create with TTL parameters."""
        # Import the module directly without going through __init__.py
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "strategy_factories", 
            "/code/src/data_fetcher_sftp/strategy_factories.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        factory = module.FileSftpBundleLocatorFactory(self.mock_sftp_manager)
        
        params = {
            "sftp_config": self.mock_sftp_config,
            "file_paths": ["/test/file1.txt"],
            "processed_files_ttl": timedelta(days=7),
            "processing_results_ttl": timedelta(days=30),
            "error_state_ttl": timedelta(hours=24),
        }
        
        locator = factory.create(params)
        
        self.assertEqual(locator.processed_files_ttl, timedelta(days=7))
        self.assertEqual(locator.processing_results_ttl, timedelta(days=30))
        self.assertEqual(locator.error_state_ttl, timedelta(hours=24))


if __name__ == '__main__':
    unittest.main()
