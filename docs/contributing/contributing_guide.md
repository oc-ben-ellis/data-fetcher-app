# Contributing Guide

Welcome to the OC Fetcher project! This guide explains how to contribute to the project, including development setup, code standards, testing, and the pull request process.

## Overview

The OC Fetcher is a composable, streaming-first Python framework for fetching resources from heterogeneous remote sources. We welcome contributions from the community and have established processes to ensure code quality and maintainability.

## How to Contribute

### 1. Development Setup

Before contributing, ensure you have a proper development environment:

- **DevContainer**: Use the provided DevContainer for consistent setup
- **Dependencies**: Install with `poetry install`
- **Pre-commit hooks**: Install with `make pre-commit`
- **Documentation**: Build with `make docs`

See [Development Setup](development_setup.md) for detailed requirements.

### 2. Code Standards

All contributions must follow our established standards:

- **PEP 257 compliance** with Google-style docstrings
- **Type hints** for all public functions and classes
- **Code formatting** with Ruff
- **Linting** with Ruff and MyPy

See [Code Standards](code_standards.md) for detailed guidelines.

### 3. Testing

All contributions must include appropriate tests:

- **Unit tests** for new functionality
- **Integration tests** for complex workflows
- **Test coverage** should not decrease
- **All tests** must pass before submission

See [Testing Guide](../testing/overview.md) for testing guidelines.

### 4. Pull Request Process

1. **Fork and branch**: Create a feature branch from `main`
2. **Develop**: Make your changes following our standards
3. **Test**: Ensure all tests pass and coverage is maintained
4. **Document**: Update documentation if needed
5. **Submit**: Create a pull request with a clear description
6. **Review**: Address feedback from maintainers
7. **Merge**: Maintainers will merge after approval

## Project Structure

### Code Organization

```
src/
├── data_fetcher_app/            # Main application entry point
├── data_fetcher_core/           # Core framework components
├── data_fetcher_recipes/        # Built-in configurations
├── data_fetcher_protocols/      # Protocol implementations
├── data_fetcher_storage/        # Storage implementations
└── data_fetcher_utils/          # Utility functions

tests/
├── test_unit/                   # Unit tests
├── test_integration/            # Integration tests
├── test_functional/             # Functional tests
└── stubs/                       # Mock services and test data

docs/
├── index.md                     # Homepage
├── 01_architecture/             # Architecture documentation
├── user_guide/                  # User documentation
├── configurations/              # Configuration guides
└── assets/                      # Images and diagrams
```

### Key Components

- **Fetcher**: Main orchestration component
- **Bundle Locators**: Generate URLs/targets to fetch
- **Bundle Loaders**: Fetch individual targets
- **Storage**: Composable storage with decorators
- **Protocol Managers**: Handle rate limiting and policies

## Development Workflow

### 1. Setting Up Your Environment

```bash
# Clone the repository
git clone <repository-url>
cd data-fetcher-sftp

# Install dependencies
poetry install

# Install pre-commit hooks
make pre-commit

# Verify setup
make all-checks
```

### 2. Making Changes

```bash
# Create a feature branch
git checkout -b feature/your-feature-name

# Make your changes
# ... edit code ...

# Run quality checks
make format          # Format code
make lint            # Check for issues
make test            # Run tests
make docs            # Build documentation

# Commit your changes
git add .
git commit -m "feat: add your feature description"
```

### 3. Quality Assurance

Before submitting a pull request, ensure:

- [ ] All tests pass (`make test`)
- [ ] Code is formatted (`make format`)
- [ ] No linting errors (`make lint`)
- [ ] Documentation builds (`make docs`)
- [ ] New code has appropriate tests
- [ ] New functionality is documented

## Documentation Guidelines

When contributing to the project, you may need to update or add documentation. Follow these guidelines:

### Documentation Structure

The documentation is organized into logical sections:

- **Architecture**: System design and component relationships
- **User Guide**: How to use the framework
- **Configurations**: Available configurations and how to create new ones
- **Contributing**: Development and contribution guidelines
- **Troubleshooting**: Common issues and solutions

