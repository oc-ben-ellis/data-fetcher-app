# Bundle ID (BID) Architecture

## Overview

A **Bundle ID (BID)** is a unique identifier assigned to each bundle within the OC Fetcher framework. BIDs are implemented as UUIDv7-like identifiers that combine timestamp information with random bits to ensure both uniqueness and chronological ordering.

## What is a BID?

A BID is a time-ordered, unique identifier that serves multiple purposes in the data fetching pipeline:

- **Unique Identification**: Each bundle gets a unique identifier for tracking and correlation
- **Time-based Ordering**: BIDs contain timestamp information for chronological sorting
- **Tracing and Debugging**: BIDs are included in logging contexts for enhanced observability
- **Storage Organization**: Storage layers can use BIDs for path determination and organization

## BID Format

BIDs follow a UUIDv7-like format that combines timestamp and randomness:

```
{timestamp_ms}-{random_hex}
```

### Format Breakdown

- **Timestamp Part**: 13 digits representing milliseconds since Unix epoch
- **Random Part**: 20 hexadecimal characters providing uniqueness
- **Total Format**: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

### Example BID

```
17571960-2065-e0cd-cf71-8196d8577b7e
```

## BID Generation

BIDs are automatically generated when `BundleRef` objects are created:

```python
from data_fetcher_core.core import BundleRef, BID

# Automatic BID generation
bundle_ref = BundleRef(
    primary_url="https://example.com",
    resources_count=1
)
print(f"Generated BID: {bundle_ref.bid}")

# Custom BID
custom_bid = BID("custom-bundle-id")
bundle_ref = BundleRef(
    primary_url="https://example.com",
    resources_count=1,
    bid=custom_bid
)
```

## BID Usage Throughout the Pipeline

### 1. Loader Integration

Loaders generate BIDs when creating `BundleRef` objects and include them in logging contexts:

```python
# Create bundle reference with auto-generated BID
bundle_ref = BundleRef(
    primary_url=request.url,
    resources_count=1,
    meta={"status_code": response.status_code}
)

# Create logger with BID context for tracing
bid_logger = logger.bind(bid=str(bundle_ref.bid))
bid_logger.info("BUNDLE_CREATED_SUCCESSFULLY", url=request.url)
```

### 2. Storage Layer Integration

Storage implementations use BIDs for file and directory organization:

#### File Storage
```python
# Directory naming using BID
bundle_dir = f"bundle_{bundle_ref.bid}"
# Example: bundle_17571960-2065-e0cd-cf71-8196d8577b7e
```

#### S3 Storage
```python
# S3 key organization using BID
s3_key = f"{prefix}/bundles/{bundle_ref.bid}/resources"
# Example: data/bundles/17571960-2065-e0cd-cf71-8196d8577b7e/resources
```

### 3. Logging and Tracing

BIDs are bound to loggers for consistent tracing across the pipeline:

```python
# All log messages include the BID for correlation
bid_logger = logger.bind(bid=str(bundle_ref.bid))
bid_logger.debug("STREAMING_TO_STORAGE", url=request.url)
bid_logger.info("BUNDLE_PROCESSING_COMPLETED")
```

## BID Benefits

### 1. Time-based Organization

BIDs contain timestamp information, enabling:
- Chronological sorting of bundles
- Time-based storage organization
- Historical analysis and debugging

### 2. Enhanced Debugging

BID context in logs provides:
- Correlation of log messages across components
- End-to-end tracing of bundle processing
- Easier troubleshooting and monitoring

### 3. Storage Flexibility

Storage layers can leverage BIDs for:
- Time-based directory structures
- Efficient file organization
- Future deduplication capabilities

### 4. Unique Identification

Each bundle has a guaranteed unique identifier for:
- Tracking bundle lifecycle
- Preventing conflicts
- Supporting future features like retry logic

## BID Class API

The `BID` class provides a simple interface for working with bundle identifiers:

