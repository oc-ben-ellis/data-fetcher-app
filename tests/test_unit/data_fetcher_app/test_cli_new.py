"""Unit tests for the new CLI functionality using openc_python_common.

This module contains comprehensive unit tests for the new CLI interface
that uses openc_python_common instead of Click.
"""

import os
import sys
import types
from unittest.mock import MagicMock, patch

# Stub missing modules expected by main import
_stub_fc = types.ModuleType("data_fetcher_core.fetcher_config")


class YamlFetcherConfig:  # type: ignore[misc]
    pass


_stub_fc.YamlFetcherConfig = YamlFetcherConfig
sys.modules.setdefault("data_fetcher_core.fetcher_config", _stub_fc)

# Also stub retry module path used by some tests
_stub_retry = types.ModuleType("data_fetcher_core.retry")
sys.modules.setdefault("data_fetcher_core.retry", _stub_retry)

# Stub additional legacy modules referenced by http_api factories
_proto_mod = types.ModuleType("data_fetcher_core.protocol_config")


class HttpProtocolConfig:  # type: ignore[misc]
    def __init__(self, **kwargs) -> None:
        self.params = kwargs


_proto_mod.HttpProtocolConfig = HttpProtocolConfig
sys.modules.setdefault("data_fetcher_core.protocol_config", _proto_mod)

_config_factory_mod = types.ModuleType("data_fetcher_core.config_factory")


class AppConfig:  # type: ignore[misc]
    pass


_config_factory_mod.AppConfig = AppConfig
sys.modules.setdefault("data_fetcher_core.config_factory", _config_factory_mod)

from data_fetcher_app.main import (
    generate_run_id,
    health_command,
    main,
    run_command,
    show_help,
)


class TestRunIdGeneration:
    """Test run ID generation functionality."""

    def test_generate_run_id_format(self) -> None:
        """Test that run ID is generated with correct format."""
        config_id = "test-config"
        run_id = generate_run_id(config_id)

        assert run_id.startswith("fetcher_")
        assert run_id.startswith(f"fetcher_{config_id}_")

        # Check timestamp format (YYYYMMDDHHMMSS)
        timestamp_part = run_id.replace(f"fetcher_{config_id}_", "")
        assert len(timestamp_part) == 14  # YYYYMMDDHHMMSS
        assert timestamp_part.count("_") == 0

    def test_generate_run_id_uniqueness(self) -> None:
        """Test that run IDs are unique."""
        config_id = "test-config"
        run_id1 = generate_run_id(config_id)

        # Add a delay to ensure different timestamps
        import time

        time.sleep(1.0)  # 1 second delay to ensure different timestamps

        run_id2 = generate_run_id(config_id)

        # Should be different due to timestamp
        assert run_id1 != run_id2

    def test_generate_run_id_with_different_configs(self) -> None:
        """Test run ID generation with different configuration IDs."""
        run_id1 = generate_run_id("config1")
        run_id2 = generate_run_id("config2")

        assert run_id1 != run_id2
        assert "config1" in run_id1
        assert "config2" in run_id2


class TestMainFunction:
    """Test the main CLI entry point."""

    def test_main_help(self) -> None:
        """Test that main shows help correctly."""
        with patch("sys.argv", ["main.py", "--help"]):
            with patch("sys.exit", side_effect=SystemExit(0)) as mock_exit:
                with patch("builtins.print") as mock_print:
                    try:
                        main()
                    except SystemExit:
                        pass
                    mock_print.assert_called()
                    mock_exit.assert_called_with(0)

    def test_main_version(self) -> None:
        """Test that main shows version correctly."""
        with patch("sys.argv", ["main.py", "--version"]):
            with patch("sys.exit", side_effect=SystemExit(0)) as mock_exit:
                with patch("builtins.print") as mock_print:
                    try:
                        main()
                    except SystemExit:
                        pass
                    # Check that the version string was printed (may have additional parameters)
                    call_args = mock_print.call_args[0]
                    assert "data-fetcher-app, version 0.1.0" in call_args[0]
                    mock_exit.assert_called_with(0)

    def test_main_no_arguments(self) -> None:
        """Test main with no arguments shows help."""
        with patch("sys.argv", ["main.py"]):
            with patch("sys.exit", side_effect=SystemExit(1)) as mock_exit:
                with patch("builtins.print") as mock_print:
                    try:
                        main()
                    except SystemExit:
                        pass
                    mock_print.assert_called()
                    mock_exit.assert_called_with(1)

    def test_main_unknown_command(self) -> None:
        """Test main with unknown command."""
        with patch("sys.argv", ["main.py", "unknown"]):
            with patch("sys.exit", side_effect=SystemExit(1)) as mock_exit:
                with patch("builtins.print") as mock_print:
                    try:
                        main()
                    except SystemExit:
                        pass
                    mock_print.assert_called()
                    mock_exit.assert_called_with(1)


