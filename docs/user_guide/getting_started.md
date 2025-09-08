# Getting Started

Welcome to the Data Fetcher App! This guide will help you get up and running quickly.

## What is Data Fetcher?

Data Fetcher is a composable, streaming-first fetch framework for Python that simplifies data collection from heterogeneous remote sources. It automatically handles complex data retrieval tasks, bundles resources with metadata, and stores them in a standardized format ready for downstream ETL processing.

## Key Benefits

- **Simplified Data Collection**: One framework handles multiple protocols (HTTP/HTTPS, SFTP)
- **Built-in Best Practices**: Predefined configurations with optimized settings
- **Production Ready**: Comprehensive error handling, retry logic, and structured logging
- **Extensible**: Easy to add new protocols and customize data processing pipelines

## Quick Overview

The framework uses a configuration-based approach where you can run predefined fetchers:

```bash
# Run US Florida SFTP fetcher
poetry run python -m data_fetcher_app.main run us-fl

# Run France API fetcher
poetry run python -m data_fetcher_app.main run fr
```

## Available Configurations

Currently, the following configurations are available:

- **`us-fl`**: US Florida SFTP - Downloads files from SFTP servers
- **`fr`**: France API - Fetches data from REST APIs

## Next Steps

1. **[Command Line Usage](command_line_usage.md)** - Learn how to run the application from the command line
2. **[Docker Usage](docker_usage.md)** - Learn how to run the application with Docker
3. **[Application Configuration](application_configuration.md)** - Configure the application settings
4. **[Configurations](../configurations/creating_a_recipe.md)** - Learn about available configurations

## Prerequisites

- Python 3.11+
- Poetry (for dependency management)
- Docker (optional, for containerized deployment)
- AWS credentials (for accessing AWS CodeArtifact for Python packages)

### AWS SSO Setup (Recommended)

For development and ci using AWS services, configure AWS SSO for secure authentication:

```bash
# Start the interactive AWS SSO configuration
aws configure sso
```

During the interactive setup, you'll be prompted for the following information:

1. **SSO session name**: `OpenCorporates-Management-Developer`
2. **SSO start URL**: `https://d-9c671d0d67.awsapps.com/start`
3. **SSO region**: `eu-west-2`
4. **SSO registration scopes**: `sso:account:access` (default)
5. **AWS account selection**: Choose the **management** account (`089449186373`)
6. **Role selection**: Choose the **Developer** role
7. **Default client region**: `eu-west-2`
8. **CLI default output format**: `json`
9. **Profile name**: `oc-management-dev` (required for makefile compatibility)

The setup process will:
- Open your browser for authentication
- Set up SSO session with your organization's AWS SSO
- Configure the default region to `eu-west-2`
- Set JSON as the default output format
- Create a profile with your chosen name

After configuration, verify your setup:
```bash
aws sts get-caller-identity --profile oc-management-dev
```

### AWS SSO Login

**Important**: After configuring AWS SSO, you must log in before using AWS services. This is required for:

- **Accessing OpenCorporates Python packages** from private repositories (CodeArtifact)
- **Installing project dependencies** that include private OpenCorporates packages

**Note**: The AWS Secrets Manager and S3 storage used by the application are managed through environment variables and CLI arguments, not through this AWS profile configuration.

To log in:
```bash
aws sso login --profile oc-management-dev
```

This will:
- Open your browser for authentication
- Create temporary credentials for the session
- Allow access to AWS services for the configured profile

**Session Duration**: SSO sessions typically last 8-12 hours. You'll need to re-run the login command when your session expires.

## Installation

### Option 1: DevContainer (Recommended)

The project includes a DevContainer configuration for a consistent development environment with automatic AWS profile configuration:

1. Open the project in VS Code or Cursor
2. When prompted, click "Reopen in Container"
3. Wait for the container to build and dependencies to install

#### DevContainer Features
The devcontainer automatically configures:
- **Shell Configuration**: Adds AWS profile export to both `.bashrc` and `.zshrc`
- **Intelligent AWS SSO Detection**: Automatically detects and configures AWS SSO profiles
- **Attended Session Detection**: Only runs interactive setup in attended shells (not in Cursor agents)
- **Persistent AWS Configuration**: AWS config and SSO cache are persisted across container restarts using Docker volumes
- **Customizable**: You can override the profile name in `devcontainer.json`

### Option 2: Local Installation

```bash
# Install Poetry (if not already installed)
pip install poetry

# Clone the repository
git clone https://github.com/openc/data-fetcher-sftp.git
cd data-fetcher-sftp

# IMPORTANT: Log in to AWS SSO before installing dependencies
# This is required for accessing private OpenCorporates Python packages
aws sso login --profile production

# Install dependencies (includes private OpenCorporates packages)
poetry install

# Activate virtual environment
poetry shell
```

## Verification

Test your installation by listing available configurations:

```bash
poetry run python -m data_fetcher_app.main
```

You should see output listing the available configurations (`us-fl`, `fr`).

## Getting Help

- Check the [Troubleshooting](../troubleshooting/troubleshooting_guide.md) guide for common issues
- Review the [Architecture](../architecture/README.md) documentation for technical details
- See the [Contributing](../contributing/contributing_guide.md) section for development setup
