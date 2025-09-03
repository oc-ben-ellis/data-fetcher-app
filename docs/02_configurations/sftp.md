# SFTP Functionality

The framework includes an SFTP loader that provides enterprise-grade capabilities:

## Architecture

1. **🔐 CredentialsProvider Interface**: Protocol for any credential source
2. **🔑 Credential Providers**: AWS Secrets Manager, environment variables, static credentials
3. **📁 SftpManager**: Handles SFTP connection management, rate limiting, and scheduling
4. **📄 SFTPLoader**: Handles SFTP file operations
5. **☁️ S3Storage**: Handles S3 uploads with metadata

## Quick Start

```python
from oc_fetcher import get_fetcher, FetchPlan

# Get the SFTP fetcher
fetcher = get_fetcher("us-sftp")

# Create a fetch plan with date and environment
plan = FetchPlan(
    concurrency=1,
    loader_params={
        "input_date": "20240101",
        "env": "dev",
    }
)

# Run the fetch
result = await fetcher.run(plan)
```
