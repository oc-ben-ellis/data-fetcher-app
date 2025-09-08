#!/usr/bin/env python3
"""Unit tests for StorageBuilder updates with SQS integration."""

import os
from unittest.mock import Mock, patch

import pytest

from data_fetcher_core.storage.builder import SqsQueueUrlRequiredError, StorageBuilder


class TestStorageBuilderUpdates:
    """Test StorageBuilder updates for SQS integration."""

    @pytest.fixture
    def storage_builder(self) -> StorageBuilder:
        """Create a StorageBuilder instance for testing."""
        return StorageBuilder()

    def test_pipeline_storage_requires_sqs_queue_url(
        self, storage_builder: StorageBuilder
    ) -> None:
        """Test that PipelineStorage requires OC_SQS_QUEUE_URL environment variable."""
        # Clear environment variables
        with patch.dict(os.environ, {}, clear=True):
            # Try to build PipelineStorage without SQS queue URL
            with pytest.raises(
                SqsQueueUrlRequiredError,
                match="OC_SQS_QUEUE_URL environment variable is required for PipelineStorage",
            ):
                storage_builder.pipeline_storage("test-bucket").build()

    def test_pipeline_storage_with_sqs_queue_url_succeeds(
        self, storage_builder: StorageBuilder
    ) -> None:
        """Test that PipelineStorage builds successfully with SQS queue URL."""
        with patch.dict(
            os.environ,
            {
                "OC_SQS_QUEUE_URL": "https://sqs.eu-west-2.amazonaws.com/123456789012/test-queue"
            },
        ):
            with patch(
                "data_fetcher_core.storage.builder.SqsPublisher"
            ) as mock_sqs_publisher_class:
                mock_sqs_publisher = Mock()
                mock_sqs_publisher_class.return_value = mock_sqs_publisher

                with patch(
                    "data_fetcher_core.storage.PipelineStorage"
                ) as mock_pipeline_storage_class:
                    mock_pipeline_storage = Mock()
                    mock_pipeline_storage_class.return_value = mock_pipeline_storage

                    # Build PipelineStorage
                    result = storage_builder.pipeline_storage("test-bucket").build()

                    # Verify SqsPublisher was created with correct parameters
                    mock_sqs_publisher_class.assert_called_once_with(
                        queue_url="https://sqs.eu-west-2.amazonaws.com/123456789012/test-queue",
                        region="eu-west-2",  # Default region
                        endpoint_url=None,
                    )

                    # Verify PipelineStorage was created with SQS publisher
                    mock_pipeline_storage_class.assert_called_once_with(
                        bucket_name="test-bucket",
                        sqs_publisher=mock_sqs_publisher,
                        prefix="",
                        region="eu-west-2",
                        endpoint_url=None,
                    )

                    # Verify result is the PipelineStorage instance
                    assert result == mock_pipeline_storage

    def test_pipeline_storage_with_custom_region(
        self, storage_builder: StorageBuilder
    ) -> None:
        """Test that PipelineStorage uses custom region when specified."""
        with patch.dict(
            os.environ,
            {
                "OC_SQS_QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"
            },
        ):
            with patch(
                "data_fetcher_core.storage.builder.SqsPublisher"
            ) as mock_sqs_publisher_class:
                mock_sqs_publisher = Mock()
                mock_sqs_publisher_class.return_value = mock_sqs_publisher

                with patch(
                    "data_fetcher_core.storage.PipelineStorage"
                ) as mock_pipeline_storage_class:
                    mock_pipeline_storage = Mock()
                    mock_pipeline_storage_class.return_value = mock_pipeline_storage

                    # Build PipelineStorage with custom region
                    storage_builder.pipeline_storage(
                        "test-bucket", region="us-east-1"
                    ).build()

                    # Verify SqsPublisher was created with custom region
                    mock_sqs_publisher_class.assert_called_once_with(
                        queue_url="https://sqs.us-east-1.amazonaws.com/123456789012/test-queue",
                        region="us-east-1",
                        endpoint_url=None,
                    )

                    # Verify PipelineStorage was created with custom region
                    mock_pipeline_storage_class.assert_called_once_with(
                        bucket_name="test-bucket",
                        sqs_publisher=mock_sqs_publisher,
                        prefix="",
                        region="us-east-1",
                        endpoint_url=None,
                    )

    def test_pipeline_storage_with_endpoint_url(
        self, storage_builder: StorageBuilder
    ) -> None:
        """Test that PipelineStorage uses endpoint URL when specified."""
        with patch.dict(
            os.environ,
            {
                "OC_SQS_QUEUE_URL": "http://localhost:4566/000000000000/test-queue",
                "AWS_ACCESS_KEY_ID": "test-key",
                "AWS_SECRET_ACCESS_KEY": "test-secret",
            },
        ):
            with patch(
                "data_fetcher_core.storage.builder.SqsPublisher"
            ) as mock_sqs_publisher_class:
                mock_sqs_publisher = Mock()
                mock_sqs_publisher_class.return_value = mock_sqs_publisher

                with patch(
                    "data_fetcher_core.storage.PipelineStorage"
                ) as mock_pipeline_storage_class:
                    mock_pipeline_storage = Mock()
                    mock_pipeline_storage_class.return_value = mock_pipeline_storage

                    # Build PipelineStorage with endpoint URL
                    storage_builder.pipeline_storage(
                        "test-bucket", endpoint_url="http://localhost:4566"
                    ).build()

                    # Verify SqsPublisher was created with endpoint URL
                    mock_sqs_publisher_class.assert_called_once_with(
                        queue_url="http://localhost:4566/000000000000/test-queue",
                        region="eu-west-2",
                        endpoint_url="http://localhost:4566",
                    )

                    # Verify PipelineStorage was created with endpoint URL
                    mock_pipeline_storage_class.assert_called_once_with(
                        bucket_name="test-bucket",
                        sqs_publisher=mock_sqs_publisher,
                        prefix="",
                        region="eu-west-2",
                        endpoint_url="http://localhost:4566",
                    )

    def test_pipeline_storage_with_prefix(
        self, storage_builder: StorageBuilder
    ) -> None:
        """Test that PipelineStorage uses prefix when specified."""
        with patch.dict(
            os.environ,
            {
                "OC_SQS_QUEUE_URL": "https://sqs.eu-west-2.amazonaws.com/123456789012/test-queue"
            },
        ):
            with patch(
                "data_fetcher_core.storage.builder.SqsPublisher"
            ) as mock_sqs_publisher_class:
                mock_sqs_publisher = Mock()
                mock_sqs_publisher_class.return_value = mock_sqs_publisher

                with patch(
                    "data_fetcher_core.storage.PipelineStorage"
                ) as mock_pipeline_storage_class:
                    mock_pipeline_storage = Mock()
                    mock_pipeline_storage_class.return_value = mock_pipeline_storage

                    # Build PipelineStorage with prefix
                    storage_builder.pipeline_storage(
                        "test-bucket", prefix="test-prefix/"
                    ).build()

                    # Verify PipelineStorage was created with prefix
                    mock_pipeline_storage_class.assert_called_once_with(
                        bucket_name="test-bucket",
                        sqs_publisher=mock_sqs_publisher,
                        prefix="test-prefix/",
                        region="eu-west-2",
                        endpoint_url=None,
                    )

    def test_file_storage_builds_without_sqs_requirements(
        self, storage_builder: StorageBuilder
    ) -> None:
        """Test that FileStorage builds without SQS requirements."""
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "data_fetcher_core.storage.FileStorage"
            ) as mock_file_storage_class:
                mock_file_storage = Mock()
                mock_file_storage_class.return_value = mock_file_storage

                # Build FileStorage
                result = storage_builder.file_storage("./test_storage").build()

                # Verify FileStorage was created
                mock_file_storage_class.assert_called_once_with("./test_storage")

                # Verify result is the FileStorage instance
                assert result == mock_file_storage

    def test_fallback_file_storage_builds_without_sqs_requirements(
        self, storage_builder: StorageBuilder
    ) -> None:
        """Test that fallback FileStorage builds without SQS requirements."""
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "data_fetcher_core.storage.FileStorage"
            ) as mock_file_storage_class:
                mock_file_storage = Mock()
                mock_file_storage_class.return_value = mock_file_storage

                # Build without specifying storage type (should fallback to FileStorage)
                result = storage_builder.build()

                # Verify FileStorage was created with default path
                mock_file_storage_class.assert_called_once_with("tmp/file_storage")

                # Verify result is the FileStorage instance
                assert result == mock_file_storage

    def test_pipeline_storage_with_decorators(
        self, storage_builder: StorageBuilder
    ) -> None:
        """Test that PipelineStorage with decorators works correctly."""
        with patch.dict(
            os.environ,
            {
                "OC_SQS_QUEUE_URL": "https://sqs.eu-west-2.amazonaws.com/123456789012/test-queue"
            },
        ):
            with patch(
                "data_fetcher_core.storage.builder.SqsPublisher"
            ) as mock_sqs_publisher_class:
                mock_sqs_publisher = Mock()
                mock_sqs_publisher_class.return_value = mock_sqs_publisher

                with patch(
                    "data_fetcher_core.storage.PipelineStorage"
                ) as mock_pipeline_storage_class:
                    mock_pipeline_storage = Mock()
                    mock_pipeline_storage_class.return_value = mock_pipeline_storage

                    # Build PipelineStorage without bundler decorator
                    result = (
                        storage_builder.pipeline_storage("test-bucket")
                        .storage_decorators(use_unzip=False)
                        .build()
                    )

                    # Verify PipelineStorage was created
                    mock_pipeline_storage_class.assert_called_once()

                    # Verify result is the base storage (no decorators applied)
                    assert result == mock_pipeline_storage

    def test_pipeline_storage_without_bundler_decorator(
        self, storage_builder: StorageBuilder
    ) -> None:
        """Test that PipelineStorage can be built without bundler decorator."""
        with patch.dict(
            os.environ,
            {
                "OC_SQS_QUEUE_URL": "https://sqs.eu-west-2.amazonaws.com/123456789012/test-queue"
            },
        ):
            with patch(
                "data_fetcher_core.storage.builder.SqsPublisher"
            ) as mock_sqs_publisher_class:
                mock_sqs_publisher = Mock()
                mock_sqs_publisher_class.return_value = mock_sqs_publisher

                with patch(
                    "data_fetcher_core.storage.PipelineStorage"
                ) as mock_pipeline_storage_class:
                    mock_pipeline_storage = Mock()
                    mock_pipeline_storage_class.return_value = mock_pipeline_storage

                    # Build PipelineStorage without bundler decorator
                    result = (
                        storage_builder.pipeline_storage("test-bucket")
                        .storage_decorators(use_unzip=False)
                        .build()
                    )

                    # Verify PipelineStorage was created
                    mock_pipeline_storage_class.assert_called_once()

                    # Verify result is the PipelineStorage instance
                    assert result == mock_pipeline_storage

    def test_pipeline_storage_with_unzip_decorator(
        self, storage_builder: StorageBuilder
    ) -> None:
        """Test that PipelineStorage with unzip decorator works correctly."""
        with patch.dict(
            os.environ,
            {
                "OC_SQS_QUEUE_URL": "https://sqs.eu-west-2.amazonaws.com/123456789012/test-queue"
            },
        ):
            with patch(
                "data_fetcher_core.storage.builder.SqsPublisher"
            ) as mock_sqs_publisher_class:
                mock_sqs_publisher = Mock()
                mock_sqs_publisher_class.return_value = mock_sqs_publisher

                with patch(
                    "data_fetcher_core.storage.PipelineStorage"
                ) as mock_pipeline_storage_class:
                    mock_pipeline_storage = Mock()
                    mock_pipeline_storage_class.return_value = mock_pipeline_storage

                    with patch(
                        "data_fetcher_core.storage.UnzipResourceDecorator"
                    ) as mock_unzip_class:
                        mock_unzip = Mock()
                        mock_unzip_class.return_value = mock_unzip

                        # Build PipelineStorage with unzip decorator
                        result = (
                            storage_builder.pipeline_storage("test-bucket")
                            .storage_decorators(use_unzip=True)
                            .build()
                        )

                        # Verify PipelineStorage was created
                        mock_pipeline_storage_class.assert_called_once()

                        # Verify UnzipResourceDecorator was applied
                        mock_unzip_class.assert_called_once_with(mock_pipeline_storage)

                        # Verify result is the decorated storage
                        assert result == mock_unzip

    def test_pipeline_storage_with_both_decorators(
        self, storage_builder: StorageBuilder
    ) -> None:
        """Test that PipelineStorage with both decorators works correctly."""
        with patch.dict(
            os.environ,
            {
                "OC_SQS_QUEUE_URL": "https://sqs.eu-west-2.amazonaws.com/123456789012/test-queue"
            },
        ):
            with patch(
                "data_fetcher_core.storage.builder.SqsPublisher"
            ) as mock_sqs_publisher_class:
                mock_sqs_publisher = Mock()
                mock_sqs_publisher_class.return_value = mock_sqs_publisher

                with patch(
                    "data_fetcher_core.storage.PipelineStorage"
                ) as mock_pipeline_storage_class:
                    mock_pipeline_storage = Mock()
                    mock_pipeline_storage_class.return_value = mock_pipeline_storage

                    with patch(
                        "data_fetcher_core.storage.UnzipResourceDecorator"
                    ) as mock_unzip_class:
                        mock_unzip = Mock()
                        mock_unzip_class.return_value = mock_unzip

                        # Build PipelineStorage with unzip decorator
                        result = (
                            storage_builder.pipeline_storage("test-bucket")
                            .storage_decorators(use_unzip=True)
                            .build()
                        )

                        # Verify PipelineStorage was created
                        mock_pipeline_storage_class.assert_called_once()

                        # Verify UnzipResourceDecorator was applied
                        mock_unzip_class.assert_called_once_with(mock_pipeline_storage)

                        # Verify result is the unzip decorated storage
                        assert result == mock_unzip

    def test_sqs_publisher_creation_with_environment_region(
        self, storage_builder: StorageBuilder
    ) -> None:
        """Test that SqsPublisher uses environment region when available."""
        with patch.dict(
            os.environ,
            {
                "OC_SQS_QUEUE_URL": "https://sqs.us-west-2.amazonaws.com/123456789012/test-queue",
                "AWS_REGION": "us-west-2",
            },
        ):
            with patch(
                "data_fetcher_core.storage.builder.SqsPublisher"
            ) as mock_sqs_publisher_class:
                mock_sqs_publisher = Mock()
                mock_sqs_publisher_class.return_value = mock_sqs_publisher

                with patch(
                    "data_fetcher_core.storage.PipelineStorage"
                ) as mock_pipeline_storage_class:
                    mock_pipeline_storage = Mock()
                    mock_pipeline_storage_class.return_value = mock_pipeline_storage

                    # Build PipelineStorage
                    storage_builder.pipeline_storage("test-bucket").build()

                    # Verify SqsPublisher was created with environment region
                    mock_sqs_publisher_class.assert_called_once_with(
                        queue_url="https://sqs.us-west-2.amazonaws.com/123456789012/test-queue",
                        region="us-west-2",  # From AWS_REGION environment variable
                        endpoint_url=None,
                    )

    def test_sqs_publisher_creation_with_custom_region_overrides_environment(
        self, storage_builder: StorageBuilder
    ) -> None:
        """Test that custom region overrides environment region."""
        with patch.dict(
            os.environ,
            {
                "OC_SQS_QUEUE_URL": "https://sqs.us-west-2.amazonaws.com/123456789012/test-queue",
                "AWS_REGION": "us-west-2",
            },
        ):
            with patch(
                "data_fetcher_core.storage.builder.SqsPublisher"
            ) as mock_sqs_publisher_class:
                mock_sqs_publisher = Mock()
                mock_sqs_publisher_class.return_value = mock_sqs_publisher

                with patch(
                    "data_fetcher_core.storage.PipelineStorage"
                ) as mock_pipeline_storage_class:
                    mock_pipeline_storage = Mock()
                    mock_pipeline_storage_class.return_value = mock_pipeline_storage

                    # Build PipelineStorage with custom region
                    storage_builder.pipeline_storage(
                        "test-bucket", region="us-east-1"
                    ).build()

                    # Verify SqsPublisher was created with custom region
                    mock_sqs_publisher_class.assert_called_once_with(
                        queue_url="https://sqs.us-west-2.amazonaws.com/123456789012/test-queue",
                        region="us-east-1",  # Custom region overrides environment
                        endpoint_url=None,
                    )

    def test_storage_builder_chain_configuration(
        self, storage_builder: StorageBuilder
    ) -> None:
        """Test that StorageBuilder supports method chaining."""
        with patch.dict(
            os.environ,
            {
                "OC_SQS_QUEUE_URL": "https://sqs.eu-west-2.amazonaws.com/123456789012/test-queue"
            },
        ):
            # Test method chaining
            (
                storage_builder.pipeline_storage(
                    "test-bucket", prefix="test/", region="us-east-1"
                )
                .storage_decorators(use_unzip=True)
                .build()
            )

            # Verify the builder was configured correctly
            assert storage_builder._s3_bucket == "test-bucket"
            assert storage_builder._s3_prefix == "test/"
            assert storage_builder._s3_region == "us-east-1"
            assert storage_builder._use_unzip is True

    def test_storage_builder_reset_after_build(
        self, storage_builder: StorageBuilder
    ) -> None:
        """Test that StorageBuilder can be reused after build."""
        with patch.dict(
            os.environ,
            {
                "OC_SQS_QUEUE_URL": "https://sqs.eu-west-2.amazonaws.com/123456789012/test-queue"
            },
        ):
            with patch(
                "data_fetcher_core.storage.builder.SqsPublisher"
            ) as mock_sqs_publisher_class:
                mock_sqs_publisher = Mock()
                mock_sqs_publisher_class.return_value = mock_sqs_publisher

                with patch(
                    "data_fetcher_core.storage.PipelineStorage"
                ) as mock_pipeline_storage_class:
                    mock_pipeline_storage = Mock()
                    mock_pipeline_storage_class.return_value = mock_pipeline_storage

                    # First build
                    result1 = storage_builder.pipeline_storage("bucket1").build()

                    # Second build with different configuration
                    result2 = storage_builder.pipeline_storage(
                        "bucket2", prefix="prefix2/"
                    ).build()

                    # Verify both builds succeeded
                    assert result1 == mock_pipeline_storage
                    assert result2 == mock_pipeline_storage

                    # Verify the second build used the new configuration
                    assert mock_pipeline_storage_class.call_count == 2
                    second_call = mock_pipeline_storage_class.call_args_list[1]
                    assert second_call[1]["bucket_name"] == "bucket2"
                    assert second_call[1]["prefix"] == "prefix2/"
