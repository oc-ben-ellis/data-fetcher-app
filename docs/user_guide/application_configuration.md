# Application Configuration

This guide covers how to configure the Data Fetcher application for different environments and use cases.

## Configuration Overview

The Data Fetcher application uses a hierarchical configuration system:

1. **Environment Variables** - Override defaults
2. **Configuration Files** - Application settings
3. **Runtime Configuration** - Dynamic settings

> **Important**: The fetcher now requires a key-value store configuration for the persistent queue system. This enables resumable operations across application restarts. See the [Persistent Queue System](../architecture/queue/README.md) documentation for more details.

## Environment Variables

### Core Application Settings

```bash
# Configuration ID (which fetcher to run)
export OC_CONFIG_ID=us-fl

# Credential provider type
export OC_CREDENTIAL_PROVIDER_TYPE=aws  # or 'environment'

# Log level
export OC_LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

### AWS Configuration

```bash
# AWS Region
export AWS_REGION=eu-west-2
```

### Key-Value Store Configuration

```bash
# Key-value store type (required for persistent queue)
export OC_KV_STORE_TYPE=redis  # or 'memory' for testing

# Redis configuration (when using redis store)
export OC_KV_STORE_REDIS_HOST=localhost
export OC_KV_STORE_REDIS_PORT=6379
export OC_KV_STORE_REDIS_DB=0
export OC_KV_STORE_REDIS_PASSWORD=  # optional

# Serializer type
export OC_KV_STORE_SERIALIZER=json  # or 'pickle'

# Default TTL in seconds
export OC_KV_STORE_DEFAULT_TTL=3600
```

### SQS Configuration

```bash
# SQS Queue URL for bundle completion notifications (required for PipelineStorage)
export OC_SQS_QUEUE_URL=https://sqs.eu-west-2.amazonaws.com/123456789012/bundle-completions

# For LocalStack development
export OC_SQS_QUEUE_URL=http://localhost:4566/000000000000/bundle-completions
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
```

### Logging Configuration

```bash
# Log level
export OC_LOG_LEVEL=INFO

# Log format (JSON is default)
export OC_LOG_FORMAT=json

# Log output destination
export OC_LOG_OUTPUT=stdout
```

## Credential Providers

### AWS Secrets Manager (Default)

The application uses AWS Secrets Manager by default for secure credential storage.

#### Setup

1. **Create IAM Role/User** with permissions to access secrets:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "secretsmanager:GetSecretValue"
         ],
         "Resource": "arn:aws:secretsmanager:*:*:secret:oc-fetcher/*"
       }
     ]
   }
   ```

2. **Store Credentials** in AWS Secrets Manager:
   ```bash
   # US Florida SFTP credentials
   aws secretsmanager create-secret \
     --name "oc-fetcher/us-fl" \
     --secret-string '{"host":"sftp.example.com","username":"user","password":"pass"}'

   # France API credentials
   aws secretsmanager create-secret \
     --name "oc-fetcher/fr" \
     --secret-string '{"client_id":"id","client_secret":"secret"}'
   ```

3. **Configure AWS Profile**:
   ```bash
   # Option A: AWS SSO (recommended)
   # Start the interactive AWS SSO configuration
   aws configure sso

   # During setup, provide:
   # - SSO session name: OpenCorporates-Management-Developer
   # - SSO start URL: https://d-9c671d0d67.awsapps.com/start
   # - SSO region: eu-west-2
   # - SSO registration scopes: sso:account:access (default)
   # - AWS account: Choose the management account (089449186373)
   # - Role: Choose the Developer role
   # - Default client region: eu-west-2
   # - CLI default output format: json
   # - Profile name: oc-management-dev (required for makefile compatibility)

   # Set the profile for the application
   export AWS_PROFILE=oc-management-dev

   # Log in to AWS SSO (required before using AWS services)
   aws sso login --profile oc-management-dev
   ```

### Environment Variables

For development or testing, you can use environment variables instead of AWS Secrets Manager.

#### Setup

```bash
# Set credential provider type
export OC_CREDENTIAL_PROVIDER_TYPE=environment

# US Florida SFTP credentials
export OC_CREDENTIAL_US_FL_HOST="sftp.example.com"
export OC_CREDENTIAL_US_FL_USERNAME="username"
export OC_CREDENTIAL_US_FL_PASSWORD="password"

# France API credentials
export OC_CREDENTIAL_FR_API_CLIENT_ID="client-id"
export OC_CREDENTIAL_FR_API_CLIENT_SECRET="client-secret"
```

#### Credential Naming Convention

Configuration names with hyphens are converted to underscores in environment variable names:

- `us-fl` → `OC_CREDENTIAL_US_FL_*`
- `fr` → `OC_CREDENTIAL_FR_*`

## Logging Configuration

### Log Levels

```bash
# Debug level (verbose)
export OC_LOG_LEVEL=DEBUG

# Info level (default)
export OC_LOG_LEVEL=INFO

# Warning level
export OC_LOG_LEVEL=WARNING

# Error level (minimal)
export OC_LOG_LEVEL=ERROR
```

### Log Format

The application uses structured logging with JSON output by default:

```json
{
  "timestamp": "2025-01-27T10:30:00Z",
  "level": "info",
  "logger": "data_fetcher_core.fetcher",
  "message": "Starting fetcher",
  "config_id": "us-fl",
  "event": "fetcher_start"
}
```

