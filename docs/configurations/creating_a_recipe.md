# Creating a Fetcher Recipe

This guide explains how to create new fetcher recipes for the Data Fetcher framework. Fetcher recipes encapsulate best practices and common patterns, making it easy to add support for new data sources.

## Overview

A fetcher recipe in the Data Fetcher framework consists of:

- **Bundle Locators**: Define where to find data (URLs, file paths, etc.)
- **Bundle Loaders**: Handle the actual data retrieval (HTTP, SFTP, etc.)
- **ProtocolConfig**: Define protocol-specific settings (rate limiting, authentication, etc.)
- **Storage**: Define where and how to store the retrieved data

## Fetcher Recipe Structure

### Basic Fetcher Recipe Template

```python
"""Your fetcher recipe module."""

from collections.abc import Callable
import structlog

from data_fetcher_core.core import FetcherRecipe, create_fetcher_config
from data_fetcher_http.factory import (
    create_http_protocol_config,  # or create_sftp_protocol_config
)
from data_fetcher_http_api.factory import (
    create_tracking_http_bundle_loader,  # or create_sftp_loader
    create_single_http_bundle_locator,  # or other locator types
)
# Credential provider is now passed via app_config parameter
from data_fetcher_core.recipebook import register_recipe

# Get logger for this module
logger = structlog.get_logger(__name__)


def _setup_your_config_fetcher() -> FetcherRecipe:
    """Your fetcher recipe setup function."""
    # Credential provider is passed via app_config parameter

    # Create protocol configuration
    http_config = create_http_protocol_config(
        timeout=30.0,
        rate_limit_requests_per_second=2.0,
        max_retries=3,
    )

    # Create loader with ProtocolConfig
    loader = create_tracking_http_bundle_loader(
        http_config=http_config,
        meta_load_name="your_config_loader",
    )

    # Create bundle locators with ProtocolConfig
    provider = create_single_http_bundle_locator(
        http_config=http_config,
        urls=["https://api.example.com/data"],
        headers={"Accept": "application/json"},
        state_management_prefix="your_config_provider",
    )

    # Build and return fetcher recipe
    return (
        create_fetcher_config()
        .use_bundle_loader(loader)
        .add_bundle_locator(provider)
        .build()
    )


# Register the fetcher recipe
register_recipe("your-config", _setup_your_config_fetcher)
```

## Configuration Components

### 1. Bundle Locators

Bundle locators define where to find data. Choose the appropriate type:

#### HTTP/API Locators

```python
# Create protocol configuration
http_config = create_http_protocol_config(
    timeout=30.0,
    rate_limit_requests_per_second=2.0,
    max_retries=3,
)

# Single API endpoint
provider = create_single_http_bundle_locator(
    http_config=http_config,
    urls=["https://api.example.com/data"],
    headers={"Accept": "application/json"},
    state_management_prefix="your_provider",
)

# Multiple API endpoints
provider = create_single_http_bundle_locator(
    http_config=http_config,
    urls=[
        "https://api.example.com/companies",
        "https://api.example.com/officers",
        "https://api.example.com/filings",
    ],
    headers={"Accept": "application/json"},
    state_management_prefix="your_provider",
)

# Paginated API with complex logic
provider = create_complex_pagination_http_bundle_locator(
    http_config=http_config,
    base_url="https://api.example.com/v1",
    date_start="2025-01-01",
    date_end="2025-01-31",
    max_records_per_page=1000,
    rate_limit_requests_per_second=2.0,
    headers={"Accept": "application/json"},
    query_builder=your_query_builder,
    pagination_strategy=your_pagination_strategy,
    narrowing_strategy=your_narrowing_strategy,
    state_management_prefix="your_provider",
)
```

#### SFTP Locators

```python
# Directory-based file discovery
provider = create_directory_provider(
    sftp_config=sftp_config,
    remote_dir="/data/exports",
    filename_pattern="*.csv",
    max_files=None,
    file_filter=your_file_filter,
    sort_key=lambda file_path, mtime: mtime,
    sort_reverse=True,
)

# Specific file paths
provider = create_file_provider(
    sftp_config=sftp_config,
    file_paths=[
        "/data/exports/daily/companies.csv",
        "/data/exports/daily/officers.csv",
    ],
)
```

### 2. Bundle Loaders

Bundle loaders handle the actual data retrieval:

```python
# Create protocol configurations
http_config = create_http_protocol_config(
    timeout=30.0,
    rate_limit_requests_per_second=2.0,
    max_retries=3,
)

sftp_config = create_sftp_protocol_config(
    config_name="your-config",
    connect_timeout=20.0,
    rate_limit_requests_per_second=2.0,
)

# HTTP/API loader
loader = create_tracking_http_bundle_loader(
    http_config=http_config,
    meta_load_name="your_loader",
    error_handler=your_error_handler,  # Optional
)

# SFTP loader
loader = create_sftp_loader(
    sftp_config=sftp_config,
    meta_load_name="your_loader",
)
```

