# Debugging Tests

This guide covers debugging and troubleshooting test issues in the OC Fetcher framework.

## Debugging Tools

### Verbose Output

```bash
# Run with maximum verbosity
poetry run pytest -vvv

# Show print statements
poetry run pytest -s

# Show local variables on failure
poetry run pytest -l

# Show full traceback
poetry run pytest --tb=long
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

## Common Issues

### Test Failures

#### Import Errors

```python
# Problem: Module not found
ImportError: No module named 'data_fetcher_core'

# Solution: Ensure you're in the right environment
poetry shell
# or
poetry run pytest
```

#### Async Test Issues

```python
# Problem: Async test not running
RuntimeError: There is no current event loop

# Solution: Use proper async test markers
@pytest.mark.asyncio
async def test_async_function():
    pass
```

#### Mock Issues

```python
# Problem: Mock not working
AssertionError: Expected call not made

# Solution: Check mock setup and call verification
mock_service.method.assert_called_with(expected_args)
```

### Performance Issues

#### Slow Tests

```bash
# Identify slow tests
poetry run pytest --durations=10

# Run only fast tests
make test/fast

# Run only slow tests
make test/slow
```

#### Memory Issues

```python
# Monitor memory usage
import psutil
import os

def test_memory_usage():
    process = psutil.Process(os.getpid())
    memory_before = process.memory_info().rss

    # Run test code

    memory_after = process.memory_info().rss
    memory_used = memory_after - memory_before
    assert memory_used < 100 * 1024 * 1024  # 100MB limit
```

### Environment Issues

#### Docker Issues

```bash
# If Docker is not running
sudo systemctl start docker

# If permission issues
sudo usermod -aG docker $USER
# Log out and back in
```

#### LocalStack Issues

```bash
# If LocalStack is not responding
docker-compose -f stubs/docker-compose.yml down
docker-compose -f stubs/docker-compose.yml up -d

# Check LocalStack health
curl http://localhost:4566/health
```

## Debugging Techniques

### Print Debugging

```python
def test_with_prints():
    """Test using print statements for debugging."""
    result = some_function()
    print(f"Result: {result}")
    print(f"Result type: {type(result)}")
    print(f"Result attributes: {dir(result)}")

    assert result is not None
```

### Logging Debugging

```python
import logging

def test_with_logging():
    """Test using logging for debugging."""
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    logger.debug("TEST_STARTING")
    result = some_function()
    logger.debug("TEST_RESULT_RECEIVED", result=result)

    assert result is not None
```

### Assertion Debugging

```python
def test_with_detailed_assertions():
    """Test with detailed assertion messages."""
    result = some_function()

    assert result is not None, f"Result is None, got: {result}"
    assert result.status == "success", f"Expected success, got: {result.status}"
    assert len(result.items) > 0, f"Expected items, got: {result.items}"
```

### Exception Debugging

```python
def test_exception_debugging():
    """Test with exception debugging."""
    try:
        function_that_might_fail()
    except Exception as e:
        print(f"Exception type: {type(e)}")
        print(f"Exception message: {str(e)}")
        print(f"Exception args: {e.args}")
        raise  # Re-raise to fail the test
```

## Test Isolation

### Fixture Cleanup

```python
@pytest.fixture
def temp_file():
    """Fixture with proper cleanup."""
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_file.write(b"test data")
    temp_file.close()

    yield temp_file.name

    # Cleanup
    os.unlink(temp_file.name)
```

### Mock Reset

```python
@pytest.fixture
def mock_service():
    """Fixture with mock reset."""
    mock = Mock()
    yield mock
    mock.reset_mock()
```

### Database Cleanup

```python
@pytest.fixture
def clean_database():
    """Fixture for database cleanup."""
    # Setup
    db.create_all()

    yield

    # Cleanup
    db.drop_all()
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
make pre-commit

# Run all hooks
make pre-commit/run-all
```

## Performance Debugging

### Test Timing

```python
import time

def test_performance():
    """Test with performance monitoring."""
    start_time = time.time()

    # Run test code
    result = some_function()

    end_time = time.time()
    duration = end_time - start_time

    assert duration < 1.0, f"Test took too long: {duration:.2f}s"
    assert result is not None
```

### Memory Profiling

```python
import tracemalloc

def test_memory_profiling():
    """Test with memory profiling."""
    tracemalloc.start()

    # Run test code
    result = some_function()

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert peak < 50 * 1024 * 1024, f"Peak memory usage too high: {peak / 1024 / 1024:.1f}MB"
    assert result is not None
```

## Test Data Debugging

### Data Validation

```python
def test_data_validation():
    """Test with data validation."""
    data = load_test_data()

    # Validate data structure
    assert isinstance(data, dict), f"Expected dict, got {type(data)}"
    assert "items" in data, f"Missing 'items' key, got keys: {list(data.keys())}"
    assert isinstance(data["items"], list), f"Expected list, got {type(data['items'])}"

    # Validate data content
    for item in data["items"]:
        assert "id" in item, f"Missing 'id' in item: {item}"
        assert "name" in item, f"Missing 'name' in item: {item}"
```

### File System Debugging

```python
def test_file_system():
    """Test with file system debugging."""
    test_file = "test_file.txt"

    # Check file exists
    assert os.path.exists(test_file), f"File does not exist: {test_file}"

    # Check file permissions
    assert os.access(test_file, os.R_OK), f"File not readable: {test_file}"

    # Check file content
    with open(test_file, 'r') as f:
        content = f.read()
        assert len(content) > 0, f"File is empty: {test_file}"
```

## Getting Help

### Resources

- **Check logs**: Look at test output and error messages
- **Verify setup**: Run `make all-checks` to verify environment
- **Check issues**: Look at existing GitHub issues
- **Ask questions**: Use GitHub Discussions for help

### Debugging Checklist

- [ ] Are you in the correct environment? (`poetry shell`)
- [ ] Are all dependencies installed? (`poetry install`)
- [ ] Are pre-commit hooks installed? (`make pre-commit`)
- [ ] Do all tests pass? (`make test`)
- [ ] Is the code formatted? (`make format`)
- [ ] Are there linting errors? (`make lint`)
- [ ] Is documentation building? (`make docs`)

## See Also

- **[Testing Overview](overview.md)** - Testing basics and quick start
- **[Writing Tests](writing_tests.md)** - How to write effective tests
- **[Mock Services](mock_services.md)** - Mock services and test fixtures
- **[Troubleshooting Guide](../troubleshooting/troubleshooting_guide.md)** - General troubleshooting
