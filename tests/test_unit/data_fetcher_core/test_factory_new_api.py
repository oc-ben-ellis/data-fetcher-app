"""Tests for the new factory functions with ProtocolConfig.

This module contains unit tests for the updated factory functions.
"""

from data_fetcher_core.factory import (
    create_sftp_manager,
    create_sftp_protocol_config,
)
from data_fetcher_core.protocol_config import HttpProtocolConfig, SftpProtocolConfig
from data_fetcher_http.factory import (
    create_http_manager,
    create_http_protocol_config,
)
from data_fetcher_http.http_manager import HttpManager
from data_fetcher_sftp.sftp_manager import SftpManager


class TestFactoryNewAPI:
    """Test factory functions with new ProtocolConfig API."""

    def test_create_http_protocol_config_defaults(self) -> None:
        """Test creating HTTP protocol config with default values."""
        config = create_http_protocol_config()

        assert isinstance(config, HttpProtocolConfig)
        assert config.timeout == 30.0
        assert config.rate_limit_requests_per_second == 10.0
        assert config.max_retries == 3
        assert config.default_headers is not None
        assert config.default_headers["User-Agent"] == "OCFetcher/1.0"
        assert config.authentication_mechanism is None

    def test_create_http_protocol_config_custom(self) -> None:
        """Test creating HTTP protocol config with custom values."""
        custom_headers = {"User-Agent": "CustomAgent/1.0", "X-Custom": "value"}
        config = create_http_protocol_config(
            timeout=60.0,
            rate_limit_requests_per_second=5.0,
            max_retries=5,
            default_headers=custom_headers,
        )

        assert isinstance(config, HttpProtocolConfig)
        assert config.timeout == 60.0
        assert config.rate_limit_requests_per_second == 5.0
        assert config.max_retries == 5
        assert config.default_headers == custom_headers

    def test_create_http_manager(self) -> None:
        """Test creating HTTP manager."""
        manager = create_http_manager()

        assert isinstance(manager, HttpManager)
        assert hasattr(manager, "_connection_pools")
        assert len(manager._connection_pools) == 0

    def test_create_sftp_protocol_config_defaults(self) -> None:
        """Test creating SFTP protocol config with default values."""
        config = create_sftp_protocol_config(config_name="test_config")

        assert isinstance(config, SftpProtocolConfig)
        assert config.config_name == "test_config"
        assert config.connect_timeout == 20.0
        assert config.rate_limit_requests_per_second == 2.0
        assert config.max_retries == 3
        assert config.base_retry_delay == 1.0
        assert config.max_retry_delay == 60.0
        assert config.retry_exponential_base == 2.0

    def test_create_sftp_protocol_config_custom(self) -> None:
        """Test creating SFTP protocol config with custom values."""
        config = create_sftp_protocol_config(
            config_name="custom_config",
            connect_timeout=30.0,
            rate_limit_requests_per_second=1.0,
            max_retries=5,
        )

        assert isinstance(config, SftpProtocolConfig)
        assert config.config_name == "custom_config"
        assert config.connect_timeout == 30.0
        assert config.rate_limit_requests_per_second == 1.0
        assert config.max_retries == 5

    def test_create_sftp_manager(self) -> None:
        """Test creating SFTP manager."""
        manager = create_sftp_manager()

        assert isinstance(manager, SftpManager)
        assert hasattr(manager, "_connection_pools")
        assert len(manager._connection_pools) == 0

    def test_protocol_config_connection_keys(self) -> None:
        """Test that protocol configs generate unique connection keys."""
        # Same config should generate same key
        config1 = create_http_protocol_config(timeout=30.0, max_retries=3)
        config2 = create_http_protocol_config(timeout=30.0, max_retries=3)
        assert config1.get_connection_key() == config2.get_connection_key()

        # Different config should generate different key
        config3 = create_http_protocol_config(timeout=60.0, max_retries=3)
        assert config1.get_connection_key() != config3.get_connection_key()

        # SFTP configs
        sftp_config1 = create_sftp_protocol_config(
            config_name="test", connect_timeout=20.0
        )
        sftp_config2 = create_sftp_protocol_config(
            config_name="test", connect_timeout=20.0
        )
        sftp_config3 = create_sftp_protocol_config(
            config_name="test", connect_timeout=30.0
        )

        assert sftp_config1.get_connection_key() == sftp_config2.get_connection_key()
        assert sftp_config1.get_connection_key() != sftp_config3.get_connection_key()

    def test_protocol_config_types(self) -> None:
        """Test that protocol configs return correct protocol types."""
        http_config = create_http_protocol_config()
        sftp_config = create_sftp_protocol_config(config_name="test")

        assert http_config.get_protocol_type() == "http"
        assert sftp_config.get_protocol_type() == "sftp"
