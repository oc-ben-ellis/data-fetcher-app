# Bundle Locators

Bundle locators are the core components responsible for generating URLs to be processed by the OC Fetcher framework. They implement the `BundleLocator` protocol and coordinate with the fetcher to manage URL generation, pagination, and processing state.

## Overview

Bundle locators serve as the "frontier" of the crawling/fetching process by:
- **Generating URLs**: Creating the next batch of URLs to be processed
- **Managing State**: Tracking which URLs have been processed
- **Handling Pagination**: Managing complex pagination logic for APIs
- **Coordinating Processing**: Responding to URL processing completion

## Locator Interface

All bundle locators implement the following interface:

```python
class BundleLocator(Protocol):
    async def get_next_urls(self, ctx: FetchRunContext) -> List[RequestMeta]:
        """Generate the next batch of URLs to be processed."""
        pass
    
    async def handle_url_processed(
        self, 
        request: RequestMeta, 
        bundle_refs: List[BundleRef], 
        ctx: FetchRunContext
    ) -> None:
        """Called when a URL has been successfully processed."""
        pass
```

## Available Locators

### SFTP Locators

#### SFTPDirectoryBundleLocator

Generates SFTP URLs for files in a remote directory.

```python
from oc_fetcher.bundle_locators import SFTPDirectoryBundleLocator
from oc_fetcher.protocols import SftpManager

# Create SFTP manager
sftp_manager = SftpManager(
    credentials_provider=credentials_provider,
    connect_timeout=20.0,
    rate_limit_requests_per_second=2.0,
)

# Create directory locator
provider = SFTPDirectoryBundleLocator(
    sftp_manager=sftp_manager,
    remote_dir="/data/daily",
    filename_pattern="*.txt",
    max_files=1000,  # Optional: limit number of files
)

# Usage in fetcher configuration
from oc_fetcher.core import create_fetcher_config

config = (
    create_fetcher_config()
    .use_bundle_loader(loader)
    .add_bundle_locator(provider)
    .build()
)
```

**Parameters:**
- `sftp_manager`: SFTP connection manager
- `remote_dir`: Remote directory path to scan
- `filename_pattern`: Glob pattern for file matching (default: "*")
- `max_files`: Maximum number of files to process (optional)

#### SFTPFileBundleLocator

Generates SFTP URLs for specific individual files.

```python
from oc_fetcher.bundle_locators import SFTPFileBundleLocator

# Create file locator for specific files
provider = SFTPFileBundleLocator(
    sftp_manager=sftp_manager,
    file_paths=[
        "/data/archive/2024-01-01.zip",
        "/data/archive/2024-01-02.zip",
        "/data/quarterly/report.zip"
    ]
)
```

**Parameters:**
- `sftp_manager`: SFTP connection manager
- `file_paths`: List of specific file paths to process

### Generic Providers

#### GenericDirectoryBundleLocator

SFTP directory provider with custom filtering and sorting.

```python
from oc_fetcher.bundle_locators import GenericDirectoryBundleLocator
from datetime import datetime

# Create custom file filter
def daily_file_filter(filename: str) -> bool:
    """Filter for daily files from a specific date."""
    try:
        # Extract date from filename like "data_20240101.txt"
        date_str = filename.split("_")[1].split(".")[0]
        file_date = datetime.strptime(date_str, "%Y%m%d")
        start_date = datetime.strptime("20240101", "%Y%m%d")
        return file_date >= start_date
    except:
        return False

# Create custom sort key
def sort_by_date(file_path: str, mtime: float) -> float:
    """Sort files by modification time (newest first)."""
    return mtime

# Create generic directory locator
provider = GenericDirectoryBundleLocator(
    sftp_manager=sftp_manager,
    remote_dir="/data/daily",
    filename_pattern="*.txt",
    max_files=None,
    file_filter=daily_file_filter,
    sort_key=sort_by_date,
    sort_reverse=True,  # Newest files first
)
```

**Parameters:**
- `sftp_manager`: SFTP connection manager
- `remote_dir`: Remote directory path to scan
- `filename_pattern`: Glob pattern for file matching
- `max_files`: Maximum number of files to process (optional)
- `file_filter`: Custom function to filter files (optional)
- `sort_key`: Custom function to sort files (optional)
- `sort_reverse`: Sort order (default: True for newest first)

