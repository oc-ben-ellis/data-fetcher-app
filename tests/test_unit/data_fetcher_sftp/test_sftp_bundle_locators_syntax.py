"""Syntax tests for SFTP bundle locators.

This module contains basic syntax and structure tests for the SFTP bundle locators,
verifying that the code can be parsed and basic structure is correct.
"""

import ast
import unittest
from pathlib import Path


class TestSftpBundleLocatorsSyntax(unittest.TestCase):
    """Test SFTP bundle locators syntax and structure."""

    def test_sftp_bundle_locators_syntax(self):
        """Test that sftp_bundle_locators.py has valid Python syntax."""
        file_path = Path("/code/src/data_fetcher_sftp/sftp_bundle_locators.py")
        self.assertTrue(file_path.exists(), "sftp_bundle_locators.py should exist")
        
        with open(file_path, 'r') as f:
            source = f.read()
        
        # Parse the source code to check for syntax errors
        try:
            tree = ast.parse(source)
            self.assertIsNotNone(tree, "Should be able to parse the source code")
        except SyntaxError as e:
            self.fail(f"Syntax error in sftp_bundle_locators.py: {e}")

    def test_strategy_factories_syntax(self):
        """Test that strategy_factories.py has valid Python syntax."""
        file_path = Path("/code/src/data_fetcher_sftp/strategy_factories.py")
        self.assertTrue(file_path.exists(), "strategy_factories.py should exist")
        
        with open(file_path, 'r') as f:
            source = f.read()
        
        # Parse the source code to check for syntax errors
        try:
            tree = ast.parse(source)
            self.assertIsNotNone(tree, "Should be able to parse the source code")
        except SyntaxError as e:
            self.fail(f"Syntax error in strategy_factories.py: {e}")

    def test_sftp_bundle_locators_has_ttl_parameters(self):
        """Test that sftp_bundle_locators.py contains TTL parameters."""
        file_path = Path("/code/src/data_fetcher_sftp/sftp_bundle_locators.py")
        
        with open(file_path, 'r') as f:
            source = f.read()
        
        # Check for TTL parameter names
        ttl_params = [
            "processed_files_ttl",
            "processing_results_ttl", 
            "error_state_ttl"
        ]
        
        for param in ttl_params:
            self.assertIn(param, source, f"Should contain {param} parameter")

    def test_sftp_bundle_locators_has_timedelta_import(self):
        """Test that sftp_bundle_locators.py imports timedelta."""
        file_path = Path("/code/src/data_fetcher_sftp/sftp_bundle_locators.py")
        
        with open(file_path, 'r') as f:
            source = f.read()
        
        self.assertIn("timedelta", source, 
                     "Should import timedelta from datetime")

    def test_strategy_factories_has_ttl_parameters(self):
        """Test that strategy_factories.py contains TTL parameters."""
        file_path = Path("/code/src/data_fetcher_sftp/strategy_factories.py")
        
        with open(file_path, 'r') as f:
            source = f.read()
        
        # Check for TTL parameter names
        ttl_params = [
            "processed_files_ttl",
            "processing_results_ttl", 
            "error_state_ttl"
        ]
        
        for param in ttl_params:
            self.assertIn(param, source, f"Should contain {param} parameter")

    def test_strategy_factories_has_timedelta_import(self):
        """Test that strategy_factories.py imports timedelta."""
        file_path = Path("/code/src/data_fetcher_sftp/strategy_factories.py")
        
        with open(file_path, 'r') as f:
            source = f.read()
        
        self.assertIn("timedelta", source, 
                     "Should import timedelta from datetime")

    def test_sftp_bundle_locators_has_directory_class(self):
        """Test that sftp_bundle_locators.py contains DirectorySftpBundleLocator class."""
        file_path = Path("/code/src/data_fetcher_sftp/sftp_bundle_locators.py")
        
        with open(file_path, 'r') as f:
            source = f.read()
        
        self.assertIn("class DirectorySftpBundleLocator", source,
                     "Should contain DirectorySftpBundleLocator class")

    def test_sftp_bundle_locators_has_file_class(self):
        """Test that sftp_bundle_locators.py contains FileSftpBundleLocator class."""
        file_path = Path("/code/src/data_fetcher_sftp/sftp_bundle_locators.py")
        
        with open(file_path, 'r') as f:
            source = f.read()
        
        self.assertIn("class FileSftpBundleLocator", source,
                     "Should contain FileSftpBundleLocator class")

    def test_strategy_factories_has_directory_factory(self):
        """Test that strategy_factories.py contains DirectorySftpBundleLocatorFactory class."""
        file_path = Path("/code/src/data_fetcher_sftp/strategy_factories.py")
        
        with open(file_path, 'r') as f:
            source = f.read()
        
        self.assertIn("class DirectorySftpBundleLocatorFactory", source,
                     "Should contain DirectorySftpBundleLocatorFactory class")

    def test_strategy_factories_has_file_factory(self):
        """Test that strategy_factories.py contains FileSftpBundleLocatorFactory class."""
        file_path = Path("/code/src/data_fetcher_sftp/strategy_factories.py")
        
        with open(file_path, 'r') as f:
            source = f.read()
        
        self.assertIn("class FileSftpBundleLocatorFactory", source,
                     "Should contain FileSftpBundleLocatorFactory class")

    def test_strategy_factories_has_config_classes(self):
        """Test that strategy_factories.py contains config dataclasses."""
        file_path = Path("/code/src/data_fetcher_sftp/strategy_factories.py")
        
        with open(file_path, 'r') as f:
            source = f.read()
        
        config_classes = [
            "class SftpDirectoryLocatorConfig",
            "class SftpFileLocatorConfig"
        ]
        
        for config_class in config_classes:
            self.assertIn(config_class, source,
                         f"Should contain {config_class}")

    def test_sftp_bundle_locators_has_kv_store_methods(self):
        """Test that sftp_bundle_locators.py contains KV store methods."""
        file_path = Path("/code/src/data_fetcher_sftp/sftp_bundle_locators.py")
        
        with open(file_path, 'r') as f:
            source = f.read()
        
        kv_methods = [
            "_is_file_processed",
            "_mark_file_processed",
            "_get_file_processed_mtime",
            "_mark_file_processed_with_mtime"
        ]
        
        for method in kv_methods:
            self.assertIn(f"def {method}", source,
                         f"Should contain {method} method")

    def test_sftp_bundle_locators_removed_old_methods(self):
        """Test that sftp_bundle_locators.py no longer contains removed methods."""
        file_path = Path("/code/src/data_fetcher_sftp/sftp_bundle_locators.py")
        
        with open(file_path, 'r') as f:
            source = f.read()
        
        removed_methods = [
            "_load_persistence_state",
            "_save_persistence_state",
            "_is_initialized",
            "_pop_from_queue",
            "_append_to_queue",
            "_get_queue_size"
        ]
        
        for method in removed_methods:
            self.assertNotIn(f"def {method}", source,
                           f"Should not contain removed {method} method")


if __name__ == '__main__':
    unittest.main()
