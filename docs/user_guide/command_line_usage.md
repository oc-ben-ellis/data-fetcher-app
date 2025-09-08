# Command Line Usage

This guide covers how to run the Data Fetcher application from the command line using the openc_python_common-based CLI with subcommand structure and explicit configuration system.

## Basic Usage

The main entry point is the `data_fetcher_app.main` module with subcommands:

```bash
# Show help and available commands
poetry run python -m data_fetcher_app.main --help

# Run a recipe
poetry run python -m data_fetcher_app.main run <recipe_id>

# List available recipes
poetry run python -m data_fetcher_app.main list

# Start health check server
poetry run python -m data_fetcher_app.main health
```

## Configuration System

The application now uses an explicit configuration system that creates instances based on CLI arguments and environment variables, eliminating global state dependencies. Configuration components are:

- **Credential Provider**: Manages authentication credentials
- **Key-Value Store**: Handles persistence and caching
- **Storage Configuration**: Manages data storage (S3, file, etc.)

All configuration is created explicitly and passed through the application, making it more testable and maintainable.

## Available Recipes

List all available recipes:

```bash
poetry run python -m data_fetcher_app.main list
```

This will show output like:
```
Available fetcher recipes:

  fr
  us-fl

Total: 2 recipe(s)

Use 'python -m data_fetcher_app.main run <recipe_id>' to run a specific recipe.
```

## Running Specific Recipes

### US Florida SFTP Recipe

```bash
# Run the US Florida SFTP fetcher
poetry run python -m data_fetcher_app.main run us-fl
```

### France API Recipe

```bash
# Run the France API fetcher
poetry run python -m data_fetcher_app.main run fr
```

## Health Check Server

The application includes a built-in health check server for monitoring and load balancer integration:

```bash
# Start health check server on default port 8080
poetry run python -m data_fetcher_app.main health

# Start on custom port
poetry run python -m data_fetcher_app.main health --port 8081

# Start on custom host and port
poetry run python -m data_fetcher_app.main health --host 0.0.0.0 --port 8080
```

### Health Check Endpoints

The health server provides three endpoints:

- **`/health`** - Simple healthy/unhealthy status (JSON response)
- **`/status`** - Detailed application status with uptime and individual check results
- **`/heartbeat`** - Lightweight endpoint for load balancers (plain text "OK" or "FAIL")

Example responses:

```bash
# Health endpoint
curl http://localhost:8080/health
{"status": "healthy"}

# Status endpoint
curl http://localhost:8080/status
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

# Heartbeat endpoint
curl http://localhost:8080/heartbeat
OK
```

## Credential Providers

The application supports different credential providers for different deployment scenarios.

### AWS Secrets Manager (Default)

```bash
# Use AWS Secrets Manager (default behavior)
poetry run python -m data_fetcher_app.main run us-fl

# Explicitly specify AWS provider
poetry run python -m data_fetcher_app.main run us-fl --credentials-provider aws
```

### Environment Variables

```bash
# Use environment variables for credentials
poetry run python -m data_fetcher_app.main run us-fl --credentials-provider env
```

## Environment Variable Setup

When using the environment variable credential provider, set credentials in this format:

### For US Florida Configuration (us-fl)

```bash
export OC_CREDENTIAL_US_FL_HOST="sftp.example.com"
export OC_CREDENTIAL_US_FL_USERNAME="username"
export OC_CREDENTIAL_US_FL_PASSWORD="password"
```

### For France API Configuration (fr)

```bash
export OC_CREDENTIAL_FR_CLIENT_ID="client-id"
export OC_CREDENTIAL_FR_CLIENT_SECRET="client-secret"
```

**Note**: Recipe names with hyphens (e.g., 'us-fl') are converted to underscores (e.g., 'US_FL') in environment variable names.

## Storage and Persistence Options

The application supports multiple storage and persistence mechanisms:

### Storage Options

```bash
# Use S3 storage (default)
poetry run python -m data_fetcher_app.main run us-fl --storage s3

# Use local file storage
poetry run python -m data_fetcher_app.main run us-fl --storage file
```

### Key-Value Store Options

```bash
# Use Redis for persistence
poetry run python -m data_fetcher_app.main run us-fl --kvstore redis

# Use in-memory storage (default)
poetry run python -m data_fetcher_app.main run us-fl --kvstore memory
```

## Command Line Arguments

### Recipe ID

```bash
# Specify recipe ID as argument to run command
poetry run python -m data_fetcher_app.main run us-fl

# Or set via environment variable
export DATA_FETCHER_APP_RECIPE_ID=us-fl
poetry run python -m data_fetcher_app.main run us-fl
```

