"""Base credential provider interface and abstract classes.

This module defines the base CredentialProvider interface and abstract classes
that all credential providers must implement for consistent authentication.
"""

from abc import ABC, abstractmethod


class CredentialProvider(ABC):
    """Interface for credential providers."""

    @abstractmethod
    async def get_credential(self, config_name: str, config_key: str) -> str:
        """Get a credential value for the given configuration and key.

        Args:
            config_name: The configuration name (e.g., "us-fl")
            config_key: The configuration key (e.g., "username", "password", "host")

        Returns:
            The credential value
        """

    def clear(self) -> None:
        """Clear any cached credentials.

        This method should be overridden by providers that implement caching.
        Default implementation is a no-op.
        """
        # Default implementation is a no-op for providers that don't cache
        return
