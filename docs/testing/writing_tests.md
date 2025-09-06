# Writing Tests

This guide covers how to write effective tests for the OC Fetcher framework.

## Basic Test Structure

### Simple Test

```python
import pytest
from data_fetcher_core.registry import get_fetcher

@pytest.mark.asyncio
async def test_basic_fetch():
    """Test basic fetch functionality."""
    fetcher = get_fetcher("us-fl")
    # Test implementation
```

### Testing Fetcher Recipes

```python
@pytest.mark.asyncio
async def test_us_fl_configuration():
    """Test US Florida fetcher recipe."""
    fetcher = get_fetcher("us-fl")
    assert fetcher is not None
    # Additional assertions
```

### Testing Error Conditions

```python
@pytest.mark.asyncio
async def test_invalid_configuration():
    """Test handling of invalid fetcher recipe."""
    with pytest.raises(KeyError):
        get_fetcher("invalid-config")
```

## Test Cases Framework

The Test Cases Framework provides a structured approach to functional testing with automatic discovery, mock environment management, and output validation.

### Creating Test Cases

Test cases are automatically discovered from the `mocks/test_cases/` directory structure:

```
mocks/test_cases/
├── <recipe>/                    # Recipe name (e.g., fr, us_fl)
│   └── <test_case>/            # Test case name (e.g., basic, advanced)
│       ├── inputs/             # Input configuration and sample data
│       │   ├── config.json     # Test configuration
│       │   ├── sample_input.*  # Sample input files (optional)
│       │   └── mockoon-environment.json  # Mockoon config (HTTP recipes)
│       └── expected/           # Expected output structure
│           └── sample_output/  # Sample expected output files
```

### Test Case Configuration

Create a `config.json` file for each test case:

```json
{
  "description": "Basic French SIREN API test case",
  "recipe": "fr",
  "credentials": {
    "provider_type": "environment",
    "client_id": "test_client_id",
    "client_secret": "test_client_secret"
  },
  "storage": {
    "type": "file",
    "path": "tmp/test_output"
  },
  "date_range": {
    "start_date": "2025-09-07",
    "end_date": "2025-09-07"
  }
}
```

### HTTP API Test Cases (FR Recipe)

For HTTP-based recipes, include Mockoon configuration:

```json
{
  "uuid": "environment-uuid",
  "name": "French SIREN API Mock",
  "port": 3000,
  "routes": [
    {
      "uuid": "route-token",
      "method": "POST",
      "endpoint": "token",
      "responses": [
        {
          "uuid": "response-token",
          "body": "{\"access_token\": \"mock_access_token\", \"expires_in\": 3600}",
          "statusCode": 200,
          "headers": [{"key": "Content-Type", "value": "application/json"}]
        }
      ]
    }
  ]
}
```

### SFTP Test Cases (US_FL Recipe)

For SFTP-based recipes, include sample input data:

```csv
id,name,date,value
1,Test Company A,2025-09-01,100.50
2,Test Company B,2025-09-01,250.75
3,Test Company C,2025-09-01,175.25
```

### Expected Output Structure

Create expected output files in `expected/sample_output/`:

**bundle.meta**:
```json
{
  "bid": "bundle_recipe_20250907_001",
  "primary_url": "https://api.example.com/data",
  "resources_count": 2,
  "storage_key": "bundle_recipe_20250907_001"
}
```

**Response files**: Actual data files (JSON, CSV, etc.)
**Metadata files**: `.meta` files with file-specific metadata

### Running Test Cases

Test cases are automatically discovered and run:

```bash
# Run all test cases
poetry run python -m pytest tests/test_functional/test_all_test_cases.py -v

# Run specific recipe tests
poetry run python -m pytest tests/test_functional/test_all_test_cases.py::TestAllTestCases::test_fr_recipe_test_cases -v

# Run specific test case
poetry run python -m pytest tests/test_functional/test_all_test_cases.py::TestAllTestCases::test_fr_basic_test_case -v
```

For detailed information, see [Test Cases Framework](test_cases_framework.md).

## Integration Testing

### End-to-End Tests

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_fetch_workflow():
    """Test complete fetch workflow."""
    # Setup test data
    # Run fetcher
    # Verify results
```

### Performance Tests

```python
@pytest.mark.slow
@pytest.mark.asyncio
async def test_large_file_processing():
    """Test processing of large files."""
    # Test with large files
    # Verify memory usage
    # Check performance metrics
```

## Test Fixtures

### Basic Fixtures

```python
import pytest

@pytest.fixture
def sample_configuration():
    """Provide sample configuration for tests."""
    return {
        "name": "test-config",
        "type": "sftp",
        "settings": {...}
    }
```

### Temporary Files

```python
import tempfile
import pytest

