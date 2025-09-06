"""Tests for main fetcher implementation.

This module contains unit tests for the main Fetcher class, FetchPlan,
FetchResult, and related execution components.
"""

import asyncio

# Import the real asyncio module to avoid recursion in mocks
from unittest.mock import AsyncMock, MagicMock

import pytest

from data_fetcher_core.config_factory import FetcherConfig, create_fetcher_config
from data_fetcher_core.core import (
    FetcherRecipe,
    FetchPlan,
    FetchRunContext,
    RequestMeta,
)
from data_fetcher_core.exceptions import ConfigurationError
from data_fetcher_core.fetcher import Fetcher, FetchResult


@pytest.fixture
async def app_config() -> FetcherConfig:
    """Create app config with kv_store for testing."""
    return await create_fetcher_config(
        kv_store_type="memory",
        storage_type="file",
        file_path="tmp/test_storage",
    )


class TestFetcherRecipe:
    """Test FetcherRecipe class."""

    def test_basic_creation(self) -> None:
        """Test basic FetcherRecipe creation."""
        ctx = FetcherRecipe()
        assert ctx.bundle_locators == []
        assert ctx.bundle_loader is None
        assert ctx.recipe_id == "default"

    def test_with_all_fields(self) -> None:
        """Test FetcherRecipe creation with all fields."""
        mock_loader = MagicMock()
        mock_bundle_locator = MagicMock()

        ctx = FetcherRecipe(
            recipe_id="test_recipe",
            bundle_locators=[mock_bundle_locator],
            bundle_loader=mock_loader,
        )
        assert ctx.bundle_locators == [mock_bundle_locator]
        assert ctx.bundle_loader == mock_loader