```python
from data_fetcher_core.core import BID

# Create a new BID
bid = BID()
print(f"BID: {bid}")

# Create BID with custom value
custom_bid = BID("custom-value")

# Generate new BID using class method
new_bid = BID.generate()

# Access the underlying value
bid_value = bid.value

# Equality and hashing
bid1 = BID("same-value")
bid2 = BID("same-value")
assert bid1 == bid2
assert hash(bid1) == hash(bid2)
```

## Integration Points

### BundleRef Integration

BIDs are automatically included in `BundleRef` objects:

```python
@dataclass
class BundleRef:
    primary_url: Url
    resources_count: int
    bid: BID = field(default_factory=BID.generate)  # Auto-generated
    storage_key: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)
```

### Loader Integration

All loaders automatically generate BIDs and include them in logging:

- `HttpBundleLoader`
- `SftpBundleLoader`
- `StreamingHttpBundleLoader`

### Storage Integration

Storage implementations use BIDs for organization:

- `FileStorage`: BID-based directory naming
- `S3StorageBundle`: BID-based S3 key structure
- Metadata storage includes BID information

## Future Extensibility

BIDs provide a foundation for future enhancements:

1. **Deduplication**: Use BIDs to identify and prevent duplicate processing
2. **Retry Logic**: Track failed bundles by BID for retry mechanisms
3. **Analytics**: Analyze bundle processing patterns using BID timestamps
4. **Caching**: Use BIDs as cache keys for processed bundles
5. **Monitoring**: Track bundle processing metrics using BID correlation

## Best Practices

### 1. Always Use BID Context in Logging

```python
# Good: Include BID in logging context
bid_logger = logger.bind(bid=str(bundle_ref.bid))
bid_logger.info("BUNDLE_PROCESSING")

# Avoid: Logging without BID context
logger.info("BUNDLE_PROCESSING")  # Harder to correlate
```

### 2. Preserve BID in Storage Metadata

```python
# Include BID in storage metadata
metadata = {
    "bid": str(bundle_ref.bid),
    "primary_url": bundle_ref.primary_url,
    "resources_count": bundle_ref.resources_count,
    # ... other metadata
}
```

### 3. Use BID for File Organization

```python
# Use BID for consistent file organization
file_path = f"{base_dir}/bundles/{bundle_ref.bid}/data"
```

## Run ID vs Bundle ID (BID)

While both Run IDs and BIDs provide unique identification, they serve different purposes:

| Aspect          | Run ID                              | Bundle ID (BID)                      |
| --------------- | ----------------------------------- | ------------------------------------ |
| **Scope**       | Entire application execution        | Individual bundle                    |
| **Lifetime**    | Duration of application run         | Duration of bundle processing        |
| **Format**      | `fetcher_{recipe_id}_{timestamp}`   | UUIDv7-like with timestamp           |
| **Purpose**     | Execution tracing and correlation   | Bundle identification and storage    |
| **Usage**       | Logging context, execution tracking | Storage organization, bundle tracing |
| **Granularity** | One per application run             | One per bundle created               |

### Relationship

```python
# Run ID: Identifies the entire execution
run_id = "fetcher_fr_20250127143022"

# BID: Identifies individual bundles within the run
bundle_ref = BundleRef(
    primary_url="https://example.com",
    resources_count=1
)
bundle_bid = str(bundle_ref.bid)  # e.g., "17571960-2065-e0cd-cf71-8196d8577b7e"

# Both appear in logs for complete traceability
logger.info(
    "Bundle created",
    run_id=run_id,           # Execution context
    bid=bundle_bid,          # Bundle context
    url="https://example.com"
)
```

## Related Documentation

- [Run ID Architecture](run_id/README.md) - Execution identification and tracing system
- [Storage Architecture](storage/README.md) - How storage uses BIDs for organization
- [Loaders Architecture](loaders/README.md) - How loaders generate and use BIDs
- [Logging Development Guide](../../contributing/logging_development.md) - BID integration in logging
