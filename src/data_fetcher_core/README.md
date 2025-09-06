# Data Fetcher Core Module

The core module provides the fundamental building blocks of the OC Fetcher framework, including base classes, configuration utilities, and standardized error handling.

## Key Components

### Core Classes

- **`BundleRef`**: Reference to a bundle of fetched resources with BID-based identification
- **`RequestMeta`**: Metadata for fetch requests with validation
- **`ResourceMeta`**: Metadata for fetched resources with validation
- **`FetchRunContext`**: Context for fetch operations
- **`FetcherRecipe`**: Recipe configuration for fetcher operations
- **`FetchPlan`**: Execution plan with concurrency settings

### Error Handling

The module provides standardized error handling through the `exceptions` module:

- **`DataFetcherError`**: Base exception for all framework errors
- **`ConfigurationError`**: Configuration-related errors
- **`ValidationError`**: Data validation failures
- **`ResourceError`**: Resource operation failures
- **`StorageError`**: Storage operation failures
- **`NetworkError`**: Network-related failures
- **`RetryableError`**: Errors that can be retried
- **`FatalError`**: Errors that cannot be retried

### Bundle ID (BID) System

The BID system provides time-ordered, unique identifiers for bundles:

- **Format**: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` (UUIDv7-like)
- **Time-based ordering**: BIDs contain timestamp information
- **Validation**: Automatic format validation on creation
- **Usage**: Tracing, debugging, and file organization

### Validation

All core data classes include comprehensive validation:

- **Type checking**: Ensures correct data types
- **Range validation**: Validates numeric ranges (e.g., HTTP status codes)
- **Format validation**: Validates string formats (e.g., BID format)
- **Required fields**: Validates presence of required fields

## Usage Examples

### Creating Bundle References

```python
from data_fetcher_core.core import BundleRef, BID

# Create with auto-generated BID
bundle_ref = BundleRef(
    primary_url="https://example.com",
    resources_count=1
)

# Create with custom BID
custom_bid = BID("17571960-2065-e0cd-cf71-8196d8577b7e")
bundle_ref = BundleRef(
    primary_url="https://example.com",
    resources_count=1,
    bid=custom_bid
)
```

### Error Handling

```python
from data_fetcher_core.exceptions import ConfigurationError, ValidationError

try:
    # Some operation that might fail
    pass
except ConfigurationError as e:
    print(f"Configuration error: {e.message}")
    print(f"Component: {e.component}")
except ValidationError as e:
    print(f"Validation error: {e.message}")
    print(f"Field: {e.field}")
```

### Request Metadata

```python
from data_fetcher_core.core import RequestMeta

# Create request with validation
request = RequestMeta(
    url="https://example.com/api",
    depth=1,
    headers={"User-Agent": "DataFetcher/1.0"},
    flags={"priority": "high"}
)
```

## Recent Improvements

### Error Handling Standardization

- All components now use standardized exception types
- Consistent error messages and error codes
- Proper error chaining and context preservation

### Validation Enhancements

- Comprehensive validation for all data classes
- BID format validation with detailed error messages
- HTTP status code range validation
- Required field validation with clear error messages

### Race Condition Fixes

- Fixed busy-wait loop in `BundleStorageContext`
- Proper synchronization using `asyncio.Event`
- Thread-safe upload tracking

### Configuration Improvements

- Robust configuration handling in `recipebook.py`
- Graceful error handling for component configuration
- Detailed logging for configuration operations

### Queue Implementation

- Enhanced error handling in `KVStoreQueue`
- Better validation and logging
- Proper exception chaining

## Best Practices

### Error Handling

1. **Use specific exception types**: Choose the most appropriate exception type
2. **Include context**: Provide meaningful error messages and context
3. **Chain exceptions**: Use `from e` when re-raising exceptions
4. **Log appropriately**: Use appropriate log levels based on error severity

### Validation

1. **Validate early**: Validate data as soon as it's created
2. **Provide clear messages**: Include field names in validation errors
3. **Check types**: Always validate data types before processing
4. **Handle edge cases**: Consider null values and empty strings

### BID Usage

1. **Use for tracing**: Include BIDs in logs for correlation
2. **File organization**: Use BIDs for time-ordered file paths
3. **Validation**: Always validate BID format when parsing
4. **Generation**: Let the system generate BIDs unless you have a specific need

## Testing

The core module includes comprehensive tests for:

- Data class validation
- Error handling scenarios
- BID generation and validation
- Configuration handling
- Queue operations

Run tests with:

```bash
poetry run pytest tests/test_unit/data_fetcher_core/
```

## Migration Guide

### From Old Error Handling

**Before:**
```python
raise ValueError("Invalid configuration")
```

**After:**
```python
from data_fetcher_core.exceptions import ConfigurationError
raise ConfigurationError("Invalid configuration", "component_name")
```

### From Old Validation

**Before:**
```python
if not url:
    raise ValueError("URL required")
```

**After:**
```python
from data_fetcher_core.exceptions import ValidationError
if not url:
    raise ValidationError("URL required", "url")
```

### From Old BundleRef Creation

**Before:**
```python
bundle_ref = BundleRef.from_dict(data)  # No validation
```

**After:**
```python
bundle_ref = BundleRef.from_dict(data)  # Full validation with clear errors
```
