# Development Setup

This guide helps you set up a development environment for the OC Fetcher project.

## Prerequisites

### System Requirements

- **Python 3.11+**: Required for the project
- **Poetry**: For dependency management
- **Docker**: For containerized development and testing
- **Git**: For version control
- **Make**: For running project commands

### Operating System

The project supports:
- **Linux** (recommended for development)
- **macOS** (with Docker Desktop)
- **Windows** (with WSL2 and Docker Desktop)

## Quick Start

### Option 1: DevContainer (Recommended)

The easiest way to get started is using the provided DevContainer:

1. **Open in VS Code**: Open the project in VS Code
2. **Install Dev Containers extension**: Install the "Dev Containers" extension
3. **Reopen in container**: Click "Reopen in Container" when prompted
4. **Wait for setup**: The container will build and install dependencies automatically

### Option 2: Local Setup

If you prefer to set up locally:

```bash
# Clone the repository
git clone <repository-url>
cd data-fetcher-sftp

# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Install pre-commit hooks
make pre-commit

# Verify setup
make all-checks
```

## Development Environment

### Python Environment

The project uses Poetry for dependency management:

```bash
# Activate the virtual environment
poetry shell

# Install dependencies
poetry install

# Add new dependencies
poetry add <package-name>

# Add development dependencies
poetry add --group dev <package-name>
```

### Project Structure

```
data-fetcher-sftp/
├── src/                          # Source code
│   ├── data_fetcher_app/         # Main application
│   ├── data_fetcher_core/        # Core framework
│   ├── data_fetcher_recipes/     # Built-in configurations
│   ├── data_fetcher_protocols/   # Protocol implementations
│   ├── data_fetcher_storage/     # Storage implementations
│   └── data_fetcher_utils/       # Utility functions
├── tests/                        # Test suite
├── docs/                         # Documentation
├── examples/                     # Example code
├── stubs/                        # Mock services for testing
├── pyproject.toml               # Project configuration
├── Makefile                     # Development commands
└── docker-compose.yml           # Docker services
```

## Development Tools

### Code Quality

The project includes several tools for maintaining code quality:

```bash
# Format code
make format

# Lint code
make lint

# Check docstrings
make lint/docstrings

# Run all quality checks
make all-checks
```

### Testing

```bash
# Run all tests
make test

# Run specific test categories
poetry run pytest -m "not integration"  # Skip integration tests
poetry run pytest -m integration        # Run only integration tests

# Run with coverage
poetry run pytest --cov=data_fetcher

# Run tests with verbose output
poetry run pytest -v
```

### Documentation

```bash
# Build documentation
make docs

# Build and serve locally
make docs/serve

# Check for build errors
make docs/build
```

## Configuration

### Environment Variables

The project uses environment variables for configuration:

```bash
# Set configuration ID
export OC_CONFIG_ID=us-fl

# Set credentials provider
export OC_CREDENTIALS_PROVIDER=env

# Set storage configuration
export OC_STORAGE_TYPE=s3
export OC_STORAGE_BUCKET=my-bucket
```

### Credential Providers

#### AWS Secrets Manager (Default)

For AWS SSO setup (recommended):

```bash
# Configure AWS SSO interactively
aws configure sso

# During setup, provide:
# - SSO session name: OpenCorporates-Management-Developer
# - SSO start URL: https://d-9c671d0d67.awsapps.com/start
# - SSO region: eu-west-2
# - SSO registration scopes: sso:account:access (default)
# - AWS account: Choose the management account (089449186373)
# - Role: Choose the Developer role
# - Default client region: eu-west-2
# - CLI default output format: json
# - Profile name: oc-management-dev (required for makefile compatibility)

# Set the profile for the application
export AWS_PROFILE=oc-management-dev

# Log in to AWS SSO (required before using AWS services)
aws sso login --profile oc-management-dev
```

For traditional AWS credentials (legacy):

```bash
# Set AWS credentials
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_DEFAULT_REGION=us-east-1
```

#### Environment Variables

```bash
# US Florida SFTP credentials
export OC_CREDENTIAL_US_FL_HOST=sftp.example.com
export OC_CREDENTIAL_US_FL_USERNAME=username
export OC_CREDENTIAL_US_FL_PASSWORD=password

# France API credentials
export OC_CREDENTIAL_FR_CLIENT_ID=your-client-id
export OC_CREDENTIAL_FR_CLIENT_SECRET=your-client-secret
```

## Testing Services

### LocalStack (AWS Services)

For testing AWS services locally:

```bash
# Start LocalStack
docker-compose -f stubs/docker-compose.yml up -d

# Run tests that require LocalStack
poetry run pytest -m localstack

# Stop LocalStack
docker-compose -f stubs/docker-compose.yml down
```

### Mock API Server

For testing API integrations:

```bash
# Start mock Sirene API server
cd mocks/api_fr_siren
docker build -t siren_api_mock .
docker run -p 5000:5000 siren_api_mock

# Run API tests
poetry run pytest tests/test_functional/test_fr.py
```

## IDE Setup

### VS Code

Recommended extensions:

- **Python**: Python language support
- **Dev Containers**: Container development
- **Ruff**: Code formatting and linting
- **MyPy**: Type checking
- **Mermaid**: Diagram support

### PyCharm

1. **Open project**: Open the project directory
2. **Configure interpreter**: Set Python interpreter to Poetry virtual environment
3. **Install plugins**: Install Poetry and Docker plugins
4. **Configure run configurations**: Set up test and run configurations

## Troubleshooting

### Common Issues

#### Poetry Installation

```bash
# If Poetry is not found
curl -sSL https://install.python-poetry.org | python3 -
export PATH="$HOME/.local/bin:$PATH"

# If virtual environment issues
poetry env remove python
poetry install
```

#### Docker Issues

```bash
# If Docker is not running
sudo systemctl start docker

# If permission issues
sudo usermod -aG docker $USER
# Log out and back in
```

#### Test Failures

```bash
# If tests fail due to missing services
docker-compose -f stubs/docker-compose.yml up -d

# If tests fail due to credentials
export OC_CREDENTIALS_PROVIDER=env
# Set required environment variables
```

### Getting Help

- **Check logs**: Look at test output and error messages
- **Verify setup**: Run `make all-checks` to verify environment
- **Check issues**: Look at existing GitHub issues
- **Ask questions**: Use GitHub Discussions for help

## Next Steps

After setting up your development environment:

1. **Read the documentation**: Start with [Architecture](../architecture/README.md)
2. **Run examples**: Try the examples in the `examples/` directory
3. **Explore tests**: Look at existing tests to understand the codebase
4. **Make a small change**: Try making a small improvement or fix
5. **Submit a PR**: Follow the [Contributing Guide](contributing_guide.md)

## Additional Resources

- **[Contributing Guide](contributing_guide.md)**: How to contribute to the project
- **[Code Standards](code_standards.md)**: Coding guidelines and standards
- **[Testing Guide](../testing/overview.md)**: Comprehensive testing information
- **[Architecture Documentation](../architecture/README.md)**: System design and components
- **[User Guide](../user_guide/getting_started.md)**: How to use the framework
- **[Diagrams Guide](../references/diagrams/README.md)**: Creating and managing Mermaid diagrams
