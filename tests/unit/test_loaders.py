"""Tests for bundle loader implementations.

This module contains unit tests for various bundle loaders,
including HTTP, API, and SFTP loader functionality.
"""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from data_fetcher.bundle_loaders.api_loader import ApiLoader
from data_fetcher.bundle_loaders.http_loader import HttpxStreamingLoader
from data_fetcher.bundle_loaders.sftp_loader import SFTPLoader
from data_fetcher.core import FetchRunContext, RequestMeta
from data_fetcher.storage import FileStorage


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

        async def mock_aiter_bytes() -> AsyncGenerator[bytes, None]:
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

        async def mock_aiter_bytes() -> AsyncGenerator[bytes, None]:
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
        async def mock_aiter_bytes() -> AsyncGenerator[bytes, None]:
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


class TestSFTPLoader:
    """Test SFTPLoader class."""

    @pytest.fixture
    def mock_sftp_manager(self) -> AsyncMock:
        """Create a mock SFTP manager."""
        manager = AsyncMock()
        # Mock the async method explicitly
        manager.get_connection = AsyncMock()
        return manager

    @pytest.fixture
    def loader(self, mock_sftp_manager: AsyncMock) -> SFTPLoader:
        """Create a loader instance for testing."""
        return SFTPLoader(
            sftp_manager=mock_sftp_manager,
            remote_dir="/remote/path",
            filename_pattern="*.txt",
            meta_load_name="test_sftp_loader",
        )

    def test_loader_creation(
        self, loader: SFTPLoader, mock_sftp_manager: AsyncMock
    ) -> None:
        """Test loader creation."""
        assert loader.sftp_manager == mock_sftp_manager
        assert loader.remote_dir == "/remote/path"
        assert loader.filename_pattern == "*.txt"
        assert loader.meta_load_name == "test_sftp_loader"

    @pytest.mark.asyncio
    async def test_load_sftp_file(
        self, loader: SFTPLoader, mock_sftp_manager: AsyncMock
    ) -> None:
        """Test loading SFTP file."""
        # Mock SFTP manager connection and file operations
        mock_conn = Mock()  # Use regular Mock for SFTP connection (synchronous methods)
        # Since get_connection is async, we need to return the mock directly
        mock_sftp_manager.get_connection.return_value = mock_conn

        # Mock file stat (not a directory) - stat is synchronous in pysftp
        mock_stat = Mock()
        mock_stat.st_mode = 0o644  # Regular file
        mock_stat.st_size = 1024
        mock_stat.st_mtime = 1234567890
        mock_conn.stat.return_value = mock_stat

        # Mock file stream
        mock_file = Mock()
        mock_file.read.return_value = b"file content"
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_file
        mock_context.__exit__.return_value = None
        mock_conn.open.return_value = mock_context

        # Create request and context
        request = RequestMeta(url="sftp://example.com/remote/file.txt")
        ctx = FetchRunContext()

        # Mock storage bundle
        mock_storage = Mock()
        # setup_storage_bundle_mock configures mock_storage.open_bundle but we don't need the returned mock_bundle
        setup_storage_bundle_mock(mock_storage)

        # Load the request
        bundle_refs = await loader.load(request, mock_storage, ctx)

        # Verify results
        assert len(bundle_refs) == 1
        assert (
            bundle_refs[0].primary_url
            == "sftp:///remote/path/example.com/remote/file.txt"
        )

        # Verify SFTP manager was called
        mock_sftp_manager.get_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_with_sftp_error(
        self, loader: SFTPLoader, mock_sftp_manager: AsyncMock
    ) -> None:
        """Test loading when SFTP manager raises an error."""
        # Mock SFTP manager to raise an exception
        mock_sftp_manager.get_connection.side_effect = Exception("SFTP error")

        # Create request and context
        request = RequestMeta(url="sftp://example.com/remote/file.txt")
        ctx = FetchRunContext()

        # Mock storage bundle
        mock_storage = Mock()
        # setup_storage_bundle_mock configures mock_storage.open_bundle but we don't need the returned mock_bundle
        setup_storage_bundle_mock(mock_storage)

        # Load the request - should handle error gracefully
        bundle_refs = await loader.load(request, mock_storage, ctx)

        # Should return empty list or handle error appropriately
        assert isinstance(bundle_refs, list)


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

        async def mock_aiter_bytes() -> AsyncGenerator[bytes, None]:
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

        async def mock_aiter_bytes() -> AsyncGenerator[bytes, None]:
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


class TestLoaderIntegration:
    """Integration tests for loaders."""

    @pytest.mark.asyncio
    async def test_loader_with_storage_decorators(self) -> None:
        """Test loader with storage decorators."""
        # This test would verify that loaders work correctly with storage decorators
        # like unzip decorators, bundle decorators, etc.

    @pytest.mark.asyncio
    async def test_loader_with_different_content_types(self) -> None:
        """Test loader with different content types."""
        # This test would verify that loaders handle different content types correctly

    @pytest.mark.asyncio
    async def test_loader_with_large_files(self) -> None:
        """Test loader with large files."""
        # This test would verify that loaders handle large files correctly
