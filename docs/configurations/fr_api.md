# FR - France API Fetcher Recipe

## Summary

The `fr` fetcher recipe fetches data from the French INSEE SIRENE API using OAuth 2.0 authentication. It's designed for modern REST APIs with cursor-based pagination and comprehensive error handling.

## Key Features

- **OAuth 2.0 Authentication**: Uses INSEE API token endpoint
- **Cursor-based Pagination**: Handles large datasets efficiently with `curseurSuivant`
- **Complex Query Logic**: SIREN prefix narrowing with date filtering
- **Multiple Providers**: Main data, gap-filling, and failed company retry
- **Rate Limiting**: Conservative 2 requests/second with 5 retries
- **ProtocolConfig Architecture**: Uses HttpProtocolConfig for connection management

## Usage

```bash
# Run France API fetcher
poetry run python -m data_fetcher_app.main run fr

# Run with environment variable credentials
poetry run python -m data_fetcher_app.main run fr --credentials-provider env
```

## Fetcher Recipe Details

### Authentication
- **Token URL**: `https://api.insee.fr/token`
- **Base URL**: `https://api.insee.fr/entreprises/sirene/V3.11/siren`
- **Scope**: Client credentials flow

### Pagination
- **Type**: Cursor-based with `curseurSuivant` field
- **Max Records**: 20,000 per query
- **Page Size**: 1,000 records per page

### Query Logic
- **Date Filtering**: `dateDernierTraitementUniteLegale` field
- **SIREN Narrowing**: 2-digit prefix strategy (00-99)
- **Exclusions**: Filters out category 1000 and non-diffused records

## Credential Setup

### AWS Secrets Manager (Recommended)
```bash
aws secretsmanager create-secret \
  --name "oc-fetcher/fr" \
  --secret-string '{
    "client_id": "your-client-id",
    "client_secret": "your-client-secret"
  }'
```

### Environment Variables
```bash
export OC_CREDENTIAL_PROVIDER_TYPE=environment
export OC_CREDENTIAL_FR_CLIENT_ID="your-client-id"
export OC_CREDENTIAL_FR_CLIENT_SECRET="your-client-secret"
```

## Additional Notes

### SIREN Narrowing Strategy
The fetcher recipe uses a sophisticated narrowing strategy to handle the large SIRENE dataset:
- Starts with 2-digit SIREN prefixes (00-99)
- Incrementally processes each prefix
- Handles edge cases like prefix "99" triggering date increment

### Gap Filling
Includes a reverse pagination provider for historical data collection to fill gaps in previous runs.

### Error Handling
Comprehensive error handling for:
- 404 (no items found) - logged as warning
- 500, 502, 503, 504 (server errors) - logged as exceptions
- 403 (forbidden) - logged as exception

### Performance Considerations
- Conservative rate limiting (2 req/sec) to respect INSEE API limits
- 120-second timeout for API calls
- Maximum 5 retries with exponential backoff
- Structured logging with request/response context

## ProtocolConfig Architecture

The France recipe uses the new ProtocolConfig architecture for improved connection management:

### HttpProtocolConfig Usage

```python
# Create HTTP protocol configuration with OAuth authentication
http_config = create_http_protocol_config(
    timeout=120.0,  # Longer timeout for API calls
    rate_limit_requests_per_second=2.0,  # Conservative rate limiting
    max_retries=5,
    default_headers={
        "User-Agent": "OCFetcher/1.0",
        "Accept": "application/json",
    },
    authentication_mechanism=oauth_auth,
)

# Create components with ProtocolConfig
loader = create_tracking_http_bundle_loader(
    http_config=http_config,
    meta_load_name="fr_sirene_api_loader"
)

provider = create_complex_pagination_http_bundle_locator(
    http_config=http_config,
    base_url=base_url,
    # ... other parameters
)
```

### Benefits

1. **Multiple Connection Pools**: HttpManager automatically manages multiple connection pools
2. **Configuration Reuse**: Same configurations share connection pools for efficiency
3. **Type Safety**: ProtocolConfig provides better type safety and validation
4. **Separation of Concerns**: Protocol settings are separate from manager instances

## Strategies Used

This fetcher recipe uses the following strategies:

- **[TrackingHttpBundleLoader](strategies/api/siren/tracking_api_loader.md)** - API request handling and error management
- **[ComplexPaginationHttpBundleLocator](strategies/api/siren/complex_pagination_bundle_locator.md)** - Main data collection with URL generation, pagination, and query building
- **[ReversePaginationHttpBundleLocator](strategies/api/siren/reverse_pagination_bundle_locator.md)** - Gap-filling for historical data
- **[SingleHttpBundleLocator](strategies/api/siren/single_api_bundle_locator.md)** - Error recovery for failed company lookups

## How to Test

### Prerequisites

Before testing the FR fetcher recipe, ensure you have:
- Docker and Docker Compose installed
- Poetry environment set up
- Access to the project repository

### Quick Test Setup

The easiest way to test the FR fetcher recipe is using the provided test environment:

