# SIREN API Mock

This directory contains a mock SIREN API server for testing the French INSEE API configuration in the OC Fetcher project.

## Overview

The mock server simulates the real INSEE SIREN API endpoints:
- OAuth token endpoint (`/token`)
- SIREN data endpoint (`/entreprises/sirene/V3.11/siren`)
- Health check endpoint (`/health`)

## Usage in Tests

The mock API is automatically started by the test fixtures in `tests/functional/test_functional_fr.py` using testcontainers. The tests:

1. Create a temporary Flask application with mock responses
2. Start a Python container with the Flask app
3. Configure the FR fetcher to use the mock API endpoints
4. Run the fetcher and verify it processes the mock data correctly

## Mock Data Structure

The mock server provides realistic SIREN API responses with:
- Pagination support using `curseurSuivant`
- Realistic French company data structure
- OAuth token authentication
- Error handling for invalid requests

## Manual Testing

If you want to run the mock API manually for testing:

```bash
cd tmp/siren_api_mock
docker build -t siren_api_mock .
docker run -p 5000:5000 siren_api_mock
```

Then test the endpoints:

```bash
# Health check
curl http://localhost:5000/health

# Get OAuth token
curl -X POST http://localhost:5000/token \
  -H "Authorization: Basic dGVzdF9jbGllbnRfaWQ6dGVzdF9jbGllbnRfc2VjcmV0"

# Get SIREN data
curl "http://localhost:5000/entreprises/sirene/V3.11/siren?q=siren:00*" \
  -H "Authorization: Bearer mock_access_token_12345"
```

## Test Integration

The mock API is integrated into the test suite through:

1. **Container Fixture**: `siren_api_container()` in `tests/functional/test_functional_fr.py`
2. **Credential Setup**: Test secrets configured in `tests/conftest.py`
3. **Fetcher Configuration**: FR configuration modified to use mock endpoints
4. **Verification**: Tests verify that bundles are created with mock data

## Mock Responses

The mock server provides predefined responses for different SIREN prefixes:
- `siren:00`: Returns 2 companies with pagination to `siren:01`
- `siren:01`: Returns 1 company with no further pagination
- `siren:99`: Returns empty response (end of pagination)
- Other queries: Return empty response

This allows testing of the complete pagination flow and error handling in the FR configuration.
