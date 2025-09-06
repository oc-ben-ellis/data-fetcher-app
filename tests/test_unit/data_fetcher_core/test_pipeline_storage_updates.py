#!/usr/bin/env python3
"""Unit tests for PipelineStorage updates with SQS notifications and BundleStorageContext."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, Mock, patch

import pytest

from data_fetcher_core.core import BundleRef, FetcherRecipe
from data_fetcher_core.notifications.sqs_publisher import SqsPublisher
from data_fetcher_core.storage.bundle_storage_context import BundleStorageContext
from data_fetcher_core.storage.pipeline_storage import PipelineStorage


class TestPipelineStorageUpdates:
    """Test PipelineStorage updates for new functionality."""

    @pytest.fixture
    def mock_sqs_publisher(self) -> Mock:
        """Create a mock SQS publisher."""
        publisher = Mock(spec=SqsPublisher)
        publisher.publish_bundle_completion = AsyncMock()
        return publisher

    @pytest.fixture
    def pipeline_storage(self, mock_sqs_publisher: Mock) -> PipelineStorage:
        """Create a PipelineStorage instance for testing."""
        return PipelineStorage(
            bucket_name="test-bucket",
            sqs_publisher=mock_sqs_publisher,
            prefix="test-prefix/",
            region="eu-west-2",
        )

    @pytest.fixture
    def bundle_ref(self) -> BundleRef:
        """Create a test bundle reference."""
        return BundleRef(
            primary_url="https://example.com/test",
            resources_count=1,
            storage_key="test_bundle_key",
            meta={"test": "data"},
        )

    @pytest.fixture
    def recipe(self) -> FetcherRecipe:
        """Create a test recipe."""
        return FetcherRecipe(
            recipe_id="test_recipe", bundle_locators=[], bundle_loader=None
        )

    @pytest.fixture
    def fetch_run_context(self) -> Mock:
        """Create a mock fetch run context."""
        context = Mock(spec=FetcherRecipe)
        context.run_id = "test_run_123"
        context.app_config = Mock()
        context.app_config.kv_store = Mock()
        context.app_config.kv_store.scan = AsyncMock(return_value=[])
        return context

    def test_pipeline_storage_creation_with_sqs_publisher(
        self, mock_sqs_publisher: Mock
    ) -> None:
        """Test PipelineStorage creation with SQS publisher."""
        storage = PipelineStorage(
            bucket_name="test-bucket",
            sqs_publisher=mock_sqs_publisher,
            prefix="test-prefix/",
            region="eu-west-2",
        )

        assert storage.bucket_name == "test-bucket"
        assert storage.sqs_publisher == mock_sqs_publisher
        assert storage.prefix == "test-prefix/"
        assert storage.region == "eu-west-2"
        assert storage._active_bundles == {}

    def test_pipeline_storage_creation_without_sqs_publisher_fails(self) -> None:
        """Test that PipelineStorage creation fails without SQS publisher."""
        with pytest.raises(
            ValueError,
            match="SQS publisher is required for PipelineStorage but was None",
        ):
            PipelineStorage(
                bucket_name="test-bucket",
                sqs_publisher=None,  # type: ignore[arg-type]
                prefix="test-prefix/",
            )

    def test_pipeline_storage_creation_with_empty_sqs_publisher_fails(self) -> None:
        """Test that PipelineStorage creation fails with empty SQS publisher."""
        with pytest.raises(
            ValueError,
            match="SQS publisher is required for PipelineStorage but was None",
        ):
            PipelineStorage(
                bucket_name="test-bucket",
                sqs_publisher="",  # type: ignore[arg-type]
                prefix="test-prefix/",
            )

    @pytest.mark.asyncio
    async def test_start_bundle_creates_bundle_storage_context(
        self,
        pipeline_storage: PipelineStorage,
        bundle_ref: BundleRef,
        recipe: FetcherRecipe,
    ) -> None:
        """Test that start_bundle creates a BundleStorageContext."""
        # Mock the S3StorageBundle creation
        with patch(
            "data_fetcher_core.storage.pipeline_storage.S3StorageBundle"
        ) as mock_s3_bundle:
            mock_bundle_instance = Mock()
            mock_s3_bundle.return_value = mock_bundle_instance

            # Call start_bundle
            context = await pipeline_storage.start_bundle(bundle_ref, recipe)

            # Verify BundleStorageContext was created
            assert isinstance(context, BundleStorageContext)
            assert context.bundle_ref == bundle_ref
            assert context.recipe == recipe
            assert context.storage == pipeline_storage

            # Verify S3StorageBundle was created
            mock_s3_bundle.assert_called_once_with(
                pipeline_storage.s3_client,
                pipeline_storage.bucket_name,
                pipeline_storage.prefix,
                bundle_ref,
            )

            # Verify bundle was stored in active bundles
            assert str(bundle_ref.bid) in pipeline_storage._active_bundles
            assert (
                pipeline_storage._active_bundles[str(bundle_ref.bid)]
                == mock_bundle_instance
            )

    @pytest.mark.asyncio
    async def test_add_resource_to_bundle_delegates_to_s3_bundle(
        self, pipeline_storage: PipelineStorage, bundle_ref: BundleRef
    ) -> None:
        """Test that _add_resource_to_bundle delegates to S3StorageBundle."""
        # Create a mock S3StorageBundle
        mock_s3_bundle = Mock()
        mock_s3_bundle.write_resource = AsyncMock()
        pipeline_storage._active_bundles[str(bundle_ref.bid)] = mock_s3_bundle

        # Create test data
        url = "https://example.com/resource"
        content_type = "text/html"
        status_code = 200

        async def mock_stream() -> AsyncGenerator[bytes]:
            yield b"<html>Test content</html>"

        stream = mock_stream()

        # Call _add_resource_to_bundle
        await pipeline_storage._add_resource_to_bundle(
            bundle_ref, url, content_type, status_code, stream
        )

        # Verify S3StorageBundle.write_resource was called
        mock_s3_bundle.write_resource.assert_called_once_with(
            url, content_type, status_code, stream
        )

    @pytest.mark.asyncio
    async def test_add_resource_to_bundle_with_missing_bundle_raises_error(
        self, pipeline_storage: PipelineStorage, bundle_ref: BundleRef
    ) -> None:
        """Test that _add_resource_to_bundle raises error for missing bundle."""
        # Don't add the bundle to active_bundles

        url = "https://example.com/resource"
        content_type = "text/html"
        status_code = 200

        async def mock_stream() -> AsyncGenerator[bytes]:
            yield b"<html>Test content</html>"

        stream = mock_stream()

        # Call _add_resource_to_bundle and expect it to raise an error
        with pytest.raises(ValueError, match="Bundle not found"):
            await pipeline_storage._add_resource_to_bundle(
                bundle_ref, url, content_type, status_code, stream
            )

    @pytest.mark.asyncio
    async def testcomplete_bundle_with_callbacks_hook_executes_callbacks_and_sends_sqs(
        self,
        pipeline_storage: PipelineStorage,
        bundle_ref: BundleRef,
        recipe: FetcherRecipe,
    ) -> None:
        """Test that complete_bundle_with_callbacks_hook executes callbacks and sends SQS notification."""
        # Create a mock S3StorageBundle
        mock_s3_bundle = Mock()
        mock_s3_bundle.finalize = AsyncMock()
        mock_s3_bundle.close = AsyncMock()
        pipeline_storage._active_bundles[str(bundle_ref.bid)] = mock_s3_bundle

        # Mock the callback execution
        with patch.object(
            pipeline_storage, "_execute_completion_callbacks", new_callable=AsyncMock
        ) as mock_callbacks:
            metadata = {"source": "test", "run_id": "test_run_123"}

            # Call complete_bundle_with_callbacks_hook
            await pipeline_storage.complete_bundle_with_callbacks_hook(
                bundle_ref, recipe, metadata
            )

            # Verify S3StorageBundle.close was called
            mock_s3_bundle.close.assert_called_once()

            # Verify completion callbacks were executed
            mock_callbacks.assert_called_once_with(bundle_ref, recipe)

            # Verify SQS notification was sent
            pipeline_storage.sqs_publisher.publish_bundle_completion.assert_called_once_with(  # type: ignore[attr-defined]
                bundle_ref, metadata, recipe.recipe_id
            )

            # Verify bundle was removed from active bundles
            assert str(bundle_ref.bid) not in pipeline_storage._active_bundles

    @pytest.mark.asyncio
    async def testcomplete_bundle_with_callbacks_hook_handles_sqs_error(
        self,
        pipeline_storage: PipelineStorage,
        bundle_ref: BundleRef,
        recipe: FetcherRecipe,
    ) -> None:
        """Test that complete_bundle_with_callbacks_hook handles SQS errors gracefully."""
        # Create a mock S3StorageBundle
        mock_s3_bundle = Mock()
        mock_s3_bundle.finalize = AsyncMock()
        mock_s3_bundle.close = AsyncMock()
        pipeline_storage._active_bundles[str(bundle_ref.bid)] = mock_s3_bundle

        # Mock the callback execution
        with patch.object(
            pipeline_storage, "_execute_completion_callbacks", new_callable=AsyncMock
        ):
            # Make SQS publisher raise an exception
            pipeline_storage.sqs_publisher.publish_bundle_completion.side_effect = (  # type: ignore[attr-defined]
                Exception("SQS error")
            )

            metadata = {"source": "test"}

            # Call complete_bundle_with_callbacks_hook and expect it to raise the SQS error
            with pytest.raises(Exception, match="SQS error"):
                await pipeline_storage.complete_bundle_with_callbacks_hook(
                    bundle_ref, recipe, metadata
                )

            # Verify S3StorageBundle.close was still called
            mock_s3_bundle.close.assert_called_once()

            # Verify bundle was still removed from active bundles
            assert str(bundle_ref.bid) not in pipeline_storage._active_bundles

    @pytest.mark.asyncio
    async def test_execute_completion_callbacks_calls_loader_and_locator_callbacks(
        self,
        pipeline_storage: PipelineStorage,
        bundle_ref: BundleRef,
        recipe: FetcherRecipe,
    ) -> None:
        """Test that _execute_completion_callbacks calls loader and locator callbacks."""
        # Create mock loader and locators with completion callbacks
        mock_loader = Mock()
        mock_loader.on_bundle_complete_hook = AsyncMock()
        recipe.bundle_loader = mock_loader

        mock_locator1 = Mock()
        mock_locator1.on_bundle_complete_hook = AsyncMock()
        mock_locator2 = Mock()
        mock_locator2.on_bundle_complete_hook = AsyncMock()
        recipe.bundle_locators = [mock_locator1, mock_locator2]

        # Call _execute_completion_callbacks
        await pipeline_storage._execute_completion_callbacks(bundle_ref, recipe)

        # Verify loader callback was called
        mock_loader.on_bundle_complete_hook.assert_called_once_with(bundle_ref)

        # Verify locator callbacks were called
        mock_locator1.on_bundle_complete_hook.assert_called_once_with(bundle_ref)
        mock_locator2.on_bundle_complete_hook.assert_called_once_with(bundle_ref)

    @pytest.mark.asyncio
    async def test_execute_completion_callbacks_handles_missing_callbacks(
        self,
        pipeline_storage: PipelineStorage,
        bundle_ref: BundleRef,
        recipe: FetcherRecipe,
    ) -> None:
        """Test that _execute_completion_callbacks handles missing callbacks gracefully."""
        # Create mock loader and locators without completion callbacks
        mock_loader = Mock()
        del mock_loader.on_bundle_complete_hook  # Remove the callback method
        recipe.bundle_loader = mock_loader

        mock_locator1 = Mock()
        del mock_locator1.on_bundle_complete_hook  # Remove the callback method
        mock_locator2 = Mock()
        mock_locator2.on_bundle_complete_hook = AsyncMock()  # Keep this one
        recipe.bundle_locators = [mock_locator1, mock_locator2]

        # Call _execute_completion_callbacks (should not raise an error)
        await pipeline_storage._execute_completion_callbacks(bundle_ref, recipe)

        # Verify only the locator with callback was called
        mock_locator2.on_bundle_complete_hook.assert_called_once_with(bundle_ref)

    @pytest.mark.asyncio
    async def test_execute_completion_callbacks_handles_callback_errors(
        self,
        pipeline_storage: PipelineStorage,
        bundle_ref: BundleRef,
        recipe: FetcherRecipe,
    ) -> None:
        """Test that _execute_completion_callbacks handles callback errors gracefully."""
        # Create mock loader and locators with failing callbacks
        mock_loader = Mock()
        mock_loader.on_bundle_complete_hook = AsyncMock(
            side_effect=Exception("Loader callback error")
        )
        recipe.bundle_loader = mock_loader

        mock_locator1 = Mock()
        mock_locator1.on_bundle_complete_hook = AsyncMock(
            side_effect=Exception("Locator callback error")
        )
        mock_locator2 = Mock()
        mock_locator2.on_bundle_complete_hook = AsyncMock()  # This one succeeds
        recipe.bundle_locators = [mock_locator1, mock_locator2]

        # Call _execute_completion_callbacks (should not raise an error)
        await pipeline_storage._execute_completion_callbacks(bundle_ref, recipe)

        # Verify all callbacks were attempted
        mock_loader.on_bundle_complete_hook.assert_called_once_with(bundle_ref)
        mock_locator1.on_bundle_complete_hook.assert_called_once_with(bundle_ref)
        mock_locator2.on_bundle_complete_hook.assert_called_once_with(bundle_ref)

    @pytest.mark.asyncio
    async def test_on_run_start_processes_pending_completions(
        self,
        pipeline_storage: PipelineStorage,
        fetch_run_context: Mock,
        recipe: FetcherRecipe,
    ) -> None:
        """Test that on_run_start processes pending completions."""
        # Mock the pending completion processing
        with patch.object(
            pipeline_storage, "_process_pending_completions", new_callable=AsyncMock
        ) as mock_process:
            # Call on_run_start
            await pipeline_storage.on_run_start(fetch_run_context, recipe)

            # Verify _process_pending_completions was called
            mock_process.assert_called_once_with(fetch_run_context, recipe)

    @pytest.mark.asyncio
    async def test_process_pending_completions_with_no_pending_completions(
        self,
        pipeline_storage: PipelineStorage,
        fetch_run_context: Mock,
        recipe: FetcherRecipe,
    ) -> None:
        """Test _process_pending_completions with no pending completions."""
        # Mock KV store to return no pending completions
        fetch_run_context.app_config.kv_store.scan.return_value = []

        # Call _process_pending_completions
        await pipeline_storage._process_pending_completions(fetch_run_context, recipe)

        # Verify KV store scan was called
        fetch_run_context.app_config.kv_store.scan.assert_called_once_with(
            f"sqs_notifications:pending:{recipe.recipe_id}:*"
        )

        # Verify no other operations were performed
        pipeline_storage.sqs_publisher.publish_bundle_completion.assert_not_called()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_process_pending_completions_with_pending_completions(
        self,
        pipeline_storage: PipelineStorage,
        fetch_run_context: Mock,
        recipe: FetcherRecipe,
    ) -> None:
        """Test _process_pending_completions with pending completions."""
        # Create a test bundle reference
        bundle_ref = BundleRef(
            primary_url="https://example.com/pending",
            resources_count=1,
            storage_key="pending_bundle",
        )

        # Mock pending completion data
        pending_data = {
            "bundle_ref": {
                "primary_url": str(bundle_ref.primary_url),
                "resources_count": bundle_ref.resources_count,
                "bid": str(bundle_ref.bid),
                "storage_key": bundle_ref.storage_key,
                "meta": bundle_ref.meta,
            },
            "metadata": {"source": "pending_test"},
            "timestamp": "2024-01-15T10:30:00Z",
        }

        # Mock KV store to return pending completions
        pending_key = f"sqs_notifications:pending:{recipe.recipe_id}:{bundle_ref.bid}"
        fetch_run_context.app_config.kv_store.scan.return_value = [pending_key]
        fetch_run_context.app_config.kv_store.get = AsyncMock(return_value=pending_data)
        fetch_run_context.app_config.kv_store.delete = AsyncMock()

        # Mock the callback execution
        with patch.object(
            pipeline_storage, "_execute_completion_callbacks", new_callable=AsyncMock
        ):
            # Call _process_pending_completions
            await pipeline_storage._process_pending_completions(
                fetch_run_context, recipe
            )

            # Verify KV store operations
            fetch_run_context.app_config.kv_store.get.assert_called_once_with(
                pending_key
            )
            fetch_run_context.app_config.kv_store.delete.assert_called_once_with(
                pending_key
            )

            # Verify completion callbacks were executed
            pipeline_storage._execute_completion_callbacks.assert_called_once()  # type: ignore[attr-defined]

            # Verify SQS notification was re-sent
            pipeline_storage.sqs_publisher.publish_bundle_completion.assert_called_once_with(  # type: ignore[attr-defined]
                bundle_ref, pending_data["metadata"], recipe.recipe_id
            )

    @pytest.mark.asyncio
    async def test_process_pending_completions_handles_errors_gracefully(
        self,
        pipeline_storage: PipelineStorage,
        fetch_run_context: Mock,
        recipe: FetcherRecipe,
    ) -> None:
        """Test that _process_pending_completions handles errors gracefully."""
        # Mock KV store to raise an error
        fetch_run_context.app_config.kv_store.scan.side_effect = Exception(
            "KV store error"
        )

        # Call _process_pending_completions (should raise the KV store error)
        with pytest.raises(Exception, match="KV store error"):
            await pipeline_storage._process_pending_completions(
                fetch_run_context, recipe
            )

        # Verify no other operations were attempted
        pipeline_storage.sqs_publisher.publish_bundle_completion.assert_not_called()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_process_pending_completions_handles_malformed_data(
        self,
        pipeline_storage: PipelineStorage,
        fetch_run_context: Mock,
        recipe: FetcherRecipe,
    ) -> None:
        """Test that _process_pending_completions handles malformed data gracefully."""
        # Mock KV store to return malformed data
        pending_key = f"sqs_notifications:pending:{recipe.recipe_id}:test-bundle-id"
        fetch_run_context.app_config.kv_store.scan.return_value = [pending_key]
        fetch_run_context.app_config.kv_store.get = AsyncMock(
            return_value={"invalid": "data"}
        )
        fetch_run_context.app_config.kv_store.delete = AsyncMock()

        # Call _process_pending_completions (should not raise an error)
        await pipeline_storage._process_pending_completions(fetch_run_context, recipe)

        # Verify the malformed key was NOT deleted (error occurred)
        fetch_run_context.app_config.kv_store.delete.assert_not_called()

        # Verify no other operations were attempted
        pipeline_storage.sqs_publisher.publish_bundle_completion.assert_not_called()  # type: ignore[attr-defined]

    def test_pipeline_storage_initialization_with_environment_variables(self) -> None:
        """Test PipelineStorage initialization with environment variables."""
        with patch.dict("os.environ", {"AWS_REGION": "us-east-1"}):
            mock_sqs_publisher = Mock(spec=SqsPublisher)

            storage = PipelineStorage(
                bucket_name="test-bucket", sqs_publisher=mock_sqs_publisher
            )

            # Verify region was taken from environment variable
            assert storage.region == "us-east-1"

    def test_pipeline_storage_initialization_with_default_region(self) -> None:
        """Test PipelineStorage initialization with default region."""
        with patch.dict("os.environ", {}, clear=True):
            mock_sqs_publisher = Mock(spec=SqsPublisher)

            storage = PipelineStorage(
                bucket_name="test-bucket", sqs_publisher=mock_sqs_publisher
            )

            # Verify default region was used
            assert storage.region == "eu-west-2"
