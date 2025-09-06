"""Base credential provider interface and protocols.

This module defines the base CredentialProvider protocol that all credential providers
must implement for consistent authentication.
"""

from typing import Protocol


class CredentialProvider(Protocol):
    """Interface for credential providers."""

    async def get_credential(self, config_name: str, config_key: str) -> str:
        """Get a credential value for the given configuration and key.

        Args:
            config_name: The configuration name (e.g., "us-fl")
            config_key: The configuration key (e.g., "username", "password", "host")

        Returns:
            The credential value
        """
        ...

    def clear(self) -> None:
        """Clear any cached credentials.

        This method should be overridden by providers that implement caching.
        Default implementation is a no-op.
        """
        ...
