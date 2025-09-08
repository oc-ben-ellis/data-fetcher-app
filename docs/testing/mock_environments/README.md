# Mock Environments

This directory contains documentation for the mock test environments used for development and testing. These environments are integrated with the [Test Cases Framework](../test_cases_framework.md) for comprehensive functional testing.

## Available Test Environments

### France API (FR)
- **[FR Test Setup](fr_test_setup.md)** - Complete test environment for France INSEE SIRENE API
- Includes Mockoon API mocking, OAuth 2.0 authentication, and realistic API responses
- Integrated with test cases in `mocks/test_cases/fr/`

### US Florida SFTP (US_FL)
- **[US FL Test Setup](us_fl_test_setup.md)** - Complete test environment for US Florida SFTP
- Includes mock SFTP server, LocalStack for S3/Secrets Manager, and test data
- Integrated with test cases in `mocks/test_cases/us_fl/`

## Quick Start

Each test environment includes:
- Docker Compose configuration for easy setup
- Mock services with realistic data
- Health checks for reliable service startup
- Integration with the existing test suite

## Usage

1. Navigate to the specific test environment documentation
2. Follow the setup instructions
3. Run the fetcher with the test environment
4. Use the environment for development and testing

## Integration

These environments are designed to work with:
- **[Test Cases Framework](../test_cases_framework.md)** - Automated test case execution and validation
- Functional tests in `tests/test_functional/`
- Manual testing and development
- CI/CD pipelines
- Local development workflows

## Test Case Integration

Each mock environment is integrated with corresponding test cases:

### FR Environment
- **Test Cases**: `mocks/test_cases/fr/`
- **Mock Service**: Mockoon API mocking
- **Configuration**: `mockoon-environment.json` in test case inputs
- **Validation**: JSON response structure and OAuth flow

### US_FL Environment
- **Test Cases**: `mocks/test_cases/us_fl/`
- **Mock Service**: SFTP server with test data
- **Configuration**: SFTP credentials and file patterns
- **Validation**: CSV file structure and content

## Related Documentation

- **[Testing Overview](../overview.md)** - General testing framework
- **[Mock Services](../mock_services.md)** - Mock services documentation
- **[FR API Configuration](../../configurations/fr_api.md)** - France API configuration
- **[US FL SFTP Configuration](../../configurations/us_fl_sftp.md)** - US Florida SFTP configuration
