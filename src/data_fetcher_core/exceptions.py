"""Standardized exceptions for the data fetcher core module.

This module provides consistent exception types and error handling patterns
across the core framework components.
"""


class DataFetcherError(Exception):
    """Base exception for all data fetcher errors."""

    def __init__(self, message: str, error_code: str | None = None) -> None:
        """Initialize the error with a message and optional error code.

        Args:
            message: Human-readable error message.
            error_code: Optional error code for programmatic handling.
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class ConfigurationError(DataFetcherError):
    """Raised when there are configuration-related errors."""

    def __init__(self, message: str, component: str | None = None) -> None:
        """Initialize configuration error.

        Args:
            message: Error message describing the configuration issue.
            component: Optional component name where the error occurred.
        """
        super().__init__(message, "CONFIG_ERROR")
        self.component = component


class ValidationError(DataFetcherError):
    """Raised when data validation fails."""

    def __init__(self, message: str, field: str | None = None) -> None:
        """Initialize validation error.

        Args:
            message: Error message describing the validation failure.
            field: Optional field name that failed validation.
        """
        super().__init__(message, "VALIDATION_ERROR")
        self.field = field


class ResourceError(DataFetcherError):
    """Raised when resource-related operations fail."""

    def __init__(self, message: str, resource_url: str | None = None) -> None:
        """Initialize resource error.

        Args:
            message: Error message describing the resource issue.
            resource_url: Optional URL of the resource that caused the error.
        """
        super().__init__(message, "RESOURCE_ERROR")
        self.resource_url = resource_url


class StorageError(DataFetcherError):
    """Raised when storage operations fail."""

    def __init__(self, message: str, storage_type: str | None = None) -> None:
        """Initialize storage error.

        Args:
            message: Error message describing the storage issue.
            storage_type: Optional type of storage that caused the error.
        """
        super().__init__(message, "STORAGE_ERROR")
        self.storage_type = storage_type


class NetworkError(DataFetcherError):
    """Raised when network-related operations fail."""

    def __init__(self, message: str, url: str | None = None) -> None:
        """Initialize network error.

        Args:
            message: Error message describing the network issue.
            url: Optional URL that caused the network error.
        """
        super().__init__(message, "NETWORK_ERROR")
        self.url = url


class RetryableError(DataFetcherError):
    """Raised when an operation fails but can be retried."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        """Initialize retryable error.

        Args:
            message: Error message describing the retryable failure.
            retry_after: Optional seconds to wait before retrying.
        """
        super().__init__(message, "RETRYABLE_ERROR")
        self.retry_after = retry_after


class FatalError(DataFetcherError):
    """Raised when an operation fails and cannot be retried."""

    def __init__(self, message: str, component: str | None = None) -> None:
        """Initialize fatal error.

        Args:
            message: Error message describing the fatal failure.
            component: Optional component where the fatal error occurred.
        """
        super().__init__(message, "FATAL_ERROR")
        self.component = component


class BundleRefValidationError(ValidationError):
    """Raised when BundleRef data validation fails."""

    def __init__(self, message: str) -> None:
        """Initialize the error with a specific message.

        Args:
            message: Description of the validation failure.
        """
        super().__init__(message, "bundle_ref")