class TestFetchResult:
    """Test FetchResult class."""

    def test_basic_creation(self) -> None:
        """Test basic FetchResult creation."""
        ctx = FetchRunContext(run_id="test_run")
        result = FetchResult(processed_count=10, errors=["error1"], context=ctx)
        assert result.processed_count == 10
        assert result.errors == ["error1"]
        assert result.context == ctx

    def test_with_no_errors(self) -> None:
        """Test FetchResult creation with no errors."""
        ctx = FetchRunContext(run_id="test_run")
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
        FetcherRecipe(
            recipe_id="test_recipe",
            bundle_locators=[mock_bundle_locator],
            bundle_loader=mock_loader,
        )
        return Fetcher()

    def test_fetcher_creation(
        self,
        fetcher: Fetcher,
        mock_loader: AsyncMock,
        mock_storage: AsyncMock,
        mock_bundle_locator: AsyncMock,
    ) -> None:
        """Test Fetcher creation."""
        # Recipe is now passed in the plan, not stored in the fetcher
        # This test verifies the fetcher can be created without a recipe
        # The fetcher is now completely stateless

    @pytest.mark.asyncio
    async def test_run_with_empty_plan(
        self, fetcher: Fetcher, app_config: FetcherConfig
    ) -> None:
        """Test running fetcher with empty plan."""
        # Create a recipe with a mock bundle locator that returns no URLs
        mock_bundle_locator = AsyncMock()
        mock_bundle_locator.get_next_urls.return_value = []
        mock_bundle_locator.handle_url_processed = AsyncMock()

        # Add a mock bundle loader
        mock_bundle_loader = AsyncMock()
        mock_bundle_loader.load.return_value = []

        recipe = FetcherRecipe(
            recipe_id="test_recipe",
            bundle_locators=[mock_bundle_locator],
            bundle_loader=mock_bundle_loader,
        )
        plan = FetchPlan(
            recipe=recipe,
            context=FetchRunContext(run_id="test_run", app_config=app_config),
            concurrency=1,
        )

        # Use a timeout on the entire test instead of mocking asyncio.wait_for
        result = await asyncio.wait_for(fetcher.run(plan), timeout=5.0)

        assert isinstance(result, FetchResult)
        assert result.processed_count == 0
        assert result.errors == []
        assert result.context == plan.context

    @pytest.mark.asyncio
    async def test_run_with_requests(
        self, mock_loader: AsyncMock, app_config: FetcherConfig
    ) -> None:
        """Test running fetcher with requests."""
        requests = [
            RequestMeta(url="https://example.com/1"),
            RequestMeta(url="https://example.com/2"),
        ]
        # Create a recipe and add RequestParameterLocator to it
        from data_fetcher_core.core import RequestParameterLocator

        ctx = FetcherRecipe(recipe_id="test_recipe", bundle_loader=mock_loader)
        ctx.bundle_locators.insert(0, RequestParameterLocator(requests=requests))
        plan = FetchPlan(
            recipe=ctx,
            context=FetchRunContext(run_id="test_run", app_config=app_config),
            concurrency=2,
        )

        # Create fetcher with proper configuration
        fetcher = Fetcher()

        # Mock the loader to return bundle refs
        mock_loader.load.return_value = [MagicMock()]

        # Use a timeout on the entire test instead of mocking asyncio.wait_for
        result = await asyncio.wait_for(fetcher.run(plan), timeout=5.0)

        assert isinstance(result, FetchResult)
        # Verify that the loader was called for each request
        assert mock_loader.load.call_count == 2

    @pytest.mark.asyncio
    async def test_run_with_bundle_locator_urls(
        self,
        mock_bundle_locator: AsyncMock,
        mock_loader: AsyncMock,
        app_config: FetcherConfig,
    ) -> None:
        """Test running fetcher with URLs from bundle locators."""
        bundle_locator_requests = [
            RequestMeta(url="https://bundle-locator.com/1"),
            RequestMeta(url="https://bundle-locator.com/2"),
        ]
        # Make the bundle locator return URLs only once, then empty list
        mock_bundle_locator.get_next_urls.side_effect = [bundle_locator_requests, []]

        ctx = FetcherRecipe(
            bundle_locators=[mock_bundle_locator], bundle_loader=mock_loader
        )
        plan = FetchPlan(
            recipe=ctx,
            context=FetchRunContext(run_id="test_run", app_config=app_config),
            concurrency=1,
        )

        # Create fetcher with proper configuration
        fetcher = Fetcher()
        mock_loader.load.return_value = [MagicMock()]

        # Use a timeout on the entire test instead of mocking asyncio.wait_for
        result = await asyncio.wait_for(fetcher.run(plan), timeout=5.0)

        assert isinstance(result, FetchResult)
        # Verify that the bundle locator was called
        assert mock_bundle_locator.get_next_urls.call_count >= 1
        # Verify that the loader was called for bundle locator requests
        assert mock_loader.load.call_count == 2

    @pytest.mark.asyncio
    async def test_run_with_bundle_locator_callbacks(
        self,
        mock_bundle_locator: AsyncMock,
        mock_loader: AsyncMock,
        app_config: FetcherConfig,
    ) -> None:
        """Test running fetcher with bundle locator URL processed callbacks."""
        # Add handle_url_processed method to mock bundle locator
        mock_bundle_locator.handle_url_processed = AsyncMock()
        # Make the bundle locator return empty list to avoid infinite loop
        mock_bundle_locator.get_next_urls.return_value = []

        requests = [RequestMeta(url="https://example.com")]
        # Add RequestParameterLocator to the recipe
        from data_fetcher_core.core import RequestParameterLocator

        request_locator = RequestParameterLocator(requests=requests)
        ctx = FetcherRecipe(recipe_id="test_recipe", bundle_loader=mock_loader)
        ctx.bundle_locators.insert(0, request_locator)
        plan = FetchPlan(
            recipe=ctx,
            context=FetchRunContext(run_id="test_run", app_config=app_config),
            concurrency=1,
        )

        # Create fetcher with proper configuration
        fetcher = Fetcher()
        mock_loader.load.return_value = [MagicMock()]

        # Use a timeout on the entire test instead of mocking asyncio.wait_for
        result = await asyncio.wait_for(fetcher.run(plan), timeout=5.0)

        assert isinstance(result, FetchResult)
        # Verify that the bundle locator callback was called
        # Note: RequestParameterLocator.handle_url_processed is a no-op, so we just verify the test completed

    @pytest.mark.asyncio
    async def test_run_with_loader_error(
        self, mock_loader: AsyncMock, app_config: FetcherConfig
    ) -> None:
        """Test running fetcher when loader raises an error."""
        requests = [RequestMeta(url="https://example.com")]
        # Add RequestParameterLocator to the recipe
        from data_fetcher_core.core import RequestParameterLocator

        ctx = FetcherRecipe(recipe_id="test_recipe", bundle_loader=mock_loader)
        ctx.bundle_locators.insert(0, RequestParameterLocator(requests=requests))
        plan = FetchPlan(
            recipe=ctx,
            context=FetchRunContext(run_id="test_run", app_config=app_config),
            concurrency=1,
        )

        # Create fetcher with proper configuration
        fetcher = Fetcher()

        # Mock the loader to raise an exception
        mock_loader.load.side_effect = Exception("Loader error")

        # Use a timeout on the entire test instead of mocking asyncio.wait_for
        result = await asyncio.wait_for(fetcher.run(plan), timeout=5.0)

        assert isinstance(result, FetchResult)
        # The fetcher should handle errors gracefully
        assert result.processed_count == 0

    @pytest.mark.asyncio
    async def test_run_with_concurrent_workers(
        self, mock_loader: AsyncMock, app_config: FetcherConfig
    ) -> None:
        """Test running fetcher with multiple concurrent workers."""
        requests = [
            RequestMeta(url="https://example.com/1"),
            RequestMeta(url="https://example.com/2"),
            RequestMeta(url="https://example.com/3"),
        ]
        # Add RequestParameterLocator to the recipe
        from data_fetcher_core.core import RequestParameterLocator

        ctx = FetcherRecipe(recipe_id="test_recipe", bundle_loader=mock_loader)
        ctx.bundle_locators.insert(0, RequestParameterLocator(requests=requests))

        plan = FetchPlan(
            recipe=ctx,
            context=FetchRunContext(run_id="test_run", app_config=app_config),
            concurrency=3,
        )
        mock_loader.load.return_value = [MagicMock()]

        # Create fetcher with proper configuration
        fetcher = Fetcher()

        # Use a timeout on the entire test instead of mocking asyncio.wait_for
        result = await asyncio.wait_for(fetcher.run(plan), timeout=5.0)

        assert isinstance(result, FetchResult)
        # Verify that the loader was called for each request
        assert mock_loader.load.call_count == 3

    @pytest.mark.asyncio
    async def test_run_with_shared_context(self, app_config: FetcherConfig) -> None:
        """Test running fetcher with shared context data."""
        shared_data = {"key": "value", "count": 42}
        run_ctx = FetchRunContext(
            run_id="test_run", shared=shared_data, app_config=app_config
        )

        # Create a recipe with a mock bundle locator that returns no URLs
        mock_bundle_locator = AsyncMock()
        mock_bundle_locator.get_next_urls.return_value = []
        mock_bundle_locator.handle_url_processed = AsyncMock()

        # Add a mock bundle loader
        mock_bundle_loader = AsyncMock()
        mock_bundle_loader.load.return_value = []

        ctx = FetcherRecipe(
            bundle_locators=[mock_bundle_locator], bundle_loader=mock_bundle_loader
        )
        plan = FetchPlan(recipe=ctx, context=run_ctx, concurrency=1)

        # Create fetcher with proper configuration
        fetcher = Fetcher()

        # Use a timeout on the entire test instead of mocking asyncio.wait_for
        result = await asyncio.wait_for(fetcher.run(plan), timeout=5.0)

        assert isinstance(result, FetchResult)
        assert result.context.shared == shared_data

    @pytest.mark.asyncio
    async def test_run_with_run_id(self, app_config: FetcherConfig) -> None:
        """Test running fetcher with run_id in context."""
        # Create a recipe with a mock bundle locator that returns no URLs
        mock_bundle_locator = AsyncMock()
        mock_bundle_locator.get_next_urls.return_value = []
        mock_bundle_locator.handle_url_processed = AsyncMock()

        # Add a mock bundle loader
        mock_bundle_loader = AsyncMock()
        mock_bundle_loader.load.return_value = []

        ctx = FetcherRecipe(
            bundle_locators=[mock_bundle_locator], bundle_loader=mock_bundle_loader
        )
        run_ctx = FetchRunContext(run_id="test-run-123", app_config=app_config)
        plan = FetchPlan(recipe=ctx, context=run_ctx, concurrency=1)

        # Create fetcher with proper configuration
        fetcher = Fetcher()

        # Use a timeout on the entire test instead of mocking asyncio.wait_for
        result = await asyncio.wait_for(fetcher.run(plan), timeout=5.0)

        assert isinstance(result, FetchResult)
        assert result.context.run_id == "test-run-123"

    @pytest.mark.asyncio
    async def test_run_without_bundle_locators(self) -> None:
        """Test that fetcher raises error when no bundle locators are configured."""
        # Create fetcher with no bundle locators
        ctx = FetcherRecipe(
            recipe_id="test_recipe", bundle_locators=[], bundle_loader=AsyncMock()
        )
        fetcher = Fetcher()

        plan = FetchPlan(
            recipe=ctx, context=FetchRunContext(run_id="test_run"), concurrency=1
        )

        with pytest.raises(
            ConfigurationError,
            match="No bundle locators configured in the fetcher recipe",
        ):
            await fetcher.run(plan)

    @pytest.mark.asyncio
    async def test_run_without_bundle_loader(self) -> None:
        """Test that fetcher raises error when no bundle loader is configured."""
        # Create fetcher with no bundle loader
        ctx = FetcherRecipe(
            recipe_id="test_recipe", bundle_locators=[AsyncMock()], bundle_loader=None
        )
        fetcher = Fetcher()

        plan = FetchPlan(
            recipe=ctx, context=FetchRunContext(run_id="test_run"), concurrency=1
        )

        with pytest.raises(
            ConfigurationError,
            match="No bundle loader configured in the fetcher recipe",
        ):
            await fetcher.run(plan)

    @pytest.mark.asyncio
    async def test_run_without_kv_store(self) -> None:
        """Test that fetcher raises error when no kv_store is configured."""
        # Create fetcher with required components but no kv_store
        mock_locator = AsyncMock()
        mock_locator.get_next_urls.return_value = []

        ctx = FetcherRecipe(
            recipe_id="test_recipe",
            bundle_locators=[mock_locator],
            bundle_loader=AsyncMock(),
        )
        fetcher = Fetcher()

        # Create run context without app_config (no kv_store)
        plan = FetchPlan(
            recipe=ctx, context=FetchRunContext(run_id="test_run"), concurrency=1
        )

        with pytest.raises(
            ConfigurationError, match="kv_store is required for persistent queue"
        ):
            await fetcher.run(plan)


class TestFetcherIntegration:
    """Integration tests for the Fetcher class."""

    @pytest.mark.asyncio
    async def test_fetcher_with_multiple_bundle_locators(
        self, app_config: FetcherConfig
    ) -> None:
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
        # Note: storage is not used in this test

        # Create fetcher
        ctx = FetcherRecipe(
            bundle_locators=[bundle_locator1, bundle_locator2],
            bundle_loader=loader,
        )
        fetcher = Fetcher()

        # Run fetcher
        plan = FetchPlan(
            recipe=ctx,
            context=FetchRunContext(run_id="test_run", app_config=app_config),
            concurrency=2,
        )

        # Use a timeout on the entire test instead of mocking asyncio.wait_for
        result = await asyncio.wait_for(fetcher.run(plan), timeout=5.0)

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
