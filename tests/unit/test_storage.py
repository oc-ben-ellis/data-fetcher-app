"""Tests for storage implementations and decorators.

This module contains unit tests for storage functionality,
including file storage, S3 integration, and storage decorators.
"""


import asyncio
import gzip
import io
import os
import tempfile
import zipfile
from collections.abc import AsyncGenerator, Generator

import pytest

# testcontainers imports moved to integration tests
from oc_fetcher.core import BundleRef
from oc_fetcher.storage.decorators import (
    ApplyWARCDecorator,
    BundleResourcesDecorator,
    UnzipResourceDecorator,
)
from oc_fetcher.storage.file_storage import FileStorage

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
        assert os.path.exists(temp_dir)

    @pytest.mark.asyncio
    async def test_open_bundle(
        self, storage: FileStorage, bundle_ref: BundleRef
    ) -> None:
        """Test opening a bundle."""
        async with storage.open_bundle(bundle_ref) as bundle:
            assert bundle is not None
            assert bundle.bundle_ref == bundle_ref
            assert bundle.output_dir == storage.output_dir
            assert os.path.exists(bundle.bundle_dir)

    @pytest.mark.asyncio
    async def test_write_resource(
        self, storage: FileStorage, bundle_ref: BundleRef
    ) -> None:
        """Test writing a resource to a bundle."""

        async def test_stream() -> AsyncGenerator[bytes, None]:
            yield b"<html><body>Test content</body></html>"

        async with storage.open_bundle(bundle_ref) as bundle:
            await bundle.write_resource(
                url="https://example.com/page.html",
                content_type="text/html",
                status_code=200,
                stream=test_stream(),
            )

            # Check that files were created
            files = os.listdir(bundle.bundle_dir)
            assert "page.html" in files

            # Check content
            with open(os.path.join(bundle.bundle_dir, "page.html"), "rb") as f:
                content = f.read()
                assert b"<html><body>Test content</body></html>" in content

    @pytest.mark.asyncio
    async def test_write_multiple_resources(
        self, storage: FileStorage, bundle_ref: BundleRef
    ) -> None:
        """Test writing multiple resources to a bundle."""

        async def test_stream() -> AsyncGenerator[bytes, None]:
            yield b"<html><body>Test content</body></html>"

        async with storage.open_bundle(bundle_ref) as bundle:
            # Write first resource
            await bundle.write_resource(
                url="https://example.com/page1.html",
                content_type="text/html",
                status_code=200,
                stream=test_stream(),
            )

            # Write second resource
            await bundle.write_resource(
                url="https://example.com/page2.html",
                content_type="text/html",
                status_code=200,
                stream=test_stream(),
            )

            # Check that files were created
            files = os.listdir(bundle.bundle_dir)
            assert "page1.html" in files
            assert "page2.html" in files

    @pytest.mark.asyncio
    async def test_bundle_metadata(
        self, storage: FileStorage, bundle_ref: BundleRef
    ) -> None:
        """Test bundle metadata handling."""

        async def test_stream() -> AsyncGenerator[bytes, None]:
            yield b"<html><body>Test content</body></html>"

        async with storage.open_bundle(bundle_ref) as bundle:
            await bundle.write_resource(
                url="https://example.com/page.html",
                content_type="text/html",
                status_code=200,
                stream=test_stream(),
            )

        # Check metadata file after bundle is closed
        metadata_file = os.path.join(bundle.bundle_dir, "bundle.meta")
        assert os.path.exists(metadata_file)

        # Verify metadata content

        with open(metadata_file) as f:
            metadata_content = f.read()
            # The metadata is stored as a string representation, not JSON
            assert "https://example.com" in metadata_content
            assert "test" in metadata_content