### 3. ProtocolConfig

ProtocolConfig objects define protocol-specific settings and enable multiple connection pools per manager:

#### HTTP ProtocolConfig

```python
http_config = create_http_protocol_config(
    timeout=30.0,
    rate_limit_requests_per_second=2.0,
    max_retries=3,
    default_headers={
        "User-Agent": "YourApp/1.0",
        "Accept": "application/json",
    },
    authentication_mechanism=your_auth_mechanism,  # Optional
)
```

#### SFTP ProtocolConfig

```python
sftp_config = create_sftp_protocol_config(
    config_name="your-config",
    connect_timeout=20.0,
    rate_limit_requests_per_second=2.0,
    max_retries=3,
)
```

**Note**: Managers are now created automatically by the framework and handle multiple connection pools based on ProtocolConfig objects.

### 4. Authentication

#### OAuth 2.0 Authentication

```python
from data_fetcher_sftp.authentication import OAuthAuthenticationMechanism

oauth_auth = OAuthAuthenticationMechanism(
    token_url="https://api.example.com/oauth/token",
    credential_provider=credential_provider,
    config_name="your-config",
)

# Use with HTTP ProtocolConfig
http_config = create_http_protocol_config(
    timeout=30.0,
    authentication_mechanism=oauth_auth,
)
```

#### API Key Authentication

```python
from data_fetcher_http_api.authentication import APIKeyAuthenticationMechanism

api_key_auth = APIKeyAuthenticationMechanism(
    header_name="X-API-Key",
    credential_provider=credential_provider,
    config_name="your-config",
)

# Use with HTTP ProtocolConfig
http_config = create_http_protocol_config(
    timeout=30.0,
    authentication_mechanism=api_key_auth,
)
```

## Advanced Features

### Custom Query Builders

```python
def _create_your_query_builder() -> Callable[[str, str | None], str]:
    """Create a query builder for your API."""

    def query_builder(date_str: str, narrowing: str | None = None) -> str:
        """Build API query with date and optional narrowing."""
        base_query = f"date:[{date_str}T00:00:00 TO {date_str}T23:59:59]"

        if narrowing:
            return f"{narrowing} AND {base_query}"
        return base_query

    return query_builder
```

### Custom Pagination Strategies

```python
from data_fetcher_http_api.api_pagination_bundle_locators import CursorPaginationStrategy

pagination_strategy = CursorPaginationStrategy(
    cursor_field="next_cursor",
    total_field="total_count",
    count_field="count",
    max_records=10000,
)
```

### Custom Narrowing Strategies

```python
def _create_your_narrowing_strategy() -> Callable[[str | None], str]:
    """Create a narrowing strategy for your API."""

    def narrowing_strategy(current_narrowing: str | None = None) -> str:
        """Create narrowing parameter for search."""
        if current_narrowing is None:
            return "prefix:00"

        # Extract and increment the prefix
        prefix_value = current_narrowing.split(":", 1)[1]
        new_value = str(int(prefix_value) + 1).zfill(len(prefix_value))
        return f"prefix:{new_value}"

    return narrowing_strategy
```

### Custom Error Handlers

```python
def _create_your_error_handler() -> Callable[[str, int], bool]:
    """Create an error handler for your API."""

    def error_handler(url: str, status_code: int) -> bool:
        """Handle API errors."""
        if status_code == 404:
            logger.warning("NO_ITEMS_FOUND_FOR_QUERY", url=url)
            return False
        if status_code in [500, 502, 503, 504]:
            logger.exception("SERVER_ERROR", url=url, status_code=status_code)
            return False
        if status_code != 200:
            logger.exception("UNEXPECTED_STATUS_CODE", url=url, status_code=status_code)
            return False
        return True

    return error_handler
```

### Custom File Filters

```python
def _create_your_file_filter(start_date: str) -> Callable[[str], bool]:
    """Create a file filter for your SFTP fetcher recipe."""

    def filter_function(filename: str) -> bool:
        """Check if file should be processed based on date."""
        try:
            # Extract date from filename (e.g., YYYYMMDD_*.csv)
            for i in range(len(filename) - 7):
                date_str = filename[i:i + 8]
                if date_str.isdigit() and len(date_str) == 8 and date_str >= start_date:
                    return True
        except Exception as e:
            logger.exception("DATE_PARSING_ERROR_IN_FILENAME", error=str(e), filename=filename)

        return False

    return filter_function
```

## Credential Management

### AWS Secrets Manager

Store credentials in AWS Secrets Manager:

```bash
# Create secret for your fetcher recipe
aws secretsmanager create-secret \
  --name "oc-fetcher/your-config" \
  --secret-string '{
    "api_key": "your-api-key",
    "base_url": "https://api.example.com"
  }'
```

### Environment Variables

For development or testing:

