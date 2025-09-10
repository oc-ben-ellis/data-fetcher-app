# ComplexPaginationHttpBundleLocator

## Overview

The ComplexPaginationHttpBundleLocator is a complex pagination provider used in the France API configuration for the INSEE SIRENE API. It handles cursor-based pagination with SIREN prefix narrowing and date filtering.

## Implementation

The ComplexPaginationHttpBundleLocator is implemented using multiple provider types:

### Main Data Provider
```python
# Create HTTP protocol configuration
http_config = create_http_protocol_config(
    timeout=120.0,
    rate_limit_requests_per_second=2.0,
    max_retries=5,
    authentication_mechanism=oauth_auth
)

siren_provider = create_complex_pagination_http_bundle_locator(
    http_config=http_config,
    store=kv_store,
    base_url=base_url,
    date_start=start_date,
    date_end=end_date,
    max_records_per_page=1000,
    headers={"Accept": "application/json"},
    query_builder=_create_sirene_query_builder(),
    pagination_strategy=sirene_pagination_strategy,
    narrowing_strategy=_create_siren_narrowing_strategy(),
    state_management_prefix="fr_siren_provider",
)
```

### Gap-Filling Provider
```python
gap_provider = create_reverse_pagination_http_bundle_locator(
    http_config=http_config,
    store=kv_store,
    base_url=base_url,
    date_start=gap_start_date,
    date_end=gap_end_date,
    max_records_per_page=1000,
    headers={"Accept": "application/json"},
    query_builder=_create_sirene_query_builder(),
    pagination_strategy=sirene_pagination_strategy,
    narrowing_strategy=_create_siren_narrowing_strategy(),
    state_management_prefix="fr_gap_provider",
)
```

### Failed Companies Provider
```python
failed_companies_provider = create_single_http_bundle_locator(
    http_config=http_config,
    store=kv_store,
    urls=[],  # Populated with failed company URLs
    headers={"Accept": "application/json"},
    persistence_prefix="fr_failed_companies_provider",
)
```

## Key Features

### Query Builder
- **Date Filtering**: Uses `dateDernierTraitementUniteLegale` field
- **SIREN Narrowing**: 2-digit prefix strategy (00-99)
- **Exclusions**: Filters out category 1000 and non-diffused records

### Pagination Strategy
- **Cursor-based**: Uses `curseurSuivant` field
- **Max Records**: 20,000 per query
- **Page Size**: 1,000 records per page

### Narrowing Strategy
- **SIREN Prefixes**: Incremental processing of 2-digit prefixes
- **Edge Case Handling**: Handles prefix "99" triggering date increment
- **Automatic Progression**: Moves through prefixes systematically

## Usage in Configuration

The ComplexPaginationHttpBundleLocator is used in the `fr` configuration to:
1. **Main Data Collection**: Primary SIRENE data fetching
2. **Gap Filling**: Historical data collection for missed records
3. **Error Recovery**: Retry failed company lookups

## Related Components

- **[TrackingHttpBundleLoader](tracking_api_loader.md)** - Handles HTTP requests
- **FR - France API** - Complete configuration using this locator
- **Creating a Recipe** - How to create custom locators