### Writing Style

- **Clear and concise**: Use simple, direct language
- **Consistent terminology**: Use the same terms throughout
- **Code examples**: Include working code examples
- **Cross-references**: Link to related documentation
- **Keep current**: Update documentation when code changes

### Documentation Build System

The documentation uses MkDocs with Material theme:

```bash
# Build documentation
make docs

# Build and serve locally
make docs/serve

# Check for build errors
make docs/build
```

### Adding New Documentation

1. **Create the file** in the appropriate directory
2. **Update navigation** in `mkdocs.yaml` if needed
3. **Test the build** with `make docs`
4. **Review the output** in the generated site

## Code Review Process

### What We Look For

- **Functionality**: Does the code work as intended?
- **Quality**: Is the code well-written and maintainable?
- **Testing**: Are there appropriate tests?
- **Documentation**: Is the code and functionality documented?
- **Standards**: Does it follow our coding standards?

### Review Checklist

- [ ] Code follows PEP 257 and Google-style docstrings
- [ ] All public functions have type hints
- [ ] Code is formatted with Ruff
- [ ] No linting errors
- [ ] Tests pass and coverage is maintained
- [ ] Documentation is updated if needed
- [ ] Commit messages follow conventional format

## Getting Help

### Resources

- **Documentation**: Check the [Architecture](../architecture/README.md) and [User Guide](../user_guide/getting_started.md) sections
- **Code Examples**: See the `examples/` directory
- **Issues**: Check existing issues on GitHub
- **Discussions**: Use GitHub Discussions for questions

### Contact

- **Issues**: Create a GitHub issue for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Pull Requests**: Submit PRs for code contributions

## Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Checklist

- [ ] All tests pass
- [ ] Documentation is updated
- [ ] Version is bumped
- [ ] Changelog is updated
- [ ] Release notes are written
- [ ] Docker images are built and pushed

## Contributing Types

### Bug Fixes

1. **Identify the issue**: Create a GitHub issue if one doesn't exist
2. **Reproduce**: Create a test that reproduces the bug
3. **Fix**: Implement the fix
4. **Test**: Ensure the fix works and doesn't break existing functionality
5. **Document**: Update documentation if needed

### New Features

1. **Discuss**: Open a GitHub issue to discuss the feature
2. **Design**: Plan the implementation approach
3. **Implement**: Write the code following our standards
4. **Test**: Add comprehensive tests
5. **Document**: Update documentation and examples

### Documentation

1. **Identify gaps**: Look for missing or outdated documentation
2. **Write clearly**: Use clear, concise language
3. **Include examples**: Provide working code examples
4. **Test**: Ensure documentation builds correctly
5. **Review**: Have others review for clarity and accuracy

## Best Practices

### Defensive Programming

We follow an **aggressive defensive programming approach** to ensure code reliability and catch issues early in the development cycle. This philosophy prioritizes early error detection and explicit failure handling over silent failures.

#### Core Principles

- **Fail Fast**: Check for unexpected values early in functions and raise errors immediately
- **Explicit Error Handling**: Raise specific exceptions rather than logging warnings and continuing
- **Early Validation**: Validate inputs, parameters, and state at function entry points
- **No Silent Failures**: Avoid logging errors and silently resuming execution

#### Rationale

The primary goal is to **find and fix bugs early** in the development process, preventing them from going undetected and reaching production. This approach:

- **Improves Debugging**: Errors are caught at the source, making them easier to trace and fix
- **Prevents Data Corruption**: Stops execution before invalid data can propagate through the system
- **Enhances Reliability**: Ensures the system behaves predictably under unexpected conditions
- **Reduces Production Issues**: Catches problems during development and testing phases

#### Implementation Guidelines

