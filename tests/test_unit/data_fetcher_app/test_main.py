"""Tests for application entry point.

This module contains unit tests for the main application functionality.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from data_fetcher_app.main import main_async


class TestMainApplication:
    """Test main application functionality."""

    @patch("data_fetcher_app.main.log_bind")
    @patch("data_fetcher_app.main.get_fetcher")
    @patch("data_fetcher_app.main.get_recipe_setup_function")
    @patch("data_fetcher_app.main.create_fetcher_config")
    @patch("data_fetcher_app.main.configure_application_credential_provider")
    @patch("data_fetcher_app.main.observe_around")
    @patch("data_fetcher_app.main.logger")
    def test_main_async_basic_functionality(
        self,
        mock_logger: MagicMock,
        mock_observe_around: MagicMock,
        mock_configure_credential_provider: MagicMock,
        mock_create_fetcher_config: MagicMock,
        mock_get_recipe_setup_function: MagicMock,
        mock_get_fetcher: MagicMock,
        mock_log_bind: MagicMock,
    ) -> None:
        """Test basic functionality of main_async function."""
        # Setup mocks
        mock_fetcher = AsyncMock()
        mock_get_fetcher.return_value = mock_fetcher

        # Mock create_fetcher_config (async function)
        mock_app_config = MagicMock()
        mock_create_fetcher_config.return_value = mock_app_config

        # Mock get_recipe_setup_function
        mock_recipe = MagicMock()
        mock_setup_func = MagicMock(return_value=mock_recipe)
        mock_get_recipe_setup_function.return_value = mock_setup_func

        # Mock the context manager for log_bind
        mock_log_bind.return_value.__enter__ = MagicMock()
        mock_log_bind.return_value.__exit__ = MagicMock()

        # Mock the context manager for observe_around
        mock_observe_around.return_value.__enter__ = MagicMock()
        mock_observe_around.return_value.__exit__ = MagicMock()

        # Test arguments
        args = {
            "config_name": "fr",
            "credentials_provider": "aws",
            "storage": "s3",
            "kvstore": "redis",
            "run_id": "fetcher_fr_20250906213000",
        }

        # Run the async function
        import asyncio

        asyncio.run(main_async(args))

        # Verify context binding
        mock_log_bind.assert_called_with(
            run_id="fetcher_fr_20250906213000", config_id="fr"
        )

        # Verify config creation
        mock_create_fetcher_config.assert_called_once()

        # Verify fetcher creation and execution
        mock_get_fetcher.assert_called_once()
        mock_fetcher.run.assert_called_once()

        # Verify credential provider configuration
        mock_configure_credential_provider.assert_called_once()

        # Verify recipe setup
        mock_get_recipe_setup_function.assert_called_once_with("fr")
        mock_setup_func.assert_called_once()

    def test_main_async_import(self) -> None:
        """Test that main_async function can be imported."""
        from data_fetcher_app.main import main_async

        assert callable(main_async)

    def test_cli_import(self) -> None:
        """Test that CLI functions can be imported."""
        from data_fetcher_app.main import (
            health_command,
            list_command,
            main,
            run_command,
            show_help,
        )

        assert callable(main)
        assert callable(run_command)
        assert callable(list_command)
        assert callable(health_command)
        assert callable(show_help)