class TestStorageDecorators:
    """Test storage decorators behavior with streams."""

    @pytest.fixture
    def temp_dir(self) -> Generator[str, None, None]:
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def base_storage(self, temp_dir: str) -> FileStorage:
        """Create a base FileStorage for testing decorators."""
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

    def create_test_stream(self, content: bytes) -> AsyncGenerator[bytes, None]:
        """Create a test stream from bytes."""

        async def stream() -> AsyncGenerator[bytes, None]:
            yield content

        return stream()

    @pytest.mark.asyncio
    async def test_unzip_resource_decorator_gzip(
        self, base_storage: FileStorage, bundle_ref: BundleRef
    ) -> None:
        """Test UnzipResourceDecorator with gzipped content."""
        # Create gzipped content
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

        # Check that decompressed file was created
        files = os.listdir(base_storage.output_dir)
        assert len(files) > 0

        # Find the bundle directory (it will be named with a hash)
        bundle_dirs = [
            d for d in os.listdir(base_storage.output_dir) if d.startswith("bundle_")
        ]
        assert len(bundle_dirs) == 1
        bundle_dir = os.path.join(base_storage.output_dir, bundle_dirs[0])
        bundle_files = os.listdir(bundle_dir)

        # Should have a decompressed file (ignore .meta files)
        decompressed_files = [
            f for f in bundle_files if "decompressed" in f and not f.endswith(".meta")
        ]
        assert len(decompressed_files) == 1

        # Check content
        with open(os.path.join(bundle_dir, decompressed_files[0]), "rb") as f:
            content = f.read()
            assert content == original_content

    @pytest.mark.asyncio
    async def test_unzip_resource_decorator_zip(
        self, base_storage: FileStorage, bundle_ref: BundleRef
    ) -> None:
        """Test UnzipResourceDecorator with zip content."""
        # Create zip content with multiple files
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("file1.html", "<html>File 1</html>")
            zip_file.writestr("file2.txt", "Text content")

        zip_content = zip_buffer.getvalue()

        # Create storage with unzip decorator
        unzip_storage = UnzipResourceDecorator(base_storage)

        async with unzip_storage.open_bundle(bundle_ref) as bundle:
            await bundle.write_resource(
                url="https://example.com/archive.zip",
                content_type="application/zip",
                status_code=200,
                stream=self.create_test_stream(zip_content),
            )

        # Check that extracted files were created
        bundle_dirs = [
            d for d in os.listdir(base_storage.output_dir) if d.startswith("bundle_")
        ]
        assert len(bundle_dirs) == 1
        bundle_dir = os.path.join(base_storage.output_dir, bundle_dirs[0])
        bundle_files = os.listdir(bundle_dir)

        # Should have extracted files (ignore .meta files)
        extracted_files = [
            f for f in bundle_files if "archive.zip" in f and not f.endswith(".meta")
        ]
        assert len(extracted_files) == 2  # file1.html and file2.txt

        # Check content of extracted files
        for filename in ["file1.html", "file2.txt"]:
            file_path = os.path.join(bundle_dir, f"archive.zip_{filename}")
            assert os.path.exists(file_path)

    @pytest.mark.asyncio
    async def test_unzip_resource_decorator_non_compressed(
        self, base_storage: FileStorage, bundle_ref: BundleRef
    ) -> None:
        """Test UnzipResourceDecorator with non-compressed content."""
        original_content = b"<html><body>Test content</body></html>"

        # Create storage with unzip decorator
        unzip_storage = UnzipResourceDecorator(base_storage)

        async with unzip_storage.open_bundle(bundle_ref) as bundle:
            await bundle.write_resource(
                url="https://example.com/page.html",
                content_type="text/html",
                status_code=200,
                stream=self.create_test_stream(original_content),
            )

        # Check that original file was created (not decompressed)
        bundle_dirs = [
            d for d in os.listdir(base_storage.output_dir) if d.startswith("bundle_")
        ]
        assert len(bundle_dirs) == 1
        bundle_dir = os.path.join(base_storage.output_dir, bundle_dirs[0])
        bundle_files = os.listdir(bundle_dir)

        # Should have original file, not decompressed
        html_files = [
            f for f in bundle_files if f.endswith(".html") and not f.endswith(".meta")
        ]
        assert len(html_files) == 1

        # Check content
        with open(os.path.join(bundle_dir, html_files[0]), "rb") as f:
            content = f.read()
            assert content == original_content

    @pytest.mark.asyncio
    async def test_apply_warc_decorator(
        self, base_storage: FileStorage, bundle_ref: BundleRef
    ) -> None:
        """Test ApplyWARCDecorator creates proper WARC records."""
        original_content = b"<html><body>Test content</body></html>"

        # Create storage with WARC decorator
        warc_storage = ApplyWARCDecorator(base_storage)

        async with warc_storage.open_bundle(bundle_ref) as bundle:
            await bundle.write_resource(
                url="https://example.com/page.html",
                content_type="text/html",
                status_code=200,
                stream=self.create_test_stream(original_content),
            )

        # Check that WARC file was created
        bundle_dirs = [
            d for d in os.listdir(base_storage.output_dir) if d.startswith("bundle_")
        ]
        assert len(bundle_dirs) == 1
        bundle_dir = os.path.join(base_storage.output_dir, bundle_dirs[0])
        bundle_files = os.listdir(bundle_dir)

        # Should have WARC file
        warc_files = [
            f for f in bundle_files if f.endswith(".warc") and not f.endswith(".meta")
        ]
        assert len(warc_files) == 1

        # Check WARC content
        warc_file_path = os.path.join(bundle_dir, warc_files[0])
        with open(warc_file_path, "rb") as f:
            warc_content = f.read()

        # Verify WARC format
        assert warc_content.startswith(b"WARC/1.0\r\n")
        assert b"WARC-Type: response\r\n" in warc_content
        assert b"WARC-Target-URI: https://example.com/page.html\r\n" in warc_content
        assert b"HTTP/1.1 200 OK\r\n" in warc_content
        assert b"Content-Type: text/html\r\n" in warc_content
        assert original_content in warc_content

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
            d for d in os.listdir(base_storage.output_dir) if d.startswith("bundle_")
        ]
        assert len(bundle_dirs) == 1
        bundle_dir = os.path.join(base_storage.output_dir, bundle_dirs[0])
        bundle_files = os.listdir(bundle_dir)

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

        # Create storage stack: unzip -> warc -> bundle
        unzip_storage = UnzipResourceDecorator(base_storage)
        warc_storage = ApplyWARCDecorator(unzip_storage)
        bundle_storage = BundleResourcesDecorator(warc_storage)

        async with bundle_storage.open_bundle(bundle_ref) as bundle:
            await bundle.write_resource(
                url="https://example.com/page.html.gz",
                content_type="text/html",
                status_code=200,
                stream=self.create_test_stream(gzipped_content),
            )

        # Check that WARC file was created
        bundle_dirs = [
            d for d in os.listdir(base_storage.output_dir) if d.startswith("bundle_")
        ]
        assert len(bundle_dirs) == 1
        bundle_dir = os.path.join(base_storage.output_dir, bundle_dirs[0])
        bundle_files = os.listdir(bundle_dir)

        # Should have WARC file (the WARC decorator creates .warc files)
        warc_files = [
            f for f in bundle_files if f.endswith(".warc") and not f.endswith(".meta")
        ]
        assert len(warc_files) == 1

        # Check WARC content
        warc_file_path = os.path.join(bundle_dir, warc_files[0])
        with open(warc_file_path, "rb") as f:
            warc_content = f.read()

        # Verify WARC format
        assert b"WARC/1.0\r\n" in warc_content
        # The content is wrapped in a zip file, so we need to extract it
        # The WARC contains a zip file with the gzipped content
        assert b"PK\x03\x04" in warc_content  # ZIP file signature
        assert b"resource_000.html" in warc_content  # Should contain the resource name

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
            # This should not raise an exception, but should write original content
            await bundle.write_resource(
                url="https://example.com/corrupted.gz",
                content_type="text/html",
                status_code=200,
                stream=self.create_test_stream(corrupted_content),
            )

        # Check that original file was written as fallback
        bundle_dirs = [
            d for d in os.listdir(base_storage.output_dir) if d.startswith("bundle_")
        ]
        assert len(bundle_dirs) == 1
        bundle_dir = os.path.join(base_storage.output_dir, bundle_dirs[0])
        bundle_files = os.listdir(bundle_dir)

        # Should have original file (ignore .meta files)
        # The unzip decorator writes the original file with .gz extension when it can't decompress
        gz_files = [
            f for f in bundle_files if f.endswith(".gz") and not f.endswith(".meta")
        ]
        assert len(gz_files) == 1

        # Check content
        with open(os.path.join(bundle_dir, gz_files[0]), "rb") as f:
            content = f.read()
            assert content == corrupted_content


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

        # Create storage stack: unzip -> warc -> bundle
        unzip_storage = UnzipResourceDecorator(base_storage)
        warc_storage = ApplyWARCDecorator(unzip_storage)
        bundle_storage = BundleResourcesDecorator(warc_storage)

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
        files = os.listdir(temp_dir)
        assert len(files) > 0

        # Find the bundle directory
        bundle_dirs = [d for d in os.listdir(temp_dir) if d.startswith("bundle_")]
        assert len(bundle_dirs) == 1
        bundle_dir = os.path.join(temp_dir, bundle_dirs[0])
        bundle_files = os.listdir(bundle_dir)

        # Should have one WARC file (the bundle decorator creates a zip, then WARC wraps it)
        warc_files = [
            f for f in bundle_files if f.endswith(".warc") and not f.endswith(".meta")
        ]
        assert len(warc_files) == 1  # One WARC record containing the bundle

        # Check WARC content
        warc_file_path = os.path.join(bundle_dir, warc_files[0])
        with open(warc_file_path, "rb") as f:
            content = f.read()
            assert b"WARC/1.0\r\n" in content

            # The WARC contains a zip file with both resources
            assert b"PK\x03\x04" in content  # ZIP file signature
            assert b"resource_000" in content  # Should contain resource names
            assert b"resource_001" in content

    def create_test_stream(self, content: bytes) -> AsyncGenerator[bytes, None]:
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

        bundle_ref = BundleRef(
            primary_url="https://example.com",
            resources_count=1,
            storage_key="performance_test",
            meta={"test": "performance"},
        )

        start_time = asyncio.get_event_loop().time()

        async with bundle_storage.open_bundle(bundle_ref) as bundle:
            await bundle.write_resource(
                url="https://example.com/large.html",
                content_type="text/html",
                status_code=200,
                stream=self.create_test_stream(large_content),
            )

        end_time = asyncio.get_event_loop().time()
        processing_time = end_time - start_time

        # Should complete within reasonable time (less than 10 seconds)
        assert processing_time < 10.0

        # Check that file was created
        bundle_dirs = [d for d in os.listdir(temp_dir) if d.startswith("bundle_")]
        assert len(bundle_dirs) == 1
        bundle_dir = os.path.join(temp_dir, bundle_dirs[0])
        bundle_files = os.listdir(bundle_dir)

        zip_files = [f for f in bundle_files if f.endswith(".zip")]
        assert len(zip_files) == 1

        # Check file size
        zip_file_path = os.path.join(bundle_dir, zip_files[0])
        file_size = os.path.getsize(zip_file_path)
        assert file_size > 0
        assert file_size < len(large_content)  # Should be compressed

    @pytest.mark.asyncio
    async def test_storage_concurrent_access(self, temp_dir: str) -> None:
        """Test storage with concurrent access."""
        base_storage = FileStorage(temp_dir)
        bundle_storage = BundleResourcesDecorator(base_storage)

        async def process_bundle(bundle_id: int) -> None:
            """Process a single bundle."""
            bundle_ref = BundleRef(
                primary_url=f"https://example.com/bundle{bundle_id}",
                resources_count=1,
                storage_key=f"concurrent_test_{bundle_id}",
                meta={"test": "concurrent", "id": bundle_id},
            )

            async with bundle_storage.open_bundle(bundle_ref) as bundle:
                await bundle.write_resource(
                    url=f"https://example.com/page{bundle_id}.html",
                    content_type="text/html",
                    status_code=200,
                    stream=self.create_test_stream(f"Content {bundle_id}".encode()),
                )

        # Process multiple bundles concurrently
        tasks = [process_bundle(i) for i in range(5)]
        await asyncio.gather(*tasks)

        # Check that all bundles were created
        files = os.listdir(temp_dir)
        assert len(files) >= 5

        # Check each bundle
        for _i in range(5):
            bundle_dirs = [d for d in os.listdir(temp_dir) if d.startswith("bundle_")]
            assert len(bundle_dirs) >= 1

            # Find the bundle directory for this test
            bundle_dir = None
            for bundle_dir_name in bundle_dirs:
                bundle_dir_path = os.path.join(temp_dir, bundle_dir_name)
                bundle_files = os.listdir(bundle_dir_path)
                zip_files = [f for f in bundle_files if f.endswith(".zip")]
                if len(zip_files) > 0:
                    bundle_dir = bundle_dir_path
                    break

            assert bundle_dir is not None
            assert os.path.exists(bundle_dir)

            bundle_files = os.listdir(bundle_dir)
            zip_files = [f for f in bundle_files if f.endswith(".zip")]
            assert len(zip_files) == 1
