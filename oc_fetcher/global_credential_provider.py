"""Application credential provider management.

This module manages the application-wide default credential provider instance,
allowing components to access credentials without explicit configuration.

Sets the default credential provider.

Environment Variables:
    OC_CREDENTIAL_PROVIDER_TYPE: Provider type to use ("aws" or "environment"). Default: "aws"
    OC_CREDENTIAL_PROVIDER_AWS_REGION: AWS region for Secrets Manager. Default: "eu-west-2"
    AWS_REGION: Standard AWS region environment variable (takes precedence over OC_CREDENTIAL_PROVIDER_AWS_REGION)
    OC_CREDENTIAL_PROVIDER_AWS_ENDPOINT_URL: AWS endpoint URL for LocalStack testing. Default: None
    OC_CREDENTIAL_PROVIDER_ENV_PREFIX: Environment variable prefix for environment provider. Default: "OC_CREDENTIAL_"
"""

import os

from .credentials import (
    AWSSecretsCredentialProvider,
    CredentialProvider,
    EnvironmentCredentialProvider,
)

# Default credential provider instance
_default_credential_provider: CredentialProvider | None = None


def set_default_credential_provider(provider: CredentialProvider) -> None:
    """Set the default credential provider."""
    global _default_credential_provider
    _default_credential_provider = provider


def clear_default_credential_provider() -> None:
    """Clear the default credential provider, forcing reconfiguration on next access."""
    global _default_credential_provider
    _default_credential_provider = None


def get_default_credential_provider() -> CredentialProvider:
    """Get the default application credential provider."""
    global _default_credential_provider
    if _default_credential_provider is None:
        # Create default provider based on environment configuration
        configure_global_credential_provider()
        # After configuration, it should not be None
        if _default_credential_provider is None:
            raise RuntimeError("Failed to configure default credential provider")
    return _default_credential_provider


def _get_aws_region() -> str:
    """Get AWS region with proper precedence: AWS_REGION > OC_CREDENTIAL_PROVIDER_AWS_REGION > default."""
    return (
        os.getenv("OC_CREDENTIAL_PROVIDER_AWS_REGION")
        or os.getenv("AWS_REGION", "eu-west-2")
        or "eu-west-2"
    )


def configure_global_credential_provider() -> None:
    """Configure the application credential provider with environment variables and sensible defaults."""
    # Get provider type
    provider_type = os.getenv("OC_CREDENTIAL_PROVIDER_TYPE", "aws").lower()

    provider: CredentialProvider
    if provider_type == "aws":
        # AWS Secrets Manager provider
        region = _get_aws_region()
        endpoint_url = os.getenv("OC_CREDENTIAL_PROVIDER_AWS_ENDPOINT_URL")
        provider = AWSSecretsCredentialProvider(
            region=region, endpoint_url=endpoint_url
        )
    elif provider_type == "environment":
        # Environment variable provider
        prefix = os.getenv("OC_CREDENTIAL_PROVIDER_ENV_PREFIX", "OC_CREDENTIAL_")
        provider = EnvironmentCredentialProvider(prefix=prefix)
    else:
        raise ValueError(f"Unknown credential provider type: {provider_type}")

    set_default_credential_provider(provider)


# Configure global credential provider when this module is imported
configure_global_credential_provider()


def configure_application_credential_provider() -> None:
    """Alias: Configure application credential provider.

    This is an alias for ``configure_global_credential_provider`` to emphasize
    that this configuration is application-wide rather than per-fetcher.
    """
    configure_global_credential_provider()
