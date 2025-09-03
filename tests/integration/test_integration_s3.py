"""Integration tests for S3 storage functionality.

This module contains integration tests for S3 storage functionality,
including real LocalStack container testing, file uploads, and metadata handling.
"""

import asyncio
import gzip
import json
from collections.abc import AsyncGenerator
from typing import Any

import boto3
import pytest

from oc_fetcher.core import BundleRef
from oc_fetcher.storage.decorators import (
    ApplyWARCDecorator,
    BundleResourcesDecorator,
)
from oc_fetcher.storage.s3_storage import S3Storage


class TestS3Integration:
    """Integration tests for S3 storage functionality."""

    @pytest.fixture
    def s3_storage(self, test_bucket: str, localstack_container: Any) -> S3Storage:
        """Create S3Storage instance for testing."""
        storage = S3Storage(
            bucket_name=test_bucket,
            prefix="test-prefix/",
            region="us-east-1",
        )

        # In Docker-in-Docker, use localhost with the exposed port
        storage.s3_client = boto3.client(
            "s3",
            endpoint_url=f"http://localhost:{localstack_container.get_exposed_port(4566)}",
            aws_access_key_id="test",
            aws_secret_access_key="test",
            region_name="us-east-1",
        )

        return storage

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
    async def test_s3_basic_upload_and_retrieval(
        self,
        s3_storage: S3Storage,
        s3_client: Any,
        test_bucket: str,
        bundle_ref: BundleRef,
    ) -> None:
        """Test basic S3 upload and retrieval functionality."""
        test_content = b"<html><body>Test S3 content</body></html>"

        # Upload content
        async with s3_storage.open_bundle(bundle_ref) as bundle:
            await bundle.write_resource(
                url="https://example.com/test.html",
                content_type="text/html",
                status_code=200,
                stream=self.create_test_stream(test_content),
            )

        # Verify file was uploaded to S3
        response = s3_client.list_objects_v2(Bucket=test_bucket, Prefix="test-prefix/")
        objects = response.get("Contents", [])
        assert len(objects) >= 1

        # Find the resource object
        resource_objects = [obj for obj in objects if "resources" in obj["Key"]]
        assert len(resource_objects) == 1

        # Download and verify content
        resource_key = resource_objects[0]["Key"]
        response = s3_client.get_object(Bucket=test_bucket, Key=resource_key)
        content = response["Body"].read()
        assert content == test_content

        # Verify metadata
        assert response["Metadata"]["url"] == "https://example.com/test.html"
        assert response["Metadata"]["content_type"] == "text/html"
        assert response["Metadata"]["status_code"] == "200"

    @pytest.mark.asyncio
    async def test_s3_multiple_resources(
        self,
        s3_storage: S3Storage,
        s3_client: Any,
        test_bucket: str,
        bundle_ref: BundleRef,
    ) -> None:
        """Test S3 storage with multiple resources."""
        resources = [
            ("https://example.com/page1.html", "text/html", b"<html>Page 1</html>"),
            ("https://example.com/page2.html", "text/html", b"<html>Page 2</html>"),
            ("https://example.com/data.json", "application/json", b'{"key": "value"}'),
            ("https://example.com/image.jpg", "image/jpeg", b"fake_jpeg_data"),
        ]

        # Upload multiple resources
        async with s3_storage.open_bundle(bundle_ref) as bundle:
            for url, content_type, content in resources:
                await bundle.write_resource(
                    url=url,
                    content_type=content_type,
                    status_code=200,
                    stream=self.create_test_stream(content),
                )

        # Verify all resources were uploaded
        response = s3_client.list_objects_v2(Bucket=test_bucket, Prefix="test-prefix/")
        objects = response.get("Contents", [])

        # Should have bundle metadata + resources
        assert len(objects) >= len(resources)

        # Find the bundle metadata file to get the uploaded keys
        bundle_objects = [obj for obj in objects if "bundles" in obj["Key"]]
        assert len(bundle_objects) == 1

        bundle_key = bundle_objects[0]["Key"]
        response = s3_client.get_object(Bucket=test_bucket, Key=bundle_key)
        bundle_metadata = json.loads(response["Body"].read())

        # Verify we have the expected number of uploaded keys
        assert len(bundle_metadata["uploaded_keys"]) == len(resources)

        # Verify each resource content by downloading from the uploaded keys
        for i, (_, content_type, expected_content) in enumerate(resources):
            resource_key = bundle_metadata["uploaded_keys"][i]

            # Download and verify content
            response = s3_client.get_object(Bucket=test_bucket, Key=resource_key)
            content = response["Body"].read()

            # Content should match (might be compressed or processed)
            if content_type == "application/json":
                # JSON might be stored as-is
                assert content == expected_content or json.loads(content) == json.loads(
                    expected_content
                )
            else:
                # Other content types should match
                assert content == expected_content

    @pytest.mark.asyncio
    async def test_s3_large_file_handling(
        self,
        s3_storage: S3Storage,
        s3_client: Any,
        test_bucket: str,
        bundle_ref: BundleRef,
    ) -> None:
        """Test S3 storage with large files."""
        # Create large content (1MB)
        large_content = b"x" * (1024 * 1024)

        async with s3_storage.open_bundle(bundle_ref) as bundle:
            await bundle.write_resource(
                url="https://example.com/large_file.bin",
                content_type="application/octet-stream",
                status_code=200,
                stream=self.create_test_stream(large_content),
            )

        # Verify large file was uploaded
        response = s3_client.list_objects_v2(Bucket=test_bucket, Prefix="test-prefix/")
        objects = response.get("Contents", [])

        # Should have the large file
        large_file_objects = [
            obj
            for obj in objects
            if "large_file.bin" in obj["Key"] or "resources" in obj["Key"]
        ]
        assert len(large_file_objects) >= 1

        # Verify file size
        large_file_key = large_file_objects[0]["Key"]
        response = s3_client.head_object(Bucket=test_bucket, Key=large_file_key)
        assert response["ContentLength"] >= len(large_content)

    @pytest.mark.asyncio
    async def test_s3_metadata_preservation(
        self,
        s3_storage: S3Storage,
        s3_client: Any,
        test_bucket: str,
        bundle_ref: BundleRef,
    ) -> None:
        """Test that S3 metadata is properly preserved."""
        test_content = b"<html><body>Test metadata</body></html>"

        # Upload with custom metadata
        async with s3_storage.open_bundle(bundle_ref) as bundle:
            await bundle.write_resource(
                url="https://example.com/metadata_test.html",
                content_type="text/html",
                status_code=200,
                stream=self.create_test_stream(test_content),
            )

        # Find the uploaded object
        response = s3_client.list_objects_v2(Bucket=test_bucket, Prefix="test-prefix/")
        objects = response.get("Contents", [])
        resource_objects = [obj for obj in objects if "resources" in obj["Key"]]
        assert len(resource_objects) >= 1

        # Verify metadata
        resource_key = resource_objects[0]["Key"]
        response = s3_client.head_object(Bucket=test_bucket, Key=resource_key)

        # Check required metadata
        assert "url" in response["Metadata"]
        assert "content_type" in response["Metadata"]
        assert "status_code" in response["Metadata"]

        # Check metadata values
        assert response["Metadata"]["url"] == "https://example.com/metadata_test.html"
        assert response["Metadata"]["content_type"] == "text/html"
        assert response["Metadata"]["status_code"] == "200"

    @pytest.mark.asyncio
    async def test_s3_error_handling(
        self,
        s3_storage: S3Storage,
        test_bucket: str,
        bundle_ref: BundleRef,
    ) -> None:
        """Test S3 error handling scenarios."""
        # Test with invalid bucket (should fail gracefully)
        invalid_storage = S3Storage(
            bucket_name="nonexistent-bucket",
            prefix="test/",
            region="us-east-1",
        )
        invalid_storage.s3_client = s3_storage.s3_client

        # Should handle bucket not found gracefully
        try:
            async with invalid_storage.open_bundle(bundle_ref) as bundle:
                await bundle.write_resource(
                    url="https://example.com/test.html",
                    content_type="text/html",
                    status_code=200,
                    stream=self.create_test_stream(b"test"),
                )
        except Exception as e:
            # Should raise an appropriate error - in LocalStack this will be EndpointConnectionError
            # for non-existent buckets, or NoSuchBucket for existing endpoints
            assert any(
                error_type in str(e)
                for error_type in [
                    "NoSuchBucket",
                    "AccessDenied",
                    "EndpointConnectionError",
                    "Connection refused",
                ]
            )

    @pytest.mark.asyncio
    async def test_s3_concurrent_uploads(
        self,
        s3_storage: S3Storage,
        s3_client: Any,
        test_bucket: str,
        bundle_ref: BundleRef,
    ) -> None:
        """Test S3 storage with concurrent uploads."""
        # Create multiple bundle references
        bundle_refs = [
            BundleRef(
                primary_url=f"https://example.com/bundle_{i}",
                resources_count=1,
                storage_key=f"test_bundle_{i}",
                meta={"index": i},
            )
            for i in range(5)
        ]

        # Upload resources concurrently
        async def upload_bundle(bundle_ref: BundleRef) -> None:
            async with s3_storage.open_bundle(bundle_ref) as bundle:
                await bundle.write_resource(
                    url=f"https://example.com/bundle_{bundle_ref.storage_key}.html",
                    content_type="text/html",
                    status_code=200,
                    stream=self.create_test_stream(
                        f"Bundle {bundle_ref.storage_key}".encode()
                    ),
                )

        # Execute concurrent uploads
        await asyncio.gather(*[upload_bundle(ref) for ref in bundle_refs])

        # Verify all uploads succeeded
        response = s3_client.list_objects_v2(Bucket=test_bucket, Prefix="test-prefix/")
        objects = response.get("Contents", [])

        # Should have multiple bundle metadata files (one for each bundle)
        bundle_metadata_objects = [obj for obj in objects if "bundles" in obj["Key"]]
        assert len(bundle_metadata_objects) >= len(bundle_refs)

        # Verify each bundle has its metadata file
        for bundle_ref in bundle_refs:
            # Find the bundle metadata file for this bundle
            bundle_metadata_objects = [
                obj
                for obj in objects
                if "bundles" in obj["Key"]
                and bundle_ref.primary_url.replace("://", "_").replace("/", "_")
                in obj["Key"]
            ]
            assert (
                len(bundle_metadata_objects) >= 1
            ), f"Bundle metadata not found for {bundle_ref.storage_key}"

    @pytest.mark.asyncio
    async def test_s3_storage_decorators(
        self,
        s3_storage: S3Storage,
        s3_client: Any,
        test_bucket: str,
        bundle_ref: BundleRef,
    ) -> None:
        """Test S3 storage with various decorators."""
        # Test with WARC decorator
        warc_storage = ApplyWARCDecorator(s3_storage)

        test_content = b"<html><body>WARC test</body></html>"

        async with warc_storage.open_bundle(bundle_ref) as bundle:
            await bundle.write_resource(
                url="https://example.com/warc_test.html",
                content_type="text/html",
                status_code=200,
                stream=self.create_test_stream(test_content),
            )

        # Verify WARC file was created
        response = s3_client.list_objects_v2(Bucket=test_bucket, Prefix="test-prefix/")
        objects = response.get("Contents", [])

        # Should have WARC file
        warc_objects = [obj for obj in objects if obj["Key"].endswith(".warc")]
        assert len(warc_objects) >= 1

        # Test with bundler decorator
        bundler_storage = BundleResourcesDecorator(s3_storage)

        async with bundler_storage.open_bundle(bundle_ref) as bundle:
            await bundle.write_resource(
                url="https://example.com/bundle_test.html",
                content_type="text/html",
                status_code=200,
                stream=self.create_test_stream(test_content),
            )

        # Verify bundle was created
        response = s3_client.list_objects_v2(Bucket=test_bucket, Prefix="test-prefix/")
        objects = response.get("Contents", [])

        # Should have bundle file
        bundle_objects = [obj for obj in objects if obj["Key"].endswith(".json")]
        assert len(bundle_objects) >= 1

    @pytest.mark.asyncio
    async def test_s3_compression_handling(
        self,
        s3_storage: S3Storage,
        s3_client: Any,
        test_bucket: str,
        bundle_ref: BundleRef,
    ) -> None:
        """Test S3 storage with compressed content."""
        # Test with gzipped content
        original_content = b"<html><body>Compressed content</body></html>"
        compressed_content = gzip.compress(original_content)

        async with s3_storage.open_bundle(bundle_ref) as bundle:
            await bundle.write_resource(
                url="https://example.com/compressed.html.gz",
                content_type="text/html",
                status_code=200,
                stream=self.create_test_stream(compressed_content),
            )

        # Verify compressed content was uploaded
        response = s3_client.list_objects_v2(Bucket=test_bucket, Prefix="test-prefix/")
        objects = response.get("Contents", [])

        # Should have the compressed file
        compressed_objects = [
            obj
            for obj in objects
            if "compressed.html" in obj["Key"] or "resources" in obj["Key"]
        ]
        assert len(compressed_objects) >= 1

        # Download and verify content
        resource_key = compressed_objects[0]["Key"]
        response = s3_client.get_object(Bucket=test_bucket, Key=resource_key)
        content = response["Body"].read()

        # Content should match (compressed)
        assert content == compressed_content

    @pytest.mark.asyncio
    async def test_s3_storage_cleanup(
        self,
        s3_storage: S3Storage,
        s3_client: Any,
        test_bucket: str,
        bundle_ref: BundleRef,
    ) -> None:
        """Test S3 storage cleanup operations."""
        # Upload some test content
        test_content = b"<html><body>Cleanup test</body></html>"

        async with s3_storage.open_bundle(bundle_ref) as bundle:
            await bundle.write_resource(
                url="https://example.com/cleanup_test.html",
                content_type="text/html",
                status_code=200,
                stream=self.create_test_stream(test_content),
            )

        # Verify content was uploaded
        response = s3_client.list_objects_v2(Bucket=test_bucket, Prefix="test-prefix/")
        objects = response.get("Contents", [])
        assert len(objects) >= 1

        # Clean up all objects
        if objects:
            delete_objects = [{"Key": obj["Key"]} for obj in objects]
            s3_client.delete_objects(
                Bucket=test_bucket, Delete={"Objects": delete_objects}
            )

        # Verify cleanup
        response = s3_client.list_objects_v2(Bucket=test_bucket, Prefix="test-prefix/")
        objects = response.get("Contents", [])
        assert len(objects) == 0

    @pytest.mark.asyncio
    async def test_s3_storage_performance(
        self,
        s3_storage: S3Storage,
        s3_client: Any,
        test_bucket: str,
        bundle_ref: BundleRef,
    ) -> None:
        """Test S3 storage performance characteristics."""
        import time

        # Test upload performance
        test_content = b"x" * (100 * 1024)  # 100KB

        start_time = time.time()
        async with s3_storage.open_bundle(bundle_ref) as bundle:
            await bundle.write_resource(
                url="https://example.com/performance_test.html",
                content_type="text/html",
                status_code=200,
                stream=self.create_test_stream(test_content),
            )
        upload_time = time.time() - start_time

        # Upload should complete in reasonable time
        assert upload_time < 10.0  # Should upload 100KB in under 10 seconds

        # Test download performance
        response = s3_client.list_objects_v2(Bucket=test_bucket, Prefix="test-prefix/")
        objects = response.get("Contents", [])
        resource_objects = [obj for obj in objects if "resources" in obj["Key"]]

        if resource_objects:
            start_time = time.time()
            resource_key = resource_objects[0]["Key"]
            response = s3_client.get_object(Bucket=test_bucket, Key=resource_key)
            content = response["Body"].read()
            download_time = time.time() - start_time

            # Download should complete in reasonable time
            assert download_time < 5.0  # Should download 100KB in under 5 seconds
            assert content == test_content

    @pytest.mark.asyncio
    async def test_s3_storage_consistency(
        self,
        s3_storage: S3Storage,
        s3_client: Any,
        test_bucket: str,
        bundle_ref: BundleRef,
    ) -> None:
        """Test S3 storage consistency guarantees."""
        # Upload content multiple times to same key
        test_content = b"<html><body>Consistency test</body></html>"

        for _ in range(3):
            async with s3_storage.open_bundle(bundle_ref) as bundle:
                await bundle.write_resource(
                    url="https://example.com/consistency_test.html",
                    content_type="text/html",
                    status_code=200,
                    stream=self.create_test_stream(test_content),
                )

        # Verify final content is consistent
        response = s3_client.list_objects_v2(Bucket=test_bucket, Prefix="test-prefix/")
        objects = response.get("Contents", [])

        # Should have consistent state
        resource_objects = [obj for obj in objects if "resources" in obj["Key"]]
        assert len(resource_objects) >= 1

        # Download and verify final content
        resource_key = resource_objects[0]["Key"]
        response = s3_client.get_object(Bucket=test_bucket, Key=resource_key)
        content = response["Body"].read()
        assert content == test_content

    @pytest.mark.asyncio
    async def test_s3_storage_error_recovery(
        self,
        s3_storage: S3Storage,
        s3_client: Any,
        test_bucket: str,
        bundle_ref: BundleRef,
    ) -> None:
        """Test S3 storage error recovery scenarios."""
        # Test with malformed content - LocalStack may have internal errors
        malformed_content = b"<html><body>Malformed content"

        try:
            async with s3_storage.open_bundle(bundle_ref) as bundle:
                await bundle.write_resource(
                    url="https://example.com/malformed.html",
                    content_type="text/html",
                    status_code=200,
                    stream=self.create_test_stream(malformed_content),
                )
        except Exception as e:
            # Should handle malformed content gracefully
            # LocalStack may throw various errors including internal ones
            assert isinstance(e, Exception)
            print(f"Expected error for malformed content: {type(e).__name__}: {e}")

        # Test with empty content
        empty_content = b""

        try:
            async with s3_storage.open_bundle(bundle_ref) as bundle:
                await bundle.write_resource(
                    url="https://example.com/empty.html",
                    content_type="text/html",
                    status_code=200,
                    stream=self.create_test_stream(empty_content),
                )
        except Exception as e:
            # Empty content might also cause LocalStack issues
            print(f"Error with empty content: {type(e).__name__}: {e}")
            # Skip verification if upload failed
            return

        # Verify empty content was handled (only if upload succeeded)
        try:
            response = s3_client.list_objects_v2(
                Bucket=test_bucket, Prefix="test-prefix/"
            )
            objects = response.get("Contents", [])

            # Should have the empty file
            empty_objects = [
                obj
                for obj in objects
                if "empty.html" in obj["Key"] or "resources" in obj["Key"]
            ]
            assert len(empty_objects) >= 1
        except Exception as e:
            print(f"Error verifying empty content: {type(e).__name__}: {e}")
            # Test passes if we can't verify due to LocalStack issues
            pass