```bash
# Set credential provider
export OC_CREDENTIAL_PROVIDER_TYPE=environment

# Your fetcher recipe credentials
export OC_CREDENTIAL_YOUR_CONFIG_API_KEY="your-api-key"
export OC_CREDENTIAL_YOUR_CONFIG_BASE_URL="https://api.example.com"
```

**Note**: Configuration names with hyphens are converted to underscores in environment variable names.

## Testing Your Configuration

### Basic Test

```python
# Test your fetcher recipe
from data_fetcher_core.recipebook import get_fetcher

fetcher = get_fetcher("your-config")
print("Configuration is valid")
```

### Command Line Test

```bash
# Test from command line
poetry run python -m data_fetcher_app.main run your-config
```

### Unit Tests

```python
import pytest
from data_fetcher_core.recipebook import get_fetcher

def test_your_fetcher_recipe():
    """Test that your fetcher recipe can be created."""
    fetcher = get_fetcher("your-config")
    assert fetcher is not None
    assert fetcher.context is not None
```

## Best Practices

### Configuration Design

1. **Single Responsibility**: Each fetcher recipe should handle one data source
2. **Consistent Naming**: Use descriptive, consistent names (e.g., `us-fl`, `fr`)
3. **Error Handling**: Include comprehensive error handling and logging
4. **Rate Limiting**: Respect API rate limits and implement appropriate delays
5. **Persistence**: Use persistence prefixes to track progress across runs

### Performance Considerations

1. **Concurrency**: Set appropriate concurrency limits
2. **Timeouts**: Use reasonable timeout values
3. **Retry Logic**: Implement intelligent retry strategies
4. **Memory Usage**: Use streaming for large datasets
5. **Caching**: Leverage persistence for incremental updates

### Security

1. **Credential Management**: Use AWS Secrets Manager for production
2. **Least Privilege**: Use minimal required permissions
3. **Secure Communication**: Use HTTPS/TLS for all communications
4. **Input Validation**: Validate all inputs and API responses

## Examples

### Simple API Configuration

```python
"""Simple API fetcher recipe example."""

from data_fetcher_core.core import FetcherRecipe, create_fetcher_config
from data_fetcher_http.factory import (
    create_http_manager,
)
from data_fetcher_http_api.factory import (
    create_tracking_http_bundle_loader,
    create_single_http_bundle_locator,
)
# Credential provider is now passed via app_config parameter
from data_fetcher_core.recipebook import register_recipe

def _setup_simple_api_fetcher() -> FetcherRecipe:
    """Simple API fetcher recipe."""
    # Credential provider is passed via app_config parameter

    http_config = create_http_protocol_config(
        timeout=30.0,
        rate_limit_requests_per_second=1.0,
        max_retries=3,
    )

    loader = create_tracking_http_bundle_loader(
        http_config=http_config,
        meta_load_name="simple_api_loader",
    )

    provider = create_single_http_bundle_locator(
        http_config=http_config,
        urls=["https://api.example.com/data"],
        headers={"Accept": "application/json"},
        state_management_prefix="simple_api_provider",
    )

    return (
        create_fetcher_config()
        .use_bundle_loader(loader)
        .add_bundle_locator(provider)
        .build()
    )

register_recipe("simple-api", _setup_simple_api_fetcher)
```

### SFTP Configuration

```python
"""SFTP fetcher recipe example."""

from data_fetcher_core.core import FetcherRecipe, create_fetcher_config
from data_fetcher_core.factory import create_sftp_loader, create_sftp_protocol_config
from data_fetcher_core.factory import create_directory_provider
from data_fetcher_core.recipebook import register_recipe

def _setup_sftp_fetcher() -> FetcherRecipe:
    """SFTP fetcher recipe."""
    sftp_config = create_sftp_protocol_config(
        config_name="sftp-config",
        connect_timeout=20.0,
        rate_limit_requests_per_second=2.0,
    )

    loader = create_sftp_loader(
        sftp_config=sftp_config,
        meta_load_name="sftp_loader",
    )

    provider = create_directory_provider(
        sftp_config=sftp_config,
        remote_dir="/data/exports",
        filename_pattern="*.csv",
        max_files=100,
    )

    return (
        create_fetcher_config()
        .use_bundle_loader(loader)
        .add_bundle_locator(provider)
        .build()
    )

register_recipe("sftp-config", _setup_sftp_fetcher)
```

## Next Steps

1. **Test Your Configuration**: Use the testing methods above
2. **Document Your Recipe**: Create documentation similar to the existing fetcher recipes
3. **Add to Registry**: Ensure your fetcher recipe is properly registered
4. **Deploy**: Test in your target environment
5. **Monitor**: Set up monitoring and alerting for your fetcher recipe

## Related Documentation

- **[FR - France API](fr_api.md)** - Example API fetcher recipe
- **[US_FL - US Florida SFTP](us_fl_sftp.md)** - Example SFTP fetcher recipe
- **[Application Configuration](../user_guide/application_configuration.md)** - System configuration
- **[Architecture](../architecture/README.md)** - Framework architecture
