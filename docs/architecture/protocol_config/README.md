# ProtocolConfig Architecture

The ProtocolConfig system is a key architectural component that enables flexible, configuration-driven connection management across different protocols. It separates protocol-specific settings from manager instances, allowing for multiple connection pools per manager and improved type safety.

## Overview

ProtocolConfig objects define protocol-specific settings and enable the framework to manage multiple connection pools dynamically. Each protocol manager can handle multiple configurations simultaneously, with automatic pool creation and reuse based on configuration similarity.

## Core Concepts

### ProtocolConfig Base Class

All protocol configurations inherit from the abstract `ProtocolConfig` base class:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

class ProtocolType(Enum):
    """Supported protocol types."""
    HTTP = "http"
    SFTP = "sftp"

@dataclass
class ProtocolConfig(ABC):
    """Base class for protocol-specific configurations."""

    @property
    @abstractmethod
    def protocol_type(self) -> ProtocolType:
        """Return the protocol type for this configuration."""
        pass

    @abstractmethod
    def get_connection_key(self) -> str:
        """Generate a unique key for this connection configuration."""
        pass
```

### HttpProtocolConfig

HTTP protocol configuration with comprehensive settings:

```python
@dataclass
class HttpProtocolConfig(ProtocolConfig):
    """HTTP protocol configuration."""

    timeout: float = 30.0
    rate_limit_requests_per_second: float = 10.0
    max_retries: int = 3
    default_headers: dict[str, str] | None = None
    authentication_mechanism: AuthenticationMechanism | None = None

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.HTTP

    def get_connection_key(self) -> str:
        """Generate a unique key for this HTTP connection configuration."""
        auth_key = (
            self.authentication_mechanism.get_connection_key()
            if self.authentication_mechanism
            else "no_auth"
        )
        headers_key = json.dumps(self.default_headers, sort_keys=True)
        return f"http_{self.timeout}_{self.rate_limit_requests_per_second}_{self.max_retries}_{auth_key}_{headers_key}"
```

### SftpProtocolConfig

SFTP protocol configuration with connection and retry settings:

```python
@dataclass
class SftpProtocolConfig(ProtocolConfig):
    """SFTP protocol configuration."""

    config_name: str
    connect_timeout: float = 20.0
    rate_limit_requests_per_second: float = 5.0
    max_retries: int = 3
    base_retry_delay: float = 1.0
    max_retry_delay: float = 60.0
    retry_exponential_base: float = 2.0

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.SFTP

    def get_connection_key(self) -> str:
        """Generate a unique key for this SFTP connection configuration."""
        return (
            f"sftp_{self.config_name}_{self.connect_timeout}_"
            f"{self.rate_limit_requests_per_second}_{self.max_retries}_"
            f"{self.base_retry_delay}_{self.max_retry_delay}_"
            f"{self.retry_exponential_base}"
        )
```

## Connection Pool Management

### Dynamic Pool Creation

Protocol managers automatically create and manage connection pools based on configuration similarity:

```python
class HttpManager:
    """HTTP connection manager with support for multiple connection pools."""

    def __init__(self) -> None:
        """Initialize the HTTP manager with empty connection pools."""
        self._connection_pools: Dict[str, HttpConnectionPool] = {}

    def _get_or_create_pool(self, config: HttpProtocolConfig) -> HttpConnectionPool:
        """Get or create a connection pool for the given configuration."""
        connection_key = config.get_connection_key()

        if connection_key not in self._connection_pools:
            self._connection_pools[connection_key] = HttpConnectionPool(config=config)

        return self._connection_pools[connection_key]

    async def request(
        self,
        config: HttpProtocolConfig,
        app_config: "FetcherConfig",
        method: str,
        url: str,
        **kwargs: object
    ) -> httpx.Response:
        """Make an HTTP request using the specified configuration."""
        pool = self._get_or_create_pool(config)
        return await pool.request(app_config, method, url, **kwargs)
```

### Connection Pool Isolation

Each connection pool manages its own state and behavior:

```python
@dataclass
class HttpConnectionPool:
    """HTTP connection pool for a specific configuration."""

    config: HttpProtocolConfig
    _last_request_time: float = 0.0
    _rate_limit_lock: asyncio.Lock = None
    _retry_engine: Any = None

    def __post_init__(self) -> None:
        """Initialize the connection pool."""
        if self._rate_limit_lock is None:
            self._rate_limit_lock = asyncio.Lock()

        if self._retry_engine is None:
            self._retry_engine = create_retry_engine(max_retries=self.config.max_retries)

    async def request(
        self,
        app_config: "FetcherConfig",
        method: str,
        url: str,
        **kwargs: object
    ) -> httpx.Response:
        """Make an HTTP request with rate limiting and authentication."""
        # Rate limiting logic specific to this pool
        # Authentication using app_config.credential_provider
        # Retry logic using this pool's retry engine
        pass
```

## Factory Functions

### Creating Protocol Configurations

Use factory functions to create protocol configurations:

```python
from data_fetcher_http.factory import create_http_protocol_config
from data_fetcher_core.factory import create_sftp_protocol_config

