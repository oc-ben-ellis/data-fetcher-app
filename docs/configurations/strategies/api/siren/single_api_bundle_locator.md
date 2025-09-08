# SingleHttpBundleLocator

## Overview

The SingleHttpBundleLocator is used for processing specific API endpoints or failed company lookups in the France API configuration. It handles single or multiple specific URLs rather than dynamic discovery.

## Implementation

```python
from data_fetcher_http_api.factory import create_single_http_bundle_locator

failed_companies_provider = create_single_http_bundle_locator(
    http_manager=http_manager,
    urls=[],  # Populated with failed company URLs
    headers={"Accept": "application/json"},
    persistence_prefix="fr_failed_companies_provider",
)
```

## Features

- **Specific URLs**: Processes predefined list of URLs
- **Error Recovery**: Designed for retrying failed requests
- **Simple Processing**: Straightforward URL-based processing
- **Persistence**: Tracks progress across runs

## Usage in Configuration

The SingleHttpBundleLocator is used in the `fr` configuration to:
- Retry failed company lookups
- Process specific company URLs that failed in previous runs
- Handle error recovery scenarios

## Configuration Options

- `urls`: List of specific URLs to process
- `headers`: HTTP headers to include in requests
- `persistence_prefix`: Prefix for progress tracking

## Related Components

- **[ComplexPaginationHttpBundleLocator](complex_pagination_bundle_locator.md)** - Main data collection provider
- **[TrackingHttpBundleLoader](tracking_api_loader.md)** - Handles HTTP requests
- **[FR - France API](../../../fr_api.md)** - Complete configuration using this locator
