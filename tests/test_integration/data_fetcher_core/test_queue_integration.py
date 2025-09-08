"""Integration tests for persistent queue with fetcher.

This module contains integration tests that verify the persistent queue
works correctly with the fetcher system.
"""

import asyncio
from unittest.mock import AsyncMock

import pytest
from yarl import URL

from data_fetcher_core.config_factory import FetcherConfig, create_fetcher_config
from data_fetcher_core.core import (
    FetcherRecipe,
    FetchPlan,
    FetchRunContext,
    RequestMeta,
)
from data_fetcher_core.exceptions import ConfigurationError
from data_fetcher_core.fetcher import Fetcher
from data_fetcher_core.queue import KVStoreQueue, RequestMetaSerializer


@pytest.mark.integration
class TestQueueFetcherIntegration:
    """Integration tests for queue with fetcher."""

    @pytest.fixture
    async def app_config(self) -> FetcherConfig:
        """Create app config with kv_store for testing."""
        return await create_fetcher_config(
            kv_store_type="memory",
            storage_type="file",
            file_path="tmp/test_storage",
        )

    @pytest.fixture
    def mock_bundle_locator(self) -> AsyncMock:
        """Create a mock bundle locator."""
        locator = AsyncMock()
        locator.get_next_urls.return_value = []
        locator.handle_url_processed = AsyncMock()
        return locator

    @pytest.fixture
    def mock_bundle_loader(self) -> AsyncMock:
        """Create a mock bundle loader."""
        loader = AsyncMock()
        loader.load.return_value = []
        return loader

    @pytest.mark.asyncio
    async def test_fetcher_requires_kv_store(self) -> None:
        """Test that fetcher requires kv_store in app_config."""
        # Create recipe with required components
        mock_locator = AsyncMock()
        mock_locator.get_next_urls.return_value = []

        recipe = FetcherRecipe(
            recipe_id="test_recipe",
            bundle_locators=[mock_locator],
            bundle_loader=AsyncMock(),
        )

        # Create run context without app_config (no kv_store)
        run_ctx = FetchRunContext(run_id="test_run")
        plan = FetchPlan(recipe=recipe, context=run_ctx, concurrency=1)

        fetcher = Fetcher()

        with pytest.raises(
            ConfigurationError, match="kv_store is required for persistent queue"
        ):
            await fetcher.run(plan)

    @pytest.mark.asyncio
    async def test_fetcher_with_persistent_queue(
        self,
        app_config: FetcherConfig,
        mock_bundle_locator: AsyncMock,
        mock_bundle_loader: AsyncMock,
    ) -> None:
        """Test fetcher with persistent queue."""
        # Create recipe
        recipe = FetcherRecipe(
            recipe_id="test_recipe",
            bundle_locators=[mock_bundle_locator],
            bundle_loader=mock_bundle_loader,
        )

        # Create run context with app_config (includes kv_store)
        run_ctx = FetchRunContext(run_id="test_run", app_config=app_config)
        plan = FetchPlan(recipe=recipe, context=run_ctx, concurrency=1)

        fetcher = Fetcher()

        # Run fetcher - should not raise kv_store error
        result = await asyncio.wait_for(fetcher.run(plan), timeout=5.0)

        assert result.processed_count == 0  # No URLs from locator
        assert result.errors == []
        assert result.context.run_id == "test_run"

    @pytest.mark.asyncio
    async def test_queue_persistence_across_operations(
        self, app_config: FetcherConfig
    ) -> None:
        """Test that queue persists items across operations."""
        # Create a queue directly
        queue = KVStoreQueue(
            kv_store=app_config.kv_store,
            namespace="test_persistence",
            serializer=RequestMetaSerializer(),
        )

        # Add items to queue
        requests = [
            RequestMeta(url=str(URL(f"https://example.com/{i}"))) for i in range(3)
        ]
        await queue.enqueue(requests)
        assert await queue.size() == 3

        # Create a new queue instance with same namespace
        queue2 = KVStoreQueue(
            kv_store=app_config.kv_store,
            namespace="test_persistence",
            serializer=RequestMetaSerializer(),
        )

        # Should see the same items
        assert await queue2.size() == 3

        # Dequeue from second instance
        dequeued = await queue2.dequeue()
        assert len(dequeued) == 1
        assert await queue2.size() == 2

        # First instance should also see the change
        assert await queue.size() == 2

    @pytest.mark.asyncio
    async def test_fetcher_with_requests_in_queue(
        self, app_config: FetcherConfig, mock_bundle_loader: AsyncMock
    ) -> None:
        """Test fetcher processing requests from persistent queue."""
        # Create a locator that returns URLs
        mock_locator = AsyncMock()
        mock_locator.get_next_urls.side_effect = [
            [RequestMeta(url=str(URL("https://example.com/1")))],
            [RequestMeta(url=str(URL("https://example.com/2")))],
            [],  # Then empty to stop
        ]
        mock_locator.handle_url_processed = AsyncMock()

        # Create recipe
        recipe = FetcherRecipe(
            recipe_id="test_recipe",
            bundle_locators=[mock_locator],
            bundle_loader=mock_bundle_loader,
        )

        # Create run context with app_config
        run_ctx = FetchRunContext(run_id="test_run", app_config=app_config)
        plan = FetchPlan(recipe=recipe, context=run_ctx, concurrency=1)

        fetcher = Fetcher()

        # Run fetcher
        result = await asyncio.wait_for(fetcher.run(plan), timeout=5.0)

        # Should have processed 2 requests
        assert result.processed_count == 2
        assert result.errors == []

        # Verify loader was called for each request
        assert mock_bundle_loader.load.call_count == 2

    @pytest.mark.asyncio
    async def test_queue_namespace_isolation(self, app_config: FetcherConfig) -> None:
        """Test that different run_ids use different queue namespaces."""
        # Create queues with different namespaces (different run_ids)
        queue1 = KVStoreQueue(
            kv_store=app_config.kv_store,
            namespace="fetch:run1",
            serializer=RequestMetaSerializer(),
        )
        queue2 = KVStoreQueue(
            kv_store=app_config.kv_store,
            namespace="fetch:run2",
            serializer=RequestMetaSerializer(),
        )

        # Add items to queue1
        request1 = RequestMeta(url=str(URL("https://run1.com")))
        await queue1.enqueue([request1])
        assert await queue1.size() == 1
        assert await queue2.size() == 0

        # Add items to queue2
        request2 = RequestMeta(url=str(URL("https://run2.com")))
        await queue2.enqueue([request2])
        assert await queue1.size() == 1
        assert await queue2.size() == 1

        # Verify items are in correct queues
        dequeued1 = await queue1.dequeue()
        dequeued2 = await queue2.dequeue()

        # Cast dequeued items to RequestMeta since dequeue returns list[object]
        request1_dequeued = dequeued1[0]
        request2_dequeued = dequeued2[0]

        # Type assertion for mypy
        assert isinstance(request1_dequeued, RequestMeta)
        assert isinstance(request2_dequeued, RequestMeta)

        assert str(request1_dequeued.url) == "https://run1.com"
        assert str(request2_dequeued.url) == "https://run2.com"

    @pytest.mark.asyncio
    async def test_fetcher_queue_cleanup(
        self,
        app_config: FetcherConfig,
        mock_bundle_locator: AsyncMock,
        mock_bundle_loader: AsyncMock,
    ) -> None:
        """Test that fetcher properly cleans up queue resources."""
        # Create recipe
        recipe = FetcherRecipe(
            recipe_id="test_recipe",
            bundle_locators=[mock_bundle_locator],
            bundle_loader=mock_bundle_loader,
        )

        # Create run context with app_config
        run_ctx = FetchRunContext(run_id="test_cleanup", app_config=app_config)
        plan = FetchPlan(recipe=recipe, context=run_ctx, concurrency=1)

        fetcher = Fetcher()

        # Run fetcher
        result = await asyncio.wait_for(fetcher.run(plan), timeout=5.0)

        # Fetcher should complete without errors
        assert result.processed_count == 0
        assert result.errors == []

        # Queue should be accessible after fetcher completes
        # (This tests that close() doesn't break the kv_store)
        queue = KVStoreQueue(
            kv_store=app_config.kv_store,
            namespace="fetch:test_cleanup",
            serializer=RequestMetaSerializer(),
        )

        # Should be able to use queue after fetcher cleanup
        request = RequestMeta(url=str(URL("https://test.com")))
        await queue.enqueue([request])
        assert await queue.size() == 1

    @pytest.mark.asyncio
    async def test_concurrent_fetcher_runs(self, app_config: FetcherConfig) -> None:
        """Test multiple concurrent fetcher runs with different namespaces."""

        async def run_fetcher(run_id: str) -> int:
            """Run a fetcher and return processed count."""
            mock_locator = AsyncMock()
            mock_locator.get_next_urls.return_value = []
            mock_locator.handle_url_processed = AsyncMock()

            mock_loader = AsyncMock()
            mock_loader.load.return_value = []

            recipe = FetcherRecipe(
                recipe_id=f"recipe_{run_id}",
                bundle_locators=[mock_locator],
                bundle_loader=mock_loader,
            )

            run_ctx = FetchRunContext(run_id=run_id, app_config=app_config)
            plan = FetchPlan(recipe=recipe, context=run_ctx, concurrency=1)

            fetcher = Fetcher()
            result = await fetcher.run(plan)
            return result.processed_count

        # Run multiple fetchers concurrently
        results = await asyncio.gather(
            run_fetcher("run1"),
            run_fetcher("run2"),
            run_fetcher("run3"),
        )

        # All should complete successfully
        assert all(count == 0 for count in results)  # No URLs from locators
