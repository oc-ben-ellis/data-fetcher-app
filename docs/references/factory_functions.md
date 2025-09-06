# Factory Functions Reference

This document provides a comprehensive reference for all factory functions in the Data Fetcher framework, organized by category and updated for the ProtocolConfig architecture.

## Important: Context-Based Resource Access

**All factory functions and components now use `FetchRunContext` to access resources during execution rather than accepting them as constructor parameters.**

- **Store/Storage**: Components get the key-value store from `context.app_config.kv_store` during execution
- **Credentials**: Components get credential providers from `context.app_config.credential_provider` during execution
- **Other Resources**: All context-dependent resources are accessed via `FetchRunContext` during execution

This design ensures that components are created at recipe definition time but access resources during execution when the full context is available.

## ProtocolConfig Factory Functions

### HTTP Protocol Configuration

```python
from data_fetcher_core.factory import create_http_protocol_config

def create_http_protocol_config(
    timeout: float = 30.0,
    rate_limit_requests_per_second: float = 10.0,
    max_retries: int = 3,
    default_headers: dict[str, str] | None = None,
    authentication_mechanism: AuthenticationMechanism | None = None,
) -> HttpProtocolConfig:
    """Create an HTTP protocol configuration with the given settings.

    Args:
        timeout: Request timeout in seconds.
        rate_limit_requests_per_second: Maximum requests per second.
        max_retries: Maximum number of retry attempts.
        default_headers: Default headers to include in requests.
        authentication_mechanism: Authentication mechanism to use.

    Returns:
        HttpProtocolConfig instance.
    """
```

### SFTP Protocol Configuration

```python
from data_fetcher_core.factory import create_sftp_protocol_config

def create_sftp_protocol_config(
    config_name: str,
    connect_timeout: float = 20.0,
    rate_limit_requests_per_second: float = 2.0,
    max_retries: int = 3,
    base_retry_delay: float = 1.0,
    max_retry_delay: float = 60.0,
    retry_exponential_base: float = 2.0,
) -> SftpProtocolConfig:
    """Create an SFTP protocol configuration with the given settings.

    Args:
        config_name: Name of the configuration for credential lookup.
        connect_timeout: Connection timeout in seconds.
        rate_limit_requests_per_second: Maximum requests per second.
        max_retries: Maximum number of retry attempts.
        base_retry_delay: Base delay for retry attempts.
        max_retry_delay: Maximum delay for retry attempts.
        retry_exponential_base: Exponential base for retry delay calculation.

    Returns:
        SftpProtocolConfig instance.
    """
```

## Manager Factory Functions

### HTTP Manager

```python
from data_fetcher_core.factory import create_http_manager

def create_http_manager() -> HttpManager:
    """Create an HTTP manager instance.

    Returns:
        HttpManager instance without configuration.
        Configuration is passed on each method call.
    """
```

### SFTP Manager

```python
from data_fetcher_core.factory import create_sftp_manager

def create_sftp_manager() -> SftpManager:
    """Create an SFTP manager instance.

    Returns:
        SftpManager instance without configuration.
        Configuration is passed on each method call.
    """
```

## Bundle Locator Factory Functions

### HTTP/API Locators

#### Single API Provider

```python
from data_fetcher_http_api.factory import create_single_http_bundle_locator

def create_single_http_bundle_locator(
    http_config: HttpProtocolConfig,
    store: KeyValueStore,
    urls: list[str],
    headers: dict[str, str] | None = None,
    state_management_prefix: str | None = None,
) -> SingleHttpBundleLocator:
    """Create a single API provider for fixed URLs.

    Args:
        http_config: HTTP protocol configuration.
        store: Key-value store for state management.
        urls: List of URLs to process.
        headers: Optional headers to include in requests.
        state_management_prefix: Prefix for state management keys.

    Returns:
        SingleHttpBundleLocator instance.
    """
```

#### Complex Pagination Provider

