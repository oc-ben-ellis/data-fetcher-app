# OC Fetcher Overview

![OpenCorporates Logo](../assets/OpenCorporates_Logo.png)

OC Fetcher is a composable, streaming-first fetch framework for Python that pulls resources from heterogeneous remote sources and bundles them with metadata into a standard package in a common file store for further ETL processing downstream.

## Key Features

- **Composable Architecture**: Bundle locators generate URLs for loading
- **Streaming-First**: Bundle loaders stream large payloads directly to Storage to keep RAM small
- **Protocol-Level Policies**: Managers handle cross-cutting concerns like rate limiting and scheduling
- **Multiple Protocols**: Support for HTTP(S) and SFTP with extensible architecture
- **SFTP**: Enterprise-grade SFTP with AWS Secrets Manager, S3 upload, and date-based file patterns
- **Structured Logging**: Built-in structlog integration with context variables and JSON output

## Quick Start

### Using the Configuration System (Recommended)

```bash
# Run US Florida SFTP fetcher
poetry run python -m data_fetcher.main us-fl

# Run France API fetcher
poetry run python -m data_fetcher.main fr

# List all available configurations
poetry run python -m data_fetcher.main
```

### Credential Providers

The framework supports multiple credential providers for different deployment scenarios:

#### AWS Secrets Manager (Default)
```bash
# Use AWS Secrets Manager for credentials (default behavior)
poetry run python -m data_fetcher.main us-fl

# Explicitly specify AWS provider
poetry run python -m data_fetcher.main --credentials-provider aws us-fl
```

#### Environment Variables
```bash
# Use environment variables for credentials
poetry run python -m data_fetcher.main --credentials-provider env us-fl
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

See [examples/credential_provider_example.py](../../examples/credential_provider_example.py) for more detailed usage examples.

### Basic Usage with Configuration System

```python
from data_fetcher_core.registry import get_fetcher

# Run a predefined configuration
fetcher = get_fetcher("us-fl")
result = await fetcher.run(plan)

# Run France configuration
fetcher = get_fetcher("fr")
result = await fetcher.run(plan)
```

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

## Configuration System

The framework uses a country-code based configuration system where each configuration is identified by a short code (e.g., `us-fl`, `fr`). These configurations encapsulate best practices and common patterns, making it easy to get started with the framework.

## Available Configurations

### **SFTP Configurations**
- **`us-fl`**: US Florida - SFTP batch processing

### **HTTP/API Configurations**
- **`fr`**: France - API Fetcher

## Protocol Differences

### HTTP/API Configurations

#### Characteristics
- **Protocol**: HTTP/HTTPS
- **Authentication**: OAuth tokens, API keys
- **Data Format**: JSON, XML, or other API formats
- **Rate Limiting**: API-specific rate limits
- **Pagination**: Cursor-based or offset-based pagination

#### Use Cases
- REST APIs
- GraphQL endpoints
- Web services
- Public data APIs

#### Example: France Configuration (`fr`)
```python
# France configuration uses HTTP/API protocol
fetcher = get_fetcher("fr")

# Features:
# - OAuth authentication
# - Cursor-based pagination
# - JSON response handling
# - Rate limiting for API calls
```

### SFTP Configurations

#### Characteristics
- **Protocol**: SFTP (SSH File Transfer Protocol)
- **Authentication**: SSH keys or username/password
- **Data Format**: Files (CSV, TXT, ZIP, etc.)
- **Rate Limiting**: Connection-based limits
- **File Patterns**: Date-based file naming

#### Use Cases
- File-based data sources
- Legacy systems
- Enterprise data feeds
- Batch file processing

#### Example: US Florida Configuration (`us-fl`)
```python
# US Florida configuration uses SFTP protocol
fetcher = get_fetcher("us-fl")

