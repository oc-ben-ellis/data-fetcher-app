#!/usr/bin/env python3
"""Credential provider usage example for OC Fetcher.

This example demonstrates how to use different credential providers and
the new command line flag functionality.
"""

import asyncio
import contextlib
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def credential_provider_example() -> None:
    """Demonstrate different credential providers."""
    from data_fetcher_app.config.credential_provider import (  # type: ignore[import-untyped]
        configure_application_credential_provider,
        get_default_credential_provider,
    )
    from data_fetcher_core.credentials import (
        EnvironmentCredentialProvider,
    )

    # Example 1: AWS Secrets Manager Provider (default)
    try:
        # Configure AWS provider
        os.environ["OC_CREDENTIAL_PROVIDER_TYPE"] = "aws"
        configure_application_credential_provider()

        provider = get_default_credential_provider()

        # Note: This will fail without proper AWS credentials, but that's expected

    except Exception:
        pass

    # Example 2: Environment Variable Provider
    try:
        # Configure environment provider
        os.environ["OC_CREDENTIAL_PROVIDER_TYPE"] = "environment"
        configure_application_credential_provider()

        provider = get_default_credential_provider()

        # Test with a missing environment variable to show error handling
        with contextlib.suppress(ValueError):
            await provider.get_credential("test-config", "username")

    except Exception:
        pass

    # Example 3: Direct Provider Usage
    try:
        # Create environment provider directly
        env_provider = EnvironmentCredentialProvider(prefix="TEST_")

        # Set a test environment variable
        os.environ["TEST_MY_CONFIG_USERNAME"] = "testuser"

        # Get credential
        await env_provider.get_credential("my-config", "username")

        # Check requested variables
        env_provider.get_requested_variables()

        # Clean up
        del os.environ["TEST_MY_CONFIG_USERNAME"]

    except Exception:
        pass

    # Example 4: Command Line Usage


async def environment_variables_example() -> None:
    """Show what environment variables need to be set."""


async def main() -> None:
    """Run all examples."""
    await credential_provider_example()
    await environment_variables_example()


if __name__ == "__main__":
    asyncio.run(main())
