#!/usr/bin/env python3
"""Unit tests for BundleStorageContext."""

from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from data_fetcher_core.core import BundleRef, FetcherRecipe
from data_fetcher_core.storage.bundle_storage_context import BundleStorageContext


class TestBundleStorageContext:
    """Test BundleStorageContext implementation."""

    @pytest.fixture
    def bundle_ref(self) -> BundleRef:
        """Create a test bundle reference."""
        return BundleRef(
            primary_url="https://example.com/test",
            resources_count=2,
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
    def mock_storage(self) -> Mock:
        """Create a mock storage instance."""
        storage = Mock()
        storage._add_resource_to_bundle = AsyncMock()
        storage.complete_bundle_with_callbacks_hook = AsyncMock()
        return storage

    @pytest.fixture
    def bundle_context(
        self, bundle_ref: BundleRef, recipe: FetcherRecipe, mock_storage: Mock
    ) -> BundleStorageContext:
        """Create a BundleStorageContext instance for testing."""
        return BundleStorageContext(bundle_ref, recipe, mock_storage)

    def test_bundle_context_creation(
        self, bundle_ref: BundleRef, recipe: FetcherRecipe, mock_storage: Mock
    ) -> None:
        """Test BundleStorageContext creation."""
        context = BundleStorageContext(bundle_ref, recipe, mock_storage)

        assert context.bundle_ref == bundle_ref
        assert context.recipe == recipe
        assert context.storage == mock_storage
        assert context._pending_uploads == set()
        assert context._completed_uploads == set()

    @pytest.mark.asyncio
    async def test_add_resource_success(
        self, bundle_context: BundleStorageContext
    ) -> None:
        """Test successful resource addition."""
        url = "https://example.com/resource1"
        content_type = "text/html"
        status_code = 200

        # Create a mock stream
        async def mock_stream() -> AsyncGenerator[bytes]:
            yield b"<html>Test content</html>"

        stream = mock_stream()

        # Call add_resource
        await bundle_context.add_resource(url, content_type, status_code, stream)

        # Verify the resource was processed (moved from pending to completed)
        assert url not in bundle_context._pending_uploads
        # Check that some upload was completed (upload_id format: url_stream_id)
        completed_uploads = [
            upload
            for upload in bundle_context._completed_uploads
            if upload.startswith(url)
        ]
        assert len(completed_uploads) == 1

        # Verify storage method was called
        bundle_context.storage._add_resource_to_bundle.assert_called_once_with(  # type: ignore[attr-defined]
            bundle_context.bundle_ref, url, content_type, status_code, stream
        )

    @pytest.mark.asyncio
    async def test_add_resource_with_none_content_type(
        self, bundle_context: BundleStorageContext
    ) -> None:
        """Test resource addition with None content type."""
        url = "https://example.com/resource1"
        content_type = None
        status_code = 200

        # Create a mock stream
        async def mock_stream() -> AsyncGenerator[bytes]:
            yield b"binary data"

        stream = mock_stream()

        # Call add_resource
        await bundle_context.add_resource(url, content_type, status_code, stream)

        # Verify the resource was processed
        assert url not in bundle_context._pending_uploads
        assert len(bundle_context._completed_uploads) == 1

        # Verify storage method was called with None content type
        bundle_context.storage._add_resource_to_bundle.assert_called_once_with(  # type: ignore[attr-defined]
            bundle_context.bundle_ref, url, None, status_code, stream
        )

    @pytest.mark.asyncio
    async def test_add_multiple_resources(
        self, bundle_context: BundleStorageContext
    ) -> None:
        """Test adding multiple resources."""
        resources = [
            ("https://example.com/resource1", "text/html", 200),
            ("https://example.com/resource2", "application/json", 200),
            ("https://example.com/resource3", "image/png", 200),
        ]

        # Create mock streams
        async def mock_stream(content: bytes) -> AsyncGenerator[bytes]:
            yield content

        # Add all resources
        for url, content_type, status_code in resources:
            stream = mock_stream(f"content for {url}".encode())
            await bundle_context.add_resource(url, content_type, status_code, stream)

        # Verify all resources were processed (moved from pending to completed)
        assert len(bundle_context._pending_uploads) == 0
        assert len(bundle_context._completed_uploads) == 3

        # Verify storage method was called for each resource
        assert bundle_context.storage._add_resource_to_bundle.call_count == 3  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_add_resource_error_handling(
        self, bundle_context: BundleStorageContext
    ) -> None:
        """Test error handling during resource addition."""
        url = "https://example.com/resource1"
        content_type = "text/html"
        status_code = 200

        # Create a mock stream
        async def mock_stream() -> AsyncGenerator[bytes]:
            yield b"<html>Test content</html>"

        stream = mock_stream()

        # Make storage method raise an exception
        bundle_context.storage._add_resource_to_bundle.side_effect = Exception(  # type: ignore[attr-defined]
            "Storage error"
        )

        # Call add_resource and expect it to raise an exception
        with pytest.raises(Exception, match="Storage error"):
            await bundle_context.add_resource(url, content_type, status_code, stream)

        # Verify the resource was not added to pending uploads
        assert url not in bundle_context._pending_uploads

    @pytest.mark.asyncio
    async def test_complete_with_no_pending_uploads(
        self, bundle_context: BundleStorageContext
    ) -> None:
        """Test bundle completion with no pending uploads."""
        metadata = {"source": "test", "run_id": "test_run_123"}

        # Call complete
        await bundle_context.complete(metadata)

        # Verify completion callbacks were executed
        # Completion callbacks executed via storage method call

        # Verify storage method was called
        bundle_context.storage.complete_bundle_with_callbacks_hook.assert_called_once_with(  # type: ignore[attr-defined]
            bundle_context.bundle_ref, bundle_context.recipe, metadata
        )

    @pytest.mark.asyncio
    async def test_complete_with_pending_uploads(
        self, bundle_context: BundleStorageContext
    ) -> None:
        """Test bundle completion with pending uploads."""
        # Add some resources first
        url1 = "https://example.com/resource1"
        url2 = "https://example.com/resource2"

        async def mock_stream() -> AsyncGenerator[bytes]:
            yield b"content"

        await bundle_context.add_resource(url1, "text/html", 200, mock_stream())
        await bundle_context.add_resource(url2, "application/json", 200, mock_stream())

        # Verify resources were processed
        assert len(bundle_context._pending_uploads) == 0
        assert len(bundle_context._completed_uploads) == 2

        metadata = {"source": "test"}

        # Call complete
        await bundle_context.complete(metadata)

        # Verify completion callbacks were executed
        # Completion callbacks executed via storage method call

        # Verify storage method was called
        bundle_context.storage.complete_bundle_with_callbacks_hook.assert_called_once_with(  # type: ignore[attr-defined]
            bundle_context.bundle_ref, bundle_context.recipe, metadata
        )

    @pytest.mark.asyncio
    async def test_complete_with_empty_metadata(
        self, bundle_context: BundleStorageContext
    ) -> None:
        """Test bundle completion with empty metadata."""
        metadata: dict[str, Any] = {}

        # Call complete
        await bundle_context.complete(metadata)

        # Verify completion callbacks were executed
        # Completion callbacks executed via storage method call

        # Verify storage method was called with empty metadata
        bundle_context.storage.complete_bundle_with_callbacks_hook.assert_called_once_with(  # type: ignore[attr-defined]
            bundle_context.bundle_ref, bundle_context.recipe, {}
        )

    @pytest.mark.asyncio
    async def test_complete_error_handling(
        self, bundle_context: BundleStorageContext
    ) -> None:
        """Test error handling during bundle completion."""
        metadata = {"source": "test"}

        # Make storage method raise an exception
        bundle_context.storage.complete_bundle_with_callbacks_hook.side_effect = (  # type: ignore[attr-defined]
            Exception("Completion error")
        )

        # Call complete and expect it to raise an exception
        with pytest.raises(Exception, match="Completion error"):
            await bundle_context.complete(metadata)

        # Verify completion callbacks were not marked as executed
        # Completion callbacks not yet executed

    @pytest.mark.asyncio
    async def test_complete_idempotency(
        self, bundle_context: BundleStorageContext
    ) -> None:
        """Test that complete can be called multiple times safely."""
        metadata = {"source": "test"}

        # Call complete first time
        await bundle_context.complete(metadata)
        # Completion callbacks executed via storage method call

        # Call complete second time
        await bundle_context.complete(metadata)
        # Completion callbacks executed via storage method call

        # Verify storage method was called only once
        bundle_context.storage.complete_bundle_with_callbacks_hook.assert_called_once()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_complete_with_complex_metadata(
        self, bundle_context: BundleStorageContext
    ) -> None:
        """Test bundle completion with complex metadata."""
        metadata = {
            "source": "http_api",
            "run_id": "test_run_123",
            "nested": {"field1": "value1", "field2": 42},
            "list_field": ["a", "b", "c"],
            "number_field": 123.45,
            "boolean_field": True,
        }

        # Call complete
        await bundle_context.complete(metadata)

        # Verify completion callbacks were executed
        # Completion callbacks executed via storage method call

        # Verify storage method was called with complex metadata
        bundle_context.storage.complete_bundle_with_callbacks_hook.assert_called_once_with(  # type: ignore[attr-defined]
            bundle_context.bundle_ref, bundle_context.recipe, metadata
        )

    @pytest.mark.asyncio
    async def test_add_resource_after_complete(
        self, bundle_context: BundleStorageContext
    ) -> None:
        """Test adding resources after completion."""
        # Complete the bundle first
        await bundle_context.complete({"source": "test"})
        # Completion callbacks executed via storage method call

        # Try to add a resource after completion
        url = "https://example.com/late_resource"
        content_type = "text/html"
        status_code = 200

        async def mock_stream() -> AsyncGenerator[bytes]:
            yield b"late content"

        stream = mock_stream()

        # This should still work (no restriction in current implementation)
        await bundle_context.add_resource(url, content_type, status_code, stream)

        # Verify the resource was added (upload_id format: url_stream_id)
        # Since the upload completes immediately, it should be in completed_uploads
        assert len(bundle_context._completed_uploads) == 1

        # Verify storage method was called
        assert bundle_context.storage._add_resource_to_bundle.call_count == 1  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_pending_uploads_tracking(
        self, bundle_context: BundleStorageContext
    ) -> None:
        """Test that pending uploads are properly tracked."""
        # Initially no pending uploads
        assert len(bundle_context._pending_uploads) == 0

        # Add first resource
        url1 = "https://example.com/resource1"

        async def mock_stream1() -> AsyncGenerator[bytes]:
            yield b"content1"

        await bundle_context.add_resource(url1, "text/html", 200, mock_stream1())
        assert len(bundle_context._pending_uploads) == 0
        assert len(bundle_context._completed_uploads) == 1

        # Add second resource
        url2 = "https://example.com/resource2"

        async def mock_stream2() -> AsyncGenerator[bytes]:
            yield b"content2"

        await bundle_context.add_resource(url2, "application/json", 200, mock_stream2())
        assert len(bundle_context._pending_uploads) == 0
        assert len(bundle_context._completed_uploads) == 2

        # Complete the bundle
        await bundle_context.complete({"source": "test"})

        # Completed uploads should still be tracked
        assert len(bundle_context._completed_uploads) == 2

    @pytest.mark.asyncio
    async def test_bundle_context_with_different_status_codes(
        self, bundle_context: BundleStorageContext
    ) -> None:
        """Test adding resources with different status codes."""
        resources = [
            ("https://example.com/success", "text/html", 200),
            ("https://example.com/redirect", "text/html", 301),
            ("https://example.com/not_found", "text/html", 404),
            ("https://example.com/server_error", "text/html", 500),
        ]

        # Create mock streams
        async def mock_stream(content: bytes) -> AsyncGenerator[bytes]:
            yield content

        # Add all resources with different status codes
        for url, content_type, status_code in resources:
            stream = mock_stream(f"content for {url}".encode())
            await bundle_context.add_resource(url, content_type, status_code, stream)

        # Verify all resources were processed
        assert len(bundle_context._pending_uploads) == 0
        assert len(bundle_context._completed_uploads) == 4

        # Verify storage method was called for each resource with correct status code
        assert bundle_context.storage._add_resource_to_bundle.call_count == 4  # type: ignore[attr-defined]

        # Verify the calls were made with correct parameters
        calls = bundle_context.storage._add_resource_to_bundle.call_args_list  # type: ignore[attr-defined]
        for i, (url, content_type, status_code) in enumerate(resources):
            call_args = calls[i][0]  # Get positional arguments
            assert call_args[1] == url  # url parameter
            assert call_args[2] == content_type  # content_type parameter
            assert call_args[3] == status_code  # status_code parameter
