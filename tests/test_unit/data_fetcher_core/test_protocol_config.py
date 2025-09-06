"""Tests for ProtocolConfig functionality.

This module contains unit tests for the new ProtocolConfig architecture.
"""

from data_fetcher_core.protocol_config import HttpProtocolConfig, SftpProtocolConfig


class TestHttpProtocolConfig:
    """Test HTTP protocol configuration functionality."""

    def test_http_protocol_config_creation(self) -> None:
        """Test HTTP protocol config creation with default values."""
        config = HttpProtocolConfig()

        assert config.timeout == 30.0
        assert config.rate_limit_requests_per_second == 10.0
        assert config.max_retries == 3
        assert config.default_headers is not None
        assert config.default_headers["User-Agent"] == "OCFetcher/1.0"
        assert config.authentication_mechanism is None

    def test_http_protocol_config_custom_values(self) -> None:
        """Test HTTP protocol config with custom values."""
        custom_headers = {"User-Agent": "CustomAgent/1.0", "X-Custom": "value"}
        config = HttpProtocolConfig(
            timeout=60.0,
            rate_limit_requests_per_second=5.0,
            max_retries=5,
            default_headers=custom_headers,
        )

        assert config.timeout == 60.0
        assert config.rate_limit_requests_per_second == 5.0
        assert config.max_retries == 5
        assert config.default_headers == custom_headers

    def test_http_protocol_config_connection_key(self) -> None:
        """Test HTTP protocol config connection key generation."""
        config1 = HttpProtocolConfig(timeout=30.0, max_retries=3)
        config2 = HttpProtocolConfig(timeout=30.0, max_retries=3)
        config3 = HttpProtocolConfig(timeout=60.0, max_retries=3)

        # Same config should generate same key
        assert config1.get_connection_key() == config2.get_connection_key()

        # Different config should generate different key
        assert config1.get_connection_key() != config3.get_connection_key()

        # Key should be a string
        assert isinstance(config1.get_connection_key(), str)
        assert len(config1.get_connection_key()) > 0

    def test_http_protocol_config_protocol_type(self) -> None:
        """Test HTTP protocol config protocol type."""
        config = HttpProtocolConfig()
        assert config.get_protocol_type() == "http"


class TestSftpProtocolConfig:
    """Test SFTP protocol configuration functionality."""

    def test_sftp_protocol_config_creation(self) -> None:
        """Test SFTP protocol config creation with default values."""
        config = SftpProtocolConfig(config_name="test_config")

        assert config.config_name == "test_config"
        assert config.connect_timeout == 20.0
        assert config.rate_limit_requests_per_second == 5.0
        assert config.max_retries == 3
        assert config.base_retry_delay == 1.0
        assert config.max_retry_delay == 60.0
        assert config.retry_exponential_base == 2.0

    def test_sftp_protocol_config_custom_values(self) -> None:
        """Test SFTP protocol config with custom values."""
        config = SftpProtocolConfig(
            config_name="custom_config",
            connect_timeout=30.0,
            rate_limit_requests_per_second=2.0,
            max_retries=5,
        )

        assert config.config_name == "custom_config"
        assert config.connect_timeout == 30.0
        assert config.rate_limit_requests_per_second == 2.0
        assert config.max_retries == 5

    def test_sftp_protocol_config_connection_key(self) -> None:
        """Test SFTP protocol config connection key generation."""
        config1 = SftpProtocolConfig(config_name="test", connect_timeout=20.0)
        config2 = SftpProtocolConfig(config_name="test", connect_timeout=20.0)
        config3 = SftpProtocolConfig(config_name="test", connect_timeout=30.0)

        # Same config should generate same key
        assert config1.get_connection_key() == config2.get_connection_key()

        # Different config should generate different key
        assert config1.get_connection_key() != config3.get_connection_key()

        # Key should be a string
        assert isinstance(config1.get_connection_key(), str)
        assert len(config1.get_connection_key()) > 0

    def test_sftp_protocol_config_protocol_type(self) -> None:
        """Test SFTP protocol config protocol type."""
        config = SftpProtocolConfig(config_name="test")
        assert config.get_protocol_type() == "sftp"
