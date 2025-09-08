"""Authentication and authorization handling.

This module provides authentication classes and utilities for various protocols,
including HTTP authentication headers and SFTP key management.
"""

import asyncio
import base64
from dataclasses import dataclass
from typing import Protocol

import httpx
import structlog

from data_fetcher_core.credentials import CredentialProvider

# Get logger for this module
logger = structlog.get_logger(__name__)


class AuthenticationMechanism(Protocol):
    """Interface for authentication mechanisms."""

    async def authenticate_request(
        self, request_headers: dict[str, str], credential_provider: CredentialProvider
    ) -> dict[str, str]:
        """Add authentication headers to the request.

        Args:
            request_headers: The existing request headers
            credential_provider: The credential provider to use for authentication

        Returns:
            Updated headers with authentication information
        """
        ...


@dataclass
class OAuthAuthenticationMechanism:
    """OAuth client credentials authentication mechanism."""

    token_url: str
    config_name: str
    grant_type: str = "client_credentials"

    def __post_init__(self) -> None:
        """Initialize the OAuth authentication mechanism state."""
        self._access_token: str | None = None
        self._token_expires_at: float | None = None

    async def authenticate_request(
        self, request_headers: dict[str, str], credential_provider: CredentialProvider
    ) -> dict[str, str]:
        """Add OAuth Bearer token to request headers."""
        await self._ensure_valid_token(credential_provider)

        if self._access_token:
            request_headers["Authorization"] = f"Bearer {self._access_token}"

        return request_headers

    async def _ensure_valid_token(
        self, credential_provider: CredentialProvider
    ) -> None:
        """Ensure we have a valid OAuth access token."""
        # Check if we need to refresh the token
        if (
            self._access_token
            and self._token_expires_at
            and asyncio.get_event_loop().time() < self._token_expires_at
        ):
            return  # Token is still valid

        await self._fetch_new_token(credential_provider)

    async def _fetch_new_token(self, credential_provider: CredentialProvider) -> None:
        """Fetch a new OAuth access token."""
        try:
            # Get credentials from provider
            consumer_key = await credential_provider.get_credential(
                self.config_name, "consumer_key"
            )
            consumer_secret = await credential_provider.get_credential(
                self.config_name, "consumer_secret"
            )

            if not consumer_key or not consumer_secret:
                logger.exception(
                    "Missing OAuth credentials", config_name=self.config_name
                )
                return

            # Create authorization header
            credentials = f"{consumer_key}:{consumer_secret}"
            auth_header = f"Basic {base64.b64encode(credentials.encode()).decode()}"

            # Make token request using httpx directly
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_url,
                    headers={
                        "Authorization": auth_header,
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={"grant_type": self.grant_type},
                )

                HTTP_OK = 200  # noqa: N806
                if response.status_code == HTTP_OK:
                    token_data = response.json()
                    self._access_token = token_data.get("access_token")

                    # Set expiration (default to 1 hour if not provided)
                    expires_in = token_data.get("expires_in", 3600)
                    self._token_expires_at = (
                        asyncio.get_event_loop().time() + expires_in
                    )

                    logger.info(
                        "Successfully obtained OAuth access token",
                        config_name=self.config_name,
                    )
                else:
                    logger.exception(
                        "Failed to obtain OAuth token",
                        config_name=self.config_name,
                        status_code=response.status_code,
                    )

        except Exception as e:
            logger.exception(
                "Error fetching OAuth token",
                config_name=self.config_name,
                error=str(e),
            )


@dataclass
class BasicAuthenticationMechanism:
    """Basic authentication mechanism."""

    config_name: str
    username_key: str = "username"
    password_key: str = "password"  # noqa: S105

    def __post_init__(self) -> None:
        """Initialize the basic authentication mechanism state."""
        self._cached_credentials: tuple[str, str] | None = None

    async def authenticate_request(
        self, request_headers: dict[str, str], credential_provider: CredentialProvider
    ) -> dict[str, str]:
        """Add Basic authentication to request headers."""
        if not self._cached_credentials:
            username = await credential_provider.get_credential(
                self.config_name, self.username_key
            )
            password = await credential_provider.get_credential(
                self.config_name, self.password_key
            )
            self._cached_credentials = (username, password)

        username, password = self._cached_credentials
        credentials = f"{username}:{password}"
        auth_header = f"Basic {base64.b64encode(credentials.encode()).decode()}"
        request_headers["Authorization"] = auth_header

        return request_headers


@dataclass
class BearerTokenAuthenticationMechanism:
    """Bearer token authentication mechanism."""

    config_name: str
    token_key: str = "token"  # noqa: S105

    def __post_init__(self) -> None:
        """Initialize the bearer token authentication mechanism state."""
        self._cached_token: str | None = None

    async def authenticate_request(
        self, request_headers: dict[str, str], credential_provider: CredentialProvider
    ) -> dict[str, str]:
        """Add Bearer token to request headers."""
        if not self._cached_token:
            self._cached_token = await credential_provider.get_credential(
                self.config_name, self.token_key
            )

        if self._cached_token:
            request_headers["Authorization"] = f"Bearer {self._cached_token}"

        return request_headers


@dataclass
class NoAuthenticationMechanism:
    """No authentication mechanism - passes through headers unchanged."""

    async def authenticate_request(
        self, request_headers: dict[str, str], credential_provider: CredentialProvider
    ) -> dict[str, str]:
        """Return headers unchanged."""
        _ = credential_provider  # Unused parameter for Protocol compliance
        return request_headers
