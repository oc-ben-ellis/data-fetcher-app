"""Command-line interface and main entry point.

This module provides the main CLI interface for running fetchers, including
argument parsing, recipe loading, and execution orchestration.
"""
# ruff: noqa: T201

import asyncio
import os
import sys
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast
from wsgiref.simple_server import make_server

import structlog
from openc_python_common.observability import (
    configure_logging,
    log_bind,
    observe_around,
)

# Import recipes to ensure they are registered
import data_fetcher_recipes  # noqa: F401
from data_fetcher_app.cli_config import (
    create_health_config,
    create_list_config,
    create_run_config,
)
from data_fetcher_app.health import create_health_app
from data_fetcher_core.config_factory import FetcherConfig, create_fetcher_config
from data_fetcher_core.core import FetchPlan, FetchRunContext
from data_fetcher_core.fetcher import Fetcher
from data_fetcher_core.recipebook import (
    get_fetcher,
    get_recipe_setup_function,
    list_recipes,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from wsgiref.types import StartResponse

# Application configuration name
config_name = os.getenv("OC_CONFIG_ID")


def configure_application_credential_provider(
    fetcher: Fetcher, app_config: FetcherConfig
) -> None:
    """Configure credential provider for the fetcher based on app_config.

    This function updates the fetcher's credential provider configuration
    based on the application configuration.

    Args:
        fetcher: The fetcher instance to configure.
        app_config: The application configuration containing credential settings.
    """
    # DEPRECATED: This function is a placeholder and should be removed
    # Credential provider configuration is now handled directly in get_fetcher()
    # through the app_config parameter. The fetcher and its components receive
    # the credential provider through proper dependency injection.
    # Do not implement this function - remove it instead.


# Get logger for this module
logger = structlog.get_logger(__name__)


def generate_run_id(recipe_id: str) -> str:
    """Generate a unique run ID combining recipe_id and timestamp.

    Args:
        recipe_id: The recipe identifier.

    Returns:
        A unique run ID in the format: fetcher_{recipe_id}_{timestamp}
    """
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d%H%M%S")
    return f"fetcher_{recipe_id}_{timestamp}"


def run_command(args: list[str] | None = None) -> None:
    """Run a data fetcher with the specified recipe.

    This command executes a data fetcher using the provided recipe ID.
    The fetcher will process data according to its configured rules and output
    the results to the specified destination.

    Args:
        args: Command line arguments. If None, uses sys.argv.
    """

    def _raise_recipe_id_required() -> None:
        """Raise ValueError for missing recipe_id."""
        msg = "recipe_id is required"
        print(f"Error: {msg}")
        raise ValueError(msg)

    try:
        # Extract recipe_id from positional arguments
        if not args:
            _raise_recipe_id_required()

        # At this point, args is guaranteed to be a non-empty list
        assert args is not None  # noqa: S101
        recipe_id = args[0]
        remaining_args = args[1:]

        # Set the recipe_id as an environment variable for the config
        os.environ["DATA_FETCHER_APP_RECIPE_ID"] = recipe_id

        config = create_run_config(remaining_args)

        # Generate run_id
        run_id = generate_run_id(config.recipe_id)

        # Configure logging
        configure_logging(log_level=config.log_level, dev_mode=config.dev_mode)

        # Store the arguments for the async main function
        args_dict = {
            "config_name": config.recipe_id,
            "credentials_provider": config.credentials_provider,
            "storage": config.storage,
            "kvstore": config.kvstore,
            "run_id": run_id,
        }

        # Run the async main function
        asyncio.run(main_async(args_dict))

    except Exception as e:
        logger.exception("RUN_COMMAND_ERROR", error=str(e))
        sys.exit(1)


def list_command(args: list[str] | None = None) -> None:
    """List all available fetcher recipes.

    This command displays all registered fetcher recipes that can be used
    with the 'run' command. Each recipe includes a unique identifier and
    description of what data source it fetches from.

    Args:
        args: Command line arguments. If None, uses sys.argv.
    """
    try:
        config = create_list_config(args)

        # Configure logging
        configure_logging(log_level=config.log_level, dev_mode=config.dev_mode)

        recipes = list_recipes()
        if not recipes:
            print("No fetcher recipes are available.")
            return

        print("Available fetcher recipes:")
        for recipe_id in sorted(recipes):
            print(f"  {recipe_id}")
        print(f"Total: {len(recipes)} recipe(s)")

    except (ValueError, ImportError, OSError) as e:
        print(f"Error: {e!s}")
        sys.exit(1)


def health_command(args: list[str] | None = None) -> None:
    """Start a health check server.

    This command starts a WSGI server with health check endpoints.

    Args:
        args: Command line arguments. If None, uses sys.argv.
    """
    try:
        config = create_health_config(args)

        # Configure logging
        configure_logging(log_level=config.log_level, dev_mode=config.dev_mode)

        # Create health check app
        app = create_health_app()

        # Import wsgiref for simple WSGI server

        logger.info("HEALTH_CHECK_SERVER_STARTING", host=config.host, port=config.port)

        with make_server(
            config.host,
            config.port,
            cast("Callable[[dict[str, Any], StartResponse], Any]", app),
        ) as httpd:
            logger.info(
                "HEALTH_CHECK_SERVER_STARTED",
                host=config.host,
                port=config.port,
                endpoints=["/health", "/status", "/heartbeat"],
            )
            httpd.serve_forever()

    except KeyboardInterrupt:
        logger.info("HEALTH_CHECK_SERVER_STOPPED_BY_USER")
    except Exception as e:
        print(f"Error: {e!s}")
        logger.exception("HEALTH_CHECK_SERVER_START_ERROR", error=str(e))
        sys.exit(1)


def show_help() -> None:
    """Show help information for the CLI."""
    help_text = """
OpenCorporates Data Fetcher

Usage:
    python -m data_fetcher_app.main <command> [options]

Commands:
    run <recipe_id>     Run a data fetcher with the specified recipe
    list               List all available fetcher recipes
    health             Start a health check server
    --help, -h         Show this help message
    --version, -v      Show version information

Options for run command:
    --credentials-provider <type>  Credential provider type (aws, env)
    --storage <type>              Storage type (s3, file)
    --kvstore <type>              Key-value store type (redis, memory)
    --log-level <level>           Log level (DEBUG, INFO, WARNING, ERROR)
    --dev-mode                    Enable development mode

Examples:
    python -m data_fetcher_app.main run fr
    python -m data_fetcher_app.main run us-fl --credentials-provider env --storage file
    python -m data_fetcher_app.main list
    python -m data_fetcher_app.main health --port 8080
"""
    print(help_text)


def main() -> None:
    """Main entry point for the CLI."""
    min_args = 2
    if len(sys.argv) < min_args:
        show_help()
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:] if len(sys.argv) > min_args else []

    if command == "run":
        if not args:
            show_help()
            sys.exit(1)
        run_command(args)
    elif command == "list":
        list_command(args)
    elif command == "health":
        health_command(args)
    elif command in ["--help", "-h", "help"]:
        show_help()
        sys.exit(0)
    elif command in ["--version", "-v", "version"]:
        print("data-fetcher-app, version 0.1.0")
        sys.exit(0)
    else:
        show_help()
        sys.exit(1)