#### GenericFileBundleLocator

Generic provider for specific file lists with custom logic.

```python
from oc_fetcher.bundle_locators import GenericFileBundleLocator

provider = GenericFileBundleLocator(
    sftp_manager=sftp_manager,
    file_paths=["/data/important/file1.txt", "/data/important/file2.txt"]
)
```

### API Providers

#### ApiPaginationBundleLocator

Generic API provider with date-based pagination support.

```python
from oc_fetcher.bundle_locators import ApiPaginationBundleLocator
from oc_fetcher.protocols import HttpManager

# Create HTTP manager
http_manager = HttpManager(
    rate_limit_requests_per_second=2.0,
    default_headers={"User-Agent": "OCFetcher/1.0"}
)

# Create API locator
provider = ApiPaginationBundleLocator(
    http_manager=http_manager,
    base_url="https://api.example.com/data",
    date_start="2024-01-01",
    date_end="2024-01-31",
    max_records_per_page=1000,
    rate_limit_requests_per_second=2.0,
    headers={"Authorization": "Bearer token"},
    query_params={"format": "json"},
    query_builder=lambda date_str: f"date:[{date_str}T00:00:00 TO {date_str}T23:59:59]"
)
```

**Parameters:**
- `http_manager`: HTTP connection manager
- `base_url`: Base API URL
- `date_start`: Start date for data collection
- `date_end`: End date for data collection (optional)
- `max_records_per_page`: Maximum records per API call
- `rate_limit_requests_per_second`: Rate limiting
- `date_filter`: Custom date filtering function (optional)
- `query_params`: Additional query parameters
- `headers`: HTTP headers
- `query_builder`: Custom query building function (optional)

#### SingleApiBundleLocator

Provider for single API endpoints or predefined URL lists.

```python
from oc_fetcher.bundle_locators import SingleApiBundleLocator

provider = SingleApiBundleLocator(
    http_manager=http_manager,
    urls=[
        "https://api.example.com/companies/123",
        "https://api.example.com/companies/456",
        "https://api.example.com/companies/789"
    ],
    headers={"Authorization": "Bearer token"}
)
```

**Parameters:**
- `http_manager`: HTTP connection manager
- `urls`: List of specific URLs to process
- `headers`: HTTP headers (optional)

### Advanced Pagination Providers

#### ComplexPaginationProvider

Provider for APIs with complex pagination logic including cursor-based pagination and search narrowing.

```python
from oc_fetcher.bundle_locators import (
    ComplexPaginationProvider, 
    CursorPaginationStrategy
)

# Create pagination strategy
pagination_strategy = CursorPaginationStrategy(
    cursor_field="curseurSuivant",
    total_field="total",
    count_field="nombre",
    max_records=20000
)

# Create narrowing strategy
def siren_narrowing_strategy(current_narrowing: Optional[str] = None) -> str:
    """Create SIREN prefix for narrowing search."""
    if current_narrowing is None:
        return "siren:00"
    elif current_narrowing == "siren:99":
        return "siren:99"  # Trigger date increment
    else:
        # Increment the prefix
        prefix_value = current_narrowing.split(":", 1)[1]
        new_value = str(int(prefix_value) + 1).zfill(2)
        return f"siren:{new_value}"

# Create complex pagination provider
provider = ComplexPaginationProvider(
    http_manager=http_manager,
    base_url="https://api.insee.fr/entreprises/sirene/V3.11/siren",
    date_start="2024-01-01",
    date_end="2024-01-31",
    max_records_per_page=1000,
    rate_limit_requests_per_second=2.0,
    headers={"Accept": "application/json"},
    query_builder=lambda date_str, narrowing: f"date:[{date_str}T00:00:00 TO {date_str}T23:59:59]",
    pagination_strategy=pagination_strategy,
    narrowing_strategy=siren_narrowing_strategy
)
```