**Do This:**
```python
def process_data(data: Dict[str, Any]) -> ProcessedData:
    """Process input data with validation.

    Args:
        data: Dictionary containing data to process.

    Returns:
        Processed data object.

    Raises:
        ValueError: When data is invalid or missing required fields.
        TypeError: When data is not a dictionary.
    """
    # Early validation - fail fast
    if not isinstance(data, dict):
        raise TypeError(f"Expected dict, got {type(data).__name__}")

    if not data:
        raise ValueError("Data cannot be empty")

    required_fields = ["id", "name", "value"]
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        raise ValueError(f"Missing required fields: {missing_fields}")

    # Validate data types
    if not isinstance(data["id"], str):
        raise ValueError("Field 'id' must be a string")

    if not isinstance(data["value"], (int, float)):
        raise ValueError("Field 'value' must be a number")

    # Process the validated data
    return ProcessedData(
        id=data["id"],
        name=data["name"],
        value=float(data["value"])
    )
```

**Avoid This:**
```python
def process_data(data: Dict[str, Any]) -> ProcessedData:
    """Process input data - BAD EXAMPLE."""
    # Don't silently handle errors
    if not isinstance(data, dict):
        logger.warning("EXPECTED_DICT_GOT_OTHER_TYPE", actual_type=type(data).__name__)
        return None  # Silent failure!

    if not data:
        logger.warning("DATA_IS_EMPTY")
        return None  # Silent failure!

    # Don't continue with invalid data
    if "id" not in data:
        logger.warning("MISSING_REQUIRED_FIELD", field="id")
        data["id"] = "unknown"  # Masking the problem!

    # This could cause issues downstream
    return ProcessedData(
        id=data.get("id", "unknown"),
        name=data.get("name", ""),
        value=data.get("value", 0)
    )
```

#### When to Use Defensive Programming

- **Input Validation**: Always validate function parameters and external data
- **State Checks**: Verify object state before performing operations
- **Resource Validation**: Check file existence, network connectivity, etc.
- **Type Checking**: Ensure parameters match expected types
- **Business Logic**: Validate business rules and constraints
- **Configuration**: Verify configuration values are valid

#### Exception Types to Use

- **ValueError**: For invalid values or business rule violations
- **TypeError**: For incorrect parameter types
- **FileNotFoundError**: For missing files or resources
- **ConnectionError**: For network or service connectivity issues
- **ConfigurationError**: For invalid configuration (create custom exception)
- **StateError**: For invalid object state (create custom exception)

#### Testing Defensive Code

Ensure your defensive code is properly tested:

```python
def test_process_data_validation():
    """Test that process_data validates inputs correctly."""

    # Test invalid type
    with pytest.raises(TypeError, match="Expected dict"):
        process_data("not a dict")

    # Test empty data
    with pytest.raises(ValueError, match="Data cannot be empty"):
        process_data({})

    # Test missing fields
    with pytest.raises(ValueError, match="Missing required fields"):
        process_data({"id": "test"})

    # Test invalid field types
    with pytest.raises(ValueError, match="Field 'id' must be a string"):
        process_data({"id": 123, "name": "test", "value": 1.0})
```

### Code Quality

- **Write clean code**: Follow PEP 8 and our style guidelines
- **Use type hints**: Help with IDE support and documentation
- **Write tests**: Ensure your code works and continues to work
- **Document everything**: Make your code self-documenting

### Git Workflow

- **Use descriptive commit messages**: Follow conventional commit format
- **Keep commits focused**: One logical change per commit
- **Rebase before submitting**: Keep a clean history
- **Write good PR descriptions**: Explain what and why

### Testing

- **Test edge cases**: Don't just test the happy path
- **Use appropriate test types**: Unit, integration, and functional tests
- **Mock external dependencies**: Keep tests fast and reliable
- **Maintain coverage**: Don't decrease test coverage

## Summary

Contributing to OC Fetcher involves:

1. **Setting up** your development environment
2. **Following** our code standards and practices
3. **Writing** quality code with tests
4. **Documenting** your changes
5. **Submitting** a pull request for review

We appreciate your contributions and look forward to working with you!

---

For more detailed information, see the related guides:
- [Development Setup](development_setup.md)
- [Code Standards](code_standards.md)
- [Testing Guide](../testing/overview.md)
