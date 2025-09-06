# ReversePaginationHttpBundleLocator

## Overview

The ReversePaginationHttpBundleLocator is used for gap-filling operations in the France API configuration. It processes data in reverse chronological order to fill gaps in historical data collection.

## Implementation

```python
from data_fetcher_http_api.factory import create_reverse_pagination_http_bundle_locator

gap_provider = create_reverse_pagination_http_bundle_locator(
    http_manager=http_manager,
    base_url=base_url,
    date_start=gap_start_date,
    date_end=gap_end_date,
    max_records_per_page=1000,
    rate_limit_requests_per_second=2.0,
    headers={"Accept": "application/json"},
    query_builder=_create_sirene_query_builder(),
    pagination_strategy=sirene_pagination_strategy,
    narrowing_strategy=_create_siren_narrowing_strategy(),
    persistence_prefix="fr_gap_provider",
)
```

## Features

- **Reverse Processing**: Processes data in reverse chronological order
- **Gap Filling**: Designed to fill gaps in previous data collection runs
- **Same Query Logic**: Uses the same query builder and pagination strategy as the main provider
- **Persistence**: Tracks progress to avoid reprocessing data

## Usage in Configuration

The ReversePaginationHttpBundleLocator is used in the `fr` configuration to:
- Fill gaps in historical data collection
- Process data that may have been missed in previous runs
- Ensure complete data coverage over time periods

## Related Components

- **[ComplexPaginationHttpBundleLocator](complex_pagination_bundle_locator.md)** - Main data collection provider
- **[TrackingHttpBundleLoader](tracking_api_loader.md)** - Handles HTTP requests
- **[FR - France API](../../../fr_api.md)** - Complete configuration using this locator
