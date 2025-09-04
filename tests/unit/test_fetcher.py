"""Tests for main fetcher implementation.

This module contains unit tests for the main Fetcher class, FetchPlan,
FetchResult, and related execution components.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from data_fetcher.core import FetchContext, FetchPlan, FetchRunContext, RequestMeta
from data_fetcher.fetcher import Fetcher, FetchResult


class TestFetchContext:
    """Test FetchContext class."""

    def test_basic_creation(self) -> None:
        """Test basic FetchContext creation."""
        ctx = FetchContext()
        assert ctx.bundle_locators == []
        assert ctx.bundle_loader is None
        assert ctx.storage is None

    def test_with_all_fields(self) -> None:
        """Test FetchContext creation with all fields."""
        mock_loader = MagicMock()
        mock_storage = MagicMock()
        mock_bundle_locator = MagicMock()

        ctx = FetchContext(
            bundle_locators=[mock_bundle_locator],
            bundle_loader=mock_loader,
            storage=mock_storage,
        )
        assert ctx.bundle_locators == [mock_bundle_locator]
        assert ctx.bundle_loader == mock_loader
        assert ctx.storage == mock_storage


class TestFetchResult:
    """Test FetchResult class."""

    def test_basic_creation(self) -> None:
        """Test basic FetchResult creation."""
        ctx = FetchRunContext()
        result = FetchResult(processed_count=10, errors=["error1"], context=ctx)
        assert result.processed_count == 10
        assert result.errors == ["error1"]
        assert result.context == ctx

    def test_with_no_errors(self) -> None:
        """Test FetchResult creation with no errors."""
        ctx = FetchRunContext()
        result = FetchResult(processed_count=5, errors=[], context=ctx)
        assert result.processed_count == 5
        assert result.errors == []
        assert result.context == ctx


class TestFetcher:
    """Test Fetcher class."""

    @pytest.fixture
    def mock_loader(self) -> AsyncMock:
        """Create a mock loader."""
        loader = AsyncMock()
        loader.load.return_value = []
        return loader

    @pytest.fixture
    def mock_storage(self) -> AsyncMock:
        """Create a mock storage."""
        return AsyncMock()

    @pytest.fixture
    def mock_bundle_locator(self) -> AsyncMock:
        """Create a mock frontier bundle locator."""
        bundle_locator = AsyncMock()
        bundle_locator.get_next_urls.return_value = []
        return bundle_locator

    @pytest.fixture
    def fetcher(
        self,
        mock_loader: AsyncMock,
        mock_storage: AsyncMock,
        mock_bundle_locator: AsyncMock,
    ) -> Fetcher:
        """Create a fetcher instance for testing."""
        ctx = FetchContext(
            bundle_locators=[mock_bundle_locator],
            bundle_loader=mock_loader,
            storage=mock_storage,
        )
        return Fetcher(ctx)

    def test_fetcher_creation(
        self,
        fetcher: Fetcher,
        mock_loader: AsyncMock,
        mock_storage: AsyncMock,
        mock_bundle_locator: AsyncMock,
    ) -> None:
        """Test Fetcher creation."""
        assert fetcher.ctx.bundle_loader == mock_loader
        assert fetcher.ctx.storage == mock_storage
        assert fetcher.ctx.bundle_locators == [mock_bundle_locator]
        assert isinstance(fetcher.run_ctx, FetchRunContext)

    @pytest.mark.asyncio
    async def test_run_with_empty_plan(self, fetcher: Fetcher) -> None:
        """Test running fetcher with empty plan."""
        plan = FetchPlan(requests=[], context=FetchRunContext(), concurrency=1)
        result = await fetcher.run(plan)

        assert isinstance(result, FetchResult)
        assert result.processed_count == 0
        assert result.errors == []
        assert result.context == plan.context

    @pytest.mark.asyncio
    async def test_run_with_requests(
        self, fetcher: Fetcher, mock_loader: AsyncMock
    ) -> None:
        """Test running fetcher with requests."""
        requests = [
            RequestMeta(url="https://example.com/1"),
            RequestMeta(url="https://example.com/2"),
        ]
        plan = FetchPlan(requests=requests, context=FetchRunContext(), concurrency=2)

        # Mock the loader to return bundle refs
        mock_loader.load.return_value = [MagicMock()]

        result = await fetcher.run(plan)

        assert isinstance(result, FetchResult)
        # Verify that the loader was called for each request
        assert mock_loader.load.call_count == 2

    @pytest.mark.asyncio
    async def test_run_with_bundle_locator_urls(
        self, fetcher: Fetcher, mock_bundle_locator: AsyncMock, mock_loader: AsyncMock
    ) -> None:
        """Test running fetcher with URLs from bundle locators."""
        bundle_locator_requests = [
            RequestMeta(url="https://bundle-locator.com/1"),
            RequestMeta(url="https://bundle-locator.com/2"),
        ]
        # Make the bundle locator return URLs only once, then empty list
        mock_bundle_locator.get_next_urls.side_effect = [bundle_locator_requests, []]

        plan = FetchPlan(requests=[], context=FetchRunContext(), concurrency=1)
        mock_loader.load.return_value = [MagicMock()]

        result = await fetcher.run(plan)

        assert isinstance(result, FetchResult)
        # Verify that the bundle locator was called
        assert mock_bundle_locator.get_next_urls.call_count >= 1
        # Verify that the loader was called for bundle locator requests
        assert mock_loader.load.call_count == 2

    @pytest.mark.asyncio
    async def test_run_with_bundle_locator_callbacks(
        self, fetcher: Fetcher, mock_bundle_locator: AsyncMock, mock_loader: AsyncMock
    ) -> None:
        """Test running fetcher with bundle locator URL processed callbacks."""
        # Add handle_url_processed method to mock bundle locator
        mock_bundle_locator.handle_url_processed = AsyncMock()
        # Make the bundle locator return empty list to avoid infinite loop
        mock_bundle_locator.get_next_urls.return_value = []

        requests = [RequestMeta(url="https://example.com")]
        plan = FetchPlan(requests=requests, context=FetchRunContext(), concurrency=1)
        mock_loader.load.return_value = [MagicMock()]

        result = await fetcher.run(plan)

        assert isinstance(result, FetchResult)
        # Verify that the bundle locator callback was called
        mock_bundle_locator.handle_url_processed.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_with_loader_error(
        self, fetcher: Fetcher, mock_loader: AsyncMock
    ) -> None:
        """Test running fetcher when loader raises an error."""
        requests = [RequestMeta(url="https://example.com")]
        plan = FetchPlan(requests=requests, context=FetchRunContext(), concurrency=1)

        # Mock the loader to raise an exception
        mock_loader.load.side_effect = Exception("Loader error")

        result = await fetcher.run(plan)

        assert isinstance(result, FetchResult)
        # The fetcher should handle errors gracefully
        assert result.processed_count == 0

    @pytest.mark.asyncio
    async def test_run_with_concurrent_workers(
        self, fetcher: Fetcher, mock_loader: AsyncMock
    ) -> None:
        """Test running fetcher with multiple concurrent workers."""
        requests = [
            RequestMeta(url="https://example.com/1"),
            RequestMeta(url="https://example.com/2"),
            RequestMeta(url="https://example.com/3"),
        ]
        plan = FetchPlan(requests=requests, context=FetchRunContext(), concurrency=3)
        mock_loader.load.return_value = [MagicMock()]

        result = await fetcher.run(plan)

        assert isinstance(result, FetchResult)
        # Verify that the loader was called for each request
        assert mock_loader.load.call_count == 3

    @pytest.mark.asyncio
    async def test_run_with_shared_context(self, fetcher: Fetcher) -> None:
        """Test running fetcher with shared context data."""
        shared_data = {"key": "value", "count": 42}
        run_ctx = FetchRunContext(shared=shared_data)
        plan = FetchPlan(requests=[], context=run_ctx, concurrency=1)

        result = await fetcher.run(plan)

        assert isinstance(result, FetchResult)
        assert result.context.shared == shared_data

    @pytest.mark.asyncio
    async def test_run_with_run_id(self, fetcher: Fetcher) -> None:
        """Test running fetcher with run_id in context."""
        run_ctx = FetchRunContext(run_id="test-run-123")
        plan = FetchPlan(requests=[], context=run_ctx, concurrency=1)

        result = await fetcher.run(plan)

        assert isinstance(result, FetchResult)
        assert result.context.run_id == "test-run-123"


class TestFetcherIntegration:
    """Integration tests for the Fetcher class."""

    @pytest.mark.asyncio
    async def test_fetcher_with_multiple_bundle_locators(self) -> None:
        """Test fetcher with multiple frontier bundle_locators."""
        # Create mock bundle_locators
        bundle_locator1 = AsyncMock()
        bundle_locator1.get_next_urls.side_effect = [
            [RequestMeta(url="https://bundle_locator1.com")],
            [],
        ]
        bundle_locator1.handle_url_processed = AsyncMock()

        bundle_locator2 = AsyncMock()
        bundle_locator2.get_next_urls.side_effect = [
            [RequestMeta(url="https://bundle_locator2.com")],
            [],
        ]
        bundle_locator2.handle_url_processed = AsyncMock()

        # Create mock loader and storage
        loader = AsyncMock()
        loader.load.return_value = [MagicMock()]
        storage = AsyncMock()

        # Create fetcher
        ctx = FetchContext(
            bundle_locators=[bundle_locator1, bundle_locator2],
            bundle_loader=loader,
            storage=storage,
        )
        fetcher = Fetcher(ctx)

        # Run fetcher
        plan = FetchPlan(requests=[], context=FetchRunContext(), concurrency=2)
        result = await fetcher.run(plan)

        # Verify results
        assert isinstance(result, FetchResult)
        assert (
            result.processed_count == 2
        )  # Should process both URLs from bundle_locators

        # Verify bundle_locators were called
        assert bundle_locator1.get_next_urls.call_count >= 1
        assert bundle_locator2.get_next_urls.call_count >= 1

        # Verify loader was called for each bundle_locator's URLs
        assert loader.load.call_count == 2