**Parameters:**
- `http_manager`: HTTP connection manager
- `base_url`: Base API URL
- `date_start`: Start date for data collection
- `date_end`: End date for data collection (optional)
- `max_records_per_page`: Maximum records per API call
- `rate_limit_requests_per_second`: Rate limiting
- `date_filter`: Custom date filtering function (optional)
- `query_params`: Additional query parameters
- `headers`: HTTP headers
- `query_builder`: Custom query building function
- `pagination_strategy`: Pagination strategy implementation
- `narrowing_strategy`: Search narrowing strategy (optional)

#### ReversePaginationProvider

Provider for reverse date progression, useful for gap filling or historical data collection.

```python
from oc_fetcher.bundle_locators import ReversePaginationBundleLocator

# Create reverse pagination provider for gap filling
provider = ReversePaginationProvider(
    http_manager=http_manager,
    base_url="https://api.insee.fr/entreprises/sirene/V3.11/siren",
    date_start="2024-01-01",
    date_end="2024-01-31",
    max_records_per_page=1000,
    rate_limit_requests_per_second=2.0,
    headers={"Accept": "application/json"},
    query_builder=lambda date_str, narrowing: f"date:[{date_str}T00:00:00 TO {date_str}T23:59:59]",
    pagination_strategy=pagination_strategy,
    narrowing_strategy=siren_narrowing_strategy
)
```

### Pagination Strategies

#### CursorPaginationStrategy

Strategy for cursor-based pagination commonly used in modern APIs.

```python
from oc_fetcher.bundle_locators import CursorPaginationStrategy

strategy = CursorPaginationStrategy(
    cursor_field="curseurSuivant",  # Field name for next cursor
    total_field="total",            # Field name for total records
    count_field="nombre",           # Field name for current page count
    max_records=20000              # Maximum records to process
)
```

## Factory Functions

The framework provides factory functions for easier provider creation:

```python
from oc_fetcher.factory import (
    create_directory_provider,
    create_file_provider,
    create_complex_pagination_provider,
    create_reverse_pagination_provider,
    create_single_api_provider
)

# Create providers using factory functions
directory_provider = create_directory_provider(
    sftp_manager=sftp_manager,
    remote_dir="/data",
    filename_pattern="*.txt"
)

file_provider = create_file_provider(
    sftp_manager=sftp_manager,
    file_paths=["/data/file1.txt", "/data/file2.txt"]
)

api_provider = create_complex_pagination_provider(
    http_manager=http_manager,
    base_url="https://api.example.com/data",
    date_start="2024-01-01",
    date_end="2024-01-31"
)
```

## Integration Examples

### Basic SFTP Configuration

```python
from oc_fetcher import create_fetcher_config
from oc_fetcher.bundle_locators import SFTPDirectoryBundleLocator
from oc_fetcher.factory import create_sftp_manager, create_sftp_loader

def setup_sftp_fetcher():
    # Create SFTP manager
    sftp_manager = create_sftp_manager(
        config_name="my-sftp",
        connect_timeout=20.0,
        rate_limit_requests_per_second=2.0,
    )
    
    # Create loader
    loader = create_sftp_loader(sftp_manager=sftp_manager)
    
    # Create locator
    provider = SFTPDirectoryBundleLocator(
        sftp_manager=sftp_manager,
        remote_dir="/data/daily",
        filename_pattern="*.txt",
        max_files=1000
    )
    
    # Build configuration
    return (
        create_fetcher_config()
        .use_bundle_loader(loader)
        .add_bundle_locator(provider)
        .build()
    )
```

### Advanced API Configuration

```python
from oc_fetcher import create_fetcher_config
from oc_fetcher.bundle_locators import ComplexPaginationBundleLocator, CursorPaginationStrategy
from oc_fetcher.factory import create_http_manager, create_tracking_api_loader

def setup_api_fetcher():
    # Create HTTP manager with authentication
    http_manager = create_http_manager(
        rate_limit_requests_per_second=2.0,
        authentication=OAuthAuthenticationMechanism(
            token_url="https://api.example.com/oauth/token",
            client_id="your_client_id",
            client_secret="your_client_secret"
        )
    )
    
    # Create loader
    loader = create_tracking_api_loader(http_manager=http_manager)
    
    # Create pagination strategy
    pagination_strategy = CursorPaginationStrategy(
        cursor_field="next_cursor",
        total_field="total_count",
        count_field="page_size",
        max_records=50000
    )
    
    # Create locator
    provider = ComplexPaginationBundleLocator(
        http_manager=http_manager,
        base_url="https://api.example.com/companies",
        date_start="2024-01-01",
        date_end="2024-01-31",
        max_records_per_page=1000,
        headers={"Accept": "application/json"},
        query_builder=lambda date_str, narrowing: f"updated_at:[{date_str}]",
        pagination_strategy=pagination_strategy
    )
    
    # Build configuration
    return (
        create_fetcher_config()
        .use_bundle_loader(loader)
        .add_bundle_locator(provider)
        .build()
    )
```

