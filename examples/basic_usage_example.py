#!/usr/bin/env python3
"""Basic usage example for OC Fetcher.

This example demonstrates how to use the OC Fetcher framework with the correct API.
"""

import asyncio
import contextlib
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def basic_usage_example() -> None:
    """Demonstrate basic usage of OC Fetcher."""
    # Import the necessary modules
    from data_fetcher_core.core import FetchPlan, FetchRunContext
    from data_fetcher_core.registry import get_fetcher

    # List available fetcher configurations

    # Example 1: Get a fetcher for US Florida SFTP fetcher configuration
    try:
        get_fetcher("us-fl")

        # Create a basic fetch plan
        run_context = FetchRunContext(run_id="example-us-fl")
        _ = FetchPlan(requests=[], context=run_context)

    except Exception:
        pass

    # Example 2: Get a fetcher for France API fetcher configuration
    try:
        get_fetcher("fr")

        # Create a basic fetch plan
        run_context = FetchRunContext(run_id="example-fr")
        _ = FetchPlan(requests=[], context=run_context)

    except Exception:
        pass

    # Example 3: Error handling for invalid configuration
    with contextlib.suppress(KeyError):
        get_fetcher("invalid-config")


async def configuration_example() -> None:
    """Demonstrate configuration system usage."""
    from data_fetcher_core.registry import list_configurations

    # Show available configurations
    configs = list_configurations()

    # Demonstrate getting configuration setup function
    from data_fetcher_core.registry import get_configuration_setup_function

    for config_name in configs:
        with contextlib.suppress(Exception):
            get_configuration_setup_function(config_name)


async def main() -> None:
    """Run all examples."""
    await basic_usage_example()
    await configuration_example()


if __name__ == "__main__":
    asyncio.run(main())
