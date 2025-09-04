# Structlog Setup and Usage

The OC Fetcher project uses [structlog](https://www.structlog.org/) for structured logging, providing better log formatting, context management, and integration with logging frameworks.

## Overview

Structlog is automatically configured when the `data_fetcher` package is imported. The configuration provides:

- **Structured logging** with key-value pairs
- **Automatic context variables** from `structlog.contextvars`
- **Color-coded console output** (when supported)
- **JSON output** for production environments
- **Integration with standard logging** for third-party libraries
- **Automatic timestamps** and log levels
- **Call site information** for debugging

## Environment Variables

Configure logging behavior using environment variables:

| Variable                    | Description             | Default          | Example                       |
| --------------------------- | ----------------------- | ---------------- | ----------------------------- |
| `OC_LOGGING_LEVEL`          | Overall logging level   | `"INFO"`         | `"DEBUG"`                     |
| `OC_LOGGING_HANDLER`        | Output format           | `"console-text"` | `"console-json"`              |
| `OC_LOGGING_CONSOLE_COLOR`  | Color mode              | `"auto"`         | `"force"`                     |
| `OC_LOGGING_PACKAGE_LEVELS` | Package-specific levels | `""`             | `"httpx:DEBUG,boto3:WARNING"` |

### Log Levels

- `DEBUG`: Detailed information for debugging
- `INFO`: General information about program execution
- `WARNING`: Warning messages for potentially problematic situations
- `ERROR`: Error messages for serious problems
- `CRITICAL`: Critical errors that may prevent the program from running

### Handler Types

- `console-text`: Human-readable text output (default)
- `console-json`: JSON-structured output for log aggregation

### Console Color Modes

- `auto`: Use colors if terminal supports them (default)
- `force`: Always use colors
- `off`: Never use colors

## Usage Examples

### Basic Logging

```python
import structlog

# Get a logger for your module
logger = structlog.get_logger(__name__)

# Basic logging
logger.info("Starting data fetch operation")

# Structured logging with context
logger.info(
    "Processing file",
    filename="data.csv",
    size_bytes=1024,
    checksum="abc123"
)
```

### Context Variables

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
logger.info("Starting operation")
logger.info("Processing step 1", step="authentication")
logger.info("Processing step 2", step="data_fetch")

# Clear context when done
clear_contextvars()
```

### Bound Loggers

Create loggers with pre-bound context:

```python
logger = structlog.get_logger(__name__).bind(
    component="sftp_loader",
    server="sftp.example.com"
)

# All messages from this logger include the bound context
logger.info("Connecting to SFTP server")
logger.info("Downloading file", filename="data.zip")
```

### Error Logging

```python
try:
    # Some operation that might fail
    result = risky_operation()
except Exception as e:
    logger.exception(
        "Operation failed",
        operation="data_fetch",
        error=str(e),
        error_type=type(e).__name__,
        exc_info=True  # Include full traceback
    )
```

### Different Log Levels

```python
logger = structlog.get_logger(__name__)

# Debug: Detailed information
logger.debug(
    "Processing configuration",
    config_keys=["storage", "kv_store"],
    env_vars_present=["OC_STORAGE_TYPE"]
)

# Info: General information
logger.info(
    "Starting fetch operation",
    target_countries=["us-il", "us-fl"],
    expected_files=150
)

# Warning: Potential issues
logger.warning(
    "Rate limit approaching",
    current_rate=45,
    max_rate=50
)

# Error: Problems
logger.exception(
    "Failed to connect",
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
logger.info("Processing file", filename=filename)
```

### Third-Party Libraries

Third-party libraries using standard logging will automatically be formatted by structlog. Package-specific log levels can be configured:

```bash
# Set specific log levels for packages
export OC_LOGGING_PACKAGE_LEVELS="httpx:DEBUG,boto3:WARNING,paramiko:WARNING"
```

## Configuration Examples

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

### Docker Environment

```yaml
version: '3.8'
services:
  oc-fetcher:
    build: .
    environment:
      - OC_LOGGING_LEVEL=INFO
      - OC_LOGGING_HANDLER=console-json
      - OC_LOGGING_PACKAGE_LEVELS=boto3:WARNING,paramiko:WARNING
```

## Best Practices

### 1. Use Structured Data

```python
# Good: Structured data
logger.info("Processing file", filename="data.csv", size=1024, status="success")

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
logger.info("Starting download")
logger.info("Download completed", files_downloaded=5)
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
        "Operation failed",
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
logger.info("Processing request")
logger.info("Request completed")

# Clear when done
clear_contextvars()
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

## Context Variables (Automatically Included)

Context variables are automatically included in all log messages:

```python
from structlog.contextvars import bind_contextvars
bind_contextvars(request_id="req_123", user_id="user_456")
logger.info("Processing request")  # Includes request_id and user_id
```
