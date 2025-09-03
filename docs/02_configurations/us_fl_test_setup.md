# US Florida (us-fl) Test Environment Setup

This guide explains how to manually set up a test environment for the US Florida SFTP fetcher configuration and execute oc-fetcher locally.

## Overview

The US Florida configuration (`us-fl`) is an SFTP-based fetcher that processes:
- **Daily files**: Text files from `doc/cor/` directory with date-based filtering (starting from 2023-07-28)
- **Quarterly files**: ZIP files from `doc/Quarterly/Cor/` directory

The configuration uses:
- SFTP for file access
- AWS Secrets Manager for credential management
- S3 for data storage and bundling
- Date-based file filtering for daily data

## Prerequisites

### Required Software
- **Docker**: For running SFTP server and LocalStack (S3/S3-compatible storage)
- **Python 3.10+**: For running oc-fetcher
- **Poetry**: For dependency management

### Required Dependencies
```bash
# Install project dependencies
poetry install
```

### DevContainer Environment
If you're using the VS Code devcontainer, paging for CLI tools (AWS CLI, Git, etc.) is automatically disabled for a better development experience. You won't need to append `| cat` to commands.

## Test Environment Setup

### 1. Start SFTP Test Server

The functional test uses an SFTP server container with mock data. You can set up a similar environment:

```bash
# Start SFTP server container
docker run -d \
  --name test-sftp-server \
  -p 2222:22 \
  -e SFTP_USERS=testuser:testpass:1000 \
  atmoz/sftp:latest

# Wait for container to be ready
sleep 5

# Create test directory structure
docker exec test-sftp-server mkdir -p /home/testuser/doc/cor
docker exec test-sftp-server mkdir -p /home/testuser/doc/Quarterly/Cor

# Create test daily files
docker exec test-sftp-server sh -c '
echo "Mock daily data for 20230728_daily_data.txt" > /home/testuser/doc/cor/20230728_daily_data.txt
echo "Mock daily data for 20230729_daily_data.txt" > /home/testuser/doc/cor/20230729_daily_data.txt
echo "Mock daily data for 20230730_daily_data.txt" > /home/testuser/doc/cor/20230730_daily_data.txt
echo "Mock daily data for 20240101_daily_data.txt" > /home/testuser/doc/cor/20240101_daily_data.txt
'

# Create test quarterly file
docker exec test-sftp-server sh -c '
echo "Mock quarterly corporate data" > /home/testuser/doc/Quarterly/Cor/cordata.zip
'

# Set proper permissions (note: use 'users' group, not 'testuser')
docker exec test-sftp-server chown -R testuser:users /home/testuser/doc
```

### 2. Start LocalStack (S3-compatible Storage)

For local testing, use LocalStack to provide S3-compatible storage:

```bash
# Start LocalStack container
docker run -d \
  --name test-localstack \
  -p 4566:4566 \
  -e SERVICES=s3,secretsmanager \
  -e DEFAULT_REGION=us-east-1 \
  -e AWS_ACCESS_KEY_ID=test \
  -e AWS_SECRET_ACCESS_KEY=test \
  -e DEBUG=1 \
  -e PERSISTENCE=1 \
  localstack/localstack:3.0

# Wait for LocalStack to be ready
sleep 10

# Create test S3 bucket
aws --endpoint-url=http://localhost:4566 \
  --region us-east-1 \
  --no-sign-request \
  s3 mb s3://test-us-fl-bucket
```

### 3. Set Up Test Credentials

Create test SFTP credentials in LocalStack Secrets Manager:

```bash
# Create test secret for SFTP credentials
aws --endpoint-url=http://localhost:4566 \
  --region us-east-1 \
  --no-sign-request \
  secretsmanager create-secret \
  --name us-fl-sftp-credentials \
  --secret-string '{
    "host": "localhost",
    "username": "testuser",
    "password": "testpass",
    "port": "2222"
  }'
```

## Environment Configuration

Set the following environment variables for the test environment:

```bash
# Storage configuration
export OC_STORAGE_TYPE=s3
export OC_S3_BUCKET=test-us-fl-bucket
export OC_S3_PREFIX=test-us-fl/
export OC_S3_ENDPOINT_URL=http://localhost:4566
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test

# Credential provider configuration
export OC_CREDENTIAL_PROVIDER_TYPE=aws
export OC_CREDENTIAL_PROVIDER_AWS_ENDPOINT_URL=http://localhost:4566
```

## Running the US Florida Fetcher

### Method 1: Using the Main Module

```bash
# Run the us-fl configuration
poetry run python -m oc_fetcher.main us-fl
```

