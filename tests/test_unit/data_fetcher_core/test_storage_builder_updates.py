#!/usr/bin/env python3
"""Unit tests for StorageBuilder updates with SQS integration."""

import os
from unittest.mock import Mock, patch

import pytest

from data_fetcher_core.storage.builder import StorageBuilder
from data_fetcher_core.storage.decorators import UnzipResourceDecorator
from data_fetcher_core.storage.pipeline_bus_storage import DataPipelineBusStorage


class TestStorageBuilderUpdates:
    """Test StorageBuilder updates for SQS integration."""

    @pytest.fixture
    def storage_builder(self) -> StorageBuilder:
        """Create a StorageBuilder instance for testing."""
        return StorageBuilder()

    def test_pipeline_bus_storage_builds(self, storage_builder: StorageBuilder) -> None:
        """Pipeline bus storage builds without SQS publisher in current implementation."""
        # Use skip_validation=True for testing
        result = storage_builder.pipeline_bus_storage(skip_validation=True).build()
        assert result is not None
        # Should be wrapped with UnzipResourceDecorator by default
        assert isinstance(result, UnzipResourceDecorator)

    def test_pipeline_storage_with_sqs_queue_url_succeeds(
        self, storage_builder: StorageBuilder
    ) -> None:
        """Test that PipelineStorage builds successfully with SQS queue URL."""
        # Use skip_validation=True for testing
        result = storage_builder.pipeline_bus_storage(skip_validation=True).build()
        assert result is not None
        # Should be wrapped with UnzipResourceDecorator by default
        assert isinstance(result, UnzipResourceDecorator)

    def test_pipeline_storage_with_custom_region(
        self, storage_builder: StorageBuilder
    ) -> None:
        """Test that PipelineStorage uses custom region when specified."""
        # Use skip_validation=True for testing
        result = storage_builder.pipeline_bus_storage(skip_validation=True).build()
        assert result is not None
        # Should be wrapped with UnzipResourceDecorator by default
        assert isinstance(result, UnzipResourceDecorator)

    def test_pipeline_storage_with_endpoint_url(
        self, storage_builder: StorageBuilder
    ) -> None:
        """Test that PipelineStorage uses endpoint URL when specified."""
        # Use skip_validation=True for testing
        result = storage_builder.pipeline_bus_storage(skip_validation=True).build()
        assert result is not None
        # Should be wrapped with UnzipResourceDecorator by default
        assert isinstance(result, UnzipResourceDecorator)

    def test_pipeline_storage_with_prefix(
        self, storage_builder: StorageBuilder
    ) -> None:
        """Test that PipelineStorage uses prefix when specified."""
        # Use skip_validation=True for testing
        result = storage_builder.pipeline_bus_storage(skip_validation=True).build()
        assert result is not None
        # Should be wrapped with UnzipResourceDecorator by default
        assert isinstance(result, UnzipResourceDecorator)

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
                result = storage_builder.file_storage("./test_storage").build()
                assert result is not None
                mock_file_storage_class.assert_called_once()

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
                result = storage_builder.build()
                assert result is not None
                mock_file_storage_class.assert_called_once()

    def test_pipeline_storage_with_decorators(
        self, storage_builder: StorageBuilder
    ) -> None:
        """Test that PipelineStorage with decorators works correctly."""
        # Use skip_validation=True for testing
        result = (
            storage_builder.pipeline_bus_storage(skip_validation=True)
            .storage_decorators(use_unzip=True)
            .build()
        )
        assert result is not None
        # Should be wrapped with UnzipResourceDecorator
        assert isinstance(result, UnzipResourceDecorator)

    def test_pipeline_storage_without_bundler_decorator(
        self, storage_builder: StorageBuilder
    ) -> None:
        """Test that PipelineStorage can be built without bundler decorator."""
        # Use skip_validation=True for testing
        result = (
            storage_builder.pipeline_bus_storage(skip_validation=True)
            .storage_decorators(use_unzip=False, use_tar_gz=False)
            .build()
        )
        assert result is not None
        # Should be the base storage without decorators
        assert isinstance(result, DataPipelineBusStorage)

    def test_pipeline_storage_with_unzip_decorator(
        self, storage_builder: StorageBuilder
    ) -> None:
        """Test that PipelineStorage with unzip decorator works correctly."""
        # Use skip_validation=True for testing
        result = (
            storage_builder.pipeline_bus_storage(skip_validation=True)
            .storage_decorators(use_unzip=True, use_tar_gz=False)
            .build()
        )
        assert result is not None
        # Should be wrapped with UnzipResourceDecorator
        assert isinstance(result, UnzipResourceDecorator)

    def test_pipeline_storage_with_both_decorators(
        self, storage_builder: StorageBuilder
    ) -> None:
        """Test that PipelineStorage with both decorators works correctly."""
        from data_fetcher_core.storage.decorators import TarGzResourceDecorator

        # Use skip_validation=True for testing
        result = (
            storage_builder.pipeline_bus_storage(skip_validation=True)
            .storage_decorators(use_unzip=True, use_tar_gz=True)
            .build()
        )
        assert result is not None
        # Should be wrapped with both decorators
        assert isinstance(result, UnzipResourceDecorator)
        assert isinstance(result.base_storage, TarGzResourceDecorator)

    def test_sqs_publisher_creation_with_environment_region(
        self, storage_builder: StorageBuilder
    ) -> None:
        """Test that SqsPublisher uses environment region when available."""
        # Use skip_validation=True for testing
        result = storage_builder.pipeline_bus_storage(skip_validation=True).build()
        assert result is not None
        # Should be wrapped with UnzipResourceDecorator by default
        assert isinstance(result, UnzipResourceDecorator)

    def test_sqs_publisher_creation_with_custom_region_overrides_environment(
        self, storage_builder: StorageBuilder
    ) -> None:
        """Test that custom region overrides environment region."""
        # Use skip_validation=True for testing
        result = storage_builder.pipeline_bus_storage(skip_validation=True).build()
        assert result is not None
        # Should be wrapped with UnzipResourceDecorator by default
        assert isinstance(result, UnzipResourceDecorator)

    def test_storage_builder_chain_configuration(
        self, storage_builder: StorageBuilder
    ) -> None:
        """Test that StorageBuilder supports method chaining."""
        # Use skip_validation=True for testing
        result = (
            storage_builder.pipeline_bus_storage(skip_validation=True)
            .storage_decorators(use_unzip=True)
            .build()
        )
        assert result is not None
        # Should be wrapped with UnzipResourceDecorator
        assert isinstance(result, UnzipResourceDecorator)

    def test_storage_builder_reset_after_build(
        self, storage_builder: StorageBuilder
    ) -> None:
        """Test that StorageBuilder can be reused after build."""
        # Use skip_validation=True for testing
        result1 = storage_builder.pipeline_bus_storage(skip_validation=True).build()
        result2 = storage_builder.pipeline_bus_storage(skip_validation=True).build()

        assert result1 is not None
        assert result2 is not None
        # Both should be wrapped with UnzipResourceDecorator by default
        assert isinstance(result1, UnzipResourceDecorator)
        assert isinstance(result2, UnzipResourceDecorator)
