![OC Fetcher Logo](docs/assets/OC_Fetcher_Logo_New.svg)

# OC Fetcher

A composable, streaming-first fetch framework for Python that pulls resources from heterogeneous remote sources and bundles them with metadata into a standard package in a common file store for further ETL processing downstream.

## 📖 View Rendered Documentation

For the best reading experience, view the [rendered documentation](docs/rendered/index.html) in your browser.

## Key Features

- **Composable Architecture**: Bundle locators generate URLs for loading
- **Streaming-First**: Bundle loaders stream large payloads directly to Storage (WARC) to keep RAM small
- **Protocol-Level Policies**: Managers handle cross-cutting concerns like rate limiting and scheduling
- **Multiple Protocols**: Support for HTTP(S) and SFTP with extensible architecture
- **SFTP**: Enterprise-grade SFTP with AWS Secrets Manager, S3 upload, and date-based file patterns
- **Structured Logging**: Built-in structlog integration with context variables and JSON output

## Quick Start

### Using the Configuration System (Recommended)

```bash
# Run US Florida SFTP fetcher
poetry run python -m oc_fetcher.main us-fl

# Run France API fetcher
poetry run python -m oc_fetcher.main fr

# List all available configurations
poetry run python -m oc_fetcher.main
```

### Basic Usage with Configuration System

```python
from oc_fetcher.registry import get_fetcher

# Run a predefined configuration
fetcher = get_fetcher("us-fl")
result = await fetcher.run(plan)

# Run France configuration
fetcher = get_fetcher("fr")
result = await fetcher.run(plan)
```

### Credential Providers

The framework supports multiple credential providers for different deployment scenarios:

#### AWS Secrets Manager (Default)
```bash
# Use AWS Secrets Manager for credentials (default behavior)
poetry run python -m oc_fetcher.main us-fl

# Explicitly specify AWS provider
poetry run python -m oc_fetcher.main --credentials-provider aws us-fl
```

#### Environment Variables
```bash
# Use environment variables for credentials
poetry run python -m oc_fetcher.main --credentials-provider env us-fl
```

When using environment variables, set them in this format:
```bash
# For US Florida configuration (us-fl)
export OC_CREDENTIAL_US_FL_HOST="sftp.example.com"
export OC_CREDENTIAL_US_FL_USERNAME="username"
export OC_CREDENTIAL_US_FL_PASSWORD="password"

# For France API configuration (fr-api)
export OC_CREDENTIAL_FR_API_CLIENT_ID="client-id"
export OC_CREDENTIAL_FR_API_CLIENT_SECRET="client-secret"
```

**Note**: Configuration names with hyphens (e.g., 'us-fl') are converted to underscores (e.g., 'US_FL') in environment variable names.

See [examples/credential_provider_example.py](examples/credential_provider_example.py) for more detailed usage examples.

## Installation

### Option 1: Using DevContainer (Recommended)

The project includes a DevContainer configuration that provides a consistent development environment.

#### Prerequisites
- **Docker Desktop** (Windows/Mac) or **Docker Engine** (Linux)
- **VS Code** with the **Dev Containers extension** or **Cursor**

#### Setup
1. Open the project folder in VS Code/Cursor
2. When prompted, click "Reopen in Container" or press `Ctrl+Shift+P` and run "Dev Containers: Reopen in Container"
3. Wait for the container to build and dependencies to install

### Option 2: Local Installation

```bash
# Install Poetry (if not already installed)
pip install poetry

# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

## Available Configurations

The framework comes with several predefined country-code based configurations:

### SFTP Configurations
- **`us-fl`**: US Florida - SFTP batch processing

### HTTP/API Configurations
- **`fr`**: France - API Fetcher

## Documentation Structure

This documentation is organized into the following main sections:

### [🏗️ Architecture](docs/01_architecture/) - Comprehensive architecture overview
- Core architecture principles and components
- Orchestration flow and component interactions
- Storage architecture and configuration system
- Architecture diagrams and visual guides

### [⚙️ Configurations](docs/02_configurations/) - Framework overview and configurations
- **Complete framework overview and quick start**
- API-based configurations
- SFTP configurations  
- Scheduling options

### [🌐 Global Configuration](docs/03_global_configuration/) - System-wide settings and logging
- Detailed configuration options
- Logging setup and configuration
- Environment-specific settings

### [💾 Persistence](docs/04_persistence/) - Data management and caching
- Key-value store implementation
- Data persistence features
- Caching strategies

### [📦 Storage](docs/05_storage/) - Data storage and S3 integration
- Storage system overview
- S3 integration and configuration
- Data flow and processing

### [🚀 Deployment](docs/07_deployment/) - Production deployment guide
- Production requirements and setup
- Container deployment (Docker, Kubernetes)
- Monitoring, security, and scaling

### [🧪 Testing](docs/06_testing/) - Testing framework and best practices
- Test configuration and running tests
- Writing tests and debugging
- Mock services and best practices

### [🔧 Troubleshooting](docs/troubleshooting.md) - Common issues and solutions
- Common problems and their solutions
- Debugging techniques
- Performance optimization

### [📚 Documentation Guide](docs/documentation_guide.md) - How to structure and maintain documentation
- Documentation build system
- Writing guidelines and best practices
- Maintenance procedures

## Getting Started

1. **Start with the [Complete Overview](docs/02_configurations/overview.md)** for framework introduction and quick start
2. **Explore [Architecture](docs/01_architecture/)** to understand the system design
3. **Check [Configurations](docs/02_configurations/)** for available predefined setups
4. **Review [Deployment](docs/07_deployment/)** for production deployment guidance

## Development

### Code Quality

The project enforces strict code quality standards including PEP 257 compliance and Google-style docstrings. All Python code must follow these standards:

```bash
# Format and check code quality
make format

# Check docstring compliance
make lint/docstrings

# Add standard headers to Python files
make headers

# Install pre-commit hooks for automatic checks
make pre-commit

# Run all quality checks
make all-checks
```

### Basic Development Commands

```bash
# Format code (or it happens automatically on save)
poetry run black .

# Lint code
poetry run ruff check .

# Type check
poetry run mypy .

# Run tests
poetry run pytest

# Run examples
poetry run python examples/basic_usage_example.py
```

### Docstring Standards

- **PEP 257 Compliance**: All modules, functions, classes, and methods must have docstrings
- **Google Style Format**: Use Google-style docstring format for consistency
- **Module Headers**: Every Python file includes author and copyright information
- **Automatic Enforcement**: Pre-commit hooks and CI checks ensure compliance

See [Docstring Standards](docs/docstring_standards.md) for detailed guidelines and examples.

---

© 2025 OpenCorporates. All rights reserved.

