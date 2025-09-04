#!/usr/bin/env python3
"""Unit tests for storage components."""

import gzip
import os
import tempfile
import zipfile
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest

# testcontainers imports moved to integration tests
from data_fetcher.core import BundleRef
from data_fetcher.storage.decorators import (
    BundleResourcesDecorator,
    UnzipResourceDecorator,
)
from data_fetcher.storage.file_storage import FileStorage

# S3Storage import moved to integration tests


class TestFileStorage:
    """Test FileStorage implementation."""

    @pytest.fixture
    def temp_dir(self) -> Generator[str, None, None]:
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

    def test_storage_creation(self, storage: FileStorage, temp_dir: str) -> None:
        """Test FileStorage creation."""
        assert storage.output_dir == temp_dir
        assert storage.create_dirs is True
        assert Path(temp_dir).exists()

    @pytest.mark.asyncio
    async def test_open_bundle(
        self, storage: FileStorage, bundle_ref: BundleRef
    ) -> None:
        """Test opening a bundle."""
        async with storage.open_bundle(bundle_ref) as bundle:
            assert bundle is not None
            assert bundle.bundle_ref == bundle_ref
            assert bundle.output_dir == storage.output_dir
            assert Path(bundle.bundle_dir).exists()

    @pytest.mark.asyncio
    async def test_write_resource(
        self, storage: FileStorage, bundle_ref: BundleRef
    ) -> None:
        """Test writing a resource to a bundle."""
        async with storage.open_bundle(bundle_ref) as bundle:
            await bundle.write_resource(
                url="https://example.com/page.html",
                content_type="text/html",
                status_code=200,
                stream=TestStorageDecorators.create_test_stream(
                    b"<html><body>Test content</body></html>"
                ),
            )

            # Check that files were created
            files = [f.name for f in Path(bundle.bundle_dir).iterdir()]
            assert "page.html" in files

            # Check content
            with Path(os.path.join(bundle.bundle_dir, "page.html")).open("rb") as f:
                content = f.read()
                assert b"<html><body>Test content</body></html>" in content

    @pytest.mark.asyncio
    async def test_write_multiple_resources(
        self, storage: FileStorage, bundle_ref: BundleRef
    ) -> None:
        """Test writing multiple resources to a bundle."""
        async with storage.open_bundle(bundle_ref) as bundle:
            # Write first resource
            await bundle.write_resource(
                url="https://example.com/page1.html",
                content_type="text/html",
                status_code=200,
                stream=TestStorageDecorators.create_test_stream(
                    b"<html><body>Test content</body></html>"
                ),
            )

            # Write second resource
            await bundle.write_resource(
                url="https://example.com/page2.html",
                content_type="text/html",
                status_code=200,
                stream=TestStorageDecorators.create_test_stream(
                    b"<html><body>Test content</body></html>"
                ),
            )

            # Check that both files were created
            files = [f.name for f in Path(bundle.bundle_dir).iterdir()]
            assert "page1.html" in files
            assert "page2.html" in files

            # Check content
            with Path(os.path.join(bundle.bundle_dir, "page1.html")).open("rb") as f:
                content = f.read()
                assert b"<html><body>Test content</body></html>" in content

            with Path(os.path.join(bundle.bundle_dir, "page2.html")).open("rb") as f:
                content = f.read()
                assert b"<html><body>Test content</body></html>" in content

    @pytest.mark.asyncio
    async def test_write_resource_with_metadata(
        self, storage: FileStorage, bundle_ref: BundleRef
    ) -> None:
        """Test writing a resource with metadata."""
        async with storage.open_bundle(bundle_ref) as bundle:
            await bundle.write_resource(
                url="https://example.com/data.json",
                content_type="application/json",
                status_code=200,
                stream=TestStorageDecorators.create_test_stream(b'{"key": "value"}'),
            )

            # Check that metadata file was created
            files = [f.name for f in Path(bundle.bundle_dir).iterdir()]
            assert "data.json" in files
            assert "data.json.meta" in files

            # Check metadata content
            meta_file_path = os.path.join(bundle.bundle_dir, "data.json.meta")
            with Path(meta_file_path).open() as f:
                meta_content = f.read()
                assert "https://example.com/data.json" in meta_content
                assert "application/json" in meta_content
                assert "200" in meta_content

    @staticmethod
    def create_test_stream(content: bytes) -> AsyncGenerator[bytes, None]:
        """Create a test stream from bytes."""

        async def stream() -> AsyncGenerator[bytes, None]:
            yield content

        return stream()


