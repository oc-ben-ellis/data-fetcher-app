# Logging Development Guide

This guide covers how to use structured logging effectively when developing with the OC Fetcher framework.

## Overview

The OC Fetcher project uses [structlog](https://www.structlog.org/) for structured logging, powered by openc_python_common, providing better log formatting, context management, and integration with logging frameworks. The framework includes built-in observability features with timing instrumentation and run ID tracking.

## Basic Usage

### Getting a Logger

```python
import structlog

# Get a logger for your module
logger = structlog.get_logger(__name__)
```

### Basic Logging

```python
# Basic logging
logger.info("DATA_FETCH_OPERATION_STARTED")

# Structured logging with context
logger.info(
    "FILE_PROCESSING",
    filename="data.csv",
    size_bytes=1024,
    checksum="abc123"
)
```

## Logging Convention

### Message Format

All log messages must use **UPPER_SNAKE_CASE** format for consistency and better searchability:

```python
# ✅ Correct - UPPER_SNAKE_CASE format
logger.debug("FETCHER_RUN_STARTED", run_id=run_id, concurrency=concurrency)
logger.info("REQUEST_PROCESSING", url=url, status="success")
logger.warning("RATE_LIMIT_APPROACHING", current_rate=45, max_rate=50)
logger.error("CONNECTION_FAILED", server="sftp.example.com", retry_attempt=2)
logger.exception("REQUEST_PROCESSING_ERROR", url=url, error=str(e))

# ❌ Incorrect - Mixed case or sentence format
logger.debug("Starting fetcher run", run_id=run_id)
logger.info("Processing request", url=url)
logger.error("Connection failed", server="sftp.example.com")
```

### Error Logging Rules

1. **When raising exceptions immediately after logging**: Do NOT log the error
   ```python
   # ✅ Correct - No logging before raising
   if not run_ctx.run_id:
       error_msg = "run_id is required in FetchRunContext but was not provided"
       raise ValueError(error_msg)

   # ❌ Incorrect - Logging before raising
   if not run_ctx.run_id:
       error_msg = "run_id is required in FetchRunContext but was not provided"
       logger.error(error_msg)  # Remove this line
       raise ValueError(error_msg)
   ```

2. **When handling errors without raising**: Use `logger.exception` for better context
   ```python
   # ✅ Correct - Use logger.exception for error handling
   try:
       result = risky_operation()
   except Exception as e:
       logger.exception("OPERATION_FAILED", operation="data_fetch", error=str(e))
       # Handle the error gracefully

   # ✅ Also correct - Use logger.error for non-exception contexts
   if not check_health():
       logger.error("HEALTH_CHECK_FAILED", check_name="database")
   ```

### Common Message Patterns

Use these standardized message patterns for consistency:

```python
# Operation lifecycle
logger.info("FETCHER_RUN_STARTED", run_id=run_id)
logger.info("FETCHER_RUN_COMPLETED", run_id=run_id, processed_count=count)
logger.info("WORKER_STARTED", worker_id=worker_id)
logger.info("WORKER_COMPLETED", worker_id=worker_id)

# Request processing
logger.debug("REQUEST_PROCESSING", url=url)
logger.debug("REQUEST_PROCESSING_COMPLETED", url=url)
logger.exception("REQUEST_PROCESSING_ERROR", url=url, error=str(e))

# File operations
logger.debug("FILE_PROCESSING", filename=filename, size=size)
logger.debug("STREAMING_FILE_TO_STORAGE", remote_path=path)
logger.info("FILE_DOWNLOADED", filename=filename, size=size)

# Health checks
logger.warning("HEALTH_CHECK_FAILED", check_name=name)
logger.exception("HEALTH_CHECK_ERROR", check_name=name, error=str(e))

# Server operations
logger.info("SERVER_STARTING", host=host, port=port)
logger.info("SERVER_STARTED", host=host, port=port)
logger.exception("SERVER_START_ERROR", host=host, port=port, error=str(e))
```

## Context Variables

Use context variables to automatically include information in all log messages:

```python
from structlog.contextvars import bind_contextvars, clear_contextvars

# Bind context for this operation
bind_contextvars(
    request_id="req_12345",
    user_id="user_456",
    operation="data_fetch"
)

logger = structlog.get_logger(__name__)

# All log messages will include the context variables
logger.info("OPERATION_STARTED")
logger.info("PROCESSING_STEP", step="authentication")
logger.info("PROCESSING_STEP", step="data_fetch")

# Clear context when done
clear_contextvars()
```

## Observability Features

The framework includes built-in observability features powered by openc_python_common:

### Run ID Tracking

Each execution generates a unique run ID that appears in all log messages:

```python
# Run ID format: fetcher_{recipe_id}_{timestamp}
# Example: fetcher_fr_20250906213609

# The run ID is automatically bound to all log messages during execution
logger.info("DATA_PROCESSING")  # Will include run_id in output
```

### Timing Instrumentation

Use the `observe_around` decorator for automatic timing and logging:

```python
from openc_python_common.observability import observe_around

logger = structlog.get_logger(__name__)

# Automatic timing and logging
with observe_around(logger, "DATA_PROCESSING", file_count=10):
    # Your code here
    process_files()

# This will log:
# - "DATA_PROCESSING_BEGIN" with start time
# - "DATA_PROCESSING_END" with duration and success status
```

### Context Binding

Use `log_bind` for automatic context binding:

```python
from openc_python_common.observability import log_bind

# Bind context for the entire operation
with log_bind(run_id="fetcher_fr_20250906213609", config_id="fr"):
    logger.info("OPERATION_STARTED")  # Includes run_id and config_id
    logger.info("PROCESSING_STEP")     # Includes run_id and config_id
```

## Bound Loggers

Create loggers with pre-bound context:

```python
logger = structlog.get_logger(__name__).bind(
    component="sftp_loader",
    server="sftp.example.com"
)

# All messages from this logger include the bound context
logger.info("SFTP_SERVER_CONNECTING")
logger.info("FILE_DOWNLOADING", filename="data.zip")
```

## Error Logging

```python
try:
    # Some operation that might fail
    result = risky_operation()
except Exception as e:
    logger.exception(
        "OPERATION_FAILED",
        operation="data_fetch",
        error=str(e),
        error_type=type(e).__name__,
        exc_info=True  # Include full traceback
    )
```

## Health Check Logging

The health check system includes built-in observability:

```python
# Health check endpoints automatically log with timing
# GET /health -> logs "HEALTH_CHECK_BEGIN" and "HEALTH_CHECK_END"
# GET /status -> logs "STATUS_CHECK_BEGIN" and "STATUS_CHECK_END"
# GET /heartbeat -> logs "HEARTBEAT_CHECK_BEGIN" and "HEARTBEAT_CHECK_END"

# Example log output:
{
  "event": "HEALTH_CHECK_END",
  "endpoint": "health",
  "ok": true,
  "duration_s": 0.00018376899970462546,
  "level": "info"
}
```

## Different Log Levels

```python
logger = structlog.get_logger(__name__)

# Debug: Detailed information
logger.debug(
    "CONFIGURATION_PROCESSING",
    config_keys=["storage", "kv_store"],
    env_vars_present=["OC_STORAGE_TYPE"]
)

# Info: General information
logger.info(
    "FETCH_OPERATION_STARTING",
    target_countries=["us-il", "us-fl"],
    expected_files=150
)

# Warning: Potential issues
logger.warning(
    "RATE_LIMIT_APPROACHING",
    current_rate=45,
    max_rate=50
)

# Error: Problems
logger.exception(
    "CONNECTION_FAILED",
    server="sftp.example.com",
    retry_attempt=2
)
```

## Integration with Existing Code

### Replacing Standard Logging

Replace standard logging with structlog:

```python
# Before (standard logging)
import logging
logger = logging.getLogger(__name__)
logger.info("Processing file %s", filename)

# After (structlog)
import structlog
logger = structlog.get_logger(__name__)
logger.info("FILE_PROCESSING", filename=filename)
```

### Third-Party Libraries

Third-party libraries using standard logging will automatically be formatted by structlog. Package-specific log levels can be configured:

```bash
# Set specific log levels for packages
export OC_LOGGING_PACKAGE_LEVELS="httpx:DEBUG,boto3:WARNING,paramiko:WARNING"
```

## Configuration for Development

### Development Environment

```bash
# Verbose logging for development
export OC_LOGGING_LEVEL=DEBUG
export OC_LOGGING_HANDLER=console-text
export OC_LOGGING_CONSOLE_COLOR=force
export OC_LOGGING_PACKAGE_LEVELS="httpx:DEBUG"
```

### Production Environment

```bash
# JSON logging for production
export OC_LOGGING_LEVEL=INFO
export OC_LOGGING_HANDLER=console-json
export OC_LOGGING_PACKAGE_LEVELS="boto3:WARNING,paramiko:WARNING"
```

## Best Practices

### 1. Use Structured Data

```python
# Good: Structured data with UPPER_SNAKE_CASE
logger.info("FILE_PROCESSING", filename="data.csv", size=1024, status="success")

# Avoid: String formatting
logger.info(f"Processing file data.csv with size 1024, status: success")
```

### 2. Include Context

```python
# Bind context for operations
logger = structlog.get_logger(__name__).bind(
    operation="sftp_download",
    server="sftp.example.com"
)

# All messages include operation and server context
logger.info("DOWNLOAD_STARTING")
logger.info("DOWNLOAD_COMPLETED", files_downloaded=5)
```

### 3. Use Appropriate Log Levels

- `DEBUG`: Detailed debugging information
- `INFO`: General operational information
- `WARNING`: Potential issues that don't stop operation
- `ERROR`: Problems that affect functionality
- `CRITICAL`: Critical failures

### 4. Include Error Context

```python
try:
    result = operation()
except Exception as e:
    logger.exception(
        "OPERATION_FAILED",
        operation="data_fetch",
        error=str(e),
        error_type=type(e).__name__,
        exc_info=True
    )
```

### 5. Use Context Variables for Request-Scoped Data

```python
from structlog.contextvars import bind_contextvars

# Bind request-scoped context
bind_contextvars(request_id="req_123", user_id="user_456")

# All log messages in this context include request_id and user_id
logger.info("REQUEST_PROCESSING")
logger.info("REQUEST_COMPLETED")

# Clear when done
clear_contextvars()
```

## Log Format Examples

### Text Format (Development)
```
2025-01-27 10:30:00 [info     ] DATA_FETCH_OPERATION_STARTED [config_id=us-fl]
2025-01-27 10:30:01 [info     ] FILE_PROCESSING [filename=data.csv size_bytes=1024 checksum=abc123]
```

### JSON Format (Production)
```json
{
  "timestamp": "2025-01-27T10:30:00Z",
  "level": "info",
  "logger": "data_fetcher_core.fetcher",
  "message": "FETCHER_RUN_STARTED",
  "config_id": "us-fl",
  "event": "FETCHER_RUN_STARTED"
}
```

## Troubleshooting

### Logs Not Appearing

1. Check the log level configuration
2. Verify environment variables are set correctly
3. Ensure the `data_fetcher` package is imported (triggers logging setup)

### JSON Output Issues

1. Set `OC_LOGGING_HANDLER=console-json`
2. Ensure your log aggregation system can parse JSON
3. Check that all log data is JSON-serializable

### Performance Issues

1. Use appropriate log levels (avoid DEBUG in production)
2. Limit the amount of data logged
3. Use context variables instead of repeating data

### Integration Issues

1. Ensure structlog is configured before other logging
2. Check package-specific log levels
3. Verify third-party libraries are using standard logging
