#!/usr/bin/env python3
"""Unit tests for notification components."""

import json
import os
from datetime import UTC, datetime
from typing import Any
from unittest.mock import Mock, patch

import pytest

from data_fetcher_core.core import BundleRef
from data_fetcher_core.notifications.sqs_publisher import SqsPublisher


class TestSqsPublisher:
    """Test SqsPublisher implementation."""

    @pytest.fixture
    def bundle_ref(self) -> BundleRef:
        """Create a test bundle reference."""
        return BundleRef(
            primary_url="https://api.example.com/data",
            resources_count=1,
            storage_key="test_bundle_key",
            meta={"test": "data"},
        )

    @pytest.fixture
    def sqs_publisher(self) -> SqsPublisher:
        """Create a SqsPublisher instance for testing."""
        return SqsPublisher(
            queue_url="https://sqs.eu-west-2.amazonaws.com/123456789012/test-queue",
            region="eu-west-2",
        )

    @pytest.fixture
    def localstack_sqs_publisher(self) -> SqsPublisher:
        """Create a SqsPublisher instance for LocalStack testing."""
        import os

        # Set required AWS credentials for LocalStack
        os.environ["AWS_ACCESS_KEY_ID"] = "test"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "test"

        return SqsPublisher(
            queue_url="http://localhost:4566/000000000000/test-queue",
            region="eu-west-2",
            endpoint_url="http://localhost:4566",
        )

    def test_sqs_publisher_creation(self, sqs_publisher: SqsPublisher) -> None:
        """Test SqsPublisher creation."""
        assert (
            sqs_publisher.queue_url
            == "https://sqs.eu-west-2.amazonaws.com/123456789012/test-queue"
        )
        assert sqs_publisher.region == "eu-west-2"
        assert sqs_publisher.endpoint_url is None
        assert sqs_publisher.sqs_client is not None

    def test_sqs_publisher_creation_with_endpoint(
        self, localstack_sqs_publisher: SqsPublisher
    ) -> None:
        """Test SqsPublisher creation with custom endpoint."""
        assert (
            localstack_sqs_publisher.queue_url
            == "http://localhost:4566/000000000000/test-queue"
        )
        assert localstack_sqs_publisher.region == "eu-west-2"
        assert localstack_sqs_publisher.endpoint_url == "http://localhost:4566"
        assert localstack_sqs_publisher.sqs_client is not None

    @pytest.mark.asyncio
    async def test_publish_bundle_completion_success(
        self, sqs_publisher: SqsPublisher, bundle_ref: BundleRef
    ) -> None:
        """Test successful bundle completion notification."""
        metadata = {
            "source": "http_api",
            "run_id": "test_run_123",
            "resources_count": 1,
        }
        recipe_id = "test_recipe"

        # Mock the SQS client
        mock_sqs_client = Mock()
        mock_sqs_client.send_message = Mock()
        sqs_publisher.sqs_client = mock_sqs_client

        # Call the method
        await sqs_publisher.publish_bundle_completion(bundle_ref, metadata, recipe_id)

        # Verify SQS client was called
        mock_sqs_client.send_message.assert_called_once()

        # Get the call arguments
        call_args = mock_sqs_client.send_message.call_args
        assert call_args[1]["QueueUrl"] == sqs_publisher.queue_url

        # Verify message body
        message_body = json.loads(call_args[1]["MessageBody"])
        assert message_body["bundle_id"] == str(bundle_ref.bid)
        assert message_body["recipe_id"] == recipe_id
        assert message_body["primary_url"] == bundle_ref.primary_url
        assert message_body["resources_count"] == bundle_ref.resources_count
        assert message_body["storage_key"] == bundle_ref.storage_key
        assert message_body["metadata"] == metadata
        assert "completion_timestamp" in message_body

        # Verify message attributes
        message_attributes = call_args[1]["MessageAttributes"]
        assert message_attributes["bundle_id"]["StringValue"] == str(bundle_ref.bid)
        assert message_attributes["recipe_id"]["StringValue"] == recipe_id
        assert "completion_timestamp" in message_attributes

    @pytest.mark.asyncio
    async def test_publish_bundle_completion_with_error(
        self, sqs_publisher: SqsPublisher, bundle_ref: BundleRef
    ) -> None:
        """Test bundle completion notification with SQS error."""
        metadata = {"source": "test"}
        recipe_id = "test_recipe"

        # Mock the SQS client to raise an exception
        mock_sqs_client = Mock()
        mock_sqs_client.send_message.side_effect = Exception("SQS error")
        sqs_publisher.sqs_client = mock_sqs_client

        # Call the method and expect it to raise an exception
        with pytest.raises(Exception, match="SQS error"):
            await sqs_publisher.publish_bundle_completion(
                bundle_ref, metadata, recipe_id
            )

    @pytest.mark.asyncio
    async def test_publish_bundle_completion_message_format(
        self, sqs_publisher: SqsPublisher, bundle_ref: BundleRef
    ) -> None:
        """Test that the SQS message has the correct format."""
        metadata = {
            "source": "http_api",
            "run_id": "test_run_123",
            "custom_field": "custom_value",
        }
        recipe_id = "test_recipe"

        # Mock the SQS client
        mock_sqs_client = Mock()
        sqs_publisher.sqs_client = mock_sqs_client

        # Call the method
        await sqs_publisher.publish_bundle_completion(bundle_ref, metadata, recipe_id)

        # Get the message body
        call_args = mock_sqs_client.send_message.call_args
        message_body = json.loads(call_args[1]["MessageBody"])

        # Verify all required fields are present
        required_fields = [
            "bundle_id",
            "recipe_id",
            "primary_url",
            "resources_count",
            "storage_key",
            "completion_timestamp",
            "metadata",
        ]
        for field in required_fields:
            assert field in message_body, f"Missing required field: {field}"

        # Verify field types and values
        assert message_body["bundle_id"] == str(bundle_ref.bid)
        assert message_body["recipe_id"] == recipe_id
        assert message_body["primary_url"] == bundle_ref.primary_url
        assert message_body["resources_count"] == bundle_ref.resources_count
        assert message_body["storage_key"] == bundle_ref.storage_key
        assert message_body["metadata"] == metadata

        # Verify timestamp format
        timestamp = message_body["completion_timestamp"]
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))  # Should not raise

    @pytest.mark.asyncio
    async def test_publish_bundle_completion_message_attributes(
        self, sqs_publisher: SqsPublisher, bundle_ref: BundleRef
    ) -> None:
        """Test that the SQS message attributes are correctly set."""
        metadata = {"source": "test"}
        recipe_id = "test_recipe"

        # Mock the SQS client
        mock_sqs_client = Mock()
        sqs_publisher.sqs_client = mock_sqs_client

        # Call the method
        await sqs_publisher.publish_bundle_completion(bundle_ref, metadata, recipe_id)

        # Get the message attributes
        call_args = mock_sqs_client.send_message.call_args
        message_attributes = call_args[1]["MessageAttributes"]

        # Verify required attributes are present
        required_attributes = ["bundle_id", "recipe_id", "completion_timestamp"]
        for attr in required_attributes:
            assert attr in message_attributes, f"Missing required attribute: {attr}"
            assert message_attributes[attr]["DataType"] == "String"

        # Verify attribute values
        assert message_attributes["bundle_id"]["StringValue"] == str(bundle_ref.bid)
        assert message_attributes["recipe_id"]["StringValue"] == recipe_id

    @pytest.mark.asyncio
    async def test_publish_bundle_completion_with_empty_metadata(
        self, sqs_publisher: SqsPublisher, bundle_ref: BundleRef
    ) -> None:
        """Test bundle completion notification with empty metadata."""
        metadata: dict[str, Any] = {}
        recipe_id = "test_recipe"

        # Mock the SQS client
        mock_sqs_client = Mock()
        sqs_publisher.sqs_client = mock_sqs_client

        # Call the method
        await sqs_publisher.publish_bundle_completion(bundle_ref, metadata, recipe_id)

        # Verify the call was made
        mock_sqs_client.send_message.assert_called_once()

        # Verify message body contains empty metadata
        call_args = mock_sqs_client.send_message.call_args
        message_body = json.loads(call_args[1]["MessageBody"])
        assert message_body["metadata"] == {}

    @pytest.mark.asyncio
    async def test_publish_bundle_completion_with_complex_metadata(
        self, sqs_publisher: SqsPublisher, bundle_ref: BundleRef
    ) -> None:
        """Test bundle completion notification with complex metadata."""
        metadata = {
            "source": "http_api",
            "run_id": "test_run_123",
            "nested": {"field1": "value1", "field2": 42, "field3": [1, 2, 3]},
            "list_field": ["a", "b", "c"],
            "number_field": 123.45,
            "boolean_field": True,
        }
        recipe_id = "test_recipe"

        # Mock the SQS client
        mock_sqs_client = Mock()
        sqs_publisher.sqs_client = mock_sqs_client

        # Call the method
        await sqs_publisher.publish_bundle_completion(bundle_ref, metadata, recipe_id)

        # Verify the call was made
        mock_sqs_client.send_message.assert_called_once()

        # Verify complex metadata is preserved
        call_args = mock_sqs_client.send_message.call_args
        message_body = json.loads(call_args[1]["MessageBody"])
        assert message_body["metadata"] == metadata

    @pytest.mark.asyncio
    async def test_publish_bundle_completion_timestamp_accuracy(
        self, sqs_publisher: SqsPublisher, bundle_ref: BundleRef
    ) -> None:
        """Test that the completion timestamp is accurate."""
        metadata = {"source": "test"}
        recipe_id = "test_recipe"

        # Mock the SQS client
        mock_sqs_client = Mock()
        sqs_publisher.sqs_client = mock_sqs_client

        # Record the time before the call
        before_time = datetime.now(UTC)

        # Call the method
        await sqs_publisher.publish_bundle_completion(bundle_ref, metadata, recipe_id)

        # Record the time after the call
        after_time = datetime.now(UTC)

        # Get the timestamp from the message
        call_args = mock_sqs_client.send_message.call_args
        message_body = json.loads(call_args[1]["MessageBody"])
        message_timestamp = datetime.fromisoformat(
            message_body["completion_timestamp"].replace("Z", "+00:00")
        )

        # Verify the timestamp is within the expected range
        assert before_time <= message_timestamp <= after_time

    def test_sqs_publisher_initialization_with_credentials(self) -> None:
        """Test SqsPublisher initialization with AWS credentials."""
        with patch("boto3.session.Session") as mock_boto_session:
            mock_session = Mock()
            mock_boto_session.return_value = mock_session
            mock_boto_client = mock_session.client
            mock_client = Mock()
            mock_boto_client.return_value = mock_client

            SqsPublisher(
                queue_url="https://sqs.eu-west-2.amazonaws.com/123456789012/test-queue",
                region="eu-west-2",
            )

            # Verify boto3 client was created with correct parameters
            mock_boto_client.assert_called_once_with("sqs", region_name="eu-west-2")

    def test_sqs_publisher_initialization_with_endpoint(self) -> None:
        """Test SqsPublisher initialization with custom endpoint."""
        with (
            patch("boto3.session.Session") as mock_boto_session,
            patch.dict(
                os.environ,
                {
                    "AWS_ACCESS_KEY_ID": "test-key",
                    "AWS_SECRET_ACCESS_KEY": "test-secret",
                },
            ),
        ):
            mock_session = Mock()
            mock_boto_session.return_value = mock_session
            mock_boto_client = mock_session.client
            mock_client = Mock()
            mock_boto_client.return_value = mock_client

            SqsPublisher(
                queue_url="http://localhost:4566/000000000000/test-queue",
                region="eu-west-2",
                endpoint_url="http://localhost:4566",
            )

            # Verify boto3 client was created with custom endpoint
            mock_boto_client.assert_called_once_with(
                "sqs",
                region_name="eu-west-2",
                endpoint_url="http://localhost:4566",
                aws_access_key_id="test-key",
                aws_secret_access_key="test-secret",
            )

    @pytest.mark.asyncio
    async def test_publish_bundle_completion_logging(
        self, sqs_publisher: SqsPublisher, bundle_ref: BundleRef
    ) -> None:
        """Test that bundle completion publishing is properly logged."""
        metadata = {"source": "test"}
        recipe_id = "test_recipe"

        # Mock the SQS client
        mock_sqs_client = Mock()
        sqs_publisher.sqs_client = mock_sqs_client

        # Mock the logger
        with patch(
            "data_fetcher_core.notifications.sqs_publisher.logger"
        ) as mock_logger:
            await sqs_publisher.publish_bundle_completion(
                bundle_ref, metadata, recipe_id
            )

            # Verify success logging
            mock_logger.info.assert_called_once()
            log_call = mock_logger.info.call_args
            assert "bundle_id" in log_call[1]
            assert "recipe_id" in log_call[1]
            assert log_call[1]["bundle_id"] == str(bundle_ref.bid)
            assert log_call[1]["recipe_id"] == recipe_id

    @pytest.mark.asyncio
    async def test_publish_bundle_completion_error_logging(
        self, sqs_publisher: SqsPublisher, bundle_ref: BundleRef
    ) -> None:
        """Test that SQS errors are properly logged."""
        metadata = {"source": "test"}
        recipe_id = "test_recipe"

        # Mock the SQS client to raise an exception
        mock_sqs_client = Mock()
        mock_sqs_client.send_message.side_effect = Exception("SQS connection failed")
        sqs_publisher.sqs_client = mock_sqs_client

        # Mock the logger
        with patch(
            "data_fetcher_core.notifications.sqs_publisher.logger"
        ) as mock_logger:
            with pytest.raises(Exception, match="SQS connection failed"):
                await sqs_publisher.publish_bundle_completion(
                    bundle_ref, metadata, recipe_id
                )

            # Verify error logging
            mock_logger.exception.assert_called_once()
            log_call = mock_logger.exception.call_args
            assert "bundle_id" in log_call[1]
            assert "recipe_id" in log_call[1]
            assert "error" in log_call[1]
            assert log_call[1]["bundle_id"] == str(bundle_ref.bid)
            assert log_call[1]["recipe_id"] == recipe_id
            assert "SQS connection failed" in log_call[1]["error"]
