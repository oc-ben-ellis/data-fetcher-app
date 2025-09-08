"""CLI configuration using openc_python_common envargs.

This module defines the configuration classes for command-line arguments
using the openc_python_common library's envargs functionality.
"""

import environ
from openc_python_common.envargs import args_to_config_class


@environ.config(prefix="DATA_FETCHER_APP")
class RunConfig:
    """Configuration for the run command."""

    recipe_id: str = environ.var(help="Recipe ID to run")
    credentials_provider: str = environ.var(
        default="aws", help="Credential provider to use (aws or env)"
    )
    storage: str = environ.var(
        default="s3", help="Storage mechanism to use (s3 or file)"
    )
    kvstore: str = environ.var(
        default="redis", help="Key-value store to use (redis or memory)"
    )
    log_level: str = environ.var(default="INFO", help="Log level")
    dev_mode: bool = environ.bool_var(
        default=False, help="Enable development mode logging"
    )


@environ.config(prefix="DATA_FETCHER_APP")
class ListConfig:
    """Configuration for the list command."""

    log_level: str = environ.var(default="INFO", help="Log level")
    dev_mode: bool = environ.bool_var(
        default=False, help="Enable development mode logging"
    )


@environ.config(prefix="DATA_FETCHER_APP")
class HealthConfig:
    """Configuration for the health check command."""

    port: int = environ.var(default=8080, help="Port to bind to")
    host: str = environ.var(default="127.0.0.1", help="Host to bind to")
    log_level: str = environ.var(default="INFO", help="Log level")
    dev_mode: bool = environ.bool_var(
        default=False, help="Enable development mode logging"
    )


def create_run_config(args: list[str] | None = None) -> RunConfig:
    """Create a RunConfig from command line arguments and environment variables.

    Args:
        args: Command line arguments. If None, uses sys.argv.

    Returns:
        RunConfig instance populated from args and environment variables.
    """
    return args_to_config_class(RunConfig, args)


def create_list_config(args: list[str] | None = None) -> ListConfig:
    """Create a ListConfig from command line arguments and environment variables.

    Args:
        args: Command line arguments. If None, uses sys.argv.

    Returns:
        ListConfig instance populated from args and environment variables.
    """
    return args_to_config_class(ListConfig, args)


def create_health_config(args: list[str] | None = None) -> HealthConfig:
    """Create a HealthConfig from command line arguments and environment variables.

    Args:
        args: Command line arguments. If None, uses sys.argv.

    Returns:
        HealthConfig instance populated from args and environment variables.
    """
    return args_to_config_class(HealthConfig, args)
