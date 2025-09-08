# Test Cases Framework

The Test Cases Framework provides a comprehensive, structured approach to functional testing of data fetcher recipes. It enables automated discovery, execution, and validation of test cases with input data and expected output comparison.

## Overview

The framework automatically:
- **Discovers** all test cases in the `mocks/test_cases/` directory
- **Manages** mock environments (Mockoon for HTTP APIs, SFTP servers for file-based recipes)
- **Executes** fetchers with test configurations
- **Validates** output structure and content against expected results
- **Compares** actual output with expected files for comprehensive validation

## Directory Structure

```
mocks/test_cases/
├── README.md                           # Framework documentation
├── <recipe>/                           # Recipe name (e.g., fr, us_fl)
│   └── <test_case>/                   # Test case name (e.g., basic, advanced)
│       ├── inputs/                    # Input configuration and sample data
│       │   ├── config.json            # Test configuration
│       │   ├── sample_input.*         # Sample input files (optional)
│       │   ├── sample_input_metadata.json  # Input metadata (optional)
│       │   └── mockoon-environment.json    # Mockoon config (HTTP recipes)
│       └── expected/                  # Expected output structure
│           ├── README.md              # Expected output documentation
│           └── sample_output/         # Sample expected output files
│               ├── bundle.meta        # Bundle metadata
│               ├── <response_file_1>  # Response data files
│               ├── <response_file_1>.meta  # File metadata
│               └── ...
```

## Test Case Types

### HTTP API Test Cases (e.g., FR)

**Purpose**: Test HTTP-based recipes with OAuth authentication and API responses

**Components**:
- **Mockoon Configuration**: `mockoon-environment.json` defines mock API endpoints
- **OAuth Testing**: Validates token acquisition and API authentication
- **Response Validation**: Compares JSON responses with expected structure
- **Pagination Testing**: Tests complex pagination and cursor-based navigation

**Example Structure**:
```
fr/basic/
├── inputs/
│   ├── config.json                    # FR recipe configuration
│   ├── mockoon-environment.json       # Mockoon API endpoints
│   └── sample_input_metadata.json     # API response expectations
└── expected/
    └── sample_output/
        ├── bundle.meta                # Bundle metadata
        ├── api_response.json          # Expected API response
        └── api_response.json.meta     # Response metadata
```

### SFTP Test Cases (e.g., US_FL)

**Purpose**: Test SFTP-based recipes with file download and processing

**Components**:
- **SFTP Mock Server**: `atmoz/sftp` container with test data
- **File Processing**: Validates CSV file structure and content
- **Metadata Validation**: Checks file metadata and checksums
- **Date Range Testing**: Tests file filtering by date ranges

**Example Structure**:
```
us_fl/basic/
├── inputs/
│   ├── config.json                    # US_FL recipe configuration
│   ├── sample_input.csv               # Sample CSV data
│   └── sample_input_metadata.json     # File processing expectations
└── expected/
    └── sample_output/
        ├── bundle.meta                # Bundle metadata
        ├── sample_data_2025-09-01.csv # Expected CSV file 1
        ├── sample_data_2025-09-01.csv.meta # File 1 metadata
        ├── sample_data_2025-09-02.csv # Expected CSV file 2
        └── sample_data_2025-09-02.csv.meta # File 2 metadata
```

## Configuration Files

### config.json

The main test configuration file:

```json
{
  "description": "Test case description",
  "recipe": "recipe_name",
  "credentials": {
    "provider_type": "environment",
    "key1": "value1",
    "key2": "value2"
  },
  "storage": {
    "type": "file",
    "path": "tmp/test_output"
  },
  "date_range": {
    "start_date": "2025-09-01",
    "end_date": "2025-09-02"
  },
  "additional_config": {
    "key": "value"
  }
}
```

**Required Fields**:
- `recipe`: The recipe name to test
- `credentials`: Authentication configuration
- `storage`: Output storage configuration

