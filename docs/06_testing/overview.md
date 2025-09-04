# Testing Guide

This guide covers testing the OC Fetcher framework, including test configuration, running tests, writing tests, and best practices.

## Running Tests

### Basic Test Commands

```bash
# Run all tests
poetry run pytest

# Run with verbose output
poetry run pytest -v

# Run specific test file
poetry run pytest tests/test_fetcher.py

# Run specific test
poetry run pytest tests/test_fetcher.py::TestFetcher::test_run_with_requests

# Run with coverage
poetry run pytest --cov=data_fetcher
```

### Test Configuration

The project uses pytest with the following configuration:

- **asyncio_mode**: `auto` - Automatically detects and runs async tests
- **timeout**: 300 seconds - Default timeout for all tests
- **strict-markers**: Enabled - Ensures all test markers are registered
- **disable-warnings**: Enabled - Reduces noise in test output

## Test Structure

### Test Files

- `tests/test_fetcher.py` - Core fetcher functionality
- `tests/test_configurations/` - Configuration-specific tests
- `tests/test_storage/` - Storage system tests
- `tests/test_protocols/` - Protocol manager tests
- `tests/mocks/` - Mock services for testing

### Test Markers

```python
@pytest.mark.asyncio          # Mark test as async
@pytest.mark.localstack      # Mark test as requiring localstack container
@pytest.mark.integration     # Mark test as integration test
@pytest.mark.slow           # Mark test as slow-running
```

## Graceful Shutdown Handling

### Problem
When running tests with `make test`, pressing Ctrl-C would result in logging errors like:
```
ValueError: I/O operation on closed file.
```

This happened because asyncio tasks were still running when the event loop was closed, causing the logging system to try to write to closed file handles. Additionally, the tests would continue running instead of stopping immediately when Ctrl-C was pressed.

### Solution
The test configuration now includes:

1. **Signal Handlers**: Proper handling of SIGINT and SIGTERM signals with graceful shutdown message
2. **Custom Exception Handler**: Filters out I/O errors during shutdown to prevent logging errors
3. **Task Cleanup**: Automatically cancels and waits for pending tasks
4. **Session Cleanup**: Additional cleanup at the end of the test session
5. **Immediate Termination**: Tests stop immediately when Ctrl-C is pressed

### Implementation Details

#### Signal Handling (`tests/conftest.py`)
```python
def _signal_handler(signum: int, frame: Any) -> None:
    """Handle shutdown signals gracefully."""
    global _shutdown_requested
    _shutdown_requested = True
    print(f"\nReceived signal {signum}, shutting down gracefully...")
    # Force exit to bypass pytest's signal handling
    os._exit(130)  # Exit code 130 is standard for SIGINT
```

#### Custom Exception Handler
```python
def custom_exception_handler(loop: asyncio.AbstractEventLoop, context: dict[str, Any]) -> None:
    """Custom exception handler that ignores certain errors during shutdown."""
    global _shutdown_requested

    if _shutdown_requested:
        exception = context.get('exception')
        if exception and isinstance(exception, (ValueError, OSError)):
            if "I/O operation on closed file" in str(exception):
                return  # Silently ignore during shutdown

    loop.default_exception_handler(context)
```

#### Task Cleanup
```python
# Clean up any remaining tasks before closing the loop
pending_tasks = [task for task in asyncio.all_tasks(loop) if not task.done()]
if pending_tasks:
    for task in pending_tasks:
        task.cancel()
    loop.run_until_complete(asyncio.gather(*pending_tasks, return_exceptions=True))
```

## Mock Services

### LocalStack for AWS Testing

Some tests require AWS services. Use LocalStack for local testing:

```bash
# Start LocalStack
docker-compose -f tests/mocks/docker-compose.yml up -d

# Run tests that require LocalStack
poetry run pytest -m localstack

# Stop LocalStack
docker-compose -f tests/mocks/docker-compose.yml down
```

### Mock API Server

For API testing, a mock Sirene API server is provided:

```bash
# Start mock API server
docker-compose -f tests/mocks/siren_api/docker-compose.yml up -d

# Run API tests
poetry run pytest tests/test_configurations/test_fr.py

# Stop mock server
docker-compose -f tests/mocks/siren_api/docker-compose.yml down
```

## Writing Tests

### Basic Test Structure

```python
import pytest
from data_fetcher.registry import get_fetcher

@pytest.mark.asyncio
async def test_basic_fetch():
    """Test basic fetch functionality."""
    fetcher = get_fetcher("us-fl")
    # Test implementation
```

### Testing Configurations

```python
@pytest.mark.asyncio
async def test_us_fl_configuration():
    """Test US Florida configuration."""
    fetcher = get_fetcher("us-fl")
    assert fetcher is not None
    # Additional assertions
```

### Testing Error Conditions

```python
@pytest.mark.asyncio
async def test_invalid_configuration():
    """Test handling of invalid configuration."""
    with pytest.raises(KeyError):
        get_fetcher("invalid-config")
```

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

## Debugging Tests

### Verbose Output

```bash
# Run with maximum verbosity
poetry run pytest -vvv

# Show print statements
poetry run pytest -s

# Show local variables on failure
poetry run pytest -l
```

### Debugging Failed Tests

```python
import pytest

@pytest.mark.asyncio
async def test_debug_example():
    """Example test with debugging."""
    import pdb; pdb.set_trace()  # Breakpoint for debugging
    # Test code
```

### Test Ctrl-C Handling
To test the graceful shutdown, you can run a long-running test and press Ctrl-C:
```bash
make test ARGS="tests/test_fetcher.py -v"
# Then press Ctrl-C during the test run
```

## Continuous Integration

### GitHub Actions

The project includes GitHub Actions workflows for:

- Running tests on pull requests
- Code quality checks (linting, formatting)
- Coverage reporting
- Security scanning

### Pre-commit Hooks

Install pre-commit hooks for automatic checks:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run all hooks
pre-commit run --all-files
```

## Test Data Management

### Test Fixtures

Use pytest fixtures for test data:

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

Use temporary directories for file-based tests:

```python
import tempfile
import pytest

@pytest.fixture
def temp_dir():
    """Provide temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir
```

## Dependencies

The following testing dependencies are included:

- `pytest`: Core testing framework
- `pytest-asyncio`: Async test support
- `pytest-timeout`: Test timeout support
- `coverage`: Code coverage reporting
- `testcontainers`: Container-based testing
- `mypy`: Type checking
- `black`: Code formatting
- `ruff`: Linting

## Best Practices

### Test Organization

1. **Group related tests** in the same file
2. **Use descriptive test names** that explain what is being tested
3. **Keep tests independent** - each test should be able to run alone
4. **Use appropriate assertions** - be specific about what you're testing

### Test Data

1. **Use minimal test data** - only include what's necessary
2. **Make test data deterministic** - avoid random values
3. **Clean up after tests** - use fixtures for setup/teardown
4. **Document test data** - explain what the data represents

### Performance

1. **Keep tests fast** - avoid unnecessary delays
2. **Use mocks** for external dependencies
3. **Mark slow tests** appropriately
4. **Monitor test execution time** regularly

### General Testing Guidelines

1. **Use Async Tests**: Mark async tests with `@pytest.mark.asyncio`
2. **Mock External Dependencies**: Use mocks for external services
3. **Test Timeouts**: Long-running tests should have appropriate timeouts
4. **Clean Up Resources**: Ensure proper cleanup in test fixtures
5. **Handle Interruptions**: Tests should handle Ctrl-C gracefully
