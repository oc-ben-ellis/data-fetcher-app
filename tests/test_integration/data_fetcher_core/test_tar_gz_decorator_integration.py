"""Integration tests for TarGzDecorator functionality.

This module contains integration tests for the TarGzDecorator that verify
tar and gzip file processing, streaming behavior, and resource extraction.
"""

import asyncio
import gzip
import tarfile
import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest

from data_fetcher_core.core import BundleRef, DataRegistryFetcherConfig
from data_fetcher_core.storage.decorators.tar_gz_resource import TarGzResourceDecorator


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


async def create_file_stream(file_path: str) -> AsyncGenerator[bytes]:
    """Create an async generator that yields the file content."""
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(8192)  # 8KB chunks
            if not chunk:
                break
            yield chunk


@pytest.mark.integration
class TestTarGzDecoratorIntegration:
    """Integration tests for TarGzDecorator functionality."""

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
    def decorator(self, mock_storage: MockStorage) -> TarGzResourceDecorator:
        """Create TarGzDecorator with mock storage."""
        return TarGzResourceDecorator(mock_storage)

    def create_test_gz_file(self, content: str) -> str:
        """Create a test gz file with specified content."""
        with tempfile.NamedTemporaryFile(suffix=".gz", delete=False) as temp_gz:
            gz_path = temp_gz.name

        with gzip.open(gz_path, "wt") as gz_file:
            gz_file.write(content)

        return gz_path

    def create_test_tar_file(self, files: dict[str, str]) -> str:
        """Create a test tar file with specified files and content."""
        with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as temp_tar:
            tar_path = temp_tar.name

        with tarfile.open(tar_path, "w") as tar_file:
            for filename, content in files.items():
                # Create a temporary file for each content
                with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
                    temp_file.write(content)
                    temp_file.flush()

                    # Add to tar
                    tar_file.add(temp_file.name, arcname=filename)

                    # Clean up temp file
                    Path(temp_file.name).unlink()

        return tar_path

    def create_test_tar_gz_file(self, files: dict[str, str]) -> str:
        """Create a test tar.gz file with specified files and content."""
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as temp_tar_gz:
            tar_gz_path = temp_tar_gz.name

        # First create a tar file
        with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as temp_tar:
            tar_path = temp_tar.name

        with tarfile.open(tar_path, "w") as tar_file:
            for filename, content in files.items():
                # Create a temporary file for each content
                with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
                    temp_file.write(content)
                    temp_file.flush()

                    # Add to tar
                    tar_file.add(temp_file.name, arcname=filename)

                    # Clean up temp file
                    Path(temp_file.name).unlink()

        # Then gzip the tar file
        with open(tar_path, "rb") as tar_file:
            with gzip.open(tar_gz_path, "wb") as gz_file:
                gz_file.write(tar_file.read())

        # Clean up intermediate tar file
        Path(tar_path).unlink()

        return tar_gz_path

    @pytest.mark.asyncio
    async def test_gz_file_processing(
        self,
        decorator: TarGzResourceDecorator,
        bundle_ref: BundleRef,
        recipe: DataRegistryFetcherConfig,
        mock_storage: MockStorage,
    ) -> None:
        """Test gz file processing - should stream original and decompressed content."""
        # Create test gz file
        original_content = "This is the original content that will be compressed.\nIt has multiple lines.\n"
        gz_path = self.create_test_gz_file(original_content)

        try:
            # Process gz file
            context = await decorator.start_bundle(bundle_ref, recipe)
            gz_stream = create_file_stream(gz_path)

            await context.add_resource(
                resource_name="https://example.com/test-data.gz",
                metadata={
                    "url": "https://example.com/test-data.gz",
                    "content_type": "application/gzip",
                    "status_code": 200,
                },
                stream=gz_stream,
            )

            await context.complete({"test": "metadata"})

            # Verify results - should have 2 resources: original + decompressed
            assert len(mock_storage.context.added_resources) == 2
            assert mock_storage.context.completed

            # Find resources
            original_resource = None
            decompressed_resource = None

            for resource in mock_storage.context.added_resources:
                if resource.get("url") == "https://example.com/test-data":
                    # Identify by presence of data size matching decompressed text
                    if (
                        decompressed_resource is None
                        and resource.get("size", 0) > 0
                        and resource.get("content_type") != "application/gzip"
                    ):
                        decompressed_resource = resource
                    else:
                        original_resource = resource

            # Verify original resource (compressed)
            assert original_resource is not None
            assert original_resource["content_type"] == "application/gzip"
            assert original_resource["status_code"] == 200

            # Verify decompressed resource
            assert decompressed_resource is not None
            decompressed_content = decompressed_resource["data"].decode("utf-8")
            assert decompressed_content == original_content

        finally:
            Path(gz_path).unlink()

    @pytest.mark.asyncio
    async def test_tar_file_processing(
        self,
        decorator: TarGzResourceDecorator,
        bundle_ref: BundleRef,
        recipe: DataRegistryFetcherConfig,
        mock_storage: MockStorage,
    ) -> None:
        """Test tar file processing - should stream original and extracted files."""
        # Create test tar file
        test_files = {
            "file1.txt": "Content of file 1\n",
            "file2.txt": "Content of file 2\n",
        }
        tar_path = self.create_test_tar_file(test_files)

        try:
            # Process tar file
            context = await decorator.start_bundle(bundle_ref, recipe)
            tar_stream = create_file_stream(tar_path)

            await context.add_resource(
                resource_name="https://example.com/test-data.tar",
                metadata={
                    "url": "https://example.com/test-data.tar",
                    "content_type": "application/x-tar",
                    "status_code": 200,
                },
                stream=tar_stream,
            )

            await context.complete({})

            # Verify results - should have 3 resources: original + 2 extracted files
            assert len(mock_storage.context.added_resources) == 3

            # Find resources
            original_resource = None
            extracted_resources = []

            for resource in mock_storage.context.added_resources:
                if resource.get("url") == "https://example.com/test-data":
                    original_resource = resource
                else:
                    extracted_resources.append(resource)

            # Verify original resource
            assert original_resource is not None
            assert original_resource["content_type"] == "application/x-tar"

            # Verify extracted resources
            assert len(extracted_resources) == 2

            for resource in extracted_resources:
                assert resource["url"].startswith("https://example.com/test-data/")
                assert resource["content_type"] == "application/octet-stream"

                if "file1.txt" in resource["url"]:
                    content = resource["data"].decode("utf-8")
                    assert content == "Content of file 1\n"
                elif "file2.txt" in resource["url"]:
                    content = resource["data"].decode("utf-8")
                    assert content == "Content of file 2\n"

        finally:
            Path(tar_path).unlink()

    @pytest.mark.asyncio
    async def test_tar_gz_file_processing(
        self,
        decorator: TarGzResourceDecorator,
        bundle_ref: BundleRef,
        recipe: DataRegistryFetcherConfig,
        mock_storage: MockStorage,
    ) -> None:
        """Test tar.gz file processing - should stream original and extracted files."""
        # Create test tar.gz file
        test_files = {
            "archive_file1.txt": "Content of archived file 1\n",
            "archive_file2.txt": "Content of archived file 2\n",
        }
        tar_gz_path = self.create_test_tar_gz_file(test_files)

        try:
            # Process tar.gz file
            context = await decorator.start_bundle(bundle_ref, recipe)
            tar_gz_stream = create_file_stream(tar_gz_path)

            await context.add_resource(
                resource_name="https://example.com/test-data.tar.gz",
                metadata={
                    "url": "https://example.com/test-data.tar.gz",
                    "content_type": "application/gzip",
                    "status_code": 200,
                },
                stream=tar_gz_stream,
            )

            await context.complete({})

            # Verify results - should have 3 resources: original + 2 extracted files
            assert len(mock_storage.context.added_resources) == 3

            # Find resources
            original_resource = None
            extracted_resources = []

            for resource in mock_storage.context.added_resources:
                if resource.get("url") == "https://example.com/test-data":
                    original_resource = resource
                else:
                    extracted_resources.append(resource)

            # Verify original resource
            assert original_resource is not None
            assert original_resource["content_type"] == "application/gzip"

            # Verify extracted resources
            assert len(extracted_resources) == 2

            for resource in extracted_resources:
                assert resource["url"].startswith("https://example.com/test-data/")
                assert resource["content_type"] == "application/octet-stream"

                if "archive_file1.txt" in resource["url"]:
                    content = resource["data"].decode("utf-8")
                    assert content == "Content of archived file 1\n"
                elif "archive_file2.txt" in resource["url"]:
                    content = resource["data"].decode("utf-8")
                    assert content == "Content of archived file 2\n"

        finally:
            Path(tar_gz_path).unlink()

    @pytest.mark.asyncio
    async def test_regular_file_passthrough(
        self,
        decorator: TarGzResourceDecorator,
        bundle_ref: BundleRef,
        recipe: DataRegistryFetcherConfig,
        mock_storage: MockStorage,
    ) -> None:
        """Test that regular files pass through without processing."""
        # Create a regular text file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as temp_file:
            temp_file.write("This is a regular text file.\n")
            temp_file.flush()
            file_path = temp_file.name

        try:
            # Process regular file
            context = await decorator.start_bundle(bundle_ref, recipe)
            file_stream = create_file_stream(file_path)

            await context.add_resource(
                resource_name="https://example.com/test-data.txt",
                metadata={
                    "url": "https://example.com/test-data.txt",
                    "content_type": "text/plain",
                    "status_code": 200,
                },
                stream=file_stream,
            )

            await context.complete({})

            # Verify results - should have only 1 resource (passthrough)
            assert len(mock_storage.context.added_resources) == 1

            resource = mock_storage.context.added_resources[0]
            assert resource["url"] == "https://example.com/test-data"
            assert resource["content_type"] == "text/plain"
            assert resource["status_code"] == 200

            content = resource["data"].decode("utf-8")
            assert content == "This is a regular text file.\n"

        finally:
            Path(file_path).unlink()

    @pytest.mark.asyncio
    async def test_bypass_behavior(
        self,
        decorator: TarGzResourceDecorator,
        bundle_ref: BundleRef,
        recipe: DataRegistryFetcherConfig,
        mock_storage: MockStorage,
    ) -> None:
        """Test that files with archive extensions are bypassed."""
        # Create test gz file
        gz_path = self.create_test_gz_file("Test content")

        try:
            # Process with .gz extension (should be bypassed)
            context = await decorator.start_bundle(bundle_ref, recipe)
            gz_stream = create_file_stream(gz_path)

            await context.add_resource(
                resource_name="https://example.com/test.gz",  # .gz extension
                metadata={
                    "url": "https://example.com/test.gz",
                    "content_type": "application/gzip",  # gzip content type
                    "status_code": 200,
                },
                stream=gz_stream,
            )

            await context.complete({})

            # Should only have 1 resource (bypassed, not processed)
            assert len(mock_storage.context.added_resources) == 1

            resource = mock_storage.context.added_resources[0]
            assert resource["url"] == "https://example.com/test"  # .gz stripped
            assert resource["content_type"] == "application/gzip"

        finally:
            Path(gz_path).unlink()


