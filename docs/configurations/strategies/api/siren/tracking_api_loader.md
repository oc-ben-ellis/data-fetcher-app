# TrackingHttpBundleLoader

## Overview

The TrackingHttpBundleLoader is a specialized API loader used in the France API configuration for fetching data from the INSEE SIRENE API. It's built on top of the `create_tracking_http_bundle_loader` factory function and provides comprehensive error handling and request tracking.

## Implementation

```python
from data_fetcher_http.factory import create_http_protocol_config
from data_fetcher_http_api.factory import create_tracking_http_bundle_loader

# Create HTTP protocol configuration
http_config = create_http_protocol_config(
    timeout=120.0,
    rate_limit_requests_per_second=2.0,
    max_retries=5,
    authentication_mechanism=oauth_auth
)

# Create loader with ProtocolConfig
loader = create_tracking_http_bundle_loader(
    http_config=http_config,
    meta_load_name="fr_sirene_api_loader",
    error_handler=_create_sirene_error_handler(),
)
```

## Features

- **Request Tracking**: Tracks all API requests with metadata
- **Error Handling**: Custom error handler for SIRENE API responses
- **Structured Logging**: Detailed logging of request/response cycles
- **Retry Logic**: Built-in retry mechanism for failed requests

## Error Handling

The SirenLoader includes a custom error handler that:

- **404 Responses**: Logs as warnings (no items found)
- **Server Errors (500, 502, 503, 504)**: Logs as exceptions
- **403 Forbidden**: Logs as exceptions
- **Other Errors**: Logs unexpected status codes

## Usage in Configuration

The TrackingHttpBundleLoader is used in the `fr` configuration to handle all HTTP requests to the INSEE SIRENE API endpoints.

## Related Components

- **[ComplexPaginationHttpBundleLocator](complex_pagination_bundle_locator.md)** - Handles URL generation and pagination
- **FR - France API** - Complete configuration using this loader
- **Creating a Recipe** - How to create custom loaders