class TestStorageDecorators:
    """Test storage decorators."""

    @pytest.fixture
    def temp_dir(self) -> Generator[str, None, None]:
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
        original_content = b"<html><body>Test content</body></html>"
        gzipped_content = gzip.compress(original_content)

        # Create storage with unzip decorator
        unzip_storage = UnzipResourceDecorator(base_storage)

        async with unzip_storage.open_bundle(bundle_ref) as bundle:
            await bundle.write_resource(
                url="https://example.com/page.html.gz",
                content_type="text/html",
                status_code=200,
                stream=self.create_test_stream(gzipped_content),
            )

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
    async def test_bundle_resources_decorator(
        self, base_storage: FileStorage, bundle_ref: BundleRef
    ) -> None:
        """Test BundleResourcesDecorator creates zip file with all resources."""
        # Create storage with bundle decorator
        bundle_storage = BundleResourcesDecorator(base_storage)

        async with bundle_storage.open_bundle(bundle_ref) as bundle:
            # Add multiple resources
            resources = [
                ("https://example.com/page1.html", "text/html", b"<html>Page 1</html>"),
                ("https://example.com/page2.html", "text/html", b"<html>Page 2</html>"),
                (
                    "https://example.com/data.json",
                    "application/json",
                    b'{"key": "value"}',
                ),
            ]

            for url, content_type, content in resources:
                await bundle.write_resource(
                    url=url,
                    content_type=content_type,
                    status_code=200,
                    stream=self.create_test_stream(content),
                )

        # Check that zip file was created
        bundle_dirs = [
            d.name
            for d in Path(base_storage.output_dir).iterdir()
            if d.name.startswith("bundle_")
        ]
        assert len(bundle_dirs) == 1
        bundle_dir = os.path.join(base_storage.output_dir, bundle_dirs[0])
        bundle_files = [f.name for f in Path(bundle_dir).iterdir()]

        # Should have zip file
        zip_files = [
            f for f in bundle_files if f.endswith(".zip") and not f.endswith(".meta")
        ]
        assert len(zip_files) == 1

        # Check zip content
        zip_file_path = os.path.join(bundle_dir, zip_files[0])
        with zipfile.ZipFile(zip_file_path, "r") as zip_file:
            file_list = zip_file.namelist()

            # Should have all resources
            assert len(file_list) == 3

            # Check content of each file
            assert zip_file.read("resource_000.html") == b"<html>Page 1</html>"
            assert zip_file.read("resource_001.html") == b"<html>Page 2</html>"
            assert zip_file.read("resource_002.json") == b'{"key": "value"}'

    @pytest.mark.asyncio
    async def test_multiple_decorators_integration(
        self, base_storage: FileStorage, bundle_ref: BundleRef
    ) -> None:
        """Test multiple decorators working together."""
        # Create gzipped content
        original_content = b"<html><body>Test content</body></html>"
        gzipped_content = gzip.compress(original_content)

        # Create storage stack: unzip -> bundle
        unzip_storage = UnzipResourceDecorator(base_storage)
        bundle_storage = BundleResourcesDecorator(unzip_storage)

        async with bundle_storage.open_bundle(bundle_ref) as bundle:
            await bundle.write_resource(
                url="https://example.com/page.html.gz",
                content_type="text/html",
                status_code=200,
                stream=self.create_test_stream(gzipped_content),
            )

        # Check that zip file was created
        bundle_dirs = [
            d.name
            for d in Path(base_storage.output_dir).iterdir()
            if d.name.startswith("bundle_")
        ]
        assert len(bundle_dirs) == 1
        bundle_dir = os.path.join(base_storage.output_dir, bundle_dirs[0])
        bundle_files = [f.name for f in Path(bundle_dir).iterdir()]

        # Should have zip file
        zip_files = [
            f for f in bundle_files if f.endswith(".zip") and not f.endswith(".meta")
        ]
        assert len(zip_files) == 1

        # Check zip content
        zip_file_path = os.path.join(bundle_dir, zip_files[0])
        with zipfile.ZipFile(zip_file_path, "r") as zip_file:
            file_list = zip_file.namelist()

            # Should have the unzipped resource
            assert len(file_list) == 1
            assert zip_file.read("resource_000.html") == original_content

    @pytest.mark.asyncio
    async def test_decorator_error_handling(
        self, base_storage: FileStorage, bundle_ref: BundleRef
    ) -> None:
        """Test decorator error handling with corrupted content."""
        # Create corrupted gzip content
        corrupted_content = b"<html>This is not gzipped</html>"

        # Create storage with unzip decorator
        unzip_storage = UnzipResourceDecorator(base_storage)

        async with unzip_storage.open_bundle(bundle_ref) as bundle:
            # This should handle the error gracefully
            await bundle.write_resource(
                url="https://example.com/page.html.gz",
                content_type="text/html",
                status_code=200,
                stream=self.create_test_stream(corrupted_content),
            )

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
    def create_test_stream(content: bytes) -> AsyncGenerator[bytes, None]:
        """Create a test stream from bytes."""

        async def stream() -> AsyncGenerator[bytes, None]:
            yield content

        return stream()