### Multi-Provider Configuration

```python
def setup_multi_provider_fetcher():
    # Create multiple locators
    daily_provider = SFTPDirectoryBundleLocator(
        sftp_manager=sftp_manager,
        remote_dir="/data/daily",
        filename_pattern="*.txt"
    )
    
    quarterly_provider = SFTPFileBundleLocator(
        sftp_manager=sftp_manager,
        file_paths=["/data/quarterly/report.zip"]
    )
    
    api_provider = SingleApiBundleLocator(
        http_manager=http_manager,
        urls=["https://api.example.com/status"]
    )
    
    # Build configuration with multiple locators
    return (
        create_fetcher_config()
        .use_bundle_loader(loader)
        .add_bundle_locator(daily_provider)
        .add_bundle_locator(quarterly_provider)
        .add_bundle_locator(api_provider)
        .build()
    )
```

## Best Practices

### 1. Rate Limiting

Always configure appropriate rate limits to avoid overwhelming APIs:

```python
# For APIs
http_manager = HttpManager(rate_limit_requests_per_second=2.0)

# For SFTP
sftp_manager = SftpManager(rate_limit_requests_per_second=1.0)
```

### 2. Error Handling

Implement proper error handling in custom providers:

```python
async def get_next_urls(self, ctx: FetchRunContext) -> list[RequestMeta]:
    try:
        # Generate URLs
        return urls
    except Exception as e:
        print(f"Error generating URLs: {e}")
        return []  # Return empty list to avoid crashes
```

### 3. State Management

Use the key-value store for persistent state management:

```python
from oc_fetcher.kv_store import get_global_store

async def get_next_urls(self, ctx: FetchRunContext) -> list[RequestMeta]:
    store = await get_global_store()
    
    # Check if we've already processed this
    cache_key = f"processed:{self.base_url}"
    if await store.exists(cache_key):
        return []
    
    # Mark as processed
    await store.put(cache_key, True, ttl=3600)
    return urls
```

### 4. Custom Filtering

Use custom filters to process only relevant files:

```python
def create_date_filter(start_date: str):
    def filter_function(filename: str) -> bool:
        try:
            # Extract date from filename
            date_str = filename.split("_")[1].split(".")[0]
            return date_str >= start_date
        except:
            return False
    return filter_function

provider = GenericDirectoryBundleLocator(
    sftp_manager=sftp_manager,
    remote_dir="/data",
    file_filter=create_date_filter("20240101")
)
```

### 5. Monitoring and Logging

Add logging to track provider behavior:

```python
import logging

logger = logging.getLogger(__name__)

async def get_next_urls(self, ctx: FetchRunContext) -> list[RequestMeta]:
    logger.info(f"Generating URLs for {self.remote_dir}")
    urls = []
    # ... generate URLs
    logger.info(f"Generated {len(urls)} URLs")
    return urls
```

## Troubleshooting

### Common Issues

1. **Provider not generating URLs**: Check if initialization completed successfully
2. **Rate limiting errors**: Reduce `rate_limit_requests_per_second`
3. **Authentication failures**: Verify credentials and authentication mechanism
4. **File not found errors**: Check remote directory paths and file patterns

### Debug Mode

Enable debug logging to troubleshoot provider issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

When adding new locators:

1. Implement the `BundleLocator` protocol
2. Add comprehensive docstrings
3. Include usage examples
4. Add factory functions if appropriate
5. Update this README with documentation
6. Add tests for the new locator
