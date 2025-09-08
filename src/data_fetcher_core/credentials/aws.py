"""AWS Secrets Manager credential provider.

This module provides the AWSSecretsCredentialProvider class for retrieving
credentials from AWS Secrets Manager, including SFTP and API credentials.
"""

import json
import os

import boto3
from botocore.exceptions import ClientError


class AWSSecretsCredentialProvider:
    """Default credential provider that fetches credentials from AWS Secrets Manager."""

    def __init__(
        self, region: str | None = None, endpoint_url: str | None = None
    ) -> None:
        """Initialize the AWS Secrets credential provider.

        Args:
            region: AWS region to use for Secrets Manager. Defaults to AWS_REGION env var or eu-west-2.
            endpoint_url: Optional custom endpoint URL for testing or local development.
        """
        # Use AWS_REGION environment variable if region is not specified
        if region is None:
            region = os.getenv("AWS_REGION", "eu-west-2")
        self.region = region
        self.endpoint_url = endpoint_url
        self._secrets_cache: dict[str, str] = {}

    async def get_credential(self, config_name: str, config_key: str) -> str:
        """Get credential from AWS Secrets Manager.

        The secret name is expected to be in the format: {config_name}-sftp-credentials
        The secret should contain keys like: username, password, host
        """
        # Create secret name
        secret_name = f"{config_name}-sftp-credentials"

        # Check cache first
        cache_key = f"{secret_name}:{config_key}"
        if cache_key in self._secrets_cache:
            return self._secrets_cache[cache_key]

        # Create Secrets Manager client, respecting AWS profile overrides
        profile_name = os.getenv(
            "OC_CREDENTIAL_PROVIDER_AWS_PROFILE", os.getenv("AWS_PROFILE")
        )
        if profile_name:
            session = boto3.session.Session(profile_name=profile_name)
        else:
            session = boto3.session.Session()
        client_kwargs = {"service_name": "secretsmanager", "region_name": self.region}
        if self.endpoint_url:
            client_kwargs["endpoint_url"] = self.endpoint_url
        client = session.client(**client_kwargs)  # type: ignore[call-overload]

        def _raise_key_not_found() -> None:
            """Raise error when key is not found in secret."""
            raise ValueError(  # noqa: TRY003
                f"Key '{config_key}' not found in secret '{secret_name}'"
            )

        def _raise_invalid_type() -> None:
            """Raise error when credential value is not a string."""
            raise TypeError(  # noqa: TRY003
                f"Credential value for key '{config_key}' is not a string: {type(credential_value)}"
            )

        try:
            # Get secret value
            response = client.get_secret_value(SecretId=secret_name)

            # Parse secret (assuming JSON format)
            secret_data = json.loads(response["SecretString"])

            # Get the specific key
            if config_key not in secret_data:
                _raise_key_not_found()

            credential_value = secret_data[config_key]

            # Ensure the value is a string
            if not isinstance(credential_value, str):
                _raise_invalid_type()

            # Cache the result
            self._secrets_cache[cache_key] = credential_value

            return credential_value  # type: ignore[no-any-return]  # noqa: TRY300

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "ResourceNotFoundException":
                raise ValueError(  # noqa: TRY003
                    f"Secret '{secret_name}' not found"
                ) from e
            if error_code == "AccessDeniedException":
                raise ValueError(  # noqa: TRY003
                    f"Access denied to secret '{secret_name}'"
                ) from e
            raise ValueError(f"AWS Secrets Manager error: {e}") from e  # noqa: TRY003
        except json.JSONDecodeError as e:
            raise ValueError(  # noqa: TRY003
                f"Secret '{secret_name}' not valid JSON"
            ) from e
        except Exception as e:
            raise ValueError(  # noqa: TRY003
                f"Unexpected error accessing secret '{secret_name}': {e}"
            ) from e

    def clear(self) -> None:
        """Clear the secrets cache."""
        self._secrets_cache.clear()
