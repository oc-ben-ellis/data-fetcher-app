"""Tests for HTTP manager functionality.

This module contains unit tests for HTTP manager and related HTTP functionality.
"""

from collections.abc import Awaitable, Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from testcontainers.core.container import (  # type: ignore[import-untyped]
    DockerContainer,
)

from data_fetcher_http.http_manager import HttpManager
from data_fetcher_sftp.authentication import (
    BasicAuthenticationMechanism,
    BearerTokenAuthenticationMechanism,
    NoAuthenticationMechanism,
)


class TestHttpManager:
    """Test HTTP manager functionality."""

    @pytest.fixture
    def http_manager(self) -> HttpManager:
        """Create a basic HTTP manager for testing."""
        return HttpManager(
            timeout=5.0,
            rate_limit_requests_per_second=10.0,
            max_retries=2,
        )

    @pytest.fixture
    def mock_credential_provider(self) -> AsyncMock:
        """Create a mock credential provider."""
        provider = AsyncMock()
        provider.get_credential = AsyncMock(return_value="test_value")
        return provider

    @pytest.mark.asyncio
    async def test_http_manager_creation(self, http_manager: HttpManager) -> None:
        """Test HTTP manager creation with default values."""
        assert http_manager.timeout == 5.0
        assert http_manager.rate_limit_requests_per_second == 10.0
        assert http_manager.max_retries == 2
        assert http_manager.default_headers is not None
        assert http_manager.default_headers["User-Agent"] == "OCFetcher/1.0"
        assert isinstance(
            http_manager.authentication_mechanism, NoAuthenticationMechanism
        )

    @pytest.mark.asyncio
    async def test_http_manager_custom_headers(self) -> None:
        """Test HTTP manager with custom headers."""
        custom_headers = {"User-Agent": "CustomAgent/1.0", "X-Custom": "value"}
        manager = HttpManager(default_headers=custom_headers)

        assert manager.default_headers is not None
        assert manager.default_headers["User-Agent"] == "CustomAgent/1.0"
        assert manager.default_headers["X-Custom"] == "value"

    @pytest.mark.asyncio
    async def test_http_manager_rate_limiting(self, http_manager: HttpManager) -> None:
        """Test HTTP manager rate limiting."""
        # Mock asyncio.sleep to avoid real waiting
        with patch("asyncio.sleep") as mock_sleep:
            with patch("httpx.AsyncClient") as mock_client:
                mock_response = MagicMock()
                mock_response.status_code = 200
                # Use AsyncMock for async context manager methods
                mock_client_instance = AsyncMock()
                mock_client_instance.request.return_value = mock_response
                mock_client.return_value.__aenter__ = AsyncMock(
                    return_value=mock_client_instance
                )
                mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

                # First request
                await http_manager.request("GET", "https://example.com")
                # First request should not sleep
                assert mock_sleep.call_count == 0

                # Second request should be rate limited
                await http_manager.request("GET", "https://example.com")

                # Should have called sleep once for rate limiting
                assert mock_sleep.call_count == 1
                assert mock_sleep.call_args is not None
                call_args = mock_sleep.call_args
                assert call_args is not None
                sleep_duration = call_args[0][0]
                assert 0.09 <= sleep_duration <= 0.11  # ~100ms minimum interval

    @pytest.mark.asyncio
    async def test_http_manager_retries(self, http_manager: HttpManager) -> None:
        """Test HTTP manager retry logic."""
        with patch("httpx.AsyncClient") as mock_client:
            # First call raises exception, second succeeds
            mock_client_instance = AsyncMock()
            mock_client_instance.request.side_effect = [
                httpx.ConnectError("Connection failed"),
                MagicMock(status_code=200),
            ]
            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            response = await http_manager.request("GET", "https://example.com")
            assert response.status_code == 200

            # Should have been called twice (retry)
            assert mock_client_instance.request.call_count == 2

    @pytest.mark.asyncio
    async def test_http_manager_max_retries_exceeded(
        self, http_manager: HttpManager
    ) -> None:
        """Test HTTP manager when max retries are exceeded."""
        with patch("httpx.AsyncClient") as mock_client:
            # All calls raise exceptions - need 4 total (initial + 3 retries)
            mock_client_instance = AsyncMock()
            mock_client_instance.request.side_effect = [
                httpx.ConnectError("Connection failed"),
                httpx.ConnectError("Connection failed"),
                httpx.ConnectError("Connection failed"),
                httpx.ConnectError("Connection failed"),
            ]
            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            with pytest.raises(httpx.ConnectError):
                await http_manager.request("GET", "https://example.com")

    @pytest.mark.asyncio
    async def test_http_manager_with_basic_auth(
        self, mock_credential_provider: AsyncMock
    ) -> None:
        """Test HTTP manager with basic authentication."""
        auth_mechanism = BasicAuthenticationMechanism(
            credential_provider=mock_credential_provider, config_name="test_config"
        )

        manager = HttpManager(authentication_mechanism=auth_mechanism)

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            # Use AsyncMock for async context manager methods
            mock_client_instance = AsyncMock()
            mock_client_instance.request.return_value = mock_response
            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            await manager.request("GET", "https://example.com")

            # Check that request was made with auth headers
            call_args = mock_client_instance.request.call_args
            headers = call_args[1].get("headers", {})

            # Should have Authorization header
            assert "Authorization" in headers
            assert headers["Authorization"].startswith("Basic ")

    @pytest.mark.asyncio
    async def test_http_manager_with_bearer_auth(
        self, mock_credential_provider: AsyncMock
    ) -> None:
        """Test HTTP manager with bearer token authentication."""
        auth_mechanism = BearerTokenAuthenticationMechanism(
            credential_provider=mock_credential_provider, config_name="test_config"
        )

        manager = HttpManager(authentication_mechanism=auth_mechanism)

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            # Use AsyncMock for async context manager methods
            mock_client_instance = AsyncMock()
            mock_client_instance.request.return_value = mock_response
            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            # Mock the retry engine to call the actual _make_request function
            async def mock_execute_with_retry(
                func: Callable[[], Awaitable[httpx.Response]],
            ) -> httpx.Response:
                return await func()

            mock_retry_engine = AsyncMock()
            mock_retry_engine.execute_with_retry_async = mock_execute_with_retry
            manager._retry_engine = mock_retry_engine

            await manager.request("GET", "https://example.com")

            # Check that request was made with auth headers
            call_args = mock_client_instance.request.call_args
            assert call_args is not None
            headers = call_args[1].get("headers", {})

            # Should have Authorization header
            assert "Authorization" in headers
            assert headers["Authorization"].startswith("Bearer ")


