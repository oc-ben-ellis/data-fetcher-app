# data-fetcher-sftp

A custom SFTP data fetcher built in Python and deployed via a Docker Image to ECR. This utility transfers files from an SFTP server to an AWS S3 bucket with appropriate metadata.

## Overview

This utility performs the following operations:

1. Connects to an SFTP server using credentials stored in AWS Secrets Manager
2. Finds a specific file based on the input date (format: YYYYMMDD)
3. Transfers the file to an AWS S3 bucket with appropriate metadata tags
4. Logs the process for monitoring and troubleshooting

## Dependencies

* This repository relies on resources (S3 buckets etc) deployed from the iac-data-orchestrator repository.

### Docker

#### Prerequisites

* Docker
* The AWS CLI, configured for SSO from OpenCorporates accounts (see [SSO Playbook](https://opencorporates.atlassian.net/wiki/spaces/AWS/pages/397737995/SSO+Playbook+-+Add+a+new+account+profile+to+aws-cli))

## Installation & Local Testing

For detailed instructions on setting up the project locally and running tests, please refer to the [Local Testing Guide](docs/local-testing.md).

## Configuration

The application uses one configuration source:

1. **YAML Configuration File** (`config/sftp_config.yaml`):

   ```yaml
   # SFTP Path
   remote_dir: "/Public/doc/cor"
   filename_pattern: "[YYYYMMDD]c.txt"

   # S3 Configuration
   s3_bucket: "your-s3-bucket"
   s3_prefix: "your/s3/prefix"

   # AWS Configuration
   secret_name: "your-secret-name"
   region_name: "your-aws-region"

   # Metadata
   meta_source_system: "SourceSystem_SFTP"
   meta_source_entity: "entity_name"
   meta_load_name: "Load_Name"
   meta_load_version: "1.0.0"
   ```

## Usage

For detailed instructions on running the utility locally, please refer to the [Local Testing Guide](docs/local-testing.md).

The utility accepts two parameters:

* `YYYYMMDD` - The date in year-month-day format.
* `ENV` - The environment (play, dev, idp, or prod).

Example:

```bash
python src/sftp_to_s3.py 20250506 play
```

## Development

This project uses several tools to maintain code quality:

* **Poetry**: Dependency management
* **Black**: Code formatting
* **pytest**: Testing framework
* **Pre-commit**: Git hooks for code quality checks

## Troubleshooting

For troubleshooting common issues during local development and testing, please refer to the [Local Testing Guide](docs/local-testing.md).

## CI/CD

This project uses GitHub Actions for CI/CD:

* **Repository Hygiene**: Runs on pull requests to ensure code quality
* **Pre-commit Auto-update**: Automatically updates pre-commit hooks weekly

## Architecture Decisions

Architecture Decision Records (ADRs) are stored in the `docs/adr` directory.
