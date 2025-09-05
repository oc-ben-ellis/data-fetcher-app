# Mocks Directory

This directory contains mock services and test doubles for external APIs and services used in the OC Fetcher project.

## Purpose

The mocks directory serves as a centralized location for:

1. **Mock API Servers**: Complete mock implementations of external APIs
2. **Test Services**: Services that simulate external dependencies for testing
3. **Development Tools**: Mock services for local development when external services are unavailable

## Contents

### Mock Services

- `fr_siren_api/` - Mock SIREN API server for testing French INSEE API integration

## Usage

### Starting Mock Services

Mock services can be started manually using Docker:

```bash
# Start French SIREN API mock
cd mocks/fr_siren_api
docker build -t siren_api_mock .
docker run -p 5000:5000 siren_api_mock

# Stop the mock service (Ctrl+C or docker stop)
```

### In Tests

Mock services are automatically used by test fixtures. The test framework will:

1. Start the appropriate mock service containers
2. Configure the fetcher to use the mock endpoints
3. Run tests against the mock service
4. Clean up containers after tests complete

### Manual Testing

You can also run mock services manually for development and testing:

```bash
# Start the mock service
cd mocks/fr_siren_api
docker build -t siren_api_mock .
docker run -p 5000:5000 siren_api_mock

# Test the endpoints
curl http://localhost:5000/health
```

## Organization

Mock services are organized by the external service they simulate:

- `fr_siren_api/` - French INSEE SIREN API mock
- Future mocks can be added following the same pattern (e.g., `us_sec_api/`, `uk_companies_api/`)

## Development Guidelines

1. **Naming**: Use descriptive names that indicate the service and country/region (e.g., `fr_siren_api`)
2. **Documentation**: Each mock service should include its own README.md explaining its purpose and usage
3. **Docker**: Use Docker for easy deployment and testing
4. **Realistic Data**: Provide realistic mock responses that match the actual API structure
5. **Error Handling**: Include error scenarios and edge cases in mock responses

## Integration with Tests

Mock services are integrated with the test suite through:

1. **Test Fixtures**: Automatic container management in test fixtures
2. **Configuration**: Test configurations that point to mock endpoints
3. **Cleanup**: Automatic cleanup of containers after test completion

See the individual mock service directories for specific usage instructions.