@pytest.mark.integration
class TestHttpIntegration:
    """Integration tests for HTTP components using testcontainers."""

    @pytest.fixture(scope="class")
    def http_server_container(self) -> DockerContainer:
        """Start a simple HTTP server container for testing."""
        try:
            container = DockerContainer("python:3.9-slim")
            container.with_command(["python", "-m", "http.server", "8000"])
            container.with_exposed_ports(8000)
            container.start()

            # Wait for server to be ready - use HTTP health check instead of log waiting
            mapped_port = container.get_exposed_port(8000)
            url = f"http://localhost:{mapped_port}"

            # Wait for HTTP server to be responsive
            import time

            import httpx

            max_attempts = 30  # 30 seconds total
            for attempt in range(max_attempts):
                try:
                    with httpx.Client(timeout=1.0) as client:
                        response = client.get(url)
                        if response.status_code == 200:
                            break
                except Exception:
                    pass

                if attempt < max_attempts - 1:
                    time.sleep(1)
            else:
                # If we get here, the server never responded
                container.stop()
                pytest.fail(
                    f"HTTP server container failed to respond after {max_attempts} seconds"
                )

            yield container

            container.stop()
        except Exception as e:
            pytest.fail(f"Failed to start HTTP server container: {e}")

    @pytest.mark.asyncio
    async def test_http_manager_integration(
        self, http_server_container: DockerContainer
    ) -> None:
        """Test HTTP manager with real HTTP server."""
        # Get the mapped port
        mapped_port = http_server_container.get_exposed_port(8000)
        url = f"http://localhost:{mapped_port}"

        manager = HttpManager(timeout=10.0, rate_limit_requests_per_second=5.0)

        # Make a real HTTP request
        response = await manager.request("GET", url)

        assert response.status_code == 200
        assert "Directory listing for" in response.text


# Mark tests that require Docker/containers
def pytest_configure(config: Any) -> None:
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test requiring containers"
    )
    config.addinivalue_line("markers", "slow: mark test as slow running")
