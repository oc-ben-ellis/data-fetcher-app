"""Tests for API loader implementation.

This module contains unit tests for API loader functionality.
"""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, Mock

import pytest

from data_fetcher_core.core import FetchRunContext, RequestMeta
from data_fetcher_core.storage import FileStorage
from data_fetcher_http_api.api_loader import ApiLoader


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


class TestApiLoader:
    """Test ApiLoader class."""

    @pytest.fixture
    def mock_http_manager(self) -> AsyncMock:
        """Create a mock HTTP manager."""
        manager = AsyncMock()
        # Mock the async method explicitly
        manager.request = AsyncMock()
        return manager

    @pytest.fixture
    def loader(self, mock_http_manager: AsyncMock) -> ApiLoader:
        """Create a loader instance for testing."""
        return ApiLoader(
            http_manager=mock_http_manager,
            meta_load_name="test_api_loader",
            follow_redirects=True,
            max_redirects=5,
        )

    def test_loader_creation(
        self, loader: ApiLoader, mock_http_manager: AsyncMock
    ) -> None:
        """Test loader creation."""
        assert loader.http_manager == mock_http_manager
        assert loader.meta_load_name == "test_api_loader"
        assert loader.follow_redirects is True
        assert loader.max_redirects == 5

    @pytest.mark.asyncio
    async def test_load_api_request(
        self, loader: ApiLoader, mock_http_manager: AsyncMock
    ) -> None:
        """Test loading API request."""
        # Mock the HTTP manager response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        # Mock aiter_bytes as an async method that returns an async iterator

        async def mock_aiter_bytes() -> AsyncGenerator[bytes]:
            yield b'{"data": "test"}'

        mock_response.aiter_bytes = mock_aiter_bytes
        mock_http_manager.request.return_value = mock_response

        # Create request and context
        request = RequestMeta(url="https://api.example.com/v1/users")
        ctx = FetchRunContext()

        # Mock storage bundle
        mock_storage = Mock()
        # setup_storage_bundle_mock configures mock_storage.open_bundle but we don't need the returned mock_bundle
        setup_storage_bundle_mock(mock_storage)

        # Load the request
        bundle_refs = await loader.load(request, mock_storage, ctx)

        # Verify results
        assert len(bundle_refs) == 1
        assert bundle_refs[0].primary_url == "https://api.example.com/v1/users"

        # Verify HTTP manager was called
        mock_http_manager.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_with_api_error(
        self, loader: ApiLoader, mock_http_manager: AsyncMock
    ) -> None:
        """Test loading when API returns an error."""
        # Mock error response
        mock_response = AsyncMock()
        mock_response.status_code = 401
        mock_response.headers = {"content-type": "application/json"}
        # Mock aiter_bytes as an async method that returns an async iterator

        async def mock_aiter_bytes() -> AsyncGenerator[bytes]:
            yield b'{"error": "Unauthorized"}'

        mock_response.aiter_bytes = mock_aiter_bytes
        mock_http_manager.request.return_value = mock_response

        # Create request and context
        request = RequestMeta(url="https://api.example.com/v1/users")
        ctx = FetchRunContext()

        # Mock storage bundle
        mock_storage = Mock()
        # setup_storage_bundle_mock configures mock_storage.open_bundle but we don't need the returned mock_bundle
        setup_storage_bundle_mock(mock_storage)

        # Load the request
        bundle_refs = await loader.load(request, mock_storage, ctx)

        # Should still return bundle refs even for error responses
        assert len(bundle_refs) == 1
        assert bundle_refs[0].primary_url == "https://api.example.com/v1/users"