# Features:
# - SSH key authentication
# - Directory scanning
# - File pattern matching
# - Date-based filtering
```

### Key Differences

| Aspect             | HTTP/API            | SFTP                        |
| ------------------ | ------------------- | --------------------------- |
| **Protocol**       | HTTP/HTTPS          | SFTP over SSH               |
| **Authentication** | OAuth, API keys     | SSH keys, username/password |
| **Data Access**    | API endpoints       | File system                 |
| **Rate Limiting**  | API-specific        | Connection-based            |
| **Pagination**     | Cursor/offset-based | File-based                  |
| **Error Handling** | HTTP status codes   | SFTP error codes            |
| **Data Format**    | JSON, XML           | Raw files                   |
| **Use Case**       | Modern APIs         | Legacy systems              |

### Configuration Selection

#### Choose HTTP/API when:
- Working with modern REST APIs
- Data is available via API endpoints
- Authentication uses OAuth or API keys
- Need real-time data access
- Data format is JSON or XML

#### Choose SFTP when:
- Working with file-based data sources
- Data is available as files on a server
- Authentication uses SSH keys
- Need batch file processing
- Data format is CSV, TXT, or other file formats

## Configuration Sections

### [Scheduling](scheduling.md)
Built-in support for daily and interval-based scheduling with enterprise-grade scheduling capabilities.

### [API](api.md)
API-based fetching configurations with authentication support and pagination handling.

### [SFTP](sftp.md)
Enterprise-grade SFTP configurations with AWS integration, secrets management, and date-based file patterns.

## Using Configurations

### **Command Line Usage**
```bash
# Run US Florida SFTP fetcher
poetry run python -m data_fetcher.main us-fl

# Run France API fetcher
poetry run python -m data_fetcher.main fr

# List all available configurations
poetry run python -m data_fetcher.main
```

### **Programmatic Usage**
```python
from data_fetcher_core.registry import get_fetcher

# Run a predefined configuration
fetcher = get_fetcher("us-fl")
result = await fetcher.run(plan)

# Run France configuration
fetcher = get_fetcher("fr")
result = await fetcher.run(plan)
```

### **Configuration Overrides**
```python
from data_fetcher_core.registry import get_fetcher

# Get fetcher with custom configuration
fetcher = get_fetcher("fr")
# Customize the fetcher context as needed
result = await fetcher.run(plan)
```

## Configuration Features

### **Predefined Settings**
- Optimized concurrency and timeout settings
- Protocol-specific rate limiting configurations
- Storage backend and decorator configurations
- Logging and monitoring setups

### **Environment Adaptation**
- Automatic environment detection
- Environment-specific settings (development, staging, production)
- Sensitive configuration through environment variables

### **Extensibility**
- Easy to create new configurations
- Configuration inheritance and composition
- Custom configuration validation

## Creating Custom Configurations

### **Basic Configuration**
```python
from data_fetcher_core.configurations import Configuration

class MyCustomConfig(Configuration):
    def __init__(self):
        super().__init__()
        self.name = "my-custom"
        self.description = "My custom fetching configuration"

    def build(self):
        # Configure components
        return self.builder.build()
```

### **Configuration Registration**
```python
from data_fetcher_core.registry import register_configuration

register_configuration(MyCustomConfig())
```

## Development

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

## Documentation Structure

This documentation is organized into the following main sections:

### [Architecture](../architecture/) - Comprehensive architecture overview
### [Application Configuration](../application_configuration/) - System-wide settings and logging
### [Persistence](../persistence/) - Data management and caching
### [Storage](../storage/) - Data storage and S3 integration
### [Troubleshooting](../troubleshooting.md) - Common issues and solutions
### [Deployment](../deployment/) - Production deployment guide
### [Testing](../testing/) - Testing framework and best practices
### [Documentation Guide](../documentation_guide.md) - How to structure and maintain documentation

## Key Features

- **Ready-to-Use**: Predefined configurations for common scenarios
- **Best Practices**: Configurations encapsulate proven patterns
- **Flexible**: Easy to override and customize settings
- **Extensible**: Simple to create new configurations
- **Environment Aware**: Automatic adaptation to different environments
- **Documented**: Each configuration includes usage examples and documentation

---

© 2025 OpenCorporates. All rights reserved.