async def main_async(args: dict[str, Any]) -> None:
    """Main entry point for the fetcher application."""
    # Get config_name and run_id from arguments
    final_config_name = args["config_name"]
    run_id = args["run_id"]

    # Bind run_id and config_id to context for all subsequent logs
    with log_bind(run_id=run_id, config_id=final_config_name):
        # Log storage and kvstore configuration
        logger.info(
            "STORAGE_MECHANISM_SELECTED",
            storage_type=args["storage"],
            kvstore_type=args["kvstore"],
            credentials_provider_type=args["credentials_provider"],
        )

        # Map CLI credential provider types to config factory types
        credential_type_mapping = {"aws": "aws", "env": "environment"}

        # Create fetcher configuration with CLI arguments
        with observe_around(logger, "CREATE_FETCHER_CONFIG"):
            app_config = await create_fetcher_config(
                credentials_provider_type=credential_type_mapping.get(
                    args["credentials_provider"], args["credentials_provider"]
                ),
                storage_type=args["storage"],
                kv_store_type=args["kvstore"],
                config_id=final_config_name,
            )

        try:
            with observe_around(logger, "INITIALIZE_FETCHER"):
                logger.info("FETCHER_INITIALIZING", config_id=final_config_name)
                fetcher = get_fetcher(final_config_name, app_config)

                # Configure credential provider for the fetcher
                configure_application_credential_provider(fetcher, app_config)

            # Create a basic fetch plan with run_id in context
            run_context = FetchRunContext(run_id=run_id, app_config=app_config)

            # Get the recipe for this configuration
            setup_func = get_recipe_setup_function(final_config_name)
            recipe = setup_func()

            plan = FetchPlan(
                recipe=recipe,
                context=run_context,
            )

            # Run the fetcher
            with observe_around(logger, "FETCH_OPERATION"):
                logger.info("FETCH_OPERATION_STARTING", config_id=final_config_name)
                result = await fetcher.run(plan)
                logger.info(
                    "FETCH_OPERATION_COMPLETED",
                    config_id=final_config_name,
                    result=str(result),
                )

        except KeyError:
            logger.exception(
                "UNKNOWN_RECIPE_ERROR",
                config_id=final_config_name,
                available_recipes=list_recipes(),
            )
            raise
        except Exception as e:
            logger.exception(
                "FETCHER_RUN_ERROR",
                config_id=final_config_name,
                error=str(e),
            )
            raise


if __name__ == "__main__":
    main()
