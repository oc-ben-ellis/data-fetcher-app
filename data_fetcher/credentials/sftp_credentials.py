"""SFTP credential management and authentication.

This module provides SFTP credential classes and wrappers for managing
authentication to SFTP servers, including key-based and password authentication.
"""

from dataclasses import dataclass

from .base import CredentialProvider


@dataclass
class SftpCredentials:
    """SFTP credentials container."""

    host: str
    username: str
    password: str
    port: int = 22


class SftpCredentialsWrapper:
    """Wrapper that provides SFTP credentials using a credential provider."""

    def __init__(
        self, config_name: str, credential_provider: CredentialProvider | None = None
    ):
        """Initialize the SFTP credentials wrapper.

        Args:
            config_name: Name of the configuration to use for credentials.
            credential_provider: Optional credential provider instance.
        """
        self.config_name = config_name
        self.credential_provider = credential_provider
        self._cached_credentials: SftpCredentials | None = None

    async def get_credentials(self) -> SftpCredentials:
        """Get SFTP credentials, using cache if available."""
        if self._cached_credentials is None:
            # Check if credential provider is available
            if self.credential_provider is None:
                raise RuntimeError("No credential provider configured")

            # Get credentials from provider
            host = await self.credential_provider.get_credential(
                self.config_name, "host"
            )
            username = await self.credential_provider.get_credential(
                self.config_name, "username"
            )
            password = await self.credential_provider.get_credential(
                self.config_name, "password"
            )

            # Try to get port, default to 22 if not provided
            try:
                port_str = await self.credential_provider.get_credential(
                    self.config_name, "port"
                )
                port = int(port_str)
            except (ValueError, TypeError, Exception):
                port = 22

            self._cached_credentials = SftpCredentials(
                host=host, username=username, password=password, port=port
            )

        return self._cached_credentials

    def clear(self) -> None:
        """Clear the cached credentials."""
        self._cached_credentials = None
