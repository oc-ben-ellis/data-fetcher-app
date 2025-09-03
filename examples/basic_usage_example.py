#!/usr/bin/env python3
"""Basic usage example for OC Fetcher.

This example demonstrates how to use the OC Fetcher framework with the correct API.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def basic_usage_example() -> None:
    """Demonstrate basic usage of OC Fetcher."""
    print("=== OC Fetcher Basic Usage Example ===")

    # Import the necessary modules
    from data_fetcher.core import FetchPlan, FetchRunContext
    from data_fetcher.registry import get_fetcher, list_configurations

    # List available fetcher configurations
    print(f"\nAvailable fetcher configurations: {list_configurations()}")

    # Example 1: Get a fetcher for US Florida SFTP fetcher configuration
    print("\n1. US Florida SFTP Fetcher Configuration:")
    try:
        fetcher = get_fetcher("us-fl")
        print("   ✓ Successfully created US Florida fetcher")

        # Create a basic fetch plan
        run_context = FetchRunContext(run_id="example-us-fl")
        _ = FetchPlan(requests=[], context=run_context)

        print("   ✓ Created fetch plan")
        print(f"   Fetcher type: {type(fetcher).__name__}")

    except Exception as e:
        print(f"   ✗ Error creating US Florida fetcher: {e}")

    # Example 2: Get a fetcher for France API fetcher configuration
    print("\n2. France API Fetcher Configuration:")
    try:
        fetcher = get_fetcher("fr")
        print("   ✓ Successfully created France fetcher")

        # Create a basic fetch plan
        run_context = FetchRunContext(run_id="example-fr")
        _ = FetchPlan(requests=[], context=run_context)

        print("   ✓ Created fetch plan")
        print(f"   Fetcher type: {type(fetcher).__name__}")

    except Exception as e:
        print(f"   ✗ Error creating France fetcher: {e}")

    # Example 3: Error handling for invalid configuration
    print("\n3. Error Handling:")
    try:
        fetcher = get_fetcher("invalid-config")
        print("   ✗ Should have raised an error")
    except KeyError as e:
        print(f"   ✓ Correctly handled invalid configuration: {e}")

    print("\n=== Example completed ===")


async def configuration_example() -> None:
    """Demonstrate configuration system usage."""
    print("\n=== Configuration System Example ===")

    from data_fetcher.registry import list_configurations

    # Show available configurations
    configs = list_configurations()
    print(f"Available configurations: {configs}")

    # Demonstrate getting configuration setup function
    from data_fetcher.registry import get_configuration_setup_function

    for config_name in configs:
        try:
            setup_func = get_configuration_setup_function(config_name)
            print(f"   ✓ {config_name}: {setup_func.__name__}")
        except Exception as e:
            print(f"   ✗ {config_name}: Error - {e}")

    print("\n=== Configuration example completed ===")


async def main() -> None:
    """Run all examples."""
    await basic_usage_example()
    await configuration_example()


if __name__ == "__main__":
    asyncio.run(main())
