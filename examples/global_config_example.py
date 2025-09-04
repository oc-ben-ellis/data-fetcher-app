"""Application configuration example for the OC Fetcher framework."""

#!/usr/bin/env python3

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def demonstrate_storage_config() -> None:
    """Demonstrate storage configuration."""
    # Example 1: S3 Storage (default)

    # Set environment variables
    os.environ["OC_STORAGE_TYPE"] = "s3"
    os.environ["OC_S3_BUCKET"] = "my-example-bucket"
    os.environ["AWS_REGION"] = "eu-west-2"

    # Import and configure storage
    from data_fetcher.global_storage import configure_application_storage

    configure_application_storage()

    # Example 2: File Storage

    os.environ["OC_STORAGE_TYPE"] = "file"
    os.environ["OC_STORAGE_FILE_PATH"] = "./captures"

    configure_application_storage()


async def demonstrate_kv_store_config() -> None:
    """Demonstrate key-value store configuration."""
    # Example 1: Memory Store (default)

    # Clear any existing Redis configuration
    os.environ.pop("OC_KV_STORE_TYPE", None)
    os.environ.pop("OC_KV_STORE_REDIS_HOST", None)

    # Import and configure KV store
    from data_fetcher.global_kv_store import configure_application_kv_store

    configure_application_kv_store()

    # Example 2: Redis Store

    os.environ["OC_KV_STORE_TYPE"] = "redis"
    os.environ["OC_KV_STORE_REDIS_HOST"] = "localhost"
    os.environ["OC_KV_STORE_REDIS_PORT"] = "6379"
    os.environ["OC_KV_STORE_REDIS_KEY_PREFIX"] = "example:"

    configure_application_kv_store()


async def demonstrate_credential_provider_config() -> None:
    """Demonstrate credential provider configuration."""
    # Example 1: AWS Secrets Manager (default)

    # Clear any existing configuration
    os.environ.pop("OC_CREDENTIAL_PROVIDER_TYPE", None)

    # Import and configure credential provider
    from data_fetcher.global_credential_provider import (
        configure_application_credential_provider,
    )

    configure_application_credential_provider()

    # Example 2: Environment Variables

    os.environ["OC_CREDENTIAL_PROVIDER_TYPE"] = "environment"
    os.environ["OC_CREDENTIAL_PROVIDER_ENV_PREFIX"] = "EXAMPLE_CRED_"
    os.environ["EXAMPLE_CRED_MY_CONFIG_USERNAME"] = "myuser"
    os.environ["EXAMPLE_CRED_MY_CONFIG_PASSWORD"] = "mypass"

    configure_application_credential_provider()


async def demonstrate_usage() -> None:
    """Demonstrate how to use the configured components."""
    try:
        # Get the configured components
        from data_fetcher.global_credential_provider import (
            get_default_credential_provider,
        )
        from data_fetcher.kv_store import get_global_store
        from data_fetcher.storage.builder import get_global_storage

        # Get storage
        get_global_storage()

        # Get KV store
        await get_global_store()

        # Get credential provider
        cred_provider = get_default_credential_provider()

        # Test credential retrieval (if using environment provider)
        if hasattr(cred_provider, "prefix") and cred_provider.prefix == "EXAMPLE_CRED_":
            try:
                await cred_provider.get_credential("my_config", "username")
                await cred_provider.get_credential("my_config", "password")
            except Exception:
                pass

    except Exception:
        pass


async def main() -> None:
    """Run the demonstration."""
    try:
        await demonstrate_storage_config()
        await demonstrate_kv_store_config()
        await demonstrate_credential_provider_config()
        await demonstrate_usage()

    except Exception:
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
