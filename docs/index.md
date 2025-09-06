<div align="center">
  <img src="assets/OC_Fetcher_Logo_New.svg" alt="Data Fetcher Logo" width="350" style="margin-bottom: 20px;">
</div>

# Data Fetcher App

A composable, streaming-first fetch framework for Python that simplifies data collection from heterogeneous remote sources. The framework automatically handles complex data retrieval tasks, bundles resources with metadata, and stores them in a standardized format ready for downstream ETL processing.

Data Fetcher supports multiple protocols (HTTP/HTTPS, SFTP) with built-in credential management, rate limiting, and structured logging. The modular architecture allows contributors to easily extend functionality, add new protocols, and customize data processing pipelines.

## Architecture Highlights

- **Modular Design**: Clean separation of concerns with dedicated packages for different protocols
- **Composable Architecture**: Bundle locators generate URLs, loaders handle streaming, managers handle policies
- **Extensible Framework**: Easy to add new protocols, credential providers, and storage backends
- **Production Ready**: Comprehensive error handling, retry logic, and structured logging
- **Event-Driven**: SQS notifications for bundle completion events and downstream integration
- **Streaming-First**: BundleStorageContext manages bundle lifecycle with streaming data processing

## Quick Start

### Command Line Usage

Run predefined recipes directly:

```bash
# Run US Florida SFTP fetcher
poetry run python -m data_fetcher_app.main run us-fl

# Run France API fetcher
poetry run python -m data_fetcher_app.main run fr

# List all available recipes
poetry run python -m data_fetcher_app.main list

# Run with specific credentials provider
poetry run python -m data_fetcher_app.main run us-fl --credentials-provider aws
```

### Docker Usage

Run recipes in a containerized environment:

```bash
# Build the Docker image
make build/for-deployment

# Run using docker-compose (recommended for development)
make run ARGS=us-fl

# Run with observability features
make run/with-observability ARGS=us-fl

# Run specific recipe via Docker
docker run --rm -e AWS_PROFILE=your-profile data-fetcher-sftp:latest us-fl
```

### Environment Variables

For local development, set credentials via environment variables:

```bash
# For US Florida recipe (us-fl)
export OC_CREDENTIAL_US_FL_HOST="sftp.example.com"
export OC_CREDENTIAL_US_FL_USERNAME="username"
export OC_CREDENTIAL_US_FL_PASSWORD="password"

# For France API recipe (fr)
export OC_CREDENTIAL_FR_CLIENT_ID="client-id"
export OC_CREDENTIAL_FR_CLIENT_SECRET="client-secret"

# Run with environment variables
poetry run python -m data_fetcher_app.main run us-fl --credentials-provider env
```

## Development Setup

Get the development environment running:

```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest

# Format and lint code
make format
make lint

# Run examples
poetry run python examples/basic_usage_example.py
```

## Key Development Areas

### Architecture
- **[Architecture Documentation](architecture/README.md)** - System design, components, and data flow
- **[Module Hierarchy](architecture/overview/README.md)** - Package structure and dependencies
- **[Component Relationships](architecture/overview/README.md)** - How components interact

### User Guide
- **[User Guide Documentation](user_guide/README.md)** - Complete user guide overview
- **[Getting Started](user_guide/getting_started.md)** - Quick start guide for new users
- **[Command Line Usage](user_guide/command_line_usage.md)** - Run the application from command line
- **[Docker Usage](user_guide/docker_usage.md)** - Run the application with Docker
- **[Application Configuration](user_guide/application_configuration.md)** - Configure the application
- **[Deployment](deployment/overview.md)** - Production deployment and monitoring

### Fetcher Recipes
- **[Fetcher Recipes Documentation](configurations/README.md)** - Complete fetcher recipes overview
- **Contributing** - Learn how to contribute to fetcher recipes
  - **[Creating a Fetcher Recipe](configurations/creating_a_recipe.md)** - Comprehensive guide to creating new fetcher recipes
- **Available Strategies** - Reusable components for building fetcher recipes
  - **API Strategies** - HTTP/API-based data fetching components
  - **SFTP Strategies** - File-based data fetching components
- **Available Fetcher Recipes** - Ready-to-use fetcher recipes
  - **[FR - France API](configurations/fr_api.md)** - France API fetcher recipe summary
  - **[US_FL - US Florida SFTP](configurations/us_fl_sftp.md)** - US Florida SFTP fetcher recipe summary

### Architecture
- **[Architecture Documentation](architecture/README.md)** - System design, components, and data flow
- **[Module Hierarchy](architecture/overview/README.md)** - Package structure and dependencies
- **[Component Relationships](architecture/overview/README.md)** - How components interact

### Contributing
- **[Contributing Guide](contributing/contributing_guide.md)** - How to contribute to the project
- **[Development Setup](contributing/development_setup.md)** - Development environment setup
- **[Code Standards](contributing/code_standards.md)** - PEP 257 compliance and Google-style docstrings
- **[Testing Guide](testing/overview.md)** - Running tests and writing new ones
  - **[Writing Tests](testing/writing_tests.md)** - How to write effective tests
  - **[Mock Services](testing/mock_services.md)** - Mock services and test fixtures
  - **[Debugging Tests](testing/debugging_tests.md)** - Debugging and troubleshooting
### Troubleshooting
- **[Troubleshooting Guide](troubleshooting/troubleshooting_guide.md)** - Common issues and solutions

### References
- **[References Documentation](references/README.md)** - Complete references overview
- **[Architecture Decision Records](adr/README.md)** - Design decisions and rationale
- **[Additional Resources](references/README.md)** - Retry consolidation and diagrams

---

© 2025 OpenCorporates. All rights reserved.