# S3 integration tests moved to tests/integration/test_integration_s3.py


class TestStorageIntegration:
    """Integration tests for storage components."""

    @pytest.fixture
    def temp_dir(self) -> Generator[str, None, None]:
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.mark.asyncio
    async def test_complete_storage_pipeline(self, temp_dir: str) -> None:
        """Test complete storage pipeline with multiple decorators."""
        # Create base storage
        base_storage = FileStorage(temp_dir)

        # Create storage stack: unzip -> bundle
        unzip_storage = UnzipResourceDecorator(base_storage)
        bundle_storage = BundleResourcesDecorator(unzip_storage)

        # Create bundle reference
        bundle_ref = BundleRef(
            primary_url="https://example.com",
            resources_count=2,
            storage_key="integration_test",
            meta={"test": "integration"},
        )

        # Create test content
        html_content = b"<html><body>Test HTML content</body></html>"
        json_content = b'{"key": "value", "number": 42}'

        # Create gzipped JSON content
        gzipped_json = gzip.compress(json_content)

        async with bundle_storage.open_bundle(bundle_ref) as bundle:
            # Add regular HTML content
            await bundle.write_resource(
                url="https://example.com/page.html",
                content_type="text/html",
                status_code=200,
                stream=self.create_test_stream(html_content),
            )

            # Add gzipped JSON content
            await bundle.write_resource(
                url="https://example.com/data.json.gz",
                content_type="application/json",
                status_code=200,
                stream=self.create_test_stream(gzipped_json),
            )

        # Check that files were created
        files = [f.name for f in Path(temp_dir).iterdir()]
        assert len(files) > 0

        # Find the bundle directory
        bundle_dirs = [
            d.name for d in Path(temp_dir).iterdir() if d.name.startswith("bundle_")
        ]
        assert len(bundle_dirs) == 1
        bundle_dir = os.path.join(temp_dir, bundle_dirs[0])
        bundle_files = [f.name for f in Path(bundle_dir).iterdir()]

        # Should have one zip file
        zip_files = [
            f for f in bundle_files if f.endswith(".zip") and not f.endswith(".meta")
        ]
        assert len(zip_files) == 1

        # Check zip content
        zip_file_path = os.path.join(bundle_dir, zip_files[0])
        with zipfile.ZipFile(zip_file_path, "r") as zip_file:
            file_list = zip_file.namelist()

            # Should have both resources
            assert len(file_list) == 2

            # Check content
            assert zip_file.read("resource_000.html") == html_content
            assert zip_file.read("resource_001.json") == json_content

    @staticmethod
    def create_test_stream(content: bytes) -> AsyncGenerator[bytes, None]:
        """Create a test stream from bytes."""

        async def stream() -> AsyncGenerator[bytes, None]:
            yield content

        return stream()

    @pytest.mark.asyncio
    async def test_storage_performance_with_large_files(self, temp_dir: str) -> None:
        """Test storage performance with large files."""
        # Create large content (5MB)
        large_content = b"x" * (5 * 1024 * 1024)

        base_storage = FileStorage(temp_dir)
        bundle_storage = BundleResourcesDecorator(base_storage)

        # Create bundle reference
        bundle_ref = BundleRef(
            primary_url="https://example.com",
            resources_count=1,
            storage_key="large_file_test",
            meta={"test": "large_file"},
        )

        async with bundle_storage.open_bundle(bundle_ref) as bundle:
            await bundle.write_resource(
                url="https://example.com/large.html",
                content_type="text/html",
                status_code=200,
                stream=self.create_test_stream(large_content),
            )

        # Check that zip file was created
        bundle_dirs = [
            d.name for d in Path(temp_dir).iterdir() if d.name.startswith("bundle_")
        ]
        assert len(bundle_dirs) == 1
        bundle_dir = os.path.join(temp_dir, bundle_dirs[0])
        bundle_files = [f.name for f in Path(bundle_dir).iterdir()]

        # Should have zip file
        zip_files = [
            f for f in bundle_files if f.endswith(".zip") and not f.endswith(".meta")
        ]
        assert len(zip_files) == 1

        # Check zip content
        zip_file_path = os.path.join(bundle_dir, zip_files[0])
        with zipfile.ZipFile(zip_file_path, "r") as zip_file:
            file_list = zip_file.namelist()
            assert len(file_list) == 1
            assert zip_file.read("resource_000.html") == large_content
