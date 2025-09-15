"""Integration tests for UnzipDecorator functionality.

This module contains integration tests for the UnzipDecorator that verify
ZIP file processing, streaming behavior, and resource extraction.
"""

import asyncio
import tempfile
import zipfile
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest

from data_fetcher_core.core import BundleRef, DataRegistryFetcherConfig
from data_fetcher_core.storage.decorators.unzip_resource import UnzipResourceDecorator


class MockBundleStorageContext:
    """Mock bundle storage context to track resource additions."""

    def __init__(self):
        self.added_resources = []
        self.completed = False

    async def add_resource(
        self,
        resource_name: str,
        metadata: dict[str, Any],
        stream: AsyncGenerator[bytes],
    ) -> None:
        """Mock add_resource that collects stream data."""
        # Collect all data from the stream
        data = b""
        async for chunk in stream:
            data += chunk

        self.added_resources.append(
            {
                "resource_name": resource_name,
                "metadata": metadata,
                "data": data,
                "size": len(data),
            }
        )

    async def complete(self, metadata: dict[str, Any]) -> None:
        """Mock complete method."""
        self.completed = True


class MockStorage:
    """Mock storage that returns our mock context."""

    def __init__(self):
        self.context = MockBundleStorageContext()

    async def start_bundle(
        self, bundle_ref: BundleRef, recipe: DataRegistryFetcherConfig
    ) -> MockBundleStorageContext:
        """Return mock context."""
        return self.context


async def create_zip_stream(zip_path: str) -> AsyncGenerator[bytes]:
    """Create an async generator that yields the ZIP file content."""
    with open(zip_path, "rb") as f:
        while True:
            chunk = f.read(8192)  # 8KB chunks
            if not chunk:
                break
            yield chunk


