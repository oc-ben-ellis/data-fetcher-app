#!/usr/bin/env python3
"""Tests for API loader implementation.

This module contains unit tests for API loader functionality.
"""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, Mock, patch

import pytest

from data_fetcher_core.core import FetcherRecipe, FetchRunContext, RequestMeta
from data_fetcher_core.protocol_config import HttpProtocolConfig
from data_fetcher_core.storage import FileStorage
from data_fetcher_http_api.api_loader import HttpBundleLoader


def create_mock_storage() -> Mock:
    """Create a properly configured mock storage."""
    storage = Mock(spec=FileStorage)
    storage.start_bundle = AsyncMock()
    return storage


def setup_storage_bundle_context_mock(mock_storage: Mock) -> AsyncMock:
    """Set up the storage bundle context mock properly."""
    mock_bundle_context = AsyncMock()
    mock_bundle_context.add_resource = AsyncMock()
    mock_bundle_context.complete = AsyncMock()
    # Configure start_bundle to return the context directly when awaited
    mock_storage.start_bundle = AsyncMock(return_value=mock_bundle_context)
    return mock_bundle_context


class TestHttpBundleLoader:
    """Test HttpBundleLoader class."""

    @pytest.fixture
    def mock_http_config(self) -> Mock:
        """Create a mock HTTP config."""
        config = Mock(spec=HttpProtocolConfig)
        config.timeout = 5.0
        config.rate_limit_requests_per_second = 100.0
        config.max_retries = 1
        config.default_headers = {"User-Agent": "OCFetcher/1.0"}
        config.request = AsyncMock()
        return config

    @pytest.fixture
    def loader(self, mock_http_config: Mock) -> HttpBundleLoader:
        """Create a loader instance for testing."""
        return HttpBundleLoader(
            http_config=mock_http_config,
            meta_load_name="test_api_loader",
            follow_redirects=True,
            max_redirects=5,
        )

    def test_loader_creation(
        self, loader: HttpBundleLoader, mock_http_config: Mock
    ) -> None:
        """Test loader creation."""
        assert loader.http_config == mock_http_config
        assert loader.meta_load_name == "test_api_loader"
        assert loader.follow_redirects is True
        assert loader.max_redirects == 5

    @pytest.mark.asyncio
    async def test_load_api_request(
        self, loader: HttpBundleLoader, mock_http_config: Mock
    ) -> None:
        """Test loading an API request."""
        # Create mock request
        request = RequestMeta(
            url="https://api.example.com/data",
            headers={"Authorization": "Bearer token"},
            flags={"source": "test"},
        )

        # Create mock storage
        mock_storage = create_mock_storage()
        mock_bundle_context = setup_storage_bundle_context_mock(mock_storage)

        # Create mock context and recipe
        mock_context = Mock(spec=FetchRunContext)
        mock_context.run_id = "test_run_123"
        mock_context.app_config = Mock()

        mock_recipe = Mock(spec=FetcherRecipe)
        mock_recipe.recipe_id = "test_recipe"

        # Mock HTTP response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.aiter_bytes.return_value = self.create_test_stream(
            b'{"data": "test"}'
        )

        # Mock HttpManager
        with patch(
            "data_fetcher_http_api.api_loader.HttpManager"
        ) as mock_http_manager_class:
            mock_http_manager = Mock()
            mock_http_manager.request = AsyncMock(return_value=mock_response)
            mock_http_manager_class.return_value = mock_http_manager

            # Call load method
            result = await loader.load(request, mock_storage, mock_context, mock_recipe)

            # Verify HTTP request was made (do not assert exact args order beyond essentials)
            assert mock_http_manager.request.await_count == 1
            called_args, called_kwargs = mock_http_manager.request.call_args
            assert called_args[0] is mock_http_config
            assert called_args[1] is mock_context.app_config
            assert called_args[2] == "GET"
            assert called_args[3] == "https://api.example.com/data"
            assert called_kwargs.get("headers") == {"Authorization": "Bearer token"}
            assert called_kwargs.get("follow_redirects") is True

        # Verify storage operations
        mock_storage.start_bundle.assert_called_once()
        mock_bundle_context.add_resource.assert_called_once()
        mock_bundle_context.complete.assert_called_once()

        # Verify result
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].primary_url == "https://api.example.com/data"

    @pytest.mark.asyncio
    async def test_load_with_api_error(
        self, loader: HttpBundleLoader, mock_http_config: Mock
    ) -> None:
        """Test loading when API returns an error."""
        # Create mock request
        request = RequestMeta(
            url="https://api.example.com/data",
            headers={"Authorization": "Bearer token"},
            flags={"source": "test"},
        )

        # Create mock storage
        mock_storage = create_mock_storage()
        mock_bundle_context = setup_storage_bundle_context_mock(mock_storage)

        # Create mock context and recipe
        mock_context = Mock(spec=FetchRunContext)
        mock_context.run_id = "test_run_123"

        mock_recipe = Mock(spec=FetcherRecipe)
        mock_recipe.recipe_id = "test_recipe"

        # Mock error response
        mock_response = AsyncMock()
        mock_response.status_code = 401
        mock_response.headers = {"content-type": "application/json"}
        mock_response.aiter_bytes.return_value = self.create_test_stream(
            b'{"error": "Unauthorized"}'
        )

        # Mock HttpManager to return error response
        with patch(
            "data_fetcher_http_api.api_loader.HttpManager"
        ) as mock_http_manager_class:
            mock_http_manager = Mock()
            mock_http_manager.request = AsyncMock(return_value=mock_response)
            mock_http_manager_class.return_value = mock_http_manager

            # Call load method
            result = await loader.load(request, mock_storage, mock_context, mock_recipe)

            # Verify HTTP request was made
            assert mock_http_manager.request.await_count == 1

        # Verify storage operations still occurred (error responses are still stored)
        mock_storage.start_bundle.assert_called_once()
        mock_bundle_context.add_resource.assert_called_once()
        mock_bundle_context.complete.assert_called_once()

        # Verify result
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].primary_url == "https://api.example.com/data"

    @pytest.mark.asyncio
    async def test_load_with_http_exception(
        self, loader: HttpBundleLoader, mock_http_config: Mock
    ) -> None:
        """Test loading when HTTP request raises an exception."""
        # Create mock request
        request = RequestMeta(
            url="https://api.example.com/data",
            headers={"Authorization": "Bearer token"},
            flags={"source": "test"},
        )

        # Create mock storage
        mock_storage = create_mock_storage()
        setup_storage_bundle_context_mock(mock_storage)

        # Create mock context and recipe
        mock_context = Mock(spec=FetchRunContext)
        mock_context.run_id = "test_run_123"

        mock_recipe = Mock(spec=FetcherRecipe)
        mock_recipe.recipe_id = "test_recipe"

        # Mock HttpManager to raise an exception
        with patch(
            "data_fetcher_http_api.api_loader.HttpManager"
        ) as mock_http_manager_class:
            mock_http_manager = Mock()
            mock_http_manager.request = AsyncMock(
                side_effect=Exception("Connection error")
            )
            mock_http_manager_class.return_value = mock_http_manager

            # Call load method; implementation catches and returns []
            result = await loader.load(request, mock_storage, mock_context, mock_recipe)

            # Verify HTTP request was attempted and result is empty
            assert mock_http_manager.request.await_count == 1
            assert result == []

        # Verify storage operations were not performed due to exception
        mock_storage.start_bundle.assert_not_called()

    @pytest.mark.asyncio
    async def test_load_with_custom_headers(
        self, loader: HttpBundleLoader, mock_http_config: Mock
    ) -> None:
        """Test loading with custom headers."""
        # Create mock request with custom headers
        request = RequestMeta(
            url="https://api.example.com/data",
            headers={"Authorization": "Bearer token"},
            flags={"source": "test"},
        )

        # Create mock storage
        mock_storage = create_mock_storage()
        setup_storage_bundle_context_mock(mock_storage)

        # Create mock context and recipe
        mock_context = Mock(spec=FetchRunContext)
        mock_context.run_id = "test_run_123"

        mock_recipe = Mock(spec=FetcherRecipe)
        mock_recipe.recipe_id = "test_recipe"

        # Mock HTTP response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.aiter_bytes.return_value = self.create_test_stream(
            b'{"data": "test"}'
        )

        # Mock HttpManager
        with patch(
            "data_fetcher_http_api.api_loader.HttpManager"
        ) as mock_http_manager_class:
            mock_http_manager = Mock()
            mock_http_manager.request = AsyncMock(return_value=mock_response)
            mock_http_manager_class.return_value = mock_http_manager

            # Call load method
            result = await loader.load(request, mock_storage, mock_context, mock_recipe)

            # Verify HTTP request was made with custom headers
            assert mock_http_manager.request.await_count == 1
            _args, _kwargs = mock_http_manager.request.call_args
            assert _kwargs["headers"] == {"Authorization": "Bearer token"}

        # Verify result
        assert isinstance(result, list)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_load_with_custom_params(
        self, loader: HttpBundleLoader, mock_http_config: Mock
    ) -> None:
        """Test loading with custom parameters."""
        # Create mock request with custom parameters
        request = RequestMeta(
            url="https://api.example.com/data",
            headers={},
            flags={"source": "test", "params": {"page": "1", "limit": "10"}},
        )

        # Create mock storage
        mock_storage = create_mock_storage()
        setup_storage_bundle_context_mock(mock_storage)

        # Create mock context and recipe
        mock_context = Mock(spec=FetchRunContext)
        mock_context.run_id = "test_run_123"

        mock_recipe = Mock(spec=FetcherRecipe)
        mock_recipe.recipe_id = "test_recipe"

        # Mock HTTP response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.aiter_bytes.return_value = self.create_test_stream(
            b'{"data": "test"}'
        )

        # Mock HttpManager
        with patch(
            "data_fetcher_http_api.api_loader.HttpManager"
        ) as mock_http_manager_class:
            mock_http_manager = Mock()
            mock_http_manager.request = AsyncMock(return_value=mock_response)
            mock_http_manager_class.return_value = mock_http_manager

            # Call load method
            result = await loader.load(request, mock_storage, mock_context, mock_recipe)

            # Verify HTTP request was made (loader currently does not forward params)
            assert mock_http_manager.request.await_count == 1

        # Verify result
        assert isinstance(result, list)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_load_with_different_content_types(
        self, loader: HttpBundleLoader, mock_http_config: Mock
    ) -> None:
        """Test loading with different content types."""
        test_cases = [
            ("application/json", b'{"data": "json"}'),
            ("text/html", b"<html>HTML content</html>"),
            ("text/plain", b"Plain text content"),
            ("application/xml", b"<xml>XML content</xml>"),
        ]

        for content_type, content in test_cases:
            # Create mock request
            request = RequestMeta(
                url=f"https://api.example.com/data_{content_type.replace('/', '_')}",
                headers={},
                flags={"source": "test"},
            )

            # Create mock storage
            mock_storage = create_mock_storage()
            mock_bundle_context = setup_storage_bundle_context_mock(mock_storage)

            # Create mock context and recipe
            mock_context = Mock(spec=FetchRunContext)
            mock_context.run_id = "test_run_123"

            mock_recipe = Mock(spec=FetcherRecipe)
            mock_recipe.recipe_id = "test_recipe"

            # Mock HTTP response
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": content_type}
            mock_response.aiter_bytes.return_value = self.create_test_stream(content)

            # Mock HttpManager
            with patch(
                "data_fetcher_http_api.api_loader.HttpManager"
            ) as mock_http_manager_class:
                mock_http_manager = Mock()
                mock_http_manager.request = AsyncMock(return_value=mock_response)
                mock_http_manager_class.return_value = mock_http_manager

                # Call load method
                result = await loader.load(
                    request, mock_storage, mock_context, mock_recipe
                )

            # Verify result
            assert isinstance(result, list)
            assert len(result) == 1

            # Verify add_resource was called with correct content type
            mock_bundle_context.add_resource.assert_called()
            call_args = mock_bundle_context.add_resource.call_args
            assert call_args.kwargs["content_type"] == content_type

    @pytest.mark.asyncio
    async def test_load_with_different_status_codes(
        self, loader: HttpBundleLoader, mock_http_config: Mock
    ) -> None:
        """Test loading with different HTTP status codes."""
        test_cases = [200, 201, 301, 302, 400, 401, 403, 404, 500, 502, 503]

        for status_code in test_cases:
            # Create mock request
            request = RequestMeta(
                url=f"https://api.example.com/data_{status_code}",
                headers={},
                flags={"source": "test"},
            )

            # Create mock storage
            mock_storage = create_mock_storage()
            mock_bundle_context = setup_storage_bundle_context_mock(mock_storage)

            # Create mock context and recipe
            mock_context = Mock(spec=FetchRunContext)
            mock_context.run_id = "test_run_123"

            mock_recipe = Mock(spec=FetcherRecipe)
            mock_recipe.recipe_id = "test_recipe"

            # Mock HTTP response
            mock_response = AsyncMock()
            mock_response.status_code = status_code
            mock_response.headers = {"content-type": "application/json"}
            mock_response.aiter_bytes.return_value = self.create_test_stream(
                f'{{"status": {status_code}}}'.encode()
            )

            # Mock HttpManager
            with patch(
                "data_fetcher_http_api.api_loader.HttpManager"
            ) as mock_http_manager_class:
                mock_http_manager = Mock()
                mock_http_manager.request = AsyncMock(return_value=mock_response)
                mock_http_manager_class.return_value = mock_http_manager

                # Call load method
                result = await loader.load(
                    request, mock_storage, mock_context, mock_recipe
                )

            # Verify result
            assert isinstance(result, list)
            assert len(result) == 1

            # Verify add_resource was called with correct status code
            mock_bundle_context.add_resource.assert_called()
            call_args = mock_bundle_context.add_resource.call_args
            assert call_args.kwargs["status_code"] == status_code

    @staticmethod
    def create_test_stream(content: bytes) -> AsyncGenerator[bytes]:
        """Create a test stream from bytes."""

        async def stream() -> AsyncGenerator[bytes]:
            yield content

        return stream()
