#!/usr/bin/env python3
"""Credential provider usage example for OC Fetcher.

This example demonstrates how to use different credential providers and
the new command line flag functionality.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def credential_provider_example() -> None:
    """Demonstrate different credential providers."""
    print("=== OC Fetcher Credential Provider Example ===")

    from oc_fetcher.credentials import (
        EnvironmentCredentialProvider,
    )
    from oc_fetcher.global_credential_provider import (
        configure_global_credential_provider,
        get_default_credential_provider,
    )

    # Example 1: AWS Secrets Manager Provider (default)
    print("\n1. AWS Secrets Manager Provider:")
    try:
        # Configure AWS provider
        os.environ["OC_CREDENTIAL_PROVIDER_TYPE"] = "aws"
        configure_global_credential_provider()

        provider = get_default_credential_provider()
        print(f"   ✓ Successfully configured AWS provider: {type(provider).__name__}")

        # Note: This will fail without proper AWS credentials, but that's expected
        print("   Note: AWS provider requires proper AWS credentials to work")

    except Exception as e:
        print(f"   ✗ Error configuring AWS provider: {e}")

    # Example 2: Environment Variable Provider
    print("\n2. Environment Variable Provider:")
    try:
        # Configure environment provider
        os.environ["OC_CREDENTIAL_PROVIDER_TYPE"] = "environment"
        configure_global_credential_provider()

        provider = get_default_credential_provider()
        print(
            f"   ✓ Successfully configured environment provider: {type(provider).__name__}"
        )

        # Test with a missing environment variable to show error handling
        try:
            await provider.get_credential("test-config", "username")
            print("   ✗ Should have failed with missing environment variable")
        except ValueError as e:
            print("   ✓ Correctly handled missing environment variable:")
            print(f"     {str(e)[:100]}...")

    except Exception as e:
        print(f"   ✗ Error configuring environment provider: {e}")

    # Example 3: Direct Provider Usage
    print("\n3. Direct Provider Usage:")
    try:
        # Create environment provider directly
        env_provider = EnvironmentCredentialProvider(prefix="TEST_")

        # Set a test environment variable
        os.environ["TEST_MY_CONFIG_USERNAME"] = "testuser"

        # Get credential
        username = await env_provider.get_credential("my-config", "username")
        print(f"   ✓ Successfully got credential: {username}")

        # Check requested variables
        requested = env_provider.get_requested_variables()
        print(f"   Requested variables: {requested}")

        # Clean up
        del os.environ["TEST_MY_CONFIG_USERNAME"]

    except Exception as e:
        print(f"   ✗ Error with direct provider usage: {e}")

    # Example 4: Command Line Usage
    print("\n4. Command Line Usage:")
    print("   To use environment variables for credentials:")
    print("   python -m oc_fetcher.main --credentials-provider env us-fl")
    print("")
    print("   To use AWS Secrets Manager (default):")
    print("   python -m oc_fetcher.main --credentials-provider aws us-fl")
    print("   or simply:")
    print("   python -m oc_fetcher.main us-fl")
    print("")
    print("   To see help:")
    print("   python -m oc_fetcher.main --help")

    print("\n=== Credential provider example completed ===")


async def environment_variables_example() -> None:
    """Show what environment variables need to be set."""
    print("\n=== Environment Variables Example ===")

    print("When using --credentials-provider env, you need to set these variables:")
    print("")
    print("For US Florida configuration (us-fl):")
    print("  OC_CREDENTIAL_US_FL_HOST=<sftp-host>")
    print("  OC_CREDENTIAL_US_FL_USERNAME=<sftp-username>")
    print("  OC_CREDENTIAL_US_FL_PASSWORD=<sftp-password>")
    print("")
    print("For France API configuration (fr-api):")
    print("  OC_CREDENTIAL_FR_API_CLIENT_ID=<oauth-client-id>")
    print("  OC_CREDENTIAL_FR_API_CLIENT_SECRET=<oauth-client-secret>")
    print("")
    print("Environment variable format:")
    print("  OC_CREDENTIAL_<CONFIG_NAME>_<CREDENTIAL_KEY>")
    print("")
    print("Note: Config names with hyphens (e.g., 'us-fl') are converted to")
    print("      underscores (e.g., 'US_FL') in environment variable names.")

    print("\n=== Environment variables example completed ===")


async def main() -> None:
    """Run all examples."""
    await credential_provider_example()
    await environment_variables_example()


if __name__ == "__main__":
    asyncio.run(main())
