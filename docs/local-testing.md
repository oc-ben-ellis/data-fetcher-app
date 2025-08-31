# Local Testing Guide

This guide provides instructions for setting up and testing the SFTP to S3 transfer utility locally.

## Prerequisites

* Python 3.11+
* Poetry for dependency management
* Docker
* The AWS CLI, configured for SSO from OpenCorporates accounts (see [SSO Playbook](https://opencorporates.atlassian.net/wiki/spaces/AWS/pages/397737995/SSO+Playbook+-+Add+a+new+account+profile+to+aws-cli))

## Installation

### Local Development

1. Clone the repository:

   ```bash
   git clone github.com/openc/oc-data-fetcher-sftp
   cd oc-data-fetcher-sftp
   ```

2. Install dependencies using Poetry:

   ```bash
   make install
   ```

### Docker

Build the Docker image for local testing:

```bash
make build/for-local
```

## Running Tests

The project includes comprehensive unit tests to verify functionality:

```bash
# Run all tests
make test

# Run tests with verbose output
make test-verbose

# Run tests with coverage report
make test/with-coverage
```

## Local Execution

### Command Line

Run the script directly with Python:

```bash
python src/sftp_to_s3.py YYYYMMDD ENV
```

Where:

- `YYYYMMDD` is the date in year-month-day format
- `ENV` is the environment (playground, dev, idp, or prod)

Example:

```bash
python src/sftp_to_s3.py 20250506 playground
```

### Using Docker

Run the Docker container:

```bash
# First build the Docker image
make build/for-local

# Then run with date parameter and environment
make run DATE=20240601 ENV=playground

# Or specify AWS profile
make run AWS_PROFILE=your-profile DATE=20240601 ENV=playground
```

### Building for playground deployment

To build the Docker image for deployment to AWS Fargate:

```bash
# Push to ECR
make push-to-ecr-playground
```

### Available Make Commands

```bash
make help                # Show help message
make install             # Install dependencies using Poetry
make update              # Update dependencies to their latest versions
make test                # Run tests
make test-verbose        # Run tests with verbose output
make test/with-coverage  # Run tests with coverage report
make lint                # Run linting checks
make format              # Format code using black
make pre-commit          # Run pre-commit hooks on all files
make all-checks          # Run format, lint, and test with coverage
make check               # Check project settings
make build/for-local     # Build Docker image for local testing
make docker-lint         # Run linting checks inside Docker container
make clean               # Clean up build artifacts and cache files
```

## Troubleshooting

### AWS Profile Issues

If you encounter errors related to AWS profiles, such as:

```bash
ERROR - process_with_date - Configuration error: The config profile (profile-name) could not be found
```

Try the following:

1. **Debug your AWS configuration**:

   ```bash
   make debug AWS_PROFILE=profile-name
   ```

   This will show your AWS configuration as seen by the Docker container.

2. **Check your AWS configuration files**:
   * Ensure your profile exists in `~/.aws/credentials` or `~/.aws/config`
   * Make sure the profile name matches exactly (including case)
   * Verify the profile has the necessary permissions

3. **Use explicit credentials**:
   If profile-based authentication isn't working, you can use explicit credentials:

   ```bash
   docker run --rm \
     -e AWS_ACCESS_KEY_ID=your-access-key \
     -e AWS_SECRET_ACCESS_KEY=your-secret-key \
     -e AWS_SESSION_TOKEN=your-session-token \
     oc-data-fetcher-sftp YYYYMMDD ENV
   ```
