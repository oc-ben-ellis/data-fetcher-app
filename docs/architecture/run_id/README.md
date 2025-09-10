# Run ID Architecture

## Overview

A **Run ID** is a unique identifier assigned to each execution of the OC Fetcher application. Run IDs are generated at the start of each run and provide end-to-end tracing and correlation across the entire data fetching pipeline.

## What is a Run ID?

A Run ID is a time-ordered, unique identifier that serves multiple purposes in the data fetching pipeline:

- **Execution Identification**: Each application run gets a unique identifier for tracking and correlation
- **End-to-End Tracing**: Run IDs are included in all log messages for complete observability
- **Recipe Context**: Run IDs include the recipe identifier for configuration tracking
- **Time-based Ordering**: Run IDs contain timestamp information for chronological sorting
- **Debugging and Monitoring**: Run IDs enable correlation of logs across all components

## Run ID Format

Run IDs follow a structured format that combines recipe identification with timestamp:

```
fetcher_{recipe_id}_{timestamp}
```

### Format Breakdown

- **Prefix**: `fetcher_` - Identifies this as a fetcher run
- **Recipe ID**: The configuration/recipe identifier (e.g., `fr`, `us-fl`)
- **Timestamp**: 14-digit timestamp in `YYYYMMDDHHMMSS` format
- **Total Format**: `fetcher_{recipe_id}_{YYYYMMDDHHMMSS}`

### Example Run IDs

```
fetcher_fr_20250906213609
fetcher_us-fl_20250127143022
fetcher_test_20250127143022
```

## Run ID Generation

Run IDs are automatically generated when the application starts:

```python
from data_fetcher_app.main import generate_run_id
from datetime import datetime

def generate_run_id(recipe_id: str) -> str:
    """Generate a unique run ID combining recipe_id and timestamp.

    Args:
        recipe_id: The recipe identifier.

    Returns:
        A unique run ID in the format: fetcher_{recipe_id}_{timestamp}
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"fetcher_{recipe_id}_{timestamp}"

# Example usage
run_id = generate_run_id("fr")
# Result: fetcher_fr_20250127143022
```

## Run ID Usage Throughout the Pipeline

### 1. Application Initialization

Run IDs are generated at the start of each application execution:

```python
# In main.py
def run_command(args: list[str] | None = None) -> None:
    # Extract recipe_id from arguments
    recipe_id = args[0]

    # Generate run_id
    run_id = generate_run_id(recipe_id)

    # Pass run_id to async main function
    args_dict = {
        "config_name": recipe_id,
        "run_id": run_id,
        # ... other configuration
    }

    asyncio.run(main_async(args_dict))
```

### 2. Context Binding

Run IDs are bound to the logging context for the entire execution:

```python
async def main_async(args: dict[str, Any]) -> None:
    run_id = args["run_id"]
    config_name = args["config_name"]

    # Bind run_id and config_id to context for all subsequent logs
    with log_bind(run_id=run_id, config_id=config_name):
        logger.info("STORAGE_MECHANISM_SELECTED", storage_type="s3")
        logger.info("FETCHER_RUN_STARTED", concurrency=4)
        # All log messages will include run_id and config_id
```

### 3. FetchRunContext Integration

Run IDs are included in the `FetchRunContext` for the entire fetch operation:

```python
from data_fetcher_core.core import FetchRunContext, FetchPlan

# Create run context with run_id
run_context = FetchRunContext(run_id=run_id)

# Create fetch plan with run context
plan = FetchPlan(
    requests=[],
    context=run_context,
    concurrency=4
)

# Run the fetcher
result = await fetcher.run(plan)
```

### 4. Fetcher Integration

The fetcher uses run IDs for logging and coordination:

```python
class Fetcher:
    async def run(self, plan: FetchPlan) -> FetchResult:
        # Initialize the run context
        self.run_ctx = plan.context

        logger.info(
            "Starting fetcher run",
            run_id=self.run_ctx.run_id,
            concurrency=plan.concurrency,
            initial_requests=len(plan.requests),
        )

        # ... processing logic ...

        logger.info("ALL_WORKERS_COMPLETED", run_id=self.run_ctx.run_id)
```

## Run ID Benefits

### 1. End-to-End Tracing

Run IDs provide complete observability:
- All log messages include the run ID
- Easy correlation of logs across components
- Complete execution trace from start to finish