```python
from data_fetcher_http_api.factory import create_complex_pagination_http_bundle_locator

def create_complex_pagination_http_bundle_locator(
    http_config: HttpProtocolConfig,
    store: KeyValueStore,
    base_url: str,
    date_start: str,
    date_end: str,
    max_records_per_page: int = 1000,
    headers: dict[str, str] | None = None,
    query_builder: Callable | None = None,
    pagination_strategy: Callable | None = None,
    narrowing_strategy: Callable | None = None,
    state_management_prefix: str | None = None,
) -> ComplexPaginationHttpBundleLocator:
    """Create a complex pagination provider for API endpoints.

    Args:
        http_config: HTTP protocol configuration.
        store: Key-value store for state management.
        base_url: Base URL for the API endpoint.
        date_start: Start date for data fetching.
        date_end: End date for data fetching.
        max_records_per_page: Maximum records per page.
        headers: Optional headers to include in requests.
        query_builder: Function to build query parameters.
        pagination_strategy: Function to handle pagination.
        narrowing_strategy: Function to narrow down results.
        state_management_prefix: Prefix for state management keys.

    Returns:
        ComplexPaginationHttpBundleLocator instance.
    """
```

#### Reverse Pagination Provider

```python
from data_fetcher_http_api.factory import create_reverse_pagination_http_bundle_locator

def create_reverse_pagination_http_bundle_locator(
    http_config: HttpProtocolConfig,
    store: KeyValueStore,
    base_url: str,
    date_start: str,
    date_end: str,
    max_records_per_page: int = 1000,
    headers: dict[str, str] | None = None,
    query_builder: Callable | None = None,
    pagination_strategy: Callable | None = None,
    narrowing_strategy: Callable | None = None,
    state_management_prefix: str | None = None,
) -> ReversePaginationHttpBundleLocator:
    """Create a reverse pagination provider for gap-filling.

    Args:
        http_config: HTTP protocol configuration.
        store: Key-value store for state management.
        base_url: Base URL for the API endpoint.
        date_start: Start date for data fetching.
        date_end: End date for data fetching.
        max_records_per_page: Maximum records per page.
        headers: Optional headers to include in requests.
        query_builder: Function to build query parameters.
        pagination_strategy: Function to handle pagination.
        narrowing_strategy: Function to narrow down results.
        state_management_prefix: Prefix for state management keys.

    Returns:
        ReversePaginationHttpBundleLocator instance.
    """
```

### SFTP Locators

#### Directory Provider

```python
from data_fetcher_core.factory import create_directory_provider

def create_directory_provider(
    sftp_config: SftpProtocolConfig,
    remote_dir: str,
    filename_pattern: str = "*",
    max_files: int | None = None,
    file_filter: Callable[[str], bool] | None = None,
    sort_key: Callable[[str, float | int | None], Any] | None = None,
    *,
    sort_reverse: bool = True,
) -> DirectorySftpBundleLocator:
    """Create a directory provider for SFTP directory scanning.

    Args:
        sftp_config: SFTP protocol configuration.
        remote_dir: Remote directory to scan.
        filename_pattern: Pattern to match filenames. Defaults to "*".
        max_files: Maximum number of files to process. Defaults to None.
        file_filter: Optional filter function for files.
        sort_key: Key to sort files by.
        sort_reverse: Whether to sort in reverse order. Defaults to True.

    Returns:
        DirectorySftpBundleLocator instance.

    Note:
        The store for state management is obtained from FetchRunContext during execution.
    """
```

#### File Provider

```python
from data_fetcher_core.factory import create_file_provider

def create_file_provider(
    sftp_config: SftpProtocolConfig,
    file_paths: list[str],
) -> FileSftpBundleLocator:
    """Create a file provider for specific SFTP files.

    Args:
        sftp_config: SFTP protocol configuration.
        file_paths: List of file paths to process.

    Returns:
        FileSftpBundleLocator instance.

    Note:
        The store for state management is obtained from FetchRunContext during execution.
    """
```

## Bundle Loader Factory Functions

### HTTP/API Loaders

