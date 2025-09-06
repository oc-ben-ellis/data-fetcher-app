"""Integration tests for HTTP manager functionality using testcontainers.

This module contains integration tests for HTTP manager that use real HTTP servers
running in Docker containers via testcontainers.
"""

from typing import Any
from unittest.mock import MagicMock

import pytest
from testcontainers.core.container import (  # type: ignore[import-untyped]
    DockerContainer,
)

from data_fetcher_http.http_manager import HttpManager

# Import container management functions from conftest
from tests.conftest import add_test_label_to_container


@pytest.mark.integration
class TestHttpIntegration:
    """Integration tests for HTTP components using testcontainers."""

    @pytest.fixture(scope="class")
    def http_server_container(self) -> DockerContainer:
        """Start a simple HTTP server container for testing."""
        container = None
        try:
            # Use a simple Python HTTP server with better setup
            container = DockerContainer("python:3.9-slim")
            container.with_command(
                [
                    "sh",
                    "-c",
                    "mkdir -p /tmp/test && cd /tmp/test && echo '<html><body><h1>Test Server</h1></body></html>' > index.html && python -m http.server 8000 --bind 0.0.0.0",
                ]
            )
            container.with_exposed_ports(8000)

            # Add test label for cleanup tracking (before starting)
            add_test_label_to_container(container)

            container.start()

            # Wait for server to be ready - use HTTP health check instead of log waiting
            mapped_port = container.get_exposed_port(8000)
            host_ip = container.get_container_host_ip()
            url = f"http://{host_ip}:{mapped_port}"

            # Wait for HTTP server to be responsive
            import time

            import httpx

            max_attempts = 30  # 30 seconds total
            for attempt in range(max_attempts):
                try:
                    with httpx.Client(timeout=2.0) as client:
                        response = client.get(url)
                        if response.status_code == 200:
                            break
                except Exception:
                    pass

                if attempt < max_attempts - 1:
                    time.sleep(1)
            else:
                # If we get here, the server never responded
                if container:
                    container.stop()
                pytest.fail(
                    f"HTTP server container failed to respond after {max_attempts} seconds"
                )

            yield container

        except Exception as e:
            # Ensure container is stopped even if setup fails
            if container:
                try:
                    container.stop()
                except Exception:
                    pass
            pytest.fail(f"Failed to start HTTP server container: {e}")
        finally:
            # Stop container (label cleanup will be handled by Docker query)
            if container:
                try:
                    container.stop()
                except Exception:
                    pass

    @pytest.mark.asyncio
    async def test_http_manager_integration(
        self, http_server_container: DockerContainer
    ) -> None:
        """Test HTTP manager with real HTTP server."""
        # Get the mapped port and host IP
        mapped_port = http_server_container.get_exposed_port(8000)
        host_ip = http_server_container.get_container_host_ip()
        url = f"http://{host_ip}:{mapped_port}"

        manager = HttpManager()

        # Create mock config and app_config for the request
        mock_config = MagicMock()
        mock_config.max_retries = 3
        mock_config.timeout = 30.0
        mock_config.rate_limit_requests_per_second = 10.0
        mock_config.default_headers = {"User-Agent": "OCFetcher/1.0"}
        mock_config.authentication_mechanism = None
        mock_config.get_connection_key.return_value = "test_key"
        mock_app_config = MagicMock()

        # Make a real HTTP request
        response = await manager.request(mock_config, mock_app_config, "GET", url)

        assert response.status_code == 200
        assert "Test Server" in response.text


# Mark tests that require Docker/containers
def pytest_configure(config: Any) -> None:
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test requiring containers"
    )
    config.addinivalue_line("markers", "slow: mark test as slow running")
