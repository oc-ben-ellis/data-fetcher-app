# Application Configuration System

The OC Fetcher framework provides a consistent application configuration system using environment variables. This system allows you to configure storage, key-value stores, and credential providers without modifying code.

## Overview

The application configuration system consists of three main components:

1. **Application Storage** (`global_storage.py`) - Configures data storage (S3, file system)
2. **Application Key-Value Store** (`global_kv_store.py`) - Configures caching and state management
3. **Application Credential Provider** (`global_credential_provider.py`) - Configures authentication

All configurations use environment variables with sensible defaults, making the system easy to deploy in different environments.

## Environment Variables

### Storage Configuration

| Variable               | Description                                                 | Default             | Example             |
| ---------------------- | ----------------------------------------------------------- | ------------------- | ------------------- |
| `OC_STORAGE_TYPE`      | Storage type to use                                         | `"s3"`              | `"file"`            |
| `OC_S3_BUCKET`         | S3 bucket name                                              | `"oc-fetcher-data"` | `"my-company-data"` |
| `OC_S3_PREFIX`         | S3 key prefix                                               | `""`                | `"captures/2024/"`  |
| `AWS_REGION`           | Standard AWS region environment variable (takes precedence) | `"eu-west-2"`       | `"us-east-1"`       |
| `OC_S3_REGION`         | AWS region for S3 (fallback if AWS_REGION not set)          | `"eu-west-2"`       | `"eu-west-1"`       |
| `OC_STORAGE_FILE_PATH` | File storage path (when using file storage)                 | `"default_capture"` | `"/data/captures"`  |
| `OC_STORAGE_USE_UNZIP` | Enable unzip decorator                                      | `"true"`            | `"false"`           |

| `OC_STORAGE_USE_BUNDLER` | Enable bundler decorator                                    | `"true"`            | `"false"`           |

### Key-Value Store Configuration

| Variable                       | Description                              | Default           | Example               |
| ------------------------------ | ---------------------------------------- | ----------------- | --------------------- |
| `OC_KV_STORE_TYPE`             | Store type to use                        | `"memory"`        | `"redis"`             |
| `OC_KV_STORE_SERIALIZER`       | Serializer to use                        | `"json"`          | `"pickle"`            |
| `OC_KV_STORE_DEFAULT_TTL`      | Default TTL in seconds                   | `"3600"`          | `"7200"`              |
| `OC_KV_STORE_REDIS_HOST`       | Redis host (when using redis)            | `"localhost"`     | `"redis.example.com"` |
| `OC_KV_STORE_REDIS_PORT`       | Redis port (when using redis)            | `"6379"`          | `"6380"`              |
| `OC_KV_STORE_REDIS_DB`         | Redis database number (when using redis) | `"0"`             | `"1"`                 |
| `OC_KV_STORE_REDIS_PASSWORD`   | Redis password (when using redis)        | `""`              | `"secret123"`         |
| `OC_KV_STORE_REDIS_KEY_PREFIX` | Redis key prefix (when using redis)      | `"data_fetcher:"` | `"myapp:"`            |

### Credential Provider Configuration

| Variable                            | Description                                                     | Default            | Example         |
| ----------------------------------- | --------------------------------------------------------------- | ------------------ | --------------- |
| `OC_CREDENTIAL_PROVIDER_TYPE`       | Provider type to use                                            | `"aws"`            | `"environment"` |
| `AWS_REGION`                        | Standard AWS region environment variable (takes precedence)     | `"eu-west-2"`      | `"us-east-1"`   |
| `OC_CREDENTIAL_PROVIDER_AWS_REGION` | AWS region for Secrets Manager (fallback if AWS_REGION not set) | `"eu-west-2"`      | `"eu-west-1"`   |
| `OC_CREDENTIAL_PROVIDER_ENV_PREFIX` | Environment variable prefix for environment provider            | `"OC_CREDENTIAL_"` | `"MYAPP_CRED_"` |

