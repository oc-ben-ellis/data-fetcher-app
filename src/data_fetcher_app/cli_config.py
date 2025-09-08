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

    # Global AWS profile default (applies to credentials and storage unless overridden)
    aws_profile: str | None = environ.var(
        default=None, help="Default AWS profile to use for AWS SDK clients"
    )

    # Credentials provider configuration
    credentials_aws_region: str | None = environ.var(
        default=None,
        help="AWS region for credential provider (when using aws)",
    )
    credentials_aws_endpoint_url: str | None = environ.var(
        default=None,
        help="AWS endpoint URL for credential provider (e.g., LocalStack)",
    )
    credentials_env_prefix: str | None = environ.var(
        default=None,
        help="Environment variable prefix for environment credential provider",
    )

    # KV store configuration
    kvstore_serializer: str | None = environ.var(
        default=None,
        help="Serializer to use for KV store (json or pickle)",
    )
    kvstore_default_ttl: int | None = environ.var(
        default=None,
        help="Default TTL (seconds) for KV store entries",
    )
    kvstore_redis_host: str | None = environ.var(
        default=None,
        help="Redis host for KV store (when using redis)",
    )
    kvstore_redis_port: int | None = environ.var(
        default=None,
        help="Redis port for KV store (when using redis)",
    )
    kvstore_redis_db: int | None = environ.var(
        default=None,
        help="Redis database number for KV store (when using redis)",
    )
    kvstore_redis_password: str | None = environ.var(
        default=None,
        help="Redis password for KV store (when using redis)",
    )
    kvstore_redis_key_prefix: str | None = environ.var(
        default=None,
        help="Redis key prefix for KV store (when using redis)",
    )

    # Storage configuration
    storage_pipeline_aws_profile: str | None = environ.var(
        default=None,
        help="AWS profile override for pipeline storage related AWS clients",
    )
    storage_s3_bucket: str | None = environ.var(
        default=None, help="S3 bucket name (when using s3 storage)"
    )
    storage_s3_prefix: str | None = environ.var(
        default=None, help="S3 key prefix (when using s3 storage)"
    )
    storage_s3_region: str | None = environ.var(
        default=None, help="S3 region (when using s3 storage)"
    )
    storage_s3_endpoint_url: str | None = environ.var(
        default=None, help="S3 endpoint URL (e.g., LocalStack)"
    )
    storage_file_path: str | None = environ.var(
        default=None, help="Local file storage base path (when using file storage)"
    )
    storage_use_unzip: bool | None = environ.bool_var(
        default=None, help="Enable unzip decorator for storage operations"
    )
    log_level: str = environ.var(default="INFO", help="Log level")
    dev_mode: bool = environ.bool_var(
        default=False, help="Enable development mode logging"
    )

    # Credentials provider AWS profile override
    credentials_aws_profile: str | None = environ.var(
        default=None,
        help="AWS profile override for credential provider AWS SDK clients",
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
