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
    from data_fetcher_core.recipebook import get_fetcher

    # List available fetcher recipes

    # Example 1: Get a fetcher for US Florida SFTP fetcher recipe
    try:
        get_fetcher("us-fl")

        # Get the recipe
        from data_fetcher_core.recipebook import get_recipe_setup_function

        setup_func = get_recipe_setup_function("us-fl")
        recipe = setup_func()

        # Create a basic fetch plan
        run_context = FetchRunContext(run_id="example-us-fl")
        _ = FetchPlan(recipe=recipe, context=run_context)

    except Exception:
        pass

    # Example 2: Get a fetcher for France API fetcher recipe
    try:
        get_fetcher("fr")

        # Get the recipe
        setup_func = get_recipe_setup_function("fr")
        recipe = setup_func()

        # Create a basic fetch plan
        run_context = FetchRunContext(run_id="example-fr")
        _ = FetchPlan(recipe=recipe, context=run_context)

    except Exception:
        pass

    # Example 3: Error handling for invalid recipe
    with contextlib.suppress(KeyError):
        get_fetcher("invalid-config")


async def recipe_example() -> None:
    """Demonstrate recipe system usage."""
    from data_fetcher_core.recipebook import list_recipes

    # Show available recipes
    recipes = list_recipes()

    # Demonstrate getting recipe setup function
    from data_fetcher_core.recipebook import get_recipe_setup_function

    for recipe_name in recipes:
        with contextlib.suppress(Exception):
            get_recipe_setup_function(recipe_name)


async def main() -> None:
    """Run all examples."""
    await basic_usage_example()
    await recipe_example()


if __name__ == "__main__":
    asyncio.run(main())