if __name__ == "__main__":
    # Run a simple test
    async def run_simple_test():
        """Run a simple test to verify functionality."""
        decorator = TarGzResourceDecorator(MockStorage())
        bundle_ref = BundleRef(
            primary_url="https://example.com/test", resources_count=1
        )
        recipe = DataRegistryFetcherConfig()

        # Create test gz file
        with tempfile.NamedTemporaryFile(suffix=".gz", delete=False) as temp_gz:
            gz_path = temp_gz.name

        with gzip.open(gz_path, "wt") as gz_file:
            gz_file.write("Hello, World!\n")

        try:
            # Process gz file
            context = await decorator.start_bundle(bundle_ref, recipe)
            gz_stream = create_file_stream(gz_path)

            await context.add_resource(
                resource_name="https://example.com/test-data",  # Don't use .gz extension to avoid bypass
                metadata={
                    "url": "https://example.com/test-data",
                    "content_type": "application/octet-stream",  # Don't use gzip content type to avoid bypass
                    "status_code": 200,
                },
                stream=gz_stream,
            )

            await context.complete({})

            # Verify results
            mock_storage = decorator.base_storage
            assert (
                len(mock_storage.context.added_resources) == 2
            )  # Original + decompressed
            print("✅ Simple TarGz test passed!")

        finally:
            Path(gz_path).unlink()

    asyncio.run(run_simple_test())
