"""Command-line interface and main entry point.

This module provides the main CLI interface for running fetchers, including
argument parsing, configuration loading, and execution orchestration.
"""

import argparse
import asyncio
import os

import structlog

from data_fetcher_core.core import FetchPlan
from data_fetcher_core.global_credential_provider import (
    configure_application_credential_provider,
)
from data_fetcher_core.registry import get_fetcher, list_configurations

# Application configuration name
config_name = os.getenv("OC_CONFIG_ID")

# Get logger for this module
logger = structlog.get_logger(__name__)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed command line arguments.
    """
    parser = argparse.ArgumentParser(
        description="OpenCorporates Fetcher - A composable, streaming-first fetch framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m data_fetcher_app.main my-config                    # Use specific configuration
  python -m data_fetcher_app.main --credentials-provider env   # Use environment variables for credentials
  python -m data_fetcher_app.main --help                      # Show this help message
        """,
    )

    parser.add_argument(
        "config_name",
        nargs="?",
        help="Configuration name to use (overrides OC_CONFIG_ID environment variable)",
    )

    parser.add_argument(
        "--credentials-provider",
        choices=["aws", "env"],
        default="aws",
        help="Credential provider to use: 'aws' for AWS Secrets Manager (default), 'env' for environment variables",
    )

    return parser.parse_args()


async def main() -> None:
    """Main entry point for the fetcher application."""
    # Parse command line arguments
    args = parse_arguments()

    # Get config_name from command line argument or use application default
    final_config_name = args.config_name or config_name

    # Bind config_id to context for all subsequent logs
    if final_config_name:
        structlog.contextvars.bind_contextvars(config_id=final_config_name)

    # Check if we have a valid config_name
    if not final_config_name:
        logger.exception("No configuration specified")
        logger.info(
            "Please provide a configuration name as a command line argument or set the OC_CONFIG_ID environment variable"
        )
        logger.info("Available configurations", configurations=list_configurations())
        return

    # If no CLI argument was provided, show which config is being used
    if not args.config_name:
        logger.info(
            "Using configuration from OC_CONFIG_ID", config_id=final_config_name
        )

    # Configure credential provider based on command line argument
    if args.credentials_provider == "env":
        # Set environment variable to override default AWS provider
        os.environ["OC_CREDENTIAL_PROVIDER_TYPE"] = "environment"
        logger.info("Using environment variable credential provider")
    else:
        # Ensure AWS provider is used (default)
        os.environ["OC_CREDENTIAL_PROVIDER_TYPE"] = "aws"
        logger.info("Using AWS Secrets Manager credential provider")

    # Reconfigure application credential provider with new settings
    configure_application_credential_provider()

    try:
        logger.info("Initializing fetcher", config_id=final_config_name)
        fetcher = get_fetcher(final_config_name)

        # Create a basic fetch plan with fetcher_id in context
        from data_fetcher_core.core import FetchRunContext  # noqa: PLC0415

        run_context = FetchRunContext(run_id=final_config_name)

        plan = FetchPlan(
            requests=[],
            context=run_context,
        )

        # Run the fetcher
        logger.info("Starting fetch operation", config_id=final_config_name)
        result = await fetcher.run(plan)
        logger.info(
            "Fetch completed successfully",
            config_id=final_config_name,
            result=str(result),
        )

    except KeyError:
        logger.exception(
            "Unknown configuration",
            config_id=final_config_name,
            available_configurations=list_configurations(),
        )
    except Exception as e:
        logger.exception(
            "Error running fetcher",
            config_id=final_config_name,
            error=str(e),
        )


if __name__ == "__main__":
    asyncio.run(main())
