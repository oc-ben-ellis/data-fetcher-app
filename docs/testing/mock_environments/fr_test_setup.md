# French SIREN API Test Environment

This directory contains a complete test environment for the French SIREN API configuration, including mock services and supporting infrastructure.

## Overview

The test environment provides:
- Mock SIREN API server with realistic responses
- LocalStack for S3 and AWS Secrets Manager testing
- Pre-configured networking for service communication
- Health checks for reliable service startup

## Quick Start

### 1. Configure Ports (Optional)
```bash
cd mocks/environments/fr

# Copy the example environment file
cp env.example .env

# Edit .env to customize ports if needed
# SIREN_API_PORT=5001
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
# Run the setup script to verify the mock API is working
./setup-mock-data.sh
```

### 5. Set Up Test Credentials
```bash
export OC_CREDENTIAL_PROVIDER_TYPE=environment
export OC_CREDENTIAL_FR_CLIENT_ID="test_client_id"
export OC_CREDENTIAL_FR_CLIENT_SECRET="test_client_secret"
```

### 6. Run the Fetcher
```bash
# From the project root
poetry run python -m data_fetcher_app.main run fr --credentials-provider env
```

## Services

### SIREN API Server
- **Port**: 5001 (configurable via `SIREN_API_PORT` env var, mapped from container port 5000)
- **Endpoints**:
  - `/health` - Health check
  - `/token` - OAuth token endpoint
  - `/entreprises/sirene/V3.11/siren` - SIREN data endpoint
- **Health Check**: HTTP endpoint

### LocalStack
- **Port**: 4566 (configurable via `LOCALSTACK_PORT` env var)
- **Services**: S3, Secrets Manager
- **Region**: us-east-1
- **Credentials**: test/test
- **Health Check**: HTTP endpoint

## Testing Workflow

### 1. Verify API Endpoints
```bash
# Health check
curl http://localhost:5001/health

# Get OAuth token
curl -X POST http://localhost:5001/token \
  -H "Authorization: Basic dGVzdF9jbGllbnRfaWQ6dGVzdF9jbGllbnRfc2VjcmV0"

# Get SIREN data
curl "http://localhost:5001/entreprises/sirene/V3.11/siren?q=siren:00*" \
  -H "Authorization: Bearer mock_access_token_12345"
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
poetry run python -m data_fetcher_app.main run fr --credentials-provider env
```

## Mock API Responses

The mock SIREN API provides realistic responses for testing:

### OAuth Token
```json
{
  "access_token": "mock_access_token_12345",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### SIREN Data
```json
{
  "header": {
    "statut": 200,
    "message": "OK"
  },
  "unitesLegales": [
    {
      "siren": "000000001",
      "denominationUniteLegale": "Test Company 1",
      "dateDernierTraitementUniteLegale": "2023-07-28"
    }
  ],
  "curseurSuivant": "siren:01"
}
```

## Troubleshooting

### Services Not Starting
```bash
# Check logs
docker-compose logs siren-api
docker-compose logs localstack

# Restart services
docker-compose restart
```

### Connection Issues
```bash
# Verify ports are available
netstat -tlnp | grep -E ":(5001|4566)"

# Check container status
docker-compose ps
```

### API Issues
```bash
# Test API endpoints manually
curl -v http://localhost:5001/health
curl -v http://localhost:5001/token
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

This environment is designed to work with the existing test suite. The test fixtures in `tests/test_functional/test_fr.py` will automatically use these services when running functional tests.

For manual testing and development, use this docker-compose environment to have a persistent test setup.