```bash
# 1. Start the test environment
cd mocks/environments/fr
docker-compose up -d

# 2. Wait for services to be ready (check logs)
docker-compose logs -f

# 3. Setup and verify mock API
./setup-mock-data.sh

# 4. Set up test credentials
export OC_CREDENTIAL_PROVIDER_TYPE=environment
export OC_CREDENTIAL_FR_CLIENT_ID="test_client_id"
export OC_CREDENTIAL_FR_CLIENT_SECRET="test_client_secret"

# 5. Run the fetcher
cd /workspaces/data-fetcher-sftp

# Option A: Run Locally (for debugging)
poetry run python -m data_fetcher_app.main run fr --credentials-provider env

# Option B: Run via Docker (app-runner)
# First, build the application image
make build/for-deployment

# Then run via docker-compose app-runner
make run ARGS=fr
```

### Running the Fetcher

You can run the fetcher in two ways:

#### Option A: Run Locally (for debugging)
```bash
# From the project root
export OC_CREDENTIAL_PROVIDER_TYPE=environment
export OC_CREDENTIAL_FR_CLIENT_ID="test_client_id"
export OC_CREDENTIAL_FR_CLIENT_SECRET="test_client_secret"

# Run the fetcher locally
poetry run python -m data_fetcher_app.main run fr --credentials-provider env
```

#### Option B: Run via Docker (app-runner)
```bash
# From the project root
# First, build the application image
make build/for-deployment

# Run via docker-compose app-runner
make run ARGS=fr
```

**Note**: The docker approach will use the project's docker-compose setup with the app-runner service.

### Manual Testing Steps

#### 1. Verify API Endpoints
```bash
# Health check
curl http://localhost:5001/health

# Get OAuth token
curl -X POST http://localhost:5001/token \
  -H "Authorization: Basic dGVzdF9jbGllbnRfaWQ6dGVzdF9jbGllbnRfc2VjcmV0"

# Get SIREN data (using the token from previous step)
curl "http://localhost:5001/entreprises/sirene/V3.11/siren?q=siren:00*" \
  -H "Authorization: Bearer mock_access_token_12345"
```

#### 2. Verify S3 Access (LocalStack)
```bash
# Configure AWS CLI for LocalStack
export AWS_ENDPOINT_URL=http://localhost:4566
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test

# Create a test bucket
aws s3 mb s3://test-bucket

# List buckets to verify
aws s3 ls
```

#### 3. Run End-to-End Test
```bash
# Ensure credentials are set (as shown above)
# Run the fetcher from project root
poetry run python -m data_fetcher_app.main run fr --credentials-provider env
```

#### 4. Verify Results
```bash
# Check that bundles were created in S3
aws s3 ls s3://test-bucket/ --recursive

# Download and inspect a bundle
aws s3 cp s3://test-bucket/[bundle-path] ./test-bundle.json
cat test-bundle.json
```

### Test Environment Details

The test environment includes:

- **Mock SIREN API Server**:
  - Port: 5001 (mapped from container port 5000)
  - Endpoints: `/health`, `/token`, `/entreprises/sirene/V3.11/siren`
  - Mock responses with realistic French company data
  - OAuth 2.0 token authentication

- **LocalStack**:
  - Port: 4566
  - Services: S3, Secrets Manager
  - Region: us-east-1
  - Credentials: test/test

### Mock API Responses

The mock SIREN API provides realistic responses for testing:

#### OAuth Token Response
```json
{
  "access_token": "mock_access_token_12345",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

#### SIREN Data Response
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

### Testing Different Scenarios

#### Test SIREN Prefix Pagination
```bash
# Test different SIREN prefixes
curl "http://localhost:5001/entreprises/sirene/V3.11/siren?q=siren:00*" \
  -H "Authorization: Bearer mock_access_token_12345"

curl "http://localhost:5001/entreprises/sirene/V3.11/siren?q=siren:01*" \
  -H "Authorization: Bearer mock_access_token_12345"

curl "http://localhost:5001/entreprises/sirene/V3.11/siren?q=siren:99*" \
  -H "Authorization: Bearer mock_access_token_12345"
```

#### Test Error Handling
```bash
# Test invalid token
curl "http://localhost:5001/entreprises/sirene/V3.11/siren?q=siren:00*" \
  -H "Authorization: Bearer invalid_token"

# Test invalid query
curl "http://localhost:5001/entreprises/sirene/V3.11/siren?q=invalid" \
  -H "Authorization: Bearer mock_access_token_12345"
```

### Troubleshooting

#### Services Not Starting
```bash
# Check service health
docker-compose ps

# View detailed logs
docker-compose logs siren-api
docker-compose logs localstack

# Restart services
docker-compose restart
```

#### Connection Issues
```bash
# Verify ports are available
netstat -tlnp | grep -E ":(5000|4566)"

# Check container status
docker-compose ps
```

#### API Issues
```bash
# Test API endpoints manually
curl -v http://localhost:5000/health
curl -v http://localhost:5000/token

# Check API logs
docker-compose logs siren-api
```

### Cleanup

```bash
# Stop and remove containers
docker-compose down

# Remove volumes (clears all data)
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

### Integration with Automated Tests

The test environment is designed to work with the existing test suite. Functional tests in `tests/test_functional/test_fr.py` automatically use these mock services when running:

```bash
# Run functional tests
poetry run pytest tests/test_functional/test_fr.py -v
```

For more detailed information about the test environment, see [FR Test Setup](../testing/mock_environments/fr_test_setup.md).

## Related Documentation

- **[Creating a Recipe](creating_a_recipe.md)** - How to create new fetcher recipes
- **[Application Configuration](../user_guide/application_configuration.md)** - System configuration
- **[Command Line Usage](../user_guide/command_line_usage.md)** - Running fetcher recipes
