# Fetcher Configurations Documentation

This directory contains documentation about predefined fetcher configurations and the OC Fetcher framework overview.

## Recommended Reading Order

1. **[overview.md](overview.md)** - Start here for framework overview, quick start, and protocol differences
2. **[api.md](api.md)** - API-based configurations
3. **[sftp.md](sftp.md)** - SFTP configurations
4. **[us_fl_test_setup.md](us_fl_test_setup.md)** - US Florida test environment setup and execution
5. **[scheduling.md](scheduling.md)** - Scheduling options

## Credential Providers

The framework supports multiple credential providers that can be configured via environment variables or command line flags:

- **AWS Secrets Manager** (default) - For production environments
- **Environment Variables** - For development, testing, and containerized deployments

See the [overview.md](overview.md) for quick start examples and [../03_application_configuration/detailed_configuration.md](../03_application_configuration/detailed_configuration.md) for complete configuration details.

## Files

- `overview.md` - OC Fetcher framework overview, quick start, installation, and protocol differences
- `api.md` - API configuration options
- `sftp.md` - SFTP configuration and setup
- `us_fl_test_setup.md` - Complete guide for setting up US Florida test environment and running oc-fetcher
- `scheduling.md` - Scheduling configurations