### Credential Provider

```bash
# Choose credential provider
poetry run python -m data_fetcher_app.main run us-fl --credentials-provider aws
poetry run python -m data_fetcher_app.main run us-fl --credentials-provider env
```

### Storage and KVStore Options

```bash
# Choose storage mechanism
poetry run python -m data_fetcher_app.main run us-fl --storage s3
poetry run python -m data_fetcher_app.main run us-fl --storage file

# Choose key-value store
poetry run python -m data_fetcher_app.main run us-fl --kvstore redis
poetry run python -m data_fetcher_app.main run us-fl --kvstore memory
```

### Logging Options

```bash
# Set log level
poetry run python -m data_fetcher_app.main run us-fl --log-level DEBUG

# Enable development mode (human-readable logs)
poetry run python -m data_fetcher_app.main run us-fl --dev-mode
```

### Help

```bash
# Show help message
poetry run python -m data_fetcher_app.main --help

# Show help for specific command
poetry run python -m data_fetcher_app.main run --help
```

## Examples

### Basic Examples

```bash
# Run US Florida SFTP fetcher with AWS credentials
poetry run python -m data_fetcher_app.main run us-fl

# Run France API fetcher with environment variables
poetry run python -m data_fetcher_app.main run fr --credentials-provider env

# List available recipes
poetry run python -m data_fetcher_app.main list

# Start health check server
poetry run python -m data_fetcher_app.main health
```

### Development Examples

```bash
# Run with verbose logging and development mode
poetry run python -m data_fetcher_app.main run us-fl --log-level DEBUG --dev-mode

# Run with specific AWS profile
export AWS_PROFILE=my-profile
poetry run python -m data_fetcher_app.main run us-fl

# Run with file storage and in-memory kvstore for development
poetry run python -m data_fetcher_app.main run fr \
  --credentials-provider env \
  --storage file \
  --kvstore memory \
  --dev-mode

# Start health server on custom port for development
poetry run python -m data_fetcher_app.main health --port 8081 --dev-mode
```

## Output and Logging

The application uses structured logging with JSON output by default, powered by openc_python_common. Logs include:

- Configuration information
- Progress updates with timing metrics
- Error details with full context
- Performance metrics and observability data
- Run ID tracking for each execution

### Log Levels

Set the log level using command line arguments or environment variables:

```bash
# Command line
poetry run python -m data_fetcher_app.main run us-fl --log-level DEBUG

# Environment variable
export DATA_FETCHER_APP_LOG_LEVEL=DEBUG
poetry run python -m data_fetcher_app.main run us-fl
```

Available log levels:
- `DEBUG` - Verbose debugging information
- `INFO` - General information (default)
- `WARNING` - Warning messages only
- `ERROR` - Error messages only

### Development Mode

Use development mode for human-readable console output:

```bash
poetry run python -m data_fetcher_app.main run us-fl --dev-mode
```

### Run ID and Context

Each execution generates a unique run ID in the format `fetcher_{recipe_id}_{timestamp}` that appears in all log messages:

```json
{
  "event": "Using storage mechanism",
  "config_id": "fr",
  "run_id": "fetcher_fr_20250906213609",
  "storage_type": "s3",
  "kvstore_type": "memory"
}
```

## Error Handling

The application provides detailed error messages for common issues:

- **Missing configuration**: Shows available configurations
- **Credential errors**: Provides guidance on credential setup
- **Network issues**: Shows connection details and retry information
- **Permission errors**: Indicates required permissions

## Performance Considerations

- The application uses streaming to handle large files efficiently
- Concurrent processing is configured per protocol
- Memory usage is optimized for large datasets
- Progress is logged for long-running operations

## Troubleshooting

### Common Issues

1. **"recipe_id is required for run command"**
   - Provide a recipe ID as an argument to the run command
   - Or set the `DATA_FETCHER_APP_RECIPE_ID` environment variable

2. **"Unknown recipe"**
   - Check available recipes with `poetry run python -m data_fetcher_app.main list`
   - Verify the recipe name is correct

3. **Credential errors**
   - Ensure credentials are properly configured
   - Check AWS profile or environment variables
   - Verify credential provider is correct

### Getting Help

- Use `--help` for command line options
- Check the [Troubleshooting](../troubleshooting/troubleshooting_guide.md) guide
- Review configuration-specific documentation in [Configurations](../configurations/creating_a_recipe.md)