class TestRunCommand:
    """Test the run command functionality."""

    def setup_method(self) -> None:
        """Set up test environment."""
        # Clear environment variables
        if "DATA_FETCHER_APP_CONFIG_ID" in os.environ:
            del os.environ["DATA_FETCHER_APP_CONFIG_ID"]

    def teardown_method(self) -> None:
        """Clean up test environment."""
        # Clear environment variables
        if "DATA_FETCHER_APP_CONFIG_ID" in os.environ:
            del os.environ["DATA_FETCHER_APP_CONFIG_ID"]

    @patch("data_fetcher_app.main.asyncio.run")
    @patch("data_fetcher_app.main.create_run_config")
    @patch("data_fetcher_app.main.configure_logging")
    def test_run_command_success(
        self,
        mock_configure_logging: MagicMock,
        mock_create_config: MagicMock,
        mock_asyncio_run: MagicMock,
    ) -> None:
        """Test run command with successful execution."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.data_registry_id = "test-config"
        mock_config.stage = "raw"
        mock_config.config_dir = "./mocks/test/config"
        mock_config.credentials_provider = "aws"
        mock_config.storage = "s3"
        mock_config.kvstore = "memory"
        mock_config.log_level = "INFO"
        mock_config.dev_mode = False
        # Ensure optional attributes are None to avoid MagicMock leaking into env/kwargs
        mock_config.aws_profile = None
        mock_config.credentials_aws_profile = None
        mock_config.credentials_aws_region = None
        mock_config.credentials_aws_endpoint_url = None
        mock_config.credentials_env_prefix = None
        mock_config.kvstore_serializer = None
        mock_config.kvstore_default_ttl = None
        mock_config.kvstore_redis_host = None
        mock_config.kvstore_redis_port = None
        mock_config.kvstore_redis_db = None
        mock_config.kvstore_redis_password = None
        mock_config.kvstore_redis_key_prefix = None
        mock_config.storage_pipeline_aws_profile = None
        mock_config.storage_s3_bucket = None
        mock_config.storage_s3_prefix = None
        mock_config.storage_s3_region = None
        mock_config.storage_s3_endpoint_url = None
        mock_config.storage_file_path = None
        mock_config.storage_use_unzip = None
        mock_create_config.return_value = mock_config
        # Ensure step is a string for env assignment
        mock_config.step = "raw"

        # Test the command
        with patch.dict(
            os.environ,
            {
                "OC_DATA_PIPELINE_STORAGE_S3_URL": "s3://bucket/path",
                "OC_DATA_PIPELINE_STAGE": "raw",
                "DATA_FETCHER_APP_STORAGE_USE_TAR_GZ": "0",
                "DATA_FETCHER_APP_STORAGE_USE_UNZIP": "0",
            },
            clear=False,
        ):
            run_command(["test-config"])

        # Verify configuration was created
        mock_create_config.assert_called_once_with(["test-config"])

        # Verify logging was configured
        mock_configure_logging.assert_called_once_with(log_level="INFO", dev_mode=False)

        # Verify asyncio.run was called
        mock_asyncio_run.assert_called_once()

    @patch("data_fetcher_app.main.asyncio.run")
    @patch("data_fetcher_app.main.create_run_config")
    @patch("data_fetcher_app.main.configure_logging")
    def test_run_command_with_options(
        self,
        mock_configure_logging: MagicMock,
        mock_create_config: MagicMock,
        mock_asyncio_run: MagicMock,
    ) -> None:
        """Test run command with additional options."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.data_registry_id = "test-config"
        mock_config.stage = "raw"
        mock_config.config_dir = "./mocks/test/config"
        mock_config.credentials_provider = "env"
        mock_config.storage = "file"
        mock_config.kvstore = "redis"
        mock_config.log_level = "DEBUG"
        mock_config.dev_mode = True
        mock_config.aws_profile = None
        mock_config.credentials_aws_profile = None
        mock_config.credentials_aws_region = None
        mock_config.credentials_aws_endpoint_url = None
        mock_config.credentials_env_prefix = None
        mock_config.kvstore_serializer = None
        mock_config.kvstore_default_ttl = None
        mock_config.kvstore_redis_host = None
        mock_config.kvstore_redis_port = None
        mock_config.kvstore_redis_db = None
        mock_config.kvstore_redis_password = None
        mock_config.kvstore_redis_key_prefix = None
        mock_config.storage_pipeline_aws_profile = None
        mock_config.storage_s3_bucket = None
        mock_config.storage_s3_prefix = None
        mock_config.storage_s3_region = None
        mock_config.storage_s3_endpoint_url = None
        mock_config.storage_file_path = None
        mock_config.storage_use_unzip = None
        mock_create_config.return_value = mock_config
        mock_config.step = "raw"

        # Test the command with options
        with patch.dict(
            os.environ,
            {
                "OC_DATA_PIPELINE_STORAGE_S3_URL": "s3://bucket/path",
                "OC_DATA_PIPELINE_STAGE": "raw",
                "DATA_FETCHER_APP_STORAGE_USE_TAR_GZ": "0",
                "DATA_FETCHER_APP_STORAGE_USE_UNZIP": "0",
            },
            clear=False,
        ):
            run_command(["test-config", "--credentials-provider", "env", "--dev-mode"])

        # Verify configuration was created with remaining args
        mock_create_config.assert_called_once_with(
            ["test-config", "--credentials-provider", "env", "--dev-mode"]
        )

        # Verify logging was configured
        mock_configure_logging.assert_called_once_with(log_level="DEBUG", dev_mode=True)

    def test_run_command_missing_config_id(self) -> None:
        """Test run command with missing configuration ID."""
        with patch("sys.exit", side_effect=SystemExit(1)) as mock_exit:
            with patch("builtins.print") as mock_print:
                try:
                    run_command([])
                except SystemExit:
                    pass
                mock_print.assert_called()
                mock_exit.assert_called_with(1)

    def test_run_command_exception(self) -> None:
        """Test run command with exception."""
        with patch(
            "data_fetcher_app.main.create_run_config",
            side_effect=Exception("Test error"),
        ):
            with patch("sys.exit", side_effect=SystemExit(1)) as mock_exit:
                with patch("builtins.print") as mock_print:
                    try:
                        run_command(["test-config"])
                    except SystemExit:
                        pass
                    mock_print.assert_called()
                    mock_exit.assert_called_with(1)


