"""Tests for SFTP manager functionality.

This module contains unit tests for SFTP manager, authentication mechanisms,
and related SFTP functionality.
"""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from data_fetcher_sftp.sftp_manager import (
    SftpManager,
)


class TestSftpManager:
    """Test SFTP manager functionality."""

    @pytest.fixture
    def mock_credentials(self) -> MagicMock:
        """Create mock SFTP credentials."""
        credentials = MagicMock()
        credentials.host = "test-host"
        credentials.username = "test-user"
        credentials.password = "test-pass"
        credentials.port = 22
        return credentials

    @pytest.fixture
    def mock_credential_provider(self, mock_credentials: MagicMock) -> AsyncMock:
        """Create a mock credential provider for SFTP."""
        provider = AsyncMock()
        provider.get_credentials.return_value = mock_credentials
        return provider

    @pytest.fixture
    def sftp_manager(self, mock_credential_provider: AsyncMock) -> SftpManager:
        """Create a basic SFTP manager for testing."""
        return SftpManager()

    @pytest.fixture
    def sftp_manager_with_retries(
        self, mock_credential_provider: AsyncMock
    ) -> SftpManager:
        """Create an SFTP manager for testing."""
        return SftpManager()

    def _create_mock_config(self) -> MagicMock:
        """Create a mock SftpProtocolConfig with proper attributes."""
        mock_config = MagicMock()
        mock_config.config_name = "test_config"
        mock_config.max_retries = 3
        mock_config.connect_timeout = 20.0
        mock_config.rate_limit_requests_per_second = 5.0
        mock_config.base_retry_delay = 1.0
        mock_config.max_retry_delay = 60.0
        mock_config.retry_exponential_base = 2.0
        mock_config.get_connection_key.return_value = "test_key"
        return mock_config

    def _create_mock_app_config(self) -> MagicMock:
        """Create a mock FetcherConfig."""
        return MagicMock()

    def _create_mock_credentials_provider(
        self, mock_credentials: MagicMock
    ) -> AsyncMock:
        """Create a mock credentials provider."""
        provider = AsyncMock()
        provider.get_credentials.return_value = mock_credentials
        return provider

    @pytest.mark.asyncio
    async def test_sftp_manager_creation(
        self, sftp_manager: SftpManager, mock_credential_provider: AsyncMock
    ) -> None:
        """Test SFTP manager creation."""
        assert hasattr(sftp_manager, "_connection_pools")
        assert isinstance(sftp_manager._connection_pools, dict)
        assert len(sftp_manager._connection_pools) == 0

    @pytest.mark.asyncio
    async def test_sftp_manager_get_connection(
        self, sftp_manager: SftpManager, mock_credentials: MagicMock
    ) -> None:
        """Test SFTP manager connection creation."""
        # Create mock objects for the required parameters
        mock_config = self._create_mock_config()
        mock_app_config = self._create_mock_app_config()
        mock_credentials_provider = self._create_mock_credentials_provider(
            mock_credentials
        )
        # Ensure provider has update_credential_provider used by pool
        mock_credentials_provider.update_credential_provider = MagicMock()

        with patch("pysftp.Connection") as mock_connection:
            mock_conn_instance = MagicMock()
            mock_connection.return_value = mock_conn_instance

            pool = sftp_manager._get_or_create_pool(mock_config)
            conn = await pool.get_connection(mock_app_config, mock_credentials_provider)

            assert conn == mock_conn_instance
            mock_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_sftp_manager_close_all_success(
        self, sftp_manager_with_retries: SftpManager
    ) -> None:
        """Test SFTP close all connections."""
        # Create mock objects for the required parameters
        mock_config = self._create_mock_config()
        mock_app_config = self._create_mock_app_config()
        mock_credentials = MagicMock()
        mock_credentials_provider = self._create_mock_credentials_provider(
            mock_credentials
        )
        mock_credentials_provider.update_credential_provider = MagicMock()

        with patch("pysftp.Connection") as mock_connection:
            mock_conn_instance = MagicMock()
            mock_connection.return_value = mock_conn_instance

            # Set up connection
            pool = sftp_manager_with_retries._get_or_create_pool(mock_config)
            await pool.get_connection(
                mock_app_config,
                mock_credentials_provider,
            )

            # Mock close to succeed
            mock_conn_instance.close.return_value = None

            await sftp_manager_with_retries.close_all()

            assert mock_conn_instance.close.call_count == 1

    @pytest.mark.asyncio
    async def test_sftp_manager_test_connection_success(
        self, sftp_manager_with_retries: SftpManager
    ) -> None:
        """Test SFTP test_connection success."""
        # Create mock objects for the required parameters
        mock_config = self._create_mock_config()
        mock_app_config = self._create_mock_app_config()
        mock_credentials = MagicMock()
        mock_credentials_provider = self._create_mock_credentials_provider(
            mock_credentials
        )
        mock_credentials_provider.update_credential_provider = MagicMock()

        with patch("pysftp.Connection") as mock_connection:
            mock_conn_instance = MagicMock()
            mock_connection.return_value = mock_conn_instance

            # Mock pwd access to succeed
            mock_conn_instance.pwd = "test_path"

            pool = sftp_manager_with_retries._get_or_create_pool(mock_config)
            result = await pool.test_connection(
                app_config=mock_app_config,
                credentials_provider=mock_credentials_provider,
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_sftp_manager_test_connection_failure(
        self, sftp_manager_with_retries: SftpManager
    ) -> None:
        """Test SFTP test_connection failure handling."""
        # Create mock objects for the required parameters
        mock_config = self._create_mock_config()
        mock_app_config = self._create_mock_app_config()
        mock_credentials = MagicMock()
        mock_credentials_provider = self._create_mock_credentials_provider(
            mock_credentials
        )
        mock_credentials_provider.update_credential_provider = MagicMock()

        with patch("pysftp.Connection") as mock_connection:
            # Mock connection creation to always fail
            mock_connection.side_effect = Exception("Connection failed")

            pool = sftp_manager_with_retries._get_or_create_pool(mock_config)
            result = await pool.test_connection(
                app_config=mock_app_config,
                credentials_provider=mock_credentials_provider,
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_sftp_manager_connection_pool_management(
        self, sftp_manager_with_retries: SftpManager
    ) -> None:
        """Test that connection pools are managed correctly."""
        # Current SftpManager uses connection pools instead of retry engine
        assert hasattr(sftp_manager_with_retries, "_connection_pools")
        assert isinstance(sftp_manager_with_retries._connection_pools, dict)
        assert len(sftp_manager_with_retries._connection_pools) == 0

    @pytest.mark.asyncio
    async def test_sftp_manager_creation_consistency(
        self, mock_credential_provider: AsyncMock
    ) -> None:
        """Test that SftpManager creation is consistent."""
        manager = SftpManager()

        assert hasattr(manager, "_connection_pools")
        assert isinstance(manager._connection_pools, dict)
        assert len(manager._connection_pools) == 0

        # Test with different manager
        manager2 = SftpManager()

        assert hasattr(manager2, "_connection_pools")
        assert isinstance(manager2._connection_pools, dict)
        assert len(manager2._connection_pools) == 0


# Utility functions for testing
def create_test_stream(content: bytes) -> AsyncGenerator[bytes]:
    """Create a test stream from bytes."""

    async def stream() -> AsyncGenerator[bytes]:
        yield content

    return stream()