**Optional Fields**:
- `date_range`: Date range for testing
- `additional_config`: Recipe-specific configuration

### sample_input_metadata.json

Metadata about the input data and expected behavior:

```json
{
  "description": "Input data description",
  "file_count": 2,
  "expected_files": ["file1.csv", "file2.csv"],
  "date_range": {
    "start_date": "2025-09-01",
    "end_date": "2025-09-02"
  },
  "api_endpoints": ["/token", "/api/data"],
  "expected_responses": {
    "token": {
      "access_token": "mock_token",
      "token_type": "Bearer"
    }
  }
}
```

### mockoon-environment.json (HTTP Recipes)

Mockoon configuration for HTTP API mocking:

```json
{
  "uuid": "environment-uuid",
  "name": "API Mock Environment",
  "port": 3000,
  "routes": [
    {
      "uuid": "route-token",
      "method": "POST",
      "endpoint": "token",
      "responses": [
        {
          "uuid": "response-token",
          "body": "{\"access_token\": \"mock_token\"}",
          "statusCode": 200,
          "headers": [{"key": "Content-Type", "value": "application/json"}]
        }
      ]
    }
  ]
}
```

## Expected Output Structure

### bundle.meta

Bundle metadata with required fields:

```json
{
  "bid": "bundle_recipe_20250907_001",
  "primary_url": "https://api.example.com/data",
  "resources_count": 2,
  "storage_key": "bundle_recipe_20250907_001",
  "meta": {
    "recipe": "recipe_name",
    "date_range": {
      "start_date": "2025-09-01",
      "end_date": "2025-09-02"
    },
    "created_at": "2025-09-07T10:00:00Z"
  }
}
```

**Required Fields**:
- `bid`: Bundle identifier
- `primary_url`: Primary data source URL
- `resources_count`: Number of resource files
- `storage_key`: Storage location key

### Response Files

**Data Files**: Actual response data (JSON, CSV, etc.)
**Metadata Files**: `.meta` files with file-specific metadata

```json
{
  "source_path": "https://api.example.com/data",
  "file_size": 1024,
  "download_timestamp": "2025-09-07T10:00:00Z",
  "checksum": "sha256:abc123def456"
}
```

## Running Tests

### Automatic Test Discovery

The framework automatically discovers and runs all test cases:

```bash
# Run all test cases
poetry run python -m pytest tests/test_functional/test_all_test_cases.py -v

# Run specific recipe tests
poetry run python -m pytest tests/test_functional/test_all_test_cases.py::TestAllTestCases::test_fr_recipe_test_cases -v

# Run specific test case
poetry run python -m pytest tests/test_functional/test_all_test_cases.py::TestAllTestCases::test_fr_basic_test_case -v
```

### Manual Test Execution

You can also run individual test cases manually:

```bash
# Run FR basic test case
poetry run python -m pytest tests/test_functional/test_all_test_cases.py::TestAllTestCases::test_fr_basic_test_case -v

# Run US_FL basic test case
poetry run python -m pytest tests/test_functional/test_all_test_cases.py::TestAllTestCases::test_us_fl_basic_test_case -v
```

## Validation Features

### Output Structure Validation

The framework validates:
- **Directory Structure**: Ensures proper bundle directory creation
- **File Count**: Verifies correct number of output files
- **File Names**: Compares actual vs expected file names
- **Bundle Metadata**: Validates required metadata fields

### Content Comparison

**JSON Files**: Validates JSON structure and required fields
**CSV Files**: Compares headers, structure, and content
**Metadata Files**: Validates file metadata and checksums

### Flexible Validation

- **Critical Errors**: Fail tests for missing required files or invalid structure
- **Warnings**: Log warnings for content differences without failing tests
- **Configurable**: Adjust validation strictness per test case

## Mock Environment Management

### Automatic Service Management

The framework automatically:
- **Starts** appropriate mock services (Mockoon, SFTP, LocalStack)
- **Configures** services with test data
- **Waits** for services to be healthy
- **Stops** services after test completion

