#!/usr/bin/env python3
"""Unit tests for storage components."""

import gzip
import os
import tempfile
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest

from data_fetcher_core.core import BundleRef
from data_fetcher_core.storage.decorators import (
    UnzipResourceDecorator,
)
from data_fetcher_core.storage.file_storage import FileStorage


class TestFileStorage:
    """Test FileStorage implementation."""

    @pytest.fixture
    def temp_dir(self) -> Generator[str]:
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def storage(self, temp_dir: str) -> FileStorage:
        """Create a FileStorage instance for testing."""
        return FileStorage(temp_dir)

    @pytest.fixture
    def bundle_ref(self) -> BundleRef:
        """Create a test bundle reference."""
        return BundleRef(
            primary_url="https://example.com",
            resources_count=1,
            storage_key="test_bundle",
            meta={"test": "data"},
        )

    @pytest.fixture
    def bundle_ref_with_custom_bid(self) -> BundleRef:
        """Create a test bundle reference with custom BID."""
        from data_fetcher_core.core import BID

        return BundleRef(
            primary_url="https://example.com",
            resources_count=1,
            bid=BID("test-bundle-id-12345"),
            storage_key="test_bundle",
            meta={"test": "data"},
        )

    def test_storage_creation(self, storage: FileStorage, temp_dir: str) -> None:
        """Test FileStorage creation."""
        assert storage.output_dir == temp_dir
        assert storage.create_dirs is True
        assert Path(temp_dir).exists()

    @pytest.mark.asyncio
    async def test_start_bundle(
        self, storage: FileStorage, bundle_ref: BundleRef
    ) -> None:
        """Test starting a bundle."""
        from data_fetcher_core.core import FetcherRecipe

        recipe = FetcherRecipe(recipe_id="test", bundle_loader=None, bundle_locators=[])

        context = await storage.start_bundle(bundle_ref, recipe)
        assert context is not None
        assert context.bundle_ref == bundle_ref
        assert context.recipe == recipe

        await context.complete({"test": "metadata"})

    @pytest.mark.asyncio
    async def test_bid_based_directory_naming(
        self, storage: FileStorage, bundle_ref_with_custom_bid: BundleRef
    ) -> None:
        """Test that storage uses BID for directory naming."""
        from data_fetcher_core.core import FetcherRecipe

        recipe = FetcherRecipe(recipe_id="test", bundle_loader=None, bundle_locators=[])

        context = await storage.start_bundle(bundle_ref_with_custom_bid, recipe)

        # The bundle directory should be named using the BID
        expected_dir_name = f"bundle_{bundle_ref_with_custom_bid.bid}"
        bundle_dir = os.path.join(storage.output_dir, expected_dir_name)

        # The directory should exist after adding a resource
        await context.add_resource(
            url="https://example.com/test.html",
            content_type="text/html",
            status_code=200,
            stream=self.create_test_stream(b"<html>Test</html>"),
        )

        assert Path(bundle_dir).exists()

        await context.complete({"test": "metadata"})

    @pytest.mark.asyncio
    async def test_write_resource(
        self, storage: FileStorage, bundle_ref: BundleRef
    ) -> None:
        """Test writing a resource to a bundle."""
        from data_fetcher_core.core import FetcherRecipe

        recipe = FetcherRecipe(recipe_id="test", bundle_loader=None, bundle_locators=[])

        context = await storage.start_bundle(bundle_ref, recipe)

        await context.add_resource(
            url="https://example.com/page.html",
            content_type="text/html",
            status_code=200,
            stream=TestStorageDecorators.create_test_stream(
                b"<html><body>Test content</body></html>"
            ),
        )

        await context.complete({"test": "metadata"})

        # Check that files were created
        expected_dir_name = f"bundle_{bundle_ref.bid}"
        bundle_dir = os.path.join(storage.output_dir, expected_dir_name)
        files = [f.name for f in Path(bundle_dir).iterdir()]
        assert "page.html" in files

        # Check content
        with Path(os.path.join(bundle_dir, "page.html")).open("rb") as f:
            content = f.read()
            assert b"<html><body>Test content</body></html>" in content

    @pytest.mark.asyncio
    async def test_write_multiple_resources(
        self, storage: FileStorage, bundle_ref: BundleRef
    ) -> None:
        """Test writing multiple resources to a bundle."""
        from data_fetcher_core.core import FetcherRecipe

        recipe = FetcherRecipe(recipe_id="test", bundle_loader=None, bundle_locators=[])

        context = await storage.start_bundle(bundle_ref, recipe)

        # Write first resource
        await context.add_resource(
            url="https://example.com/page1.html",
            content_type="text/html",
            status_code=200,
            stream=TestStorageDecorators.create_test_stream(
                b"<html><body>Test content</body></html>"
            ),
        )

        # Write second resource
        await context.add_resource(
            url="https://example.com/page2.html",
            content_type="text/html",
            status_code=200,
            stream=TestStorageDecorators.create_test_stream(
                b"<html><body>Test content</body></html>"
            ),
        )

        await context.complete({"test": "metadata"})

        # Check that both files were created
        expected_dir_name = f"bundle_{bundle_ref.bid}"
        bundle_dir = os.path.join(storage.output_dir, expected_dir_name)
        files = [f.name for f in Path(bundle_dir).iterdir()]
        assert "page1.html" in files
        assert "page2.html" in files

        # Check content
        with Path(os.path.join(bundle_dir, "page1.html")).open("rb") as f:
            content = f.read()
            assert b"<html><body>Test content</body></html>" in content

        with Path(os.path.join(bundle_dir, "page2.html")).open("rb") as f:
            content = f.read()
            assert b"<html><body>Test content</body></html>" in content

    @pytest.mark.asyncio
    async def test_write_resource_with_metadata(
        self, storage: FileStorage, bundle_ref: BundleRef
    ) -> None:
        """Test writing a resource with metadata."""
        from data_fetcher_core.core import FetcherRecipe

        recipe = FetcherRecipe(recipe_id="test", bundle_loader=None, bundle_locators=[])

        context = await storage.start_bundle(bundle_ref, recipe)

        await context.add_resource(
            url="https://example.com/data.json",
            content_type="application/json",
            status_code=200,
            stream=TestStorageDecorators.create_test_stream(b'{"key": "value"}'),
        )

        await context.complete({"test": "metadata"})

        # Check that metadata file was created
        expected_dir_name = f"bundle_{bundle_ref.bid}"
        bundle_dir = os.path.join(storage.output_dir, expected_dir_name)
        files = [f.name for f in Path(bundle_dir).iterdir()]
        assert "data.json" in files
        assert "data.json.meta" in files

        # Check metadata content
        meta_file_path = os.path.join(bundle_dir, "data.json.meta")
        with Path(meta_file_path).open() as f:
            meta_content = f.read()
            assert "https://example.com/data.json" in meta_content
            assert "application/json" in meta_content
            assert "200" in meta_content

    @staticmethod
    def create_test_stream(content: bytes) -> AsyncGenerator[bytes]:
        """Create a test stream from bytes."""

        async def stream() -> AsyncGenerator[bytes]:
            yield content

        return stream()


