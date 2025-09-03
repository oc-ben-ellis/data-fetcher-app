# Application Configuration Overview

The OC Fetcher framework uses a comprehensive application configuration system that manages system-wide settings, logging, and cross-cutting concerns. This configuration system ensures consistent behavior across all components and provides flexibility for different deployment environments.

## Configuration Principles

### 1. **Centralized Management**
- All configuration is managed through a single, centralized system
- Environment-specific settings are handled automatically
- Configuration changes are applied consistently across all components

### 2. **Environment Awareness**
- Configuration automatically adapts to different environments (development, staging, production)
- Sensitive settings are managed through environment variables
- Default values provide sensible out-of-the-box behavior

### 3. **Component Integration**
- All components use the same configuration system
- Configuration is injected into components through dependency injection
- Changes to configuration are reflected immediately in component behavior

## Application Configuration Sections

### [Logging](logging.md)
Structured logging with structlog integration, context variables, and JSON output for comprehensive observability.

### [Detailed Configuration](detailed_configuration.md)
Complete environment variable reference and detailed configuration options for storage, key-value stores, and credential providers.

### **System Settings**
- Global timeout and retry configurations
- Concurrency and resource limits
- Environment-specific behavior settings

### **Storage Configuration**
- Default storage backend settings
- S3 bucket and region configurations
- Storage decorator enablement flags

### **Protocol Settings**
- HTTP and SFTP connection timeouts
- Rate limiting configurations
- Authentication mechanism settings

## Configuration Sources

### **Environment Variables**
```bash
# Logging configuration
DATA_FETCHER_LOG_LEVEL=INFO
DATA_FETCHER_LOG_FORMAT=json

# Storage configuration
DATA_FETCHER_S3_BUCKET=my-fetcher-bucket
DATA_FETCHER_S3_REGION=us-east-1

# Protocol settings
DATA_FETCHER_HTTP_TIMEOUT=30
DATA_FETCHER_SFTP_TIMEOUT=60
```

### **Configuration Files**
```yaml
# config.yaml
logging:
  level: INFO
  format: json
  context_variables: true

storage:
  default_backend: s3
  s3:
    bucket: my-fetcher-bucket
    region: us-east-1
    prefix: fetcher/

protocols:
  http:
    timeout: 30
    max_retries: 3
  sftp:
    timeout: 60
    max_retries: 2
```

### **Code Configuration**
```python
from data_fetcher.config import GlobalConfig

config = GlobalConfig()
config.logging.level = "DEBUG"
config.storage.s3_bucket = "my-bucket"
config.protocols.http.timeout = 30
```

## Key Features

- **Structured Logging**: Built-in structlog integration with context variables and JSON output
- **Environment Adaptation**: Automatic configuration based on deployment environment
- **Component Integration**: All components use the same configuration system
- **Flexible Sources**: Support for environment variables, configuration files, and code-based configuration
- **Validation**: Configuration validation ensures correct settings
- **Documentation**: Self-documenting configuration with help text and examples