### Service Types

**HTTP APIs**: Mockoon containers with configured endpoints
**SFTP Servers**: `atmoz/sftp` containers with test data
**AWS Services**: LocalStack for S3 and Secrets Manager

### Health Checks

All mock services include health checks to ensure reliable startup:
- **HTTP Services**: Health endpoint validation
- **SFTP Services**: Connection and authentication testing
- **AWS Services**: Service availability checks

## Adding New Test Cases

### 1. Create Test Case Directory

```bash
mkdir -p mocks/test_cases/<recipe>/<test_case_name>/inputs
mkdir -p mocks/test_cases/<recipe>/<test_case_name>/expected/sample_output
```

### 2. Add Configuration Files

Create `config.json` with test configuration:
```json
{
  "description": "Test case description",
  "recipe": "recipe_name",
  "credentials": {
    "provider_type": "environment",
    "key": "value"
  },
  "storage": {
    "type": "file",
    "path": "tmp/test_output"
  }
}
```

### 3. Add Input Data (Optional)

- `sample_input.*`: Sample input files
- `sample_input_metadata.json`: Input metadata
- `mockoon-environment.json`: Mockoon config (HTTP recipes)

### 4. Add Expected Output

Create expected output files in `expected/sample_output/`:
- `bundle.meta`: Bundle metadata
- Response files: Expected data files
- `.meta` files: File metadata

### 5. Test Discovery

The framework automatically discovers and runs the new test case.

## Best Practices

### Test Case Design

1. **Descriptive Names**: Use clear, descriptive test case names
2. **Minimal Data**: Include only necessary test data
3. **Realistic Scenarios**: Use realistic data and configurations
4. **Documentation**: Document expected behavior in README files

### Configuration Management

1. **Environment Variables**: Use environment variables for sensitive data
2. **Consistent Structure**: Follow established directory structure
3. **Validation**: Include comprehensive expected output validation
4. **Flexibility**: Allow for minor differences in output format

### Mock Environment Setup

1. **Health Checks**: Include health checks for all services
2. **Test Data**: Provide realistic test data
3. **Cleanup**: Ensure proper cleanup after tests
4. **Isolation**: Keep test environments isolated

## Troubleshooting

### Common Issues

**Service Startup Failures**:
- Check Docker service availability
- Verify port availability
- Review service health check logs

**Test Discovery Issues**:
- Ensure proper directory structure
- Verify `config.json` exists and is valid
- Check file permissions

**Validation Failures**:
- Review expected output structure
- Check file content differences
- Verify metadata format

### Debug Mode

Enable debug logging for detailed test execution:

```bash
# Run with debug output
poetry run python -m pytest tests/test_functional/test_all_test_cases.py -v -s --log-cli-level=DEBUG
```

## Integration

### CI/CD Pipelines

The test case framework integrates with CI/CD pipelines:
- **Parallel Execution**: Run multiple test cases in parallel
- **Service Management**: Automatic mock service lifecycle
- **Artifact Collection**: Collect test output for analysis
- **Failure Reporting**: Detailed failure information

### Development Workflow

Use test cases for:
- **Development Testing**: Validate changes during development
- **Regression Testing**: Ensure changes don't break existing functionality
- **Integration Testing**: Test complete recipe workflows
- **Documentation**: Provide examples of expected behavior

## See Also

### **Related Documentation**
- **[Testing Overview](overview.md)** - General testing framework
- **[Mock Environments](mock_environments/README.md)** - Mock environment setup
- **[Writing Tests](writing_tests.md)** - Test development guide
- **[Debugging Tests](debugging_tests.md)** - Troubleshooting guide

### **Related Concepts**
- **[Fetcher Recipes](../configurations/README.md)** - Recipe configuration
- **[Architecture Documentation](../architecture/README.md)** - System architecture
- **[Contributing Guide](../contributing/contributing_guide.md)** - Development workflow
