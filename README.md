![OC Fetcher Logo](docs/assets/OC_Fetcher_Logo_New.svg)

# Data Fetcher App

A composable, streaming-first fetch framework for Python that pulls resources from heterogeneous remote sources and bundles them with metadata into a standard package in a common file store for further ETL processing downstream.

## 📖 Documentation

This project includes comprehensive documentation built with MkDocs. The documentation covers architecture, configurations, deployment, testing, and more.

### Building and Viewing Documentation

#### Option 1: Build and Open Automatically (Recommended)
```bash
# Build documentation and open in your default browser
make docs/open
```

This command will:
- Build the HTML documentation from markdown files
- Automatically open the documentation in your default browser
- Work on Linux (xdg-open), macOS (open), and Windows

#### Option 2: Build Only
```bash
# Build documentation without opening browser
make docs
```

After building, manually open `site/index.html` in your browser to view the documentation.

#### Option 3: Development Server
For active documentation development:
```bash
# Start a development server with live reload
make docs/serve
```

This starts a local server at `http://0.0.0.0:8000` that automatically reloads when you make changes to the documentation files.

### Documentation Structure

The documentation is organized into focused sections covering different aspects of the framework. See the [Documentation Structure](#documentation-structure) section below for a complete overview of available topics.

## Key Features

- **Composable Architecture**: Bundle locators generate URLs for loading
- **Streaming-First**: Bundle loaders stream large payloads directly to Storage to keep RAM small
- **Protocol-Level Policies**: Managers handle cross-cutting concerns like rate limiting and scheduling
- **Multiple Protocols**: Support for HTTP(S) and SFTP with extensible architecture
- **Modern CLI**: Built with openc_python_common for robust argument parsing and environment variable support
- **Health Monitoring**: Built-in health check server with multiple endpoints for load balancer integration
- **Observability**: Comprehensive logging with run ID tracking, timing instrumentation, and structured output
- **SFTP**: Enterprise-grade SFTP with AWS Secrets Manager, S3 upload, and date-based file patterns
- **Structured Logging**: Built-in structlog integration with context variables and JSON output
- **Modular Design**: Clean separation of concerns with dedicated packages for different protocols and functionality

## Quick Start

### Running a Recipe

```bash
# List available recipes
poetry run python -m data_fetcher_app.main list

# Run a recipe with default settings
poetry run python -m data_fetcher_app.main run fr

# Run with custom options
poetry run python -m data_fetcher_app.main run us-fl \
  --credentials-provider env \
  --storage file \
  --kvstore memory \
  --dev-mode
```

### Health Monitoring

```bash
# Start health check server
poetry run python -m data_fetcher_app.main health

# Check application status
curl http://localhost:8080/health
curl http://localhost:8080/status
curl http://localhost:8080/heartbeat
```

### Observability

Each execution generates a unique run ID (e.g., `fetcher_fr_20250906213609`) that appears in all log messages, providing full traceability and context for debugging and monitoring.

## Module Structure

The framework is organized into focused, modular packages:

- **`data_fetcher_app`**: Main application entry point and configuration files
- **`data_fetcher_core`**: Core framework components and common utilities
- **`data_fetcher_recipes`**: Predefined fetcher recipes for different data sources / jurisdictions
- **`data_fetcher_sftp`**: SFTP-specific classes and modules
- **`data_fetcher_http`**: HTTP-specific classes and modules
- **`data_fetcher_http_api`**: HTTP API-specific classes and modules

## Quick Start

### Using the Recipe System (Recommended)

```bash
# Run US Florida SFTP fetcher
poetry run python -m data_fetcher_app.main run us-fl

# Run France API fetcher
poetry run python -m data_fetcher_app.main run fr

# List all available recipes
poetry run python -m data_fetcher_app.main list
```

### Basic Usage with Recipe System

```python
from data_fetcher_core.recipebook import get_fetcher

# Run a predefined recipe
fetcher = get_fetcher("us-fl")
result = await fetcher.run(plan)

# Run France recipe
fetcher = get_fetcher("fr")
result = await fetcher.run(plan)
```

### Credential Providers

The framework supports multiple credential providers for different deployment scenarios:

#### AWS Secrets Manager (Default)
```bash
# Use AWS Secrets Manager for credentials (default behavior)
poetry run python -m data_fetcher_app.main run us-fl

# Explicitly specify AWS provider
poetry run python -m data_fetcher_app.main run us-fl --credentials-provider aws
```

**Prerequisites**: Configure AWS SSO for secure authentication:
```bash
TBD
```

#### Environment Variables
```bash
# Use environment variables for credentials
poetry run python -m data_fetcher_app.main run us-fl --credentials-provider env
```

When using environment variables, set them in this format:
```bash
# For US Florida recipe (us-fl)
export OC_CREDENTIAL_US_FL_HOST="sftp.example.com"
export OC_CREDENTIAL_US_FL_USERNAME="username"
export OC_CREDENTIAL_US_FL_PASSWORD="password"

# For France API recipe (fr)
export OC_CREDENTIAL_FR_CLIENT_ID="client-id"
export OC_CREDENTIAL_FR_CLIENT_SECRET="client-secret"
```

**Note**: Recipe names with hyphens (e.g., 'us-fl') are converted to underscores (e.g., 'US_FL') in environment variable names.

### Storage and State Management Options

The framework supports multiple storage and state management mechanisms:

#### Storage Options
```bash
# Use S3 storage (default)
poetry run python -m data_fetcher_app.main run us-fl --storage s3

# Use local file storage
poetry run python -m data_fetcher_app.main run us-fl --storage file
```

#### Key-Value Store Options
```bash
# Use Redis for state management (default)
poetry run python -m data_fetcher_app.main run us-fl --kvstore redis

# Use in-memory storage
poetry run python -m data_fetcher_app.main run us-fl --kvstore memory
```

#### Complete Example with All Options
```bash
# Run with environment credentials, file storage, and in-memory kvstore
poetry run python -m data_fetcher_app.main run fr \
  --credentials-provider env \
  --storage file \
  --kvstore memory
```

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

## Available Recipes

The framework comes with several predefined country-code based recipes:

### SFTP Recipes
- **`us-fl`**: US Florida - SFTP batch processing

### HTTP/API Recipes
- **`fr`**: France - API Fetcher

## Documentation Structure

This documentation is organized into the following main sections:

### [🏗️ Architecture](docs/architecture/) - Comprehensive architecture overview
- Core architecture principles and components
- Orchestration flow and component interactions
- Storage architecture and configuration system
- Architecture diagrams and visual guides

### [⚙️ Fetcher Recipes](docs/configurations/) - Framework overview and fetcher recipes
- **Complete framework overview and quick start**
- API-based recipes
- SFTP recipes
- Scheduling options

### [🌐 Application Configuration](docs/03_application_configuration/) - System-wide settings and logging
- Detailed configuration options
- Logging setup and configuration
- Environment-specific settings

### [💾 State Management](docs/04_state_management/) - Data management and caching
- Key-value store implementation
- Data state management features
- Caching strategies

### [📦 Storage](docs/05_storage/) - Data storage and S3 integration
- Storage system overview
- S3 integration and configuration
- Data flow and processing

### [🚀 Deployment](docs/07_deployment/) - Production deployment guide
- Production requirements and setup
- Container deployment (Docker, Kubernetes)
- Health check system and monitoring
- Security and scaling considerations

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

1. **Start with the [Complete Overview](docs/configurations/README.md)** for framework introduction and quick start
2. **Explore [Architecture](docs/architecture/)** to understand the system design
3. **Check [Fetcher Recipes](docs/configurations/)** for available predefined setups
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
poetry run ruff format .

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
