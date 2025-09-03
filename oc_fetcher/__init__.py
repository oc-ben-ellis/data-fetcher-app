"""OC Fetcher - Main package initialization and exports."""

# Import logging configuration to set up structlog
# Import global storage configuration to set up default storage
# Import configuration modules to ensure they are registered
from . import (
    configurations,  # noqa: F401
    global_credential_provider,  # noqa: F401
    global_kv_store,  # noqa: F401
    global_storage,  # noqa: F401
    kv_store,  # noqa: F401
    logging,  # noqa: F401
)

# Export main components
from .core import FetcherContextBuilder, create_fetcher_config
from .credentials import (
    AWSSecretsCredentialProvider,
    CredentialProvider,
    EnvironmentCredentialProvider,
    SftpCredentials,
    SftpCredentialsWrapper,
)
from .factory import (
    create_directory_provider,
    create_file_provider,
    create_sftp_loader,
    create_sftp_manager,
)
from .fetcher import FetchContext, Fetcher, FetchPlan, FetchResult, run_fetcher
from .global_credential_provider import (
    get_default_credential_provider,
    set_default_credential_provider,
)
from .kv_store import (
    InMemoryKeyValueStore,
    RedisKeyValueStore,
    configure_global_store,
    delete,
    exists,
    get,
    get_global_store,
    get_store_context,
    put,
    range_get,
)
from .registry import get_fetcher, list_configurations
from .storage.builder import (
    StorageBuilder,
    create_storage_config,
    get_global_storage,
    set_global_storage,
)

__all__ = [
    # Main fetcher components
    "Fetcher",
    "FetchContext",
    "FetchPlan",
    "FetchResult",
    "run_fetcher",
    # Configuration system
    "get_fetcher",
    "list_configurations",
    "create_fetcher_config",
    "FetcherContextBuilder",
    # Storage system
    "create_storage_config",
    "set_global_storage",
    "get_global_storage",
    "StorageBuilder",
    # Factory methods
    "create_sftp_manager",
    "create_sftp_loader",
    "create_directory_provider",
    "create_file_provider",
    # Credential system
    "CredentialProvider",
    "AWSSecretsCredentialProvider",
    "EnvironmentCredentialProvider",
    "SftpCredentials",
    "SftpCredentialsWrapper",
    "get_default_credential_provider",
    "set_default_credential_provider",
    # Key-value store system
    "configure_global_store",
    "get_global_store",
    "get_store_context",
    "put",
    "get",
    "delete",
    "range_get",
    "exists",
    "InMemoryKeyValueStore",
    "RedisKeyValueStore",
]
