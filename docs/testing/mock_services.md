# Mock Services

This guide covers using mock services for testing the OC Fetcher framework.

## Overview

Mock services allow you to test components in isolation by replacing external dependencies with controlled test implementations. This makes tests faster, more reliable, and easier to maintain.

## LocalStack for AWS Testing

### Setup

LocalStack provides local AWS services for testing:

```bash
# Start LocalStack
docker-compose -f stubs/docker-compose.yml up -d

# Verify LocalStack is running
curl http://localhost:4566/health
```

### Using LocalStack in Tests

```python
import pytest
import boto3
from moto import mock_s3

@pytest.mark.localstack
@pytest.mark.asyncio
async def test_s3_storage():
    """Test S3 storage with LocalStack."""
    # LocalStack automatically provides S3 service
    s3_client = boto3.client('s3', endpoint_url='http://localhost:4566')

    # Create bucket
    s3_client.create_bucket(Bucket='test-bucket')

    # Test storage operations
    # ... your test code ...
```

### LocalStack Configuration

The LocalStack configuration is in `stubs/docker-compose.yml`:

```yaml
services:
  localstack:
    image: localstack/localstack:latest
    ports:
      - "4566:4566"
    environment:
      - SERVICES=s3,secretsmanager
      - DEBUG=1
      - DATA_DIR=/tmp/localstack/data
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock"
```

## Mock API Server

### Sirene API Mock

The project includes a mock Sirene API server for testing French API integrations:

```bash
# Build and run the mock server
cd mocks/api_fr_siren
docker build -t siren_api_mock .
docker run -p 5000:5000 siren_api_mock
```

### Using Mock API in Tests

```python
@pytest.mark.asyncio
async def test_sirene_api():
    """Test Sirene API with mock server."""
    # Mock server is automatically started by test fixtures
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:5000/api/sirene")
        assert response.status_code == 200
```

## Python Mocking

### unittest.mock

```python
from unittest.mock import Mock, patch, AsyncMock

def test_with_mock():
    """Test using unittest.mock."""
    # Create a mock object
    mock_service = Mock()
    mock_service.get_data.return_value = "test data"

    # Use the mock in your test
    result = function_under_test(mock_service)
    assert result == "test data"

    # Verify mock was called correctly
    mock_service.get_data.assert_called_once()
```

### Async Mocking

```python
@pytest.mark.asyncio
async def test_async_mock():
    """Test using async mocks."""
    mock_service = AsyncMock()
    mock_service.fetch_data.return_value = {"data": "test"}

    result = await async_function_under_test(mock_service)
    assert result["data"] == "test"
```

### Patching

```python
@patch('module.external_service')
def test_with_patch(mock_service):
    """Test using patch decorator."""
    mock_service.return_value.get_data.return_value = "mocked data"

    result = function_under_test()
    assert result == "mocked data"
```

## Test Fixtures

### Mock Fixtures

```python
@pytest.fixture
def mock_sftp_connection():
    """Provide mock SFTP connection."""
    mock_conn = Mock()
    mock_conn.listdir.return_value = ["file1.txt", "file2.txt"]
    mock_conn.get.return_value = b"file content"
    return mock_conn

@pytest.fixture
def mock_http_client():
    """Provide mock HTTP client."""
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.json.return_value = {"data": "test"}
    mock_client.get.return_value = mock_response
    return mock_client
```

### Service Fixtures

```python
@pytest.fixture
async def mock_storage_service():
    """Provide mock storage service."""
    service = MockStorageService()
    await service.setup()
    yield service
    await service.cleanup()

@pytest.fixture
def mock_credential_provider():
    """Provide mock credential provider."""
    provider = MockCredentialProvider()
    provider.add_credentials("test-config", {
        "username": "test_user",
        "password": "test_pass"
    })
    return provider
```

## Mock Data

### Static Mock Data