**Note**: You can also override the credential provider at runtime using the `--credentials-provider` command line flag:
- `--credentials-provider aws` - Use AWS Secrets Manager (default)
- `--credentials-provider env` - Use environment variables

## Credential Providers

The framework supports multiple credential providers for different deployment scenarios. You can configure the default provider using environment variables or override it at runtime using command line flags.

### AWS Secrets Manager (Default)

The AWS provider fetches credentials from AWS Secrets Manager and is the default choice for production environments.

```bash
# Configure via environment variable
export OC_CREDENTIAL_PROVIDER_TYPE=aws
export AWS_REGION=eu-west-2

# Use via command line (default behavior)
poetry run python -m data_fetcher.main us-fl

# Explicitly specify AWS provider
poetry run python -m data_fetcher.main --credentials-provider aws us-fl
```

### Environment Variables

The environment provider reads credentials from environment variables, making it ideal for development, testing, and containerized deployments.

```bash
# Configure via environment variable
export OC_CREDENTIAL_PROVIDER_TYPE=environment
export OC_CREDENTIAL_PROVIDER_ENV_PREFIX=OC_CREDENTIAL_

# Use via command line
poetry run python -m data_fetcher.main --credentials-provider env us-fl
```

#### Environment Variable Format

When using the environment provider, set credentials in this format:

```bash
# For US Florida configuration (us-fl)
export OC_CREDENTIAL_US_FL_HOST="sftp.example.com"
export OC_CREDENTIAL_US_FL_USERNAME="username"
export OC_CREDENTIAL_US_FL_PASSWORD="password"

# For France API configuration (fr-api)
export OC_CREDENTIAL_FR_API_CLIENT_ID="client-id"
export OC_CREDENTIAL_FR_API_CLIENT_SECRET="client-secret"
```

**Important**: Configuration names with hyphens (e.g., 'us-fl') are converted to underscores (e.g., 'US_FL') in environment variable names.

#### Error Handling

The environment provider provides detailed error messages when credentials are missing:

```bash
$ poetry run python -m data_fetcher.main --credentials-provider env us-fl

Environment variable 'OC_CREDENTIAL_US_FL_HOST' not found. Please set the following environment variables:
  OC_CREDENTIAL_US_FL_HOST

Environment variable format: OC_CREDENTIAL_US_FL_HOST
Example: For config 'us-fl' and key 'username', set: OC_CREDENTIAL_US_FL_USERNAME
```

## Usage Examples

### Development Environment

For local development, you can use file storage and in-memory key-value store:

```bash
# Use file storage for local development
export OC_STORAGE_TYPE=file
export OC_STORAGE_FILE_PATH=./captures

# Use in-memory key-value store (default)
export OC_KV_STORE_TYPE=memory

# Use environment variables for credentials
export OC_CREDENTIAL_PROVIDER_TYPE=environment
export OC_CREDENTIAL_PROVIDER_ENV_PREFIX=DEV_CRED_
export DEV_CRED_MY_CONFIG_USERNAME=myuser
export DEV_CRED_MY_CONFIG_PASSWORD=mypass
```

### Production Environment

For production, you might use S3 storage and Redis:

```bash
# Use S3 storage
export OC_STORAGE_TYPE=s3
export OC_S3_BUCKET=my-company-data
export OC_S3_PREFIX=captures/prod/
export AWS_REGION=eu-west-2

# Use Redis for key-value store
export OC_KV_STORE_TYPE=redis
export OC_KV_STORE_REDIS_HOST=redis.example.com
export OC_KV_STORE_REDIS_PORT=6379
export OC_KV_STORE_REDIS_PASSWORD=secret123
export OC_KV_STORE_REDIS_KEY_PREFIX=data_fetcher:prod:

# Use AWS Secrets Manager for credentials
export OC_CREDENTIAL_PROVIDER_TYPE=aws
export AWS_REGION=eu-west-2
```

### Docker Environment

For Docker deployments, you can set environment variables in your `docker-compose.yml`:

```yaml
version: '3.8'
services:
  oc-fetcher:
    build: .
    environment:
      - OC_STORAGE_TYPE=s3
      - OC_S3_BUCKET=my-company-data
      - AWS_REGION=eu-west-2
      - OC_KV_STORE_TYPE=redis
      - OC_KV_STORE_REDIS_HOST=redis
      - OC_KV_STORE_REDIS_PORT=6379
      - OC_CREDENTIAL_PROVIDER_TYPE=aws
      - AWS_REGION=eu-west-2
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

## Boolean Values

Boolean environment variables accept various formats:

- **True values**: `"true"`, `"1"`, `"yes"`, `"on"`
- **False values**: `"false"`, `"0"`, `"no"`, `"off"`

Examples:
```bash

export OC_STORAGE_USE_BUNDLER=1
export OC_STORAGE_USE_UNZIP=yes
```

## Configuration Precedence

The configuration system follows this precedence order:

1. **Environment variables** (highest priority)
   - `AWS_REGION` (standard AWS environment variable, takes precedence)
   - `OC_*` specific environment variables (fallback)
2. **Hard-coded defaults** (lowest priority)

### AWS Region Precedence

For AWS region configuration, the precedence order is:
1. `AWS_REGION` environment variable (standard AWS practice)
2. `OC_S3_REGION` or `OC_CREDENTIAL_PROVIDER_AWS_REGION` (framework-specific)
3. Hard-coded default (`eu-west-2`)

This means you can override any default value by setting the corresponding environment variable.

## Error Handling

The configuration system includes robust error handling:

- **Invalid storage types**: Raises `ValueError` with descriptive message
- **Invalid provider types**: Raises `ValueError` with descriptive message
- **Invalid integer values**: Falls back to default value
- **Missing environment variables**: Uses sensible defaults

## Testing Configuration

You can test your configuration using the provided test script:

```bash
python test_simple_config.py
```

This script verifies that:
- Environment variables are parsed correctly
- Default values are applied when variables are not set
- Boolean and integer parsing works as expected
- Configuration logic handles different scenarios

## Migration Guide

### From Hard-coded Values

If you were previously using hard-coded values, you can migrate by:

1. **Identify current values**: Check your current configuration
2. **Set environment variables**: Use the appropriate environment variables
3. **Test configuration**: Run the test script to verify
4. **Deploy**: The system will automatically use the new configuration

### Example Migration

**Before (hard-coded):**
```python
# In your code
storage_config = (
    create_storage_config()
    .s3_storage(
        bucket="my-old-bucket",
        prefix="old-prefix/",
        region="us-west-1"
    )
)
```

**After (environment variables):**
```bash
# Set environment variables
export OC_S3_BUCKET=my-old-bucket
export OC_S3_PREFIX=old-prefix/
export AWS_REGION=eu-west-2
```

The system will automatically use these values without code changes.

## Best Practices

1. **Use environment-specific configurations**: Different values for dev, staging, and production
2. **Secure sensitive values**: Use AWS Secrets Manager or secure environment variable management
3. **Document your configuration**: Keep a record of environment variables used in each environment
4. **Test configuration changes**: Always test configuration changes before deploying
5. **Use consistent naming**: Follow the `OC_*` prefix convention for custom variables

## Troubleshooting

### Common Issues

1. **Configuration not applied**: Ensure environment variables are set before importing modules
2. **Invalid values**: Check that boolean and integer values are in the correct format
3. **Missing dependencies**: Ensure required packages (boto3, redis) are installed
4. **Permission issues**: Verify AWS credentials and Redis access permissions

### Debug Configuration

You can debug configuration by adding logging:

```python
import os
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Log configuration values
logger.debug(f"Storage type: {os.getenv('OC_STORAGE_TYPE', 's3')}")
logger.debug(f"S3 bucket: {os.getenv('OC_S3_BUCKET', 'oc-fetcher-data')}")
logger.debug(f"AWS region: {os.getenv('AWS_REGION', 'eu-west-2')}")
```

This will help you verify that environment variables are being read correctly.