### Custom Logging

You can customize logging behavior:

```bash
# Custom log format
export OC_LOG_FORMAT=text

# Log to file
export OC_LOG_OUTPUT=file:///var/log/data-fetcher.log

# Log to syslog
export OC_LOG_OUTPUT=syslog://localhost:514
```

## Storage Configuration

### S3 Configuration

```bash
# S3 bucket for data storage
export OC_S3_BUCKET=my-data-bucket

# S3 prefix for organized storage
export OC_S3_PREFIX=fetcher-data/

# S3 region
export OC_S3_REGION=eu-west-2
```

### Local Storage

```bash
# Local storage directory
export OC_STORAGE_PATH=/var/lib/data-fetcher

# Storage type
export OC_STORAGE_TYPE=local
```

## Network Configuration

### Timeout Settings

```bash
# Connection timeout (seconds)
export OC_CONNECTION_TIMEOUT=30

# Read timeout (seconds)
export OC_READ_TIMEOUT=60

# Total timeout (seconds)
export OC_TOTAL_TIMEOUT=300
```

### Retry Configuration

```bash
# Maximum retry attempts
export OC_MAX_RETRIES=3

# Retry delay (seconds)
export OC_RETRY_DELAY=5

# Exponential backoff
export OC_RETRY_BACKOFF=true
```

## Performance Configuration

### Concurrency Settings

```bash
# Maximum concurrent connections
export OC_MAX_CONNECTIONS=10

# Connection pool size
export OC_POOL_SIZE=5

# Worker thread count
export OC_WORKER_THREADS=4
```

### Memory Configuration

```bash
# Maximum memory usage (MB)
export OC_MAX_MEMORY=1024

# Buffer size (KB)
export OC_BUFFER_SIZE=64

# Cache size (MB)
export OC_CACHE_SIZE=256
```

## Environment-Specific Configuration

### Development Environment

```bash
# Development settings
export OC_ENV=development
export OC_LOG_LEVEL=DEBUG
export OC_CREDENTIAL_PROVIDER_TYPE=environment
export OC_STORAGE_TYPE=local
export OC_STORAGE_PATH=./tmp/data
```

### Staging Environment

```bash
# Staging settings
export OC_ENV=staging
export OC_LOG_LEVEL=INFO
export OC_CREDENTIAL_PROVIDER_TYPE=aws
export OC_S3_BUCKET=staging-data-bucket
export OC_S3_PREFIX=staging/
```

### Production Environment

```bash
# Production settings
export OC_ENV=production
export OC_LOG_LEVEL=WARNING
export OC_CREDENTIAL_PROVIDER_TYPE=aws
export OC_S3_BUCKET=production-data-bucket
export OC_S3_PREFIX=production/
export OC_MAX_RETRIES=5
export OC_CONNECTION_TIMEOUT=60
```

## Configuration Validation

### Check Configuration

```bash
# Validate configuration
poetry run python -c "
from data_fetcher_app.config.credential_provider import configure_application_credential_provider
configure_application_credential_provider()
print('Configuration is valid')
"
```

### Test Credentials

```bash
# Test AWS credentials
aws sts get-caller-identity

# Test specific configuration
poetry run python -m data_fetcher_app.main --help
```

## Configuration Files

### Application Config File

Create a `config.yaml` file for complex configurations:

```yaml
# config.yaml
application:
  name: "data-fetcher"
  version: "1.0.0"
  environment: "production"

logging:
  level: "INFO"
  format: "json"
  output: "stdout"

storage:
  type: "s3"
  bucket: "my-data-bucket"
  prefix: "fetcher-data/"
  region: "eu-west-2"

credentials:
  provider: "aws"
  region: "eu-west-2"

network:
  connection_timeout: 30
  read_timeout: 60
  max_retries: 3
  retry_delay: 5

performance:
  max_connections: 10
  pool_size: 5
  worker_threads: 4
  max_memory: 1024
```

### Load Configuration

```bash
# Use configuration file
export OC_CONFIG_FILE=config.yaml
poetry run python -m data_fetcher_app.main us-fl
```

## Troubleshooting

### Common Configuration Issues

1. **Missing Environment Variables**
   ```bash
   # Check required variables
   env | grep OC_
   ```

2. **AWS Credentials Not Found**
   ```bash
   # Check AWS configuration
   aws configure list
   aws sts get-caller-identity
   ```

3. **Invalid Configuration**
   ```bash
   # Test configuration
   poetry run python -m data_fetcher_app.main --help
   ```

4. **Permission Denied**
   ```bash
   # Check file permissions
   ls -la config.yaml
   chmod 644 config.yaml
   ```

### Debug Configuration

```bash
# Enable debug logging
export OC_LOG_LEVEL=DEBUG

# Run with verbose output
poetry run python -m data_fetcher_app.main us-fl
```

## Best Practices

### Security

- Use AWS Secrets Manager for production credentials
- Never commit credentials to version control
- Use least-privilege IAM roles
- Regularly rotate credentials

### Performance

- Tune concurrency settings based on your infrastructure
- Monitor memory usage and adjust limits
- Use appropriate timeout values
- Enable retry logic for resilience

### Maintenance

- Use environment-specific configurations
- Document custom configurations
- Test configurations in staging before production
- Monitor and log configuration changes