```python
@pytest.fixture
def sample_sftp_files():
    """Provide sample SFTP file data."""
    return [
        {"name": "file1.txt", "size": 1024, "modified": "2023-01-01"},
        {"name": "file2.txt", "size": 2048, "modified": "2023-01-02"},
    ]

@pytest.fixture
def sample_api_response():
    """Provide sample API response data."""
    return {
        "data": [
            {"id": 1, "name": "Company 1"},
            {"id": 2, "name": "Company 2"},
        ],
        "pagination": {
            "page": 1,
            "total_pages": 10,
            "total_items": 100
        }
    }
```

### Dynamic Mock Data

```python
import factory

class CompanyFactory(factory.Factory):
    """Factory for generating company test data."""
    class Meta:
        model = Company

    id = factory.Sequence(lambda n: n)
    name = factory.Faker("company")
    created_at = factory.Faker("date_time")

@pytest.fixture
def sample_companies():
    """Generate sample companies using factory."""
    return CompanyFactory.build_batch(10)
```

## Mock Services for Specific Protocols

### SFTP Mocking

```python
@pytest.fixture
def mock_sftp_server():
    """Mock SFTP server for testing."""
    server = MockSFTPServer()
    server.add_file("test/file1.txt", b"content1")
    server.add_file("test/file2.txt", b"content2")
    return server

@pytest.mark.asyncio
async def test_sftp_fetch(mock_sftp_server):
    """Test SFTP fetching with mock server."""
    with patch('pysftp.Connection') as mock_conn:
        mock_conn.return_value = mock_sftp_server

        fetcher = get_fetcher("us-fl")
        result = await fetcher.run(plan)

        assert result.status == "success"
```

### HTTP API Mocking

```python
@pytest.fixture
def mock_api_server():
    """Mock HTTP API server for testing."""
    server = MockAPIServer()
    server.add_endpoint("/api/data", {"data": "test"})
    return server

@pytest.mark.asyncio
async def test_api_fetch(mock_api_server):
    """Test API fetching with mock server."""
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value = mock_api_server

        fetcher = get_fetcher("fr")
        result = await fetcher.run(plan)

        assert result.status == "success"
```

## Mock Configuration

### Environment Variables

```python
@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    with patch.dict(os.environ, {
        'OC_CREDENTIAL_US_FL_HOST': 'mock-sftp.example.com',
        'OC_CREDENTIAL_US_FL_USERNAME': 'test_user',
        'OC_CREDENTIAL_US_FL_PASSWORD': 'test_pass',
    }):
        yield
```

### Configuration Files

```python
@pytest.fixture
def mock_config_file(tmp_path):
    """Create mock configuration file."""
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text("""
    storage:
      type: s3
      bucket: test-bucket
    """)
    return config_file
```

## Best Practices

### Mock Design

1. **Keep mocks simple**: Don't over-complicate mock implementations
2. **Match real behavior**: Mocks should behave similarly to real services
3. **Use appropriate abstractions**: Mock at the right level of abstraction
4. **Document mock behavior**: Make it clear what the mock does

### Test Organization

1. **Group related mocks**: Use fixtures to organize related mocks
2. **Reuse mocks**: Create reusable mock fixtures
3. **Clean up**: Ensure mocks are properly cleaned up after tests
4. **Isolate tests**: Each test should be independent of others

### Performance

1. **Use fast mocks**: Avoid slow mock implementations
2. **Mock external dependencies**: Don't make real network calls in tests
3. **Use appropriate mocking levels**: Mock at the right level for your test
4. **Profile mock performance**: Ensure mocks don't slow down tests

## Troubleshooting

### Common Issues

1. **Mock not working**: Check that you're mocking the right import path
2. **Async mock issues**: Use `AsyncMock` for async functions
3. **Mock cleanup**: Ensure mocks are properly reset between tests
4. **Mock configuration**: Verify mock configuration matches expected behavior

### Debugging Mocks

```python
# Enable mock debugging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check mock calls
print(mock_service.method_calls)
print(mock_service.call_args_list)

# Verify mock state
assert mock_service.called
assert mock_service.call_count == 1
```

## See Also

- **[Testing Overview](overview.md)** - Testing basics and quick start
- **[Writing Tests](writing_tests.md)** - How to write effective tests
- **[Debugging Tests](debugging_tests.md)** - Debugging and troubleshooting
