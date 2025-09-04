"""OC Fetcher - Main package initialization and exports."""

# Import logging configuration to set up structlog
# Import global storage configuration to set up default storage
# Import configuration modules to ensure they are registered
from . import (
    configurations,
    global_credential_provider,
    global_kv_store,
    global_storage,
    kv_store,
    logging,
)

# Export main components
from .core import FetchContext, FetcherContextBuilder, FetchPlan, create_fetcher_config
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
from .fetcher import Fetcher, FetchResult, run_fetcher
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
    "AWSSecretsCredentialProvider",
    # Credential system
    "CredentialProvider",
    "EnvironmentCredentialProvider",
    "FetchContext",
    "FetchPlan",
    "FetchResult",
    # Main fetcher components
    "Fetcher",
    "FetcherContextBuilder",
    "InMemoryKeyValueStore",
    "RedisKeyValueStore",
    "SftpCredentials",
    "SftpCredentialsWrapper",
    "StorageBuilder",
    # Key-value store system
    "configure_global_store",
    "create_directory_provider",
    "create_fetcher_config",
    "create_file_provider",
    "create_sftp_loader",
    # Factory methods
    "create_sftp_manager",
    # Storage system
    "create_storage_config",
    "delete",
    "exists",
    "get",
    "get_default_credential_provider",
    # Configuration system
    "get_fetcher",
    "get_global_storage",
    "get_global_store",
    "get_store_context",
    "list_configurations",
    "put",
    "range_get",
    "run_fetcher",
    "set_default_credential_provider",
    "set_global_storage",
]
