"""Tests for HTTP loader implementation.

This module contains unit tests for HTTP loader functionality.
"""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, Mock

import pytest

from data_fetcher_core.core import FetchRunContext, RequestMeta
from data_fetcher_core.storage import FileStorage
from data_fetcher_http.http_loader import HttpxStreamingLoader


def create_mock_storage() -> Mock:
    """Create a properly configured mock storage."""
    return Mock(spec=FileStorage)


def setup_storage_bundle_mock(mock_storage: Mock) -> AsyncMock:
    """Set up the storage bundle mock properly."""
    mock_bundle = AsyncMock()
    # Create a proper async context manager mock
    mock_context = AsyncMock()
    # Configure the async context manager methods
    mock_context.__aenter__ = AsyncMock(return_value=mock_bundle)
    mock_context.__aexit__ = AsyncMock(return_value=None)
    mock_storage.open_bundle.return_value = mock_context
    return mock_bundle


class TestHttpxStreamingLoader:
    """Test HttpxStreamingLoader class."""

    @pytest.fixture
    def mock_http_manager(self) -> AsyncMock:
        """Create a mock HTTP manager."""
        manager = AsyncMock()
        # Mock the async method explicitly
        manager.request = AsyncMock()
        return manager

    @pytest.fixture
    def loader(self, mock_http_manager: AsyncMock) -> HttpxStreamingLoader:
        """Create a loader instance for testing."""
        return HttpxStreamingLoader(
            http_manager=mock_http_manager,
            max_related=2,
            follow_redirects=True,
            max_redirects=5,
        )

    def test_loader_creation(
        self, loader: HttpxStreamingLoader, mock_http_manager: AsyncMock
    ) -> None:
        """Test loader creation."""
        assert loader.http_manager == mock_http_manager
        assert loader.max_related == 2
        assert loader.follow_redirects is True
        assert loader.max_redirects == 5

    @pytest.mark.asyncio
    async def test_load_successful_request(
        self, loader: HttpxStreamingLoader, mock_http_manager: AsyncMock
    ) -> None:
        """Test successful HTTP request loading."""
        # Mock the HTTP manager response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html"}
        # Mock aiter_bytes as an async method that returns an async iterator

        async def mock_aiter_bytes() -> AsyncGenerator[bytes]:
            yield b"<html>test</html>"

        mock_response.aiter_bytes = mock_aiter_bytes
        mock_http_manager.request.return_value = mock_response

        # Create request and context
        request = RequestMeta(url="https://example.com")
        ctx = FetchRunContext()

        # Mock storage bundle
        mock_storage = Mock()
        setup_storage_bundle_mock(mock_storage)

        # Load the request
        bundle_refs = await loader.load(request, mock_storage, ctx)

        # Verify results
        assert len(bundle_refs) == 1
        assert bundle_refs[0].primary_url == "https://example.com"
        assert bundle_refs[0].resources_count == 1

        # Verify HTTP manager was called
        mock_http_manager.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_with_custom_headers(
        self, loader: HttpxStreamingLoader, mock_http_manager: AsyncMock
    ) -> None:
        """Test loading with custom headers."""
        # Mock response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html"}
        # Mock aiter_bytes as an async method that returns an async iterator

        async def mock_aiter_bytes() -> AsyncGenerator[bytes]:
            yield b"<html>test</html>"

        mock_response.aiter_bytes = mock_aiter_bytes
        mock_http_manager.request.return_value = mock_response

        # Create request with custom headers
        request = RequestMeta(
            url="https://example.com",
            headers={"Authorization": "Bearer token123"},
        )
        ctx = FetchRunContext()

        # Mock storage bundle
        mock_storage = Mock()
        setup_storage_bundle_mock(mock_storage)

        # Load the request
        await loader.load(request, mock_storage, ctx)

        # Verify headers were passed correctly
        call_args = mock_http_manager.request.call_args
        assert "Authorization" in call_args[1]["headers"]

    @pytest.mark.asyncio
    async def test_load_with_error_response(
        self, loader: HttpxStreamingLoader, mock_http_manager: AsyncMock
    ) -> None:
        """Test loading with error response."""
        # Mock error response
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_response.headers = {"content-type": "text/html"}

        # Mock aiter_bytes as an async method that returns an async iterator
        async def mock_aiter_bytes() -> AsyncGenerator[bytes]:
            yield b"Not Found"

        mock_response.aiter_bytes = mock_aiter_bytes
        mock_http_manager.request.return_value = mock_response

        # Create request and context
        request = RequestMeta(url="https://example.com/notfound")
        ctx = FetchRunContext()

        # Mock storage bundle
        mock_storage = Mock()
        setup_storage_bundle_mock(mock_storage)

        # Load the request
        bundle_refs = await loader.load(request, mock_storage, ctx)

        # Should still return bundle refs even for error responses
        assert len(bundle_refs) == 1
        assert bundle_refs[0].primary_url == "https://example.com/notfound"

    @pytest.mark.asyncio
    async def test_load_with_http_error(
        self, loader: HttpxStreamingLoader, mock_http_manager: AsyncMock
    ) -> None:
        """Test loading when HTTP manager raises an error."""
        # Mock HTTP manager to raise an exception
        mock_http_manager.request.side_effect = Exception("Network error")

        # Create request and context
        request = RequestMeta(url="https://example.com")
        ctx = FetchRunContext()

        # Mock storage bundle
        mock_storage = Mock()
        setup_storage_bundle_mock(mock_storage)

        # Load the request - should handle error gracefully
        bundle_refs = await loader.load(request, mock_storage, ctx)

        # Should return empty list or handle error appropriately
        assert isinstance(bundle_refs, list)