class TestStorageDecorators:
    """Test storage decorators."""

    @pytest.fixture
    def temp_dir(self) -> Generator[str]:
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def base_storage(self, temp_dir: str) -> FileStorage:
        """Create a base FileStorage instance for testing."""
        return FileStorage(temp_dir)

    @pytest.fixture
    def bundle_ref(self) -> BundleRef:
        """Create a test bundle reference."""
        return BundleRef(
            primary_url="https://example.com",
            resources_count=1,
            storage_key="test_bundle",
            meta={"test": "data"},
        )

    @pytest.mark.asyncio
    async def test_unzip_resource_decorator(
        self, base_storage: FileStorage, bundle_ref: BundleRef
    ) -> None:
        """Test UnzipResourceDecorator decompresses gzipped content."""
        from data_fetcher_core.core import FetcherRecipe

        original_content = b"<html><body>Test content</body></html>"
        gzipped_content = gzip.compress(original_content)

        # Create storage with unzip decorator
        unzip_storage = UnzipResourceDecorator(base_storage)

        # Create a minimal recipe for testing
        recipe = FetcherRecipe(recipe_id="test", bundle_loader=None, bundle_locators=[])

        # Use the new start_bundle interface
        context = await unzip_storage.start_bundle(bundle_ref, recipe)

        await context.add_resource(
            url="https://example.com/page.html.gz",
            content_type="text/html",
            status_code=200,
            stream=self.create_test_stream(gzipped_content),
        )

        await context.complete({"test": "metadata"})

        # Check that unzipped file was created
        bundle_dirs = [
            d.name
            for d in Path(base_storage.output_dir).iterdir()
            if d.name.startswith("bundle_")
        ]
        assert len(bundle_dirs) == 1
        bundle_dir = os.path.join(base_storage.output_dir, bundle_dirs[0])
        bundle_files = [f.name for f in Path(bundle_dir).iterdir()]

        # Should have unzipped file
        html_files = [
            f for f in bundle_files if f.endswith(".html") and not f.endswith(".meta")
        ]
        assert len(html_files) == 1

        # Check content
        html_file_path = os.path.join(bundle_dir, html_files[0])
        with Path(html_file_path).open("rb") as f:
            content = f.read()
            assert content == original_content

    @pytest.mark.asyncio
    async def test_decorator_error_handling(
        self, base_storage: FileStorage, bundle_ref: BundleRef
    ) -> None:
        """Test decorator error handling with corrupted content."""
        from data_fetcher_core.core import FetcherRecipe

        # Create corrupted gzip content
        corrupted_content = b"<html>This is not gzipped</html>"

        # Create storage with unzip decorator
        unzip_storage = UnzipResourceDecorator(base_storage)

        # Create a minimal recipe for testing
        recipe = FetcherRecipe(recipe_id="test", bundle_loader=None, bundle_locators=[])

        # Use the new start_bundle interface
        context = await unzip_storage.start_bundle(bundle_ref, recipe)

        # This should handle the error gracefully
        await context.add_resource(
            url="https://example.com/page.html.gz",
            content_type="text/html",
            status_code=200,
            stream=self.create_test_stream(corrupted_content),
        )

        await context.complete({"test": "metadata"})

        # Check that the corrupted content was stored as-is
        bundle_dirs = [
            d.name
            for d in Path(base_storage.output_dir).iterdir()
            if d.name.startswith("bundle_")
        ]
        assert len(bundle_dirs) == 1
        bundle_dir = os.path.join(base_storage.output_dir, bundle_dirs[0])
        bundle_files = [f.name for f in Path(bundle_dir).iterdir()]

        # Should have the file (stored as-is due to corruption)
        html_files = [
            f for f in bundle_files if f.endswith(".html") and not f.endswith(".meta")
        ]
        assert len(html_files) == 1

        # Check content (should be the corrupted content as-is)
        html_file_path = os.path.join(bundle_dir, html_files[0])
        with Path(html_file_path).open("rb") as f:
            content = f.read()
            assert content == corrupted_content

    @staticmethod
    def create_test_stream(content: bytes) -> AsyncGenerator[bytes]:
        """Create a test stream from bytes."""

        async def stream() -> AsyncGenerator[bytes]:
            yield content

        return stream()


class TestStorageIntegration:
    """Integration tests for storage components."""

    @pytest.fixture
    def temp_dir(self) -> Generator[str]:
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @staticmethod
    def create_test_stream(content: bytes) -> AsyncGenerator[bytes]:
        """Create a test stream from bytes."""

        async def stream() -> AsyncGenerator[bytes]:
            yield content

        return stream()
