# US Florida SFTP Test Environment

This directory contains a complete test environment for the US Florida SFTP configuration, including mock services and supporting infrastructure.

## Overview

The test environment provides:
- Mock SFTP server with realistic data structure
- LocalStack for S3 and AWS Secrets Manager testing
- Pre-configured networking for service communication
- Health checks for reliable service startup

## Quick Start

### 1. Configure Ports (Optional)
```bash
cd mocks/environments/us_fl

# Copy the example environment file
cp env.example .env

# Edit .env to customize ports if needed
# SFTP_PORT=2222
# LOCALSTACK_PORT=4566
```

### 2. Start the Test Environment
```bash
docker-compose up -d
```

### 3. Wait for Services to be Ready
```bash
# Check service health
docker-compose ps

# View logs
docker-compose logs -f
```

### 4. Setup Mock Data
```bash
# Run the setup script to create mock data in the SFTP container
./setup-mock-data.sh
```

### 5. Set Up Test Credentials
```bash
export OC_CREDENTIAL_PROVIDER_TYPE=environment
export OC_CREDENTIAL_US_FL_HOST="localhost"
export OC_CREDENTIAL_US_FL_USERNAME="testuser"
export OC_CREDENTIAL_US_FL_PASSWORD="testpass"
export OC_CREDENTIAL_US_FL_PORT="2222"
```

### 6. Run the Fetcher
```bash
# From the project root
poetry run python -m data_fetcher_app.main run us-fl --credentials-provider env
```

## Services

### SFTP Server
- **Port**: 2222 (configurable via `SFTP_PORT` env var, mapped from container port 22)
- **Credentials**: testuser/testpass
- **Data**: Mock daily and quarterly files
- **Health Check**: Port 22 connectivity

### LocalStack
- **Port**: 4566 (configurable via `LOCALSTACK_PORT` env var)
- **Services**: S3, Secrets Manager
- **Region**: us-east-1
- **Credentials**: test/test
- **Health Check**: HTTP endpoint

## Testing Workflow

### 1. Verify SFTP Connection
```bash
# Test SFTP access
sftp -P 2222 testuser@localhost

# List files
ls /doc/cor/
ls /doc/Quarterly/Cor/
```

### 2. Verify S3 Access
```bash
# Configure AWS CLI for LocalStack
export AWS_ENDPOINT_URL=http://localhost:4566
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test

# Create test bucket
aws s3 mb s3://test-bucket

# List buckets
aws s3 ls
```

### 3. Run End-to-End Test
```bash
# Set up credentials (as shown above)
# Run the fetcher
poetry run python -m data_fetcher_app.main run us-fl --credentials-provider env
```

## Troubleshooting

### Services Not Starting
```bash
# Check logs
docker-compose logs sftp-server
docker-compose logs localstack

# Restart services
docker-compose restart
```

### Connection Issues
```bash
# Verify ports are available
netstat -tlnp | grep -E ":(2222|4566)"

# Check container status
docker-compose ps
```

### Data Issues
```bash
# Rebuild images
docker-compose build --no-cache

# Remove volumes and restart
docker-compose down -v
docker-compose up -d
```

## Cleanup

```bash
# Stop and remove containers
docker-compose down

# Remove volumes (clears all data)
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

## Integration with Tests

This environment is designed to work with the existing test suite. The test fixtures in `tests/test_functional/test_us_fl.py` will automatically use these services when running functional tests.

For manual testing and development, use this docker-compose environment to have a persistent test setup.