# Create HTTP configuration
http_config = create_http_protocol_config(
    timeout=120.0,
    rate_limit_requests_per_second=2.0,
    max_retries=5,
    authentication_mechanism=oauth_auth
)

# Create SFTP configuration
sftp_config = create_sftp_protocol_config(
    config_name="example_sftp",
    connect_timeout=20.0,
    rate_limit_requests_per_second=2.0,
    max_retries=3
)
```

### Creating Components with ProtocolConfig

Components now accept ProtocolConfig objects instead of manager instances:

```python
from data_fetcher_http_api.factory import (
    create_tracking_http_bundle_loader,
    create_complex_pagination_http_bundle_locator,
)
from data_fetcher_core.factory import create_sftp_loader

# Create loader with ProtocolConfig
loader = create_tracking_http_bundle_loader(
    http_config=http_config,
    meta_load_name="api_loader"
)

# Create provider with ProtocolConfig
provider = create_complex_pagination_http_bundle_locator(
    http_config=http_config,
    store=kv_store,
    base_url="https://api.example.com",
    # ... other parameters
)

# Create SFTP loader with ProtocolConfig
sftp_loader = create_sftp_loader(
    sftp_config=sftp_config,
    meta_load_name="sftp_loader"
)
```

## Benefits

### 1. Multiple Connection Pools
- Each protocol manager can handle multiple configurations simultaneously
- Automatic pool creation based on configuration similarity
- Efficient resource utilization

### 2. Configuration Separation
- Protocol settings are separate from manager instances
- Better type safety and validation
- Easier testing and mocking

### 3. Connection Reuse
- Configurations with same settings automatically share connection pools
- Reduced connection overhead
- Improved performance

### 4. App Config Integration
- Credential providers are passed on every method call
- No need for `update_credential_provider` methods
- Cleaner API design

## Usage Patterns

### Recipe Configuration

```python
def _setup_fr_api_fetcher() -> FetcherRecipe:
    """Setup France API fetcher with ProtocolConfig."""

    # Create HTTP protocol configuration
    http_config = create_http_protocol_config(
        timeout=120.0,
        rate_limit_requests_per_second=2.0,
        max_retries=5,
        authentication_mechanism=oauth_auth
    )

    # Create components with ProtocolConfig
    loader = create_tracking_http_bundle_loader(
        http_config=http_config,
        meta_load_name="fr_sirene_api_loader"
    )

    provider = create_complex_pagination_http_bundle_locator(
        http_config=http_config,
        store=kv_store,
        base_url=base_url,
        # ... other parameters
    )

    return FetcherRecipe(
        bundle_loaders=[loader],
        bundle_locators=[provider],
        storage=storage
    )
```

### Manager Usage

```python
# Managers are created without configuration
http_manager = create_http_manager()
sftp_manager = create_sftp_manager()

# Configuration is passed on each method call
response = await http_manager.request(
    http_config,      # Determines which pool to use
    app_config,       # Contains credential provider
    "GET",
    "https://api.example.com"
)

connection = await sftp_manager.get_connection(
    sftp_config,      # Determines which pool to use
    app_config,       # Contains credential provider
    credentials_provider
)
```

## Migration Guide

### From Manager-Based to ProtocolConfig-Based

**Before (Manager-based):**
```python
# Create manager with configuration
http_manager = create_http_manager(
    timeout=120.0,
    rate_limit=2.0,
    max_retries=5
)

# Create components with manager
loader = create_tracking_http_bundle_loader(
    http_manager=http_manager,
    meta_load_name="loader"
)
```

**After (ProtocolConfig-based):**
```python
# Create protocol configuration
http_config = create_http_protocol_config(
    timeout=120.0,
    rate_limit_requests_per_second=2.0,
    max_retries=5
)

# Create components with ProtocolConfig
loader = create_tracking_http_bundle_loader(
    http_config=http_config,
    meta_load_name="loader"
)
```

## Best Practices

1. **Use Factory Functions**: Always use factory functions to create ProtocolConfig objects
2. **Reuse Configurations**: Use the same ProtocolConfig object for components that should share connection pools
3. **Type Safety**: Leverage ProtocolConfig classes for better type safety and validation
4. **App Config Integration**: Pass app_config on every method call for credential access
5. **Connection Key Uniqueness**: Ensure get_connection_key() returns unique values for different configurations

## Related Documentation

- **[Orchestration](../orchestration/README.md)** - How ProtocolConfig integrates with the orchestration system
- **[Recipes](../recipes/README.md)** - How to use ProtocolConfig in recipe configurations
- **[Factory Functions](../../references/factory_functions.md)** - Complete reference for factory functions
- **Authentication mechanisms and credential providers**: see
  - [Creating a Recipe – Authentication](../../configurations/creating_a_recipe.md#4-authentication)
  - [FR API – Authentication](../../configurations/fr_api.md#authentication)
  - [Terminology – Authentication Terms](../../references/terminology.md#authentication-terms)
  - [Troubleshooting – Authentication Issues](../../troubleshooting/troubleshooting_guide.md#authentication-issues)
