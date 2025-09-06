# Docstring Standards and Enforcement

## Overview

This document outlines the docstring standards enforced in the OC Fetcher project. All Python code must follow PEP 257 compliance and use Google-style docstrings for consistency and maintainability.

## Standards

### 1. PEP 257 Compliance

- **Module docstrings**: Every Python file must start with a module-level docstring
- **Function docstrings**: All public functions must have docstrings
- **Class docstrings**: All classes must have docstrings
- **Method docstrings**: All public methods must have docstrings

### 2. Google Style Format

All docstrings must follow the Google style format:

```python
def function_name(param1: str, param2: int) -> bool:
    """Short description of what the function does.

    Longer description if needed, explaining the purpose, behavior,
    and any important implementation details.

    Args:
        param1: Description of the first parameter.
        param2: Description of the second parameter.

    Returns:
        Description of what is returned.

    Raises:
        ValueError: When something goes wrong.
        TypeError: When wrong type is passed.

    Example:
        >>> function_name("test", 42)
        True
    """
    pass
```

### 3. Module Headers

Every Python file must start with this standard header:

```python
"""
Module description.

This module provides functionality for...
"""

```

### 4. Exceptions to Requirements

Small or obvious functions/classes may omit docstrings if:
- The function name is self-explanatory
- The function is a simple getter/setter
- The function is a simple property wrapper
- The class is a simple data container with obvious purpose

## Enforcement Tools

### 1. Ruff with Pydocstyle

The project uses Ruff with pydocstyle integration to enforce docstring standards:

```bash
# Check docstring compliance (included in ruff linting)
make lint/ruff

# Or directly with ruff
poetry run ruff check --select D .
```

### 2. Pre-commit Hooks

Pre-commit hooks automatically check docstrings before each commit:

```bash
# Install pre-commit hooks
make pre-commit

# Run pre-commit manually
poetry run pre-commit run --all-files
```

### 3. Make Targets

Several make targets are available for docstring management:

```bash
# Check docstring compliance (included in ruff linting)
make lint/ruff

# Format code and check docstrings
make format

# Add standard headers to Python files
make headers

# Preview header changes (dry run)
make headers/dry-run

# Run all linters (includes docstring checking)
make lint
```

## Common Patterns

### Simple Function

```python
def get_user_id() -> str:
    """Get the current user's ID.

    Returns:
        The user ID as a string.
    """
    return current_user.id
```

### Complex Function

```python
async def fetch_data(
    url: str,
    timeout: int = 30,
    retries: int = 3
) -> Dict[str, Any]:
    """Fetch data from a remote URL with retry logic.

    Attempts to fetch data from the specified URL, with configurable
    timeout and retry settings. Uses exponential backoff for retries.

    Args:
        url: The URL to fetch data from.
        timeout: Request timeout in seconds. Defaults to 30.
        retries: Number of retry attempts. Defaults to 3.

    Returns:
        Dictionary containing the fetched data and metadata.

    Raises:
        httpx.TimeoutException: When request times out.
        httpx.HTTPStatusError: When server returns error status.
        ValueError: When URL is invalid or empty.

    Example:
        >>> data = await fetch_data("https://api.example.com/data")
        >>> print(data["status"])
        'success'
    """
    pass
```

### Class Docstring

```python
class DataProcessor:
    """Process and transform data according to configured rules.

    This class provides a flexible framework for processing data
    through a series of configurable transformation steps. It supports
    both synchronous and asynchronous processing modes.

    Attributes:
        rules: List of processing rules to apply.
        cache: Optional cache for storing intermediate results.
        max_workers: Maximum number of worker threads/processes.
    """

    def __init__(self, rules: List[Rule], cache: Optional[Cache] = None):
        """Initialize the data processor.

        Args:
            rules: List of processing rules to apply.
            cache: Optional cache instance for storing results.
        """
        self.rules = rules
        self.cache = cache
```

### Property Docstring

```python
@property
def is_ready(self) -> bool:
    """Check if the processor is ready to process data.

    Returns:
        True if the processor is ready, False otherwise.
    """
    return self.rules and not self.is_processing
```

## Configuration

### Ruff Configuration

The project's `pyproject.toml` includes ruff configuration for docstring enforcement:

```toml
[tool.ruff]
select = [
    # ... other rules ...
    "D",  # pydocstyle (PEP 257)
]

[tool.ruff.pydocstyle]
convention = "google"
```

### Pre-commit Configuration

The `.pre-commit-config.yaml` file includes hooks for:
- Ruff (linting and formatting)
- MyPy (type checking)
- Custom docstring checking

## Workflow

### 1. Development

1. Write code following docstring standards
2. Use `make format` to auto-format code
3. Use `make lint` to check for issues
4. Fix any docstring violations

### 2. Before Committing

1. Run `make all-checks` to ensure compliance
2. Pre-commit hooks will run automatically
3. Fix any issues before committing

### 3. Adding New Files

1. Include proper module header
2. Add docstrings to all public functions/classes
3. Follow Google style format
4. Run `make lint` to verify

### 4. Updating Existing Code

1. Add docstrings to undocumented functions/classes
2. Update docstrings to match current implementation
3. Ensure all parameters and returns are documented
4. Run `make lint` to verify

## Troubleshooting

### Common Issues

1. **Missing module docstring**: Add module-level docstring at file start
2. **Missing function docstring**: Add docstring above function definition
3. **Incorrect format**: Follow Google style format exactly
4. **Missing parameters**: Document all parameters in Args section
5. **Missing returns**: Document return value in Returns section

### Getting Help

- Check the cursor rule: `.cursor/rules/docstring-standards.mdc`
- Run `make help` for available commands
- Use `make lint/ruff` to identify specific issues
- Review existing code for examples

## Best Practices

1. **Be concise**: Keep docstrings clear and to the point
2. **Be accurate**: Ensure docstrings match actual implementation
3. **Be complete**: Document all parameters, returns, and exceptions
4. **Use examples**: Include examples for complex functionality
5. **Follow format**: Use Google style consistently
6. **Update regularly**: Keep docstrings current with code changes

## Tools Summary

| Tool           | Purpose              | Command           |
| -------------- | -------------------- | ----------------- |
| Ruff           | Docstring linting    | `make lint/ruff`  |
| Pre-commit     | Automatic checks     | `make pre-commit` |
| Headers script | Add standard headers | `make headers`    |
| Make targets   | Various operations   | `make help`       |

Remember: Good docstrings make code self-documenting and easier to maintain. Always prioritize clarity and completeness over brevity.