### 2. Recipe Context

Run IDs include recipe information:
- Identifies which configuration was used
- Enables analysis of recipe-specific performance
- Supports multi-recipe environments

### 3. Time-based Organization

Run IDs contain timestamp information:
- Chronological sorting of executions
- Time-based analysis and debugging
- Historical execution tracking

### 4. Unique Identification

Each execution has a guaranteed unique identifier:
- Prevents confusion between concurrent runs
- Supports parallel execution tracking
- Enables run-specific debugging

## Log Message Examples

### JSON Format (Production)
```json
{
  "timestamp": "2025-01-27T14:30:22Z",
  "level": "info",
  "logger": "data_fetcher_core.fetcher",
  "message": "Starting fetcher run",
  "run_id": "fetcher_fr_20250127143022",
  "config_id": "fr",
  "concurrency": 4,
  "initial_requests": 0,
  "bundle_locators": 1
}
```

### Text Format (Development)
```
2025-01-27 14:30:22 [info     ] Starting fetcher run [run_id=fetcher_fr_20250127143022 config_id=fr concurrency=4]
2025-01-27 14:30:23 [info     ] Processing request [run_id=fetcher_fr_20250127143022 url=https://example.com]
2025-01-27 14:30:24 [info     ] All workers completed [run_id=fetcher_fr_20250127143022]
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

## Integration Points

### Application Entry Point

Run IDs are generated at the application entry point:

```python
# Command line execution
poetry run python -m data_fetcher_app.main run fr

# Generates: fetcher_fr_20250127143022
```

### Logging Context

Run IDs are bound to the logging context:

```python
from openc_python_common.observability import log_bind

with log_bind(run_id="fetcher_fr_20250127143022", config_id="fr"):
    # All log messages in this context include run_id and config_id
    logger.info("DATA_PROCESSING")
    logger.info("BUNDLE_CREATED", bid="17571960-2065-e0cd-cf71-8196d8577b7e")
```

### FetchRunContext

Run IDs are included in the fetch run context:

```python
@dataclass
class FetchRunContext:
    """Context for a fetch run."""

    shared: dict[str, Any] = field(default_factory=dict)
    run_id: str | None = None  # Run ID for execution tracking
```

### Fetcher Integration

The fetcher uses run IDs for coordination and logging:

```python
class Fetcher:
    async def run(self, plan: FetchPlan) -> FetchResult:
        self.run_ctx = plan.context

        logger.info(
            "Starting fetcher run",
            run_id=self.run_ctx.run_id,  # Run ID for tracing
            concurrency=plan.concurrency,
        )
```

## Best Practices

### 1. Always Include Run ID in Logging

```python
# Good: Run ID is automatically bound to context
with log_bind(run_id=run_id, config_id=config_name):
    logger.info("DATA_PROCESSING")  # Includes run_id

# Avoid: Logging without run ID context
logger.info("DATA_PROCESSING")  # Missing run_id correlation
```

### 2. Use Run ID for Execution Tracking

```python
# Include run_id in execution metadata
execution_metadata = {
    "run_id": run_id,
    "recipe_id": recipe_id,
    "start_time": datetime.now(),
    "status": "running"
}
```

### 3. Combine Run ID with BID for Complete Tracing

```python
# Complete traceability with both identifiers
logger.info(
    "Bundle processing completed",
    run_id=run_id,           # Execution context
    bid=str(bundle_ref.bid), # Bundle context
    url=bundle_ref.primary_url,
    resources_count=bundle_ref.resources_count
)
```

## Future Extensibility

Run IDs provide a foundation for future enhancements:

1. **Execution Analytics**: Analyze execution patterns using run ID timestamps
2. **Performance Monitoring**: Track execution performance by run ID
3. **Error Correlation**: Correlate errors across components using run ID
4. **Resource Tracking**: Monitor resource usage per execution
5. **Audit Logging**: Complete audit trail using run ID correlation

## Related Documentation

- [Bundle ID (BID) Architecture](../bid/README.md) - Bundle-level identification and relationship with Run IDs
- [Logging Development Guide](../../contributing/logging_development.md) - Run ID integration in logging
- [Orchestration Architecture](../orchestration/README.md) - How run IDs flow through the system
- [User Guide - Command Line Usage](../../user_guide/command_line_usage.md) - Run ID in CLI usage