### Method 2: Using Python Script

Create a test script (`tmp/test_us_fl.py`):

```python
#!/usr/bin/env python3
"""Test script for US Florida SFTP fetcher."""

import asyncio
import os
from oc_fetcher.core import FetchPlan, FetchRunContext
from oc_fetcher.registry import get_fetcher

async def test_us_fl_fetcher():
    """Test the US Florida SFTP fetcher."""
    print("=== US Florida SFTP Fetcher Test ===")

    try:
        # Get the us-fl fetcher
        fetcher = get_fetcher("us-fl")
        print("✓ Successfully created US Florida fetcher")

        # Create a fetch plan
        run_context = FetchRunContext(run_id="test-us-fl-manual")
        plan = FetchPlan(
            requests=[],
            context=run_context,
            concurrency=1
        )
        print("✓ Created fetch plan")

        # Run the fetcher
        print("Running fetcher...")
        result = await fetcher.run(plan)

        print(f"✓ Fetcher completed successfully")
        print(f"  Processed: {result.processed_count} files")
        print(f"  Errors: {len(result.errors)}")

        if result.errors:
            print("  Error details:")
            for error in result.errors:
                print(f"    - {error}")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_us_fl_fetcher())
```

Run the test script:

```bash
poetry run python tmp/test_us_fl.py
```

### Method 3: Using Make Commands

```bash
# Run the fetcher using make
make run ARGS=us-fl

# Or specify local mode explicitly
make MODE=local run ARGS=us-fl
```

## Verifying Results

### Check S3 Storage

```bash
# List objects in the test bucket
aws --endpoint-url=http://localhost:4566 \
  --region us-east-1 \
  --no-sign-request \
  s3 ls s3://test-us-fl-bucket/test-us-fl/ --recursive

# Download and examine a bundle file
aws --endpoint-url=http://localhost:4566 \
  --region us-east-1 \
  --no-sign-request \
  s3 cp s3://test-us-fl-bucket/test-us-fl/[bundle-name].zip ./tmp/
```

### Check Logs

The fetcher provides detailed logging. Look for:
- SFTP connection messages
- File processing information
- Bundle creation details
- S3 upload confirmations

## Troubleshooting

### Common Issues

#### 1. SFTP Connection Failed
```bash
# Check if SFTP container is running
docker ps | grep test-sftp-server

# Test SFTP connection manually
sftp -P 2222 testuser@localhost
# Password: testpass
```

#### 2. LocalStack Not Accessible
```bash
# Check LocalStack status
docker logs test-localstack

# Test S3 access
aws --endpoint-url=http://localhost:4566 \
  --region us-east-1 \
  --no-sign-request \
  s3 ls
```

#### 3. Credentials Not Found
```bash
# Verify secret exists
aws --endpoint-url=http://localhost:4566 \
  --region us-east-1 \
  --no-sign-request \
  secretsmanager list-secrets

# Check secret content
aws --endpoint-url=http://localhost:4566 \
  --region us-east-1 \
  --no-sign-request \
  secretsmanager get-secret-value \
  --secret-id us-fl-sftp-credentials
```

#### 4. Environment Variables Not Set
```bash
# Verify all required environment variables
env | grep -E "OC_|AWS_"
```

### Debug Mode

Enable debug logging by setting:

```bash
export OC_LOG_LEVEL=DEBUG
```

## Cleanup

When finished testing:

```bash
# Stop and remove containers
docker stop test-sftp-server test-localstack
docker rm test-sftp-server test-localstack

# Clean up environment variables
unset OC_STORAGE_TYPE OC_S3_BUCKET OC_S3_PREFIX OC_S3_ENDPOINT_URL
unset AWS_REGION AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY
unset OC_CREDENTIAL_PROVIDER_TYPE OC_CREDENTIAL_PROVIDER_AWS_ENDPOINT_URL
```

## Production Considerations

For production use, replace the test components with:

- **SFTP Server**: Real SFTP server with actual data
- **S3 Storage**: AWS S3 or S3-compatible storage
- **Credentials**: AWS Secrets Manager with real credentials
- **Security**: Proper network security and access controls

## Next Steps

After successful local testing:

1. **Review the [SFTP Configuration Guide](sftp.md)** for production setup
2. **Check the [Application Configuration](03_global_configuration/) documentation** for advanced settings
3. **Explore the [Deployment Guide](../07_deployment/)** for production deployment
4. **Run the functional tests** to verify everything works: `make test ARGS=tests/functional/test_functional_us_fl.py`
