"""Notification services for bundle completion events.

This module provides notification services for sending bundle completion
events to external systems like SQS.
"""

from .sqs_publisher import SqsPublisher

__all__ = [
    "SqsPublisher",
]
