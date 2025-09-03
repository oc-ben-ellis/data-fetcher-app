"""Global configuration example for the OC Fetcher framework."""

__author__ = "Ben Ellis <ben.ellis@opencorporates.com>"
__copyright__ = "Copyright (c) 2024 OpenCorporates Ltd"

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
    print("=== Storage Configuration Example ===")

    # Example 1: S3 Storage (default)
    print("\n1. S3 Storage (default configuration):")
    print("   Environment variables:")
    print("   - OC_STORAGE_TYPE=s3")
    print("   - OC_S3_BUCKET=oc-fetcher-data")
    print("   - AWS_REGION=eu-west-2")

    # Set environment variables
    os.environ["OC_STORAGE_TYPE"] = "s3"
    os.environ["OC_S3_BUCKET"] = "my-example-bucket"
    os.environ["AWS_REGION"] = "eu-west-2"

    # Import and configure storage
    from data_fetcher.global_storage import configure_global_storage

    configure_global_storage()

    print("   ✓ S3 storage configured successfully")

    # Example 2: File Storage
    print("\n2. File Storage:")
    print("   Environment variables:")
    print("   - OC_STORAGE_TYPE=file")
    print("   - OC_STORAGE_FILE_PATH=./captures")

    os.environ["OC_STORAGE_TYPE"] = "file"
    os.environ["OC_STORAGE_FILE_PATH"] = "./captures"

    configure_global_storage()
    print("   ✓ File storage configured successfully")


async def demonstrate_kv_store_config() -> None:
    """Demonstrate key-value store configuration."""
    print("\n=== Key-Value Store Configuration Example ===")

    # Example 1: Memory Store (default)
    print("\n1. Memory Store (default configuration):")
    print("   Environment variables:")
    print("   - OC_KV_STORE_TYPE=memory")
    print("   - OC_KV_STORE_SERIALIZER=json")
    print("   - OC_KV_STORE_DEFAULT_TTL=3600")

    # Clear any existing Redis configuration
    os.environ.pop("OC_KV_STORE_TYPE", None)
    os.environ.pop("OC_KV_STORE_REDIS_HOST", None)

    # Import and configure KV store
    from data_fetcher.global_kv_store import configure_global_kv_store

    configure_global_kv_store()

    print("   ✓ Memory store configured successfully")

    # Example 2: Redis Store
    print("\n2. Redis Store:")
    print("   Environment variables:")
    print("   - OC_KV_STORE_TYPE=redis")
    print("   - OC_KV_STORE_REDIS_HOST=localhost")
    print("   - OC_KV_STORE_REDIS_PORT=6379")

    os.environ["OC_KV_STORE_TYPE"] = "redis"
    os.environ["OC_KV_STORE_REDIS_HOST"] = "localhost"
    os.environ["OC_KV_STORE_REDIS_PORT"] = "6379"
    os.environ["OC_KV_STORE_REDIS_KEY_PREFIX"] = "example:"

    configure_global_kv_store()
    print("   ✓ Redis store configured successfully")


async def demonstrate_credential_provider_config() -> None:
    """Demonstrate credential provider configuration."""
    print("\n=== Credential Provider Configuration Example ===")

    # Example 1: AWS Secrets Manager (default)
    print("\n1. AWS Secrets Manager (default configuration):")
    print("   Environment variables:")
    print("   - OC_CREDENTIAL_PROVIDER_TYPE=aws")
    print("   - AWS_REGION=eu-west-2")

    # Clear any existing configuration
    os.environ.pop("OC_CREDENTIAL_PROVIDER_TYPE", None)

    # Import and configure credential provider
    from data_fetcher.global_credential_provider import (
        configure_global_credential_provider,
    )

    configure_global_credential_provider()

    print("   ✓ AWS Secrets Manager configured successfully")

    # Example 2: Environment Variables
    print("\n2. Environment Variables Provider:")
    print("   Environment variables:")
    print("   - OC_CREDENTIAL_PROVIDER_TYPE=environment")
    print("   - OC_CREDENTIAL_PROVIDER_ENV_PREFIX=EXAMPLE_CRED_")
    print("   - EXAMPLE_CRED_MY_CONFIG_USERNAME=myuser")
    print("   - EXAMPLE_CRED_MY_CONFIG_PASSWORD=mypass")

    os.environ["OC_CREDENTIAL_PROVIDER_TYPE"] = "environment"
    os.environ["OC_CREDENTIAL_PROVIDER_ENV_PREFIX"] = "EXAMPLE_CRED_"
    os.environ["EXAMPLE_CRED_MY_CONFIG_USERNAME"] = "myuser"
    os.environ["EXAMPLE_CRED_MY_CONFIG_PASSWORD"] = "mypass"

    configure_global_credential_provider()
    print("   ✓ Environment variables provider configured successfully")


async def demonstrate_usage() -> None:
    """Demonstrate how to use the configured components."""
    print("\n=== Usage Example ===")

    try:
        # Get the configured components
        from data_fetcher.global_credential_provider import (
            get_default_credential_provider,
        )
        from data_fetcher.kv_store import get_global_store
        from data_fetcher.storage.builder import get_global_storage

        # Get storage
        storage = get_global_storage()
        print(f"✓ Storage type: {type(storage).__name__}")

        # Get KV store
        kv_store = await get_global_store()
        print(f"✓ KV Store type: {type(kv_store).__name__}")

        # Get credential provider
        cred_provider = get_default_credential_provider()
        print(f"✓ Credential Provider type: {type(cred_provider).__name__}")

        # Test credential retrieval (if using environment provider)
        if hasattr(cred_provider, "prefix") and cred_provider.prefix == "EXAMPLE_CRED_":
            try:
                username = await cred_provider.get_credential("my_config", "username")
                password = await cred_provider.get_credential("my_config", "password")
                print(
                    f"✓ Retrieved credentials: username={username}, password={'*' * len(password)}"
                )
            except Exception as e:
                print(f"⚠ Credential retrieval failed: {e}")

        print("\n✓ All components configured and accessible successfully!")

    except Exception as e:
        print(f"✗ Error accessing configured components: {e}")


async def main() -> None:
    """Run the demonstration."""
    print("OC Fetcher Global Configuration System Demo")
    print("=" * 50)

    try:
        await demonstrate_storage_config()
        await demonstrate_kv_store_config()
        await demonstrate_credential_provider_config()
        await demonstrate_usage()

        print("\n" + "=" * 50)
        print("Demo completed successfully! 🎉")
        print("\nTo use this configuration system in your own code:")
        print("1. Set the appropriate environment variables")
        print("2. Import the global configuration modules")
        print("3. Use the configured components directly")
        print("\nSee GLOBAL_CONFIGURATION.md for detailed documentation.")

    except Exception as e:
        print(f"\n✗ Demo failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
