"""Tests for the new HTTP manager API with ProtocolConfig.

This module contains unit tests for the new HTTP manager architecture.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from data_fetcher_core.config_factory import FetcherConfig
from data_fetcher_core.protocol_config import HttpProtocolConfig
from data_fetcher_http.http_manager import HttpManager


class TestHttpManagerNewAPI:
    """Test HTTP manager with new ProtocolConfig API."""

    @pytest.fixture
    def http_config(self) -> HttpProtocolConfig:
        """Create a basic HTTP protocol config for testing."""
        return HttpProtocolConfig(
            timeout=5.0,
            rate_limit_requests_per_second=100.0,  # Much faster for testing
            max_retries=1,  # Fewer retries for faster tests
        )

    @pytest.fixture
    def http_manager(self) -> HttpManager:
        """Create a basic HTTP manager for testing."""
        return HttpManager()

    @pytest.fixture
    def mock_credential_provider(self) -> AsyncMock:
        """Create a mock credential provider."""
        provider = AsyncMock()
        provider.get_credential = AsyncMock(return_value="test_value")
        return provider

    @pytest.fixture
    def mock_app_config(self, mock_credential_provider: AsyncMock) -> FetcherConfig:
        """Create a mock app config for testing."""
        return FetcherConfig(
            credential_provider=mock_credential_provider,
            kv_store=AsyncMock(),  # Mock kv store
            storage=AsyncMock(),  # Mock storage
        )

    @pytest.mark.asyncio
    async def test_http_manager_creation(self, http_manager: HttpManager) -> None:
        """Test HTTP manager creation."""
        assert isinstance(http_manager, HttpManager)
        assert hasattr(http_manager, "_connection_pools")
        assert len(http_manager._connection_pools) == 0

    @pytest.mark.asyncio
    async def test_http_manager_single_request(
        self,
        http_manager: HttpManager,
        http_config: HttpProtocolConfig,
        mock_app_config: FetcherConfig,
    ) -> None:
        """Test HTTP manager single request."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "test response"

            mock_client_instance = AsyncMock()
            mock_client_instance.request.return_value = mock_response
            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            response = await http_manager.request(
                http_config, mock_app_config, "GET", "https://example.com"
            )

            assert response.status_code == 200
            assert response.text == "test response"

            # Should have created one connection pool
            assert len(http_manager._connection_pools) == 1

    @pytest.mark.asyncio
    async def test_http_manager_multiple_configs(
        self, http_manager: HttpManager, mock_app_config: FetcherConfig
    ) -> None:
        """Test HTTP manager with multiple different configurations."""
        config1 = HttpProtocolConfig(timeout=5.0, max_retries=1)
        config2 = HttpProtocolConfig(timeout=10.0, max_retries=2)

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200

            mock_client_instance = AsyncMock()
            mock_client_instance.request.return_value = mock_response
            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            # Make requests with different configs
            await http_manager.request(
                config1, mock_app_config, "GET", "https://example1.com"
            )
            await http_manager.request(
                config2, mock_app_config, "GET", "https://example2.com"
            )

            # Should have created two different connection pools
            assert len(http_manager._connection_pools) == 2

    @pytest.mark.asyncio
    async def test_http_manager_same_config_reuse(
        self,
        http_manager: HttpManager,
        http_config: HttpProtocolConfig,
        mock_app_config: FetcherConfig,
    ) -> None:
        """Test HTTP manager reuses connection pools for same config."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200

            mock_client_instance = AsyncMock()
            mock_client_instance.request.return_value = mock_response
            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            # Make multiple requests with same config
            await http_manager.request(
                http_config, mock_app_config, "GET", "https://example1.com"
            )
            await http_manager.request(
                http_config, mock_app_config, "GET", "https://example2.com"
            )
            await http_manager.request(
                http_config, mock_app_config, "GET", "https://example3.com"
            )

            # Should have created only one connection pool (reused)
            assert len(http_manager._connection_pools) == 1

    @pytest.mark.asyncio
    async def test_http_manager_rate_limiting(
        self,
        http_manager: HttpManager,
        http_config: HttpProtocolConfig,
        mock_app_config: FetcherConfig,
    ) -> None:
        """Test HTTP manager rate limiting with new API."""
        with patch("asyncio.sleep") as mock_sleep:
            with patch("httpx.AsyncClient") as mock_client:
                mock_response = MagicMock()
                mock_response.status_code = 200

                mock_client_instance = AsyncMock()
                mock_client_instance.request.return_value = mock_response
                mock_client.return_value.__aenter__ = AsyncMock(
                    return_value=mock_client_instance
                )
                mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

                # First request
                await http_manager.request(
                    http_config, mock_app_config, "GET", "https://example.com"
                )
                assert mock_sleep.call_count == 0

                # Second request should be rate limited
                await http_manager.request(
                    http_config, mock_app_config, "GET", "https://example.com"
                )
                assert mock_sleep.call_count == 1

    @pytest.mark.asyncio
    async def test_http_manager_retries(
        self,
        http_manager: HttpManager,
        http_config: HttpProtocolConfig,
        mock_app_config: FetcherConfig,
    ) -> None:
        """Test HTTP manager retry logic with new API."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200

            mock_client_instance = AsyncMock()
            mock_client_instance.request.side_effect = [
                httpx.ConnectError("Connection failed"),
                mock_response,
            ]
            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            response = await http_manager.request(
                http_config, mock_app_config, "GET", "https://example.com"
            )

            assert response.status_code == 200
            assert mock_client_instance.request.call_count == 2
