"""Tests for configuration modules.

This module contains unit tests for configuration functionality,
including FR and US FL configuration modules.
"""

import pytest


class TestConfigModules:
    """Test configuration modules."""

    def test_config_modules_importable(self) -> None:
        """Test that configuration modules can be imported without errors."""
        try:
            # Test that the modules can be imported
            import data_fetcher_recipes.fr
            import data_fetcher_recipes.us_fl
            # If we get here, imports worked
            assert hasattr(data_fetcher_recipes.fr, '__name__')
            assert hasattr(data_fetcher_recipes.us_fl, '__name__')
        except ImportError as e:
            pytest.fail(f"Failed to import configuration modules: {e}")