#### Tracking API Loader

```python
from data_fetcher_http_api.factory import create_tracking_http_bundle_loader

def create_tracking_http_bundle_loader(
    http_config: HttpProtocolConfig,
    meta_load_name: str,
    error_handler: Callable | None = None,
    follow_redirects: bool = True,
) -> TrackingHttpBundleLoader:
    """Create a tracking API loader with error handling.

    Args:
        http_config: HTTP protocol configuration.
        meta_load_name: Name for metadata tracking.
        error_handler: Optional error handler function.
        follow_redirects: Whether to follow redirects.

    Returns:
        TrackingHttpBundleLoader instance.
    """
```

#### HTTP Loader

```python
from data_fetcher_core.factory import create_http_loader

def create_http_loader(
    http_config: HttpProtocolConfig,
    meta_load_name: str,
    follow_redirects: bool = True,
) -> HttpBundleLoader:
    """Create a basic HTTP loader.

    Args:
        http_config: HTTP protocol configuration.
        meta_load_name: Name for metadata tracking.
        follow_redirects: Whether to follow redirects.

    Returns:
        HttpBundleLoader instance.
    """
```

### SFTP Loaders

#### SFTP Loader

```python
from data_fetcher_core.factory import create_sftp_loader

def create_sftp_loader(
    sftp_config: SftpProtocolConfig,
    meta_load_name: str,
) -> SftpBundleLoader:
    """Create an SFTP loader.

    Args:
        sftp_config: SFTP protocol configuration.
        meta_load_name: Name for metadata tracking.

    Returns:
        SftpBundleLoader instance.
    """
```

## Usage Examples

### Basic HTTP API Recipe

```python
from data_fetcher_http.factory import create_http_protocol_config
from data_fetcher_http_api.factory import (
    create_tracking_http_bundle_loader,
    create_single_http_bundle_locator
)

# Create protocol configuration
http_config = create_http_protocol_config(
    timeout=30.0,
    rate_limit_requests_per_second=2.0,
    max_retries=3,
    authentication_mechanism=oauth_auth
)

# Create loader
loader = create_tracking_http_bundle_loader(
    http_config=http_config,
    meta_load_name="api_loader"
)

# Create provider
provider = create_single_http_bundle_locator(
    http_config=http_config,
    store=kv_store,
    urls=["https://api.example.com/data"],
    headers={"Accept": "application/json"},
    state_management_prefix="api_provider"
)
```

### SFTP Recipe

```python
from data_fetcher_core.factory import (
    create_sftp_protocol_config,
    create_sftp_loader,
    create_directory_provider
)

# Create protocol configuration
sftp_config = create_sftp_protocol_config(
    config_name="example_sftp",
    connect_timeout=20.0,
    rate_limit_requests_per_second=2.0,
    max_retries=3
)

# Create loader
loader = create_sftp_loader(
    sftp_config=sftp_config,
    meta_load_name="sftp_loader"
)

# Create provider
provider = create_directory_provider(
    sftp_config=sftp_config,
    remote_dir="/data/exports/",
    filename_pattern="*.csv",
)
```

## Migration from Manager-Based to ProtocolConfig-Based

### Before (Manager-based)

```python
# Create manager with configuration
http_manager = create_http_manager(
    timeout=30.0,
    rate_limit=2.0,
    max_retries=3
)

# Create components with manager
loader = create_tracking_http_bundle_loader(
    http_manager=http_manager,
    meta_load_name="loader"
)
```

### After (ProtocolConfig-based)

```python
# Create protocol configuration
http_config = create_http_protocol_config(
    timeout=30.0,
    rate_limit_requests_per_second=2.0,
    max_retries=3
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

- **[ProtocolConfig Architecture](../architecture/protocol_config/README.md)** - Detailed ProtocolConfig architecture
- **[Creating a Configuration](../configurations/creating_configuration.md)** - How to create custom recipes
- **[Authentication](../references/authentication.md)** - Authentication mechanisms and credential providers
