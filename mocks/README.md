# Mocks Directory

This directory contains mock services and test doubles for external APIs and services used in the OC Fetcher project.

## Purpose

The mocks directory serves as a centralized location for:

1. **Mock API Servers**: Complete mock implementations of external APIs
2. **Test Services**: Services that simulate external dependencies for testing
3. **Development Tools**: Mock services for local development when external services are unavailable
4. **Test Environments**: Complete docker-compose environments for end-to-end testing

## Directory Structure

```
mocks/
├── images/           # Docker images for mock services
│   ├── api_fr_siren/     # French SIREN API mock
│   └── us_fl_sftp/       # US Florida SFTP mock
├── environments/     # Complete test environments
│   ├── fr/               # French SIREN API test environment
│   └── us_fl/            # US Florida SFTP test environment
└── README.md         # This file
```

## Quick Start

### Using Test Environments (Recommended)

For end-to-end testing, use the complete test environments:

```bash
# French SIREN API environment
cd mocks/environments/fr
docker-compose up -d
./setup-mock-data.sh

# US Florida SFTP environment
cd mocks/environments/us_fl
docker-compose up -d
./setup-mock-data.sh
```

Each environment includes:
- Mock service containers
- LocalStack for S3/AWS services
- Pre-configured networking
- Health checks
- Setup scripts for mock data
- Complete documentation

### Using Individual Mock Images

For development or custom testing:

```bash
# Build and run French SIREN API mock
cd mocks/images/api_fr_siren
docker build -t siren_api_mock .
docker run -p 5000:5000 siren_api_mock

# Build and run US Florida SFTP mock
cd mocks/images/us_fl_sftp
docker build -t us_fl_sftp_mock .
docker run -p 2222:22 us_fl_sftp_mock
```

## Test Environments

### French SIREN API Environment (`environments/fr/`)
- **Mock SIREN API**: Port 5001 (configurable)
- **LocalStack**: Port 4566 (configurable, S3, Secrets Manager)
- **Setup Script**: `setup-mock-data.sh` - Verifies API endpoints
- **Purpose**: Test French INSEE API integration
- **Documentation**: [environments/fr/README.md](environments/fr/README.md)

### US Florida SFTP Environment (`environments/us_fl/`)
- **Mock SFTP Server**: Port 2222 (configurable)
- **LocalStack**: Port 4566 (configurable, S3, Secrets Manager)
- **Setup Script**: `setup-mock-data.sh` - Creates mock data files
- **Purpose**: Test US Florida SFTP integration
- **Documentation**: [environments/us_fl/README.md](environments/us_fl/README.md)

## Mock Images

### French SIREN API (`images/api_fr_siren/`)
- **Type**: Flask web application
- **Endpoints**: OAuth token, SIREN data, health check
- **Documentation**: [images/api_fr_siren/README.md](images/api_fr_siren/README.md)

### US Florida SFTP (`images/us_fl_sftp/`)
- **Type**: SFTP server with mock data
- **Credentials**: testuser/testpass
- **Data**: Daily and quarterly corporate files
- **Documentation**: [images/us_fl_sftp/README.md](images/us_fl_sftp/README.md)

## Integration with Tests

Mock services are integrated with the test suite through:

1. **Test Fixtures**: Automatic container management in test fixtures
2. **Configuration**: Test configurations that point to mock endpoints
3. **Cleanup**: Automatic cleanup of containers after test completion

## Development Guidelines

1. **Naming**: Use descriptive names that indicate the service and country/region
2. **Documentation**: Each mock service should include its own README.md
3. **Docker**: Use Docker for easy deployment and testing
4. **Realistic Data**: Provide realistic mock responses that match the actual API structure
5. **Error Handling**: Include error scenarios and edge cases in mock responses
6. **Health Checks**: Include health check endpoints for reliable service startup

## Adding New Mocks

When adding new mock services:

1. Create the mock image in `images/[service_name]/`
2. Include Dockerfile, mock data, and README.md
3. Create a test environment in `environments/[service_name]/`
4. Include docker-compose.yml and README.md
5. Update this README.md with the new service information

See existing examples for the expected structure and documentation format.