@pytest.fixture
def temp_dir():
    """Provide temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir
```

### Async Fixtures

```python
@pytest.fixture
async def mock_fetcher():
    """Provide mock fetcher for tests."""
    fetcher = MockFetcher()
    await fetcher.setup()
    yield fetcher
    await fetcher.cleanup()
```

## Mock Services

### Mocking External APIs

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_api_fetch():
    """Test API fetching with mocked responses."""
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.json.return_value = {"data": "test"}
        mock_client.return_value.get.return_value = mock_response

        # Test your code
```

### Mocking SFTP Connections

```python
@pytest.mark.asyncio
async def test_sftp_fetch():
    """Test SFTP fetching with mocked connection."""
    with patch('pysftp.Connection') as mock_sftp:
        mock_sftp.return_value.listdir.return_value = ["file1.txt", "file2.txt"]

        # Test your code
```

## Test Data Management

### Using Test Data Files

```python
import json
from pathlib import Path

@pytest.fixture
def sample_data():
    """Load sample data from file."""
    data_file = Path(__file__).parent / "data" / "sample.json"
    with open(data_file) as f:
        return json.load(f)
```

### Generating Test Data

```python
import factory

class TestDataFactory(factory.Factory):
    """Factory for generating test data."""
    class Meta:
        model = TestData

    name = factory.Sequence(lambda n: f"test-{n}")
    value = factory.Faker("random_int", min=1, max=100)
```

## Assertions

### Basic Assertions

```python
def test_basic_assertions():
    """Test basic assertion patterns."""
    result = some_function()

    # Basic assertions
    assert result is not None
    assert result.status == "success"
    assert len(result.items) > 0

    # Type assertions
    assert isinstance(result, ExpectedType)

    # Collection assertions
    assert "expected_item" in result.items
    assert all(item.valid for item in result.items)
```

### Async Assertions

```python
@pytest.mark.asyncio
async def test_async_assertions():
    """Test async assertion patterns."""
    result = await async_function()

    assert result is not None
    assert await result.is_ready()
    assert result.data is not None
```

## Error Testing

### Testing Exceptions

```python
def test_exception_handling():
    """Test that exceptions are raised correctly."""
    with pytest.raises(ValueError, match="Invalid input"):
        function_that_raises_value_error("invalid")

    with pytest.raises(ConnectionError):
        function_that_raises_connection_error()
```

### Testing Async Exceptions

```python
@pytest.mark.asyncio
async def test_async_exception_handling():
    """Test async exception handling."""
    with pytest.raises(TimeoutError):
        await async_function_with_timeout()
```

## Parametrized Tests

### Basic Parametrization

```python
@pytest.mark.parametrize("input_value,expected", [
    ("test1", "result1"),
    ("test2", "result2"),
    ("test3", "result3"),
])
def test_parametrized(input_value, expected):
    """Test with multiple input values."""
    result = function_under_test(input_value)
    assert result == expected
```

### Async Parametrization

```python
@pytest.mark.parametrize("config_name", ["us-fl", "fr"])
@pytest.mark.asyncio
async def test_configurations(config_name):
    """Test multiple fetcher recipes."""
    fetcher = get_fetcher(config_name)
    assert fetcher is not None
```

## Test Organization

### Test Classes

```python
class TestFetcher:
    """Test class for Fetcher functionality."""

    @pytest.fixture
    def fetcher(self):
        """Provide fetcher instance for tests."""
        return get_fetcher("us-fl")

    @pytest.mark.asyncio
    async def test_run_success(self, fetcher):
        """Test successful run."""
        result = await fetcher.run(plan)
        assert result.status == "success"

    @pytest.mark.asyncio
    async def test_run_failure(self, fetcher):
        """Test run failure."""
        with pytest.raises(RuntimeError):
            await fetcher.run(invalid_plan)
```

### Test Modules

```python
# tests/test_unit/test_fetcher.py
"""Unit tests for Fetcher class."""

import pytest
from data_fetcher_core.fetcher import Fetcher

class TestFetcher:
    """Test cases for Fetcher class."""

    def test_initialization(self):
        """Test fetcher initialization."""
        fetcher = Fetcher(config)
        assert fetcher is not None
```

## Best Practices

### Test Naming

- Use descriptive test names that explain what is being tested
- Include the expected behavior in the test name
- Use consistent naming patterns across the test suite

### Test Structure

- Follow the Arrange-Act-Assert pattern
- Keep tests focused on a single behavior
- Use appropriate fixtures for setup and teardown

### Test Data

- Use minimal test data that covers the necessary cases
- Make test data deterministic and predictable
- Clean up test data after tests complete

### Performance

- Keep unit tests fast (under 1 second)
- Mark slow tests appropriately
- Use mocks for external dependencies

## See Also

- **[Testing Overview](overview.md)** - Testing basics and quick start
- **[Mock Services](mock_services.md)** - Mock services and test fixtures
- **[Debugging Tests](debugging_tests.md)** - Debugging and troubleshooting