class TestHealthCommand:
    """Test the health command functionality."""

    @patch("data_fetcher_app.main.create_health_app")
    @patch("data_fetcher_app.main.create_health_config")
    @patch("data_fetcher_app.main.configure_logging")
    def test_health_command_success(
        self,
        mock_configure_logging: MagicMock,
        mock_create_config: MagicMock,
        mock_create_health_app: MagicMock,
    ) -> None:
        """Test health command with successful execution."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.port = 8080
        mock_config.host = "0.0.0.0"
        mock_config.log_level = "INFO"
        mock_config.dev_mode = False
        mock_create_config.return_value = mock_config

        mock_app = MagicMock()
        mock_create_health_app.return_value = mock_app

        with patch("data_fetcher_app.main.make_server") as mock_make_server:
            mock_server = MagicMock()
            mock_make_server.return_value.__enter__.return_value = mock_server

            with patch("data_fetcher_app.main.logger"):
                # Simulate KeyboardInterrupt to stop the server
                mock_server.serve_forever.side_effect = KeyboardInterrupt()

                health_command([])

        # Verify configuration was created
        mock_create_config.assert_called_once_with([])

        # Verify logging was configured
        mock_configure_logging.assert_called_once_with(log_level="INFO", dev_mode=False)

        # Verify health app was created
        mock_create_health_app.assert_called_once()

        # Verify server was created and started
        mock_make_server.assert_called_once_with("0.0.0.0", 8080, mock_app)

    def test_health_command_exception(self) -> None:
        """Test health command with exception."""
        with patch(
            "data_fetcher_app.main.create_health_config",
            side_effect=Exception("Test error"),
        ):
            with patch("sys.exit", side_effect=SystemExit(1)) as mock_exit:
                with patch("builtins.print") as mock_print:
                    try:
                        health_command([])
                    except SystemExit:
                        pass
                    mock_print.assert_called()
                    mock_exit.assert_called_with(1)


class TestShowHelp:
    """Test the help display functionality."""

    def test_show_help_content(self) -> None:
        """Test that help shows correct content."""
        with patch("builtins.print") as mock_print:
            show_help()

            # Verify help content was printed
            mock_print.assert_called()
            help_text = mock_print.call_args[0][0]

            assert "OpenCorporates Data Fetcher" in help_text
            assert "run" in help_text
            assert "health" in help_text
            assert "--credentials-provider" in help_text
            assert "--storage" in help_text
            assert "--kvstore" in help_text


class TestCLIIntegration:
    """Test CLI integration scenarios."""

    @patch("data_fetcher_app.main.run_command")
    def test_main_run_command(self, mock_run_command: MagicMock) -> None:
        """Test main function with run command."""
        with patch("sys.argv", ["main.py", "run", "test-config"]):
            main()
            mock_run_command.assert_called_once_with(["test-config"])

    @patch("data_fetcher_app.main.health_command")
    def test_main_health_command(self, mock_health_command: MagicMock) -> None:
        """Test main function with health command."""
        with patch("sys.argv", ["main.py", "health", "--port", "8080"]):
            main()
            mock_health_command.assert_called_once_with(["--port", "8080"])

    def test_main_run_command_missing_config_id(self) -> None:
        """Test main function with run command missing configuration ID."""
        with patch("sys.argv", ["main.py", "run"]):
            with patch("sys.exit", side_effect=SystemExit(1)) as mock_exit:
                with patch("builtins.print") as mock_print:
                    try:
                        main()
                    except SystemExit:
                        pass
                    mock_print.assert_called()
                    mock_exit.assert_called_with(1)
