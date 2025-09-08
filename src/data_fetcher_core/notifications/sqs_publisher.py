"""SQS publisher for bundle completion notifications.

This module provides the SqsPublisher class for sending bundle completion
notifications to Amazon SQS queues.
"""

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import boto3
import structlog

if TYPE_CHECKING:
    from data_fetcher_core.core import BundleRef

# Get logger for this module
logger = structlog.get_logger(__name__)


class LocalStackCredentialsError(Exception):
    """Raised when AWS credentials are required for LocalStack SQS endpoint."""

    def __init__(self) -> None:
        """Initialize the error."""
        super().__init__("AWS credentials required for LocalStack SQS endpoint")


@dataclass
class SqsPublisher:
    """SQS publisher for bundle completion notifications.

    This class handles sending bundle completion notifications to Amazon SQS
    queues, with support for LocalStack testing environments.
    """

    queue_url: str
    region: str | None = None
    endpoint_url: str | None = None  # For LocalStack

    def __post_init__(self) -> None:
        """Initialize the SQS client."""
        # Use AWS_REGION environment variable if region is not specified
        if self.region is None:
            self.region = os.getenv("AWS_REGION", "eu-west-2")

        # Create SQS client
        if self.endpoint_url:
            # For LocalStack, we need to set these credentials
            aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
            aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")

            if not aws_access_key_id or not aws_secret_access_key:
                raise LocalStackCredentialsError

            self.sqs_client = boto3.client(
                "sqs",
                region_name=self.region,
                endpoint_url=self.endpoint_url,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
            )
        else:
            self.sqs_client = boto3.client("sqs", region_name=self.region)

    async def publish_bundle_completion(
        self, bundle_ref: "BundleRef", metadata: dict[str, Any], recipe_id: str
    ) -> None:
        """Publish bundle completion notification to SQS.

        Args:
            bundle_ref: Reference to the completed bundle.
            metadata: Additional metadata about the bundle.
            recipe_id: The recipe ID that created the bundle.

        Raises:
            Exception: If the SQS message fails to send.
        """
        message = {
            "bundle_id": str(bundle_ref.bid),
            "recipe_id": recipe_id,
            "primary_url": bundle_ref.primary_url,
            "resources_count": bundle_ref.resources_count,
            "storage_key": bundle_ref.storage_key,
            "completion_timestamp": datetime.now(UTC).isoformat(),
            "metadata": metadata,
        }

        try:
            # Send message to SQS
            response = self.sqs_client.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(message, indent=2),
                MessageAttributes={
                    "bundle_id": {
                        "StringValue": str(bundle_ref.bid),
                        "DataType": "String",
                    },
                    "recipe_id": {"StringValue": recipe_id, "DataType": "String"},
                    "completion_timestamp": {
                        "StringValue": message["completion_timestamp"],
                        "DataType": "String",
                    },
                },
            )

            logger.info(
                "Bundle completion notification sent to SQS",
                bundle_id=str(bundle_ref.bid),
                recipe_id=recipe_id,
                message_id=response.get("MessageId"),
                queue_url=self.queue_url,
            )

        except Exception as e:
            logger.exception(
                "Failed to send bundle completion notification to SQS",
                bundle_id=str(bundle_ref.bid),
                recipe_id=recipe_id,
                queue_url=self.queue_url,
                error=str(e),
            )
            raise