@pytest.mark.integration
class TestUnzipDecoratorIntegration:
    """Integration tests for UnzipDecorator functionality."""

    @pytest.fixture
    def recipe(self) -> DataRegistryFetcherConfig:
        """Create a simple recipe for testing."""
        return DataRegistryFetcherConfig()

    @pytest.fixture
    def bundle_ref(self) -> BundleRef:
        """Create a test bundle reference."""
        return BundleRef(primary_url="https://example.com/test-data", resources_count=1)

    @pytest.fixture
    def mock_storage(self) -> MockStorage:
        """Create mock storage for testing."""
        return MockStorage()

    @pytest.fixture
    def decorator(self, mock_storage: MockStorage) -> UnzipResourceDecorator:
        """Create UnzipDecorator with mock storage."""
        return UnzipResourceDecorator(mock_storage)

    def create_test_zip(self, files: dict[str, str]) -> str:
        """Create a test ZIP file with specified files and content."""
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_zip:
            zip_path = temp_zip.name

        with zipfile.ZipFile(zip_path, "w") as zipf:
            for filename, content in files.items():
                zipf.writestr(filename, content)

        return zip_path

    @pytest.mark.asyncio
    async def test_zip_processing_basic(
        self,
        decorator: UnzipResourceDecorator,
        bundle_ref: BundleRef,
        recipe: DataRegistryFetcherConfig,
        mock_storage: MockStorage,
    ) -> None:
        """Test basic ZIP file processing with 2 files."""
        # Create test ZIP file
        test_files = {
            "file1.txt": "This is the content of file 1.\nIt has multiple lines.\n",
            "file2.json": '{"name": "test", "value": 42, "active": true}\n',
        }
        zip_path = self.create_test_zip(test_files)

        try:
            # Start bundle and process ZIP
            context = await decorator.start_bundle(bundle_ref, recipe)
            zip_stream = create_zip_stream(zip_path)

            await context.add_resource(
                resource_name="https://example.com/test-data",
                metadata={
                    "url": "https://example.com/test-data",
                    "content_type": "application/octet-stream",
                    "status_code": 200,
                },
                stream=zip_stream,
            )

            await context.complete({"test": "metadata"})

            # Verify results
            assert len(mock_storage.context.added_resources) == 3
            assert mock_storage.context.completed

            # Find resources
            zip_resource = None
            extracted_resources = []

            for resource in mock_storage.context.added_resources:
                url = resource.get("url") or resource.get("metadata", {}).get("url")
                if url == "https://example.com/test-data":
                    zip_resource = {
                        **resource,
                        "url": url,
                        "content_type": resource.get("content_type")
                        or resource.get("metadata", {}).get("content_type"),
                        "status_code": resource.get("status_code")
                        or resource.get("metadata", {}).get("status_code"),
                    }
                else:
                    extracted_resources.append(
                        {
                            **resource,
                            "url": url,
                            "content_type": resource.get("content_type")
                            or resource.get("metadata", {}).get("content_type"),
                        }
                    )

            # Verify original ZIP resource
            assert zip_resource is not None
            assert zip_resource["content_type"] == "application/octet-stream"
            assert zip_resource["status_code"] == 200

            # Verify extracted resources
            assert len(extracted_resources) == 2

            # Verify extracted file contents
            for resource in extracted_resources:
                assert resource["content_type"] == "application/octet-stream"
                assert resource["url"].startswith("https://example.com/test-data/")

                if "file1.txt" in resource["url"]:
                    content = resource["data"].decode("utf-8")
                    assert "This is the content of file 1." in content
                elif "file2.json" in resource["url"]:
                    content = resource["data"].decode("utf-8")
                    assert '"name": "test"' in content

        finally:
            Path(zip_path).unlink()

    @pytest.mark.asyncio
    async def test_zip_processing_large_files(
        self,
        decorator: UnzipResourceDecorator,
        bundle_ref: BundleRef,
        recipe: DataRegistryFetcherConfig,
        mock_storage: MockStorage,
    ) -> None:
        """Test ZIP processing with larger files."""
        # Create test ZIP with larger content
        large_content = "x" * 10000  # 10KB of data
        test_files = {
            "large_file.txt": large_content,
            "small_file.txt": "small content",
        }
        zip_path = self.create_test_zip(test_files)

        try:
            # Process ZIP
            context = await decorator.start_bundle(bundle_ref, recipe)
            zip_stream = create_zip_stream(zip_path)

            await context.add_resource(
                resource_name="https://example.com/large-zip",
                metadata={
                    "url": "https://example.com/large-zip",
                    "content_type": "application/octet-stream",
                    "status_code": 200,
                },
                stream=zip_stream,
            )

            await context.complete({})

            # Verify results
            assert len(mock_storage.context.added_resources) == 3

            # Find the large file resource
            large_file_resource = None
            for resource in mock_storage.context.added_resources:
                url = resource.get("url") or resource.get("metadata", {}).get("url", "")
                if "large_file.txt" in url:
                    large_file_resource = resource
                    break

            assert large_file_resource is not None
            assert large_file_resource["size"] == len(large_content.encode())

        finally:
            Path(zip_path).unlink()

    @pytest.mark.asyncio
    async def test_zip_processing_multiple_files(
        self,
        decorator: UnzipResourceDecorator,
        bundle_ref: BundleRef,
        recipe: DataRegistryFetcherConfig,
        mock_storage: MockStorage,
    ) -> None:
        """Test ZIP processing with multiple files."""
        # Create test ZIP with many files
        test_files = {f"file_{i}.txt": f"Content of file {i}\n" for i in range(5)}
        zip_path = self.create_test_zip(test_files)

        try:
            # Process ZIP
            context = await decorator.start_bundle(bundle_ref, recipe)
            zip_stream = create_zip_stream(zip_path)

            await context.add_resource(
                resource_name="https://example.com/multi-file-zip",
                metadata={
                    "url": "https://example.com/multi-file-zip",
                    "content_type": "application/octet-stream",
                    "status_code": 200,
                },
                stream=zip_stream,
            )

            await context.complete({})

            # Verify results - should have 1 original + 5 extracted = 6 total
            assert len(mock_storage.context.added_resources) == 6

            # Verify all files are present
            extracted_urls = []
            for r in mock_storage.context.added_resources:
                url = r.get("url") or r.get("metadata", {}).get("url")
                if url and url != "https://example.com/multi-file-zip":
                    extracted_urls.append(url)

            for i in range(5):
                expected_url = f"https://example.com/multi-file-zip/file_{i}.txt"
                assert expected_url in extracted_urls

        finally:
            Path(zip_path).unlink()

    @pytest.mark.asyncio
    async def test_zip_processing_bypass_behavior(
        self,
        decorator: UnzipResourceDecorator,
        bundle_ref: BundleRef,
        recipe: DataRegistryFetcherConfig,
        mock_storage: MockStorage,
    ) -> None:
        """Test that ZIP files with .zip extension are bypassed."""
        # Create test ZIP file
        test_files = {"file1.txt": "content"}
        zip_path = self.create_test_zip(test_files)

        try:
            # Process ZIP with .zip extension (should be bypassed)
            context = await decorator.start_bundle(bundle_ref, recipe)
            zip_stream = create_zip_stream(zip_path)

            await context.add_resource(
                resource_name="https://example.com/test.zip",  # .zip extension
                metadata={
                    "url": "https://example.com/test.zip",
                    "content_type": "application/zip",  # zip content type
                    "status_code": 200,
                },
                stream=zip_stream,
            )

            await context.complete({})

            # Should only have 1 resource (bypassed, not extracted)
            assert len(mock_storage.context.added_resources) == 1

            resource = mock_storage.context.added_resources[0]
            url = resource.get("url") or resource.get("metadata", {}).get("url")
            content_type = resource.get("content_type") or resource.get(
                "metadata", {}
            ).get("content_type")
            assert url == "https://example.com/test"  # .zip stripped
            assert content_type == "application/zip"

        finally:
            Path(zip_path).unlink()

    @pytest.mark.asyncio
    async def test_zip_processing_error_handling(
        self,
        decorator: UnzipResourceDecorator,
        bundle_ref: BundleRef,
        recipe: DataRegistryFetcherConfig,
        mock_storage: MockStorage,
    ) -> None:
        """Test ZIP processing error handling."""
        # Create invalid ZIP file
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_zip:
            zip_path = temp_zip.name
            temp_zip.write(b"not a zip file")

        try:
            # Process invalid ZIP
            context = await decorator.start_bundle(bundle_ref, recipe)
            zip_stream = create_zip_stream(zip_path)

            # Should handle error gracefully
            await context.add_resource(
                resource_name="https://example.com/invalid-zip",
                metadata={
                    "url": "https://example.com/invalid-zip",
                    "content_type": "application/octet-stream",
                    "status_code": 200,
                },
                stream=zip_stream,
            )

            await context.complete({})

            # Should still have the original resource (error fallback)
            assert len(mock_storage.context.added_resources) == 1
            resource = mock_storage.context.added_resources[0]
            url = resource.get("url") or resource.get("metadata", {}).get("url")
            assert url == "https://example.com/invalid-zip"

        finally:
            Path(zip_path).unlink()

    @pytest.mark.asyncio
    async def test_zip_processing_streaming_behavior(
        self,
        decorator: UnzipResourceDecorator,
        bundle_ref: BundleRef,
        recipe: DataRegistryFetcherConfig,
        mock_storage: MockStorage,
    ) -> None:
        """Test that streaming behavior works correctly."""
        # Create test ZIP file
        test_files = {
            "stream_test.txt": "Streaming test content\n",
            "another_file.txt": "Another file content\n",
        }
        zip_path = self.create_test_zip(test_files)

        try:
            # Process ZIP
            context = await decorator.start_bundle(bundle_ref, recipe)
            zip_stream = create_zip_stream(zip_path)

            await context.add_resource(
                resource_name="https://example.com/stream-test",
                metadata={
                    "url": "https://example.com/stream-test",
                    "content_type": "application/octet-stream",
                    "status_code": 200,
                },
                stream=zip_stream,
            )

            await context.complete({})

            # Verify streaming worked (all resources should be present)
            assert len(mock_storage.context.added_resources) == 3

            # Verify all resources have data
            for resource in mock_storage.context.added_resources:
                assert resource["size"] > 0
                assert len(resource["data"]) > 0

        finally:
            Path(zip_path).unlink()


if __name__ == "__main__":
    # Run a simple test
    async def run_simple_test():
        """Run a simple test to verify functionality."""
        decorator = UnzipResourceDecorator(MockStorage())
        bundle_ref = BundleRef(
            primary_url="https://example.com/test", resources_count=1
        )
        recipe = DataRegistryFetcherConfig()

        # Create test ZIP
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_zip:
            zip_path = temp_zip.name

        with zipfile.ZipFile(zip_path, "w") as zipf:
            zipf.writestr("test.txt", "Hello, World!\n")

        try:
            # Process ZIP
            context = await decorator.start_bundle(bundle_ref, recipe)
            zip_stream = create_zip_stream(zip_path)

            await context.add_resource(
                resource_name="https://example.com/test",
                metadata={
                    "url": "https://example.com/test",
                    "content_type": "application/octet-stream",
                    "status_code": 200,
                },
                stream=zip_stream,
            )

            await context.complete({})

            # Verify results
            mock_storage = decorator.base_storage
            assert len(mock_storage.context.added_resources) == 2
            print("✅ Simple test passed!")

        finally:
            Path(zip_path).unlink()

    asyncio.run(run_simple_test())
