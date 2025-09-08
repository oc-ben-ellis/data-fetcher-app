"""Credential provider factory functions.

This module provides factory functions for creating credential provider instances
including AWS Secrets Manager and environment variable providers.
"""

import os

from .aws import AWSSecretsCredentialProvider
from .base import CredentialProvider
from .environment import EnvironmentCredentialProvider


class UnknownProviderTypeError(ValueError):
    """Raised when an unknown credential provider type is specified."""

    def __init__(self, provider_type: str) -> None:
        """Initialize the unknown provider type error.

        Args:
            provider_type: The unknown provider type that was specified.
        """
        super().__init__(f"Unknown provider type: {provider_type}")
        self.provider_type = provider_type


def _get_aws_region() -> str:
    """Get AWS region with proper precedence: AWS_REGION > OC_*_REGION > default."""
    return (
        os.getenv("AWS_REGION", "eu-west-2")
        or os.getenv("OC_CREDENTIAL_PROVIDER_AWS_REGION", "eu-west-2")
        or os.getenv("OC_S3_REGION", "eu-west-2")
        or "eu-west-2"
    )


def create_credential_provider(
    provider_type: str | None = None,
    aws_region: str | None = None,
    aws_endpoint_url: str | None = None,
    env_prefix: str | None = None,
) -> CredentialProvider:
    """Create a credential provider instance.

    Args:
        provider_type: Provider type to use ("aws" or "environment").
                      If None, uses OC_CREDENTIAL_PROVIDER_TYPE env var or "aws".
        aws_region: AWS region for Secrets Manager.
                   If None, uses AWS_REGION or OC_CREDENTIAL_PROVIDER_AWS_REGION env vars.
        aws_endpoint_url: AWS endpoint URL for LocalStack testing.
                         If None, uses OC_CREDENTIAL_PROVIDER_AWS_ENDPOINT_URL env var.
        env_prefix: Environment variable prefix for environment provider.
                   If None, uses OC_CREDENTIAL_PROVIDER_ENV_PREFIX env var or "OC_CREDENTIAL_".

    Returns:
        Configured credential provider instance.
    """
    # Get provider type
    if provider_type is None:
        provider_type = os.getenv("OC_CREDENTIAL_PROVIDER_TYPE", "aws").lower()
    else:
        provider_type = provider_type.lower()

    if provider_type == "aws":
        # AWS Secrets Manager provider
        if aws_region is None:
            aws_region = _get_aws_region()
        if aws_endpoint_url is None:
            aws_endpoint_url = os.getenv("OC_CREDENTIAL_PROVIDER_AWS_ENDPOINT_URL")

        return AWSSecretsCredentialProvider(
            region=aws_region, endpoint_url=aws_endpoint_url
        )
    if provider_type == "environment":
        # Environment variable provider
        if env_prefix is None:
            env_prefix = os.getenv(
                "OC_CREDENTIAL_PROVIDER_ENV_PREFIX", "OC_CREDENTIAL_"
            )

        return EnvironmentCredentialProvider(prefix=env_prefix)
    raise UnknownProviderTypeError(provider_type)
