# Troubleshooting Guide

This guide covers common issues and their solutions when using OC Fetcher.

## Common Issues

### Configuration Errors

#### "Unknown configuration" Error
```
KeyError: Unknown configuration: us-il
```

**Cause**: The configuration doesn't exist in the registry.

**Solution**:
- Check available configurations: `poetry run python -m data_fetcher.main`
- Use only available configurations: `us-fl` or `fr`

#### Missing Environment Variables
```
ValueError: Missing required environment variable OC_S3_BUCKET
```

**Cause**: Required environment variables are not set.

**Solution**: Set the required environment variables:
```bash
export OC_S3_BUCKET=your-bucket-name
export AWS_REGION=eu-west-2
```

### Authentication Issues

#### SFTP Connection Failed
```
ConnectionError: Failed to connect to SFTP server
```

**Cause**: Invalid credentials or network issues.

**Solution**:
1. Verify credentials in AWS Secrets Manager
2. Check network connectivity
3. Verify SFTP server is accessible

#### Credential Provider Issues

##### Environment Variable Provider Errors
```
ValueError: Environment variable 'OC_CREDENTIAL_US_FL_HOST' not found. Please set the following environment variables:
  OC_CREDENTIAL_US_FL_HOST

Environment variable format: OC_CREDENTIAL_US_FL_HOST
Example: For config 'us-fl' and key 'username', set: OC_CREDENTIAL_US_FL_USERNAME
```

**Cause**: Missing environment variables for credentials.

**Solution**:
1. Set the required environment variables:
   ```bash
   export OC_CREDENTIAL_US_FL_HOST="sftp.example.com"
   export OC_CREDENTIAL_US_FL_USERNAME="username"
   export OC_CREDENTIAL_US_FL_PASSWORD="password"
   ```
2. Use the correct format: `OC_CREDENTIAL_<CONFIG_NAME>_<CREDENTIAL_KEY>`
3. Remember that hyphens in config names become underscores in environment variables

##### AWS Secrets Manager Errors
```
ValueError: Unexpected error accessing secret 'us-fl-sftp-credentials': Unable to locate credentials
```

**Cause**: AWS credentials not configured or insufficient permissions.

**Solution**:
1. Configure AWS credentials (IAM user, role, or credentials file)
2. Ensure the IAM user/role has `secretsmanager:GetSecretValue` permission
3. Verify the secret exists in the specified region
4. Check AWS region configuration: `export AWS_REGION=eu-west-2`

##### Switching Credential Providers

If you need to switch between credential providers:

**From AWS to Environment Variables:**
```bash
# Use command line flag to override
poetry run python -m data_fetcher.main --credentials-provider env us-fl

# Or set environment variable
export OC_CREDENTIAL_PROVIDER_TYPE=environment
poetry run python -m data_fetcher.main us-fl
```

**From Environment Variables to AWS:**
```bash
# Use command line flag to override
poetry run python -m data_fetcher.main --credentials-provider aws us-fl

# Or set environment variable
export OC_CREDENTIAL_PROVIDER_TYPE=aws
poetry run python -m data_fetcher.main us-fl
```

**Check Current Provider:**
```bash
# View help to see current options
poetry run python -m data_fetcher.main --help
```

#### API Authentication Failed
```
HTTPStatusError: 401 Unauthorized
```

**Cause**: Invalid API credentials or expired tokens.

**Solution**:
1. Check OAuth token expiration
2. Verify API credentials in AWS Secrets Manager
3. Ensure proper authentication headers

### Storage Issues

#### S3 Upload Failed
```
S3UploadFailedError: Failed to upload to S3
```

**Cause**: Insufficient permissions or bucket issues.

**Solution**:
1. Verify AWS credentials and permissions
2. Check S3 bucket exists and is accessible
3. Ensure bucket has proper CORS configuration

#### File System Permission Error
```
PermissionError: [Errno 13] Permission denied
```

**Cause**: Insufficient file system permissions.

**Solution**:
1. Check directory permissions
2. Ensure write access to storage directory
3. Run with appropriate user permissions

### Network Issues

#### Connection Timeout
```
ConnectTimeout: Connection timed out
```

**Cause**: Network connectivity issues or server unavailability.

**Solution**:
1. Check network connectivity
2. Verify server is accessible
3. Increase timeout settings if needed

#### Rate Limiting
```
HTTPStatusError: 429 Too Many Requests
```

**Cause**: Exceeding API rate limits.

**Solution**:
1. Reduce concurrency settings
2. Implement exponential backoff
3. Check rate limit configuration

### Memory Issues

#### Out of Memory Error
```
MemoryError: Unable to allocate memory
```

**Cause**: Large files being loaded into memory.

**Solution**:
1. Ensure streaming is enabled
2. Reduce concurrency to lower memory usage
3. Check for memory leaks in custom code

## Debugging

### Enable Debug Logging

Set environment variable for detailed logging:
```bash
export OC_LOG_LEVEL=DEBUG
```

### Check Logs

Look for structured JSON logs with context:
```json
{
  "event": "fetch_started",
  "config_id": "us-fl",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### Common Log Patterns

#### Successful Operation
```
INFO: Fetch completed successfully
INFO: Processed 1000 files
INFO: Storage upload completed
```

#### Error Patterns
```
ERROR: Connection failed
ERROR: Authentication failed
ERROR: Storage upload failed
```

## Performance Issues

### Slow Processing

**Symptoms**: Low throughput, long processing times.

**Solutions**:
1. Increase concurrency settings
2. Check network bandwidth
3. Verify storage performance
4. Monitor system resources

### High Memory Usage

**Symptoms**: Memory usage growing over time.

**Solutions**:
1. Ensure streaming is working properly
2. Check for memory leaks
3. Reduce concurrency
4. Monitor garbage collection

## Configuration Validation

### Validate Configuration

Check configuration before running:
```python
from data_fetcher.registry import get_fetcher

try:
    fetcher = get_fetcher("us-fl")
    print("Configuration is valid")
except Exception as e:
    print(f"Configuration error: {e}")
```

### Environment Check

Verify environment setup:
```bash
# Check Python environment
python --version
poetry --version

# Check AWS credentials
aws sts get-caller-identity

# Check environment variables
env | grep OC_
```

## Getting Help

### Log Files

Check log files for detailed error information:
- Application logs: Check console output
- System logs: `/var/log/` (Linux)
- AWS CloudWatch logs (if configured)

### Common Debugging Commands

```bash
# Test configuration
poetry run python -m data_fetcher.main

# Run with verbose logging
OC_LOG_LEVEL=DEBUG poetry run python -m data_fetcher.main us-fl

# Check dependencies
poetry show

# Run tests
poetry run pytest -v
```

### Reporting Issues

When reporting issues, include:
1. Error message and stack trace
2. Configuration being used
3. Environment details (OS, Python version)
4. Log output with DEBUG level
5. Steps to reproduce the issue
