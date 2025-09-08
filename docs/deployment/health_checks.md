# Health Check System

This guide covers the built-in health check system for monitoring and load balancer integration.

## Overview

The Data Fetcher application includes a comprehensive health check system that provides endpoints for monitoring application status, uptime, and individual component health. The system is built using a simple WSGI router and integrates with the application's observability features.

## Starting the Health Check Server

### Basic Usage

```bash
# Start health check server on default port 8080
poetry run python -m data_fetcher_app.main health

# Start on custom port
poetry run python -m data_fetcher_app.main health --port 8081

# Start on custom host and port
poetry run python -m data_fetcher_app.main health --host 0.0.0.0 --port 8080
```

### Configuration Options

```bash
# Available options
--host HOST          # Host to bind to (default: 0.0.0.0)
--port PORT          # Port to bind to (default: 8080)
--log-level LEVEL    # Log level (default: INFO)
--dev-mode           # Enable development mode logging
```

### Environment Variables

All options can also be set via environment variables:

```bash
export DATA_FETCHER_APP_HOST=0.0.0.0
export DATA_FETCHER_APP_PORT=8080
export DATA_FETCHER_APP_LOG_LEVEL=INFO
export DATA_FETCHER_APP_DEV_MODE=true
```

## Health Check Endpoints

The health check server provides three endpoints:

### `/health` - Simple Health Status

Returns a simple healthy/unhealthy status in JSON format.

**Request:**
```bash
curl http://localhost:8080/health
```

**Response (Healthy):**
```json
{
  "status": "healthy"
}
```

**Response (Unhealthy):**
```json
{
  "status": "unhealthy"
}
```

**HTTP Status Codes:**
- `200 OK` - Application is healthy
- `503 Service Unavailable` - Application is unhealthy

### `/status` - Detailed Application Status

Returns comprehensive application status including uptime and individual check results.

**Request:**
```bash
curl http://localhost:8080/status
```

**Response:**
```json
{
  "app_name": "data-fetcher-app",
  "status": "healthy",
  "uptime_seconds": 123.45,
  "timestamp": 1757194202.1328213,
  "checks": {
    "basic": {
      "status": "pass",
      "error": null
    }
  }
}
```

**Response Fields:**
- `app_name` - Application name
- `status` - Overall health status ("healthy" or "unhealthy")
- `uptime_seconds` - Application uptime in seconds
- `timestamp` - Unix timestamp of the status check
- `checks` - Individual health check results

**HTTP Status Codes:**
- `200 OK` - Application is healthy
- `503 Service Unavailable` - Application is unhealthy

### `/heartbeat` - Load Balancer Endpoint

Returns a simple text response for load balancer health checks.

**Request:**
```bash
curl http://localhost:8080/heartbeat
```

**Response (Healthy):**
```
OK
```

**Response (Unhealthy):**
```
FAIL
```

**HTTP Status Codes:**
- `200 OK` - Application is healthy
- `503 Service Unavailable` - Application is unhealthy

## Health Check Implementation

### Basic Health Checks

The system includes a basic health check that always returns `true`:

```python
def always_healthy() -> bool:
    """Basic health check that always returns True."""
    return True

health_check.add_check("basic", always_healthy)
```

### Adding Custom Health Checks

You can extend the health check system by adding custom checks:

```python
from data_fetcher_app.health import HealthCheck

# Create a custom health check
def database_health_check() -> bool:
    """Check database connectivity."""
    try:
        # Your database check logic here
        return True
    except Exception:
        return False

def redis_health_check() -> bool:
    """Check Redis connectivity."""
    try:
        # Your Redis check logic here
        return True
    except Exception:
        return False

# Add checks to the health check instance
health_check.add_check("database", database_health_check)
health_check.add_check("redis", redis_health_check)
```

### Health Check Results

Individual health checks can return:
- `True` - Check passed
- `False` - Check failed
- Exception - Check error (treated as failed)

## Observability Integration

The health check system integrates with the application's observability features:

### Automatic Logging

All health check endpoints automatically log with timing information:

```json
{
  "event": "HEALTH_CHECK_END",
  "endpoint": "health",
  "ok": true,
  "duration_s": 0.00018376899970462546,
  "level": "info",
  "timestamp": "2025-09-06T21:36:09.651714Z"
}
```

### Log Events

- `HEALTH_CHECK_BEGIN` / `HEALTH_CHECK_END` - For `/health` endpoint
- `STATUS_CHECK_BEGIN` / `STATUS_CHECK_END` - For `/status` endpoint
- `HEARTBEAT_CHECK_BEGIN` / `HEARTBEAT_CHECK_END` - For `/heartbeat` endpoint

## Deployment Integration

### Load Balancer Configuration

Configure your load balancer to use the `/heartbeat` endpoint:

```yaml
# Example Kubernetes health check
livenessProbe:
  httpGet:
    path: /heartbeat
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
```

### Docker Health Check

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1
```

### Monitoring Integration

Use the `/status` endpoint for detailed monitoring:

```bash
# Example monitoring script
#!/bin/bash
STATUS=$(curl -s http://localhost:8080/status)
UPTIME=$(echo $STATUS | jq -r '.uptime_seconds')
HEALTH=$(echo $STATUS | jq -r '.status')

echo "Health: $HEALTH, Uptime: $UPTIME seconds"
```

## Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Use a different port
   poetry run python -m data_fetcher_app.main health --port 8081
   ```

2. **Health check fails**
   - Check application logs for errors
   - Verify all dependencies are available
   - Check individual health check results in `/status` endpoint

3. **Load balancer not detecting health**
   - Ensure the health server is running
   - Check firewall settings
   - Verify the correct endpoint is being used (`/heartbeat` for load balancers)

### Debugging

Enable debug logging to troubleshoot health check issues:

```bash
poetry run python -m data_fetcher_app.main health --log-level DEBUG --dev-mode
```

This will provide detailed information about health check execution and any errors.
