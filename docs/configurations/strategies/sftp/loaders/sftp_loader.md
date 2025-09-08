# SftpBundleLoader

## Overview

The SftpBundleLoader is a specialized loader for SFTP-based data sources. It's built using the `create_sftp_loader` factory function and provides file downloading capabilities with progress tracking and error handling.

## Implementation

```python
from data_fetcher_core.factory import create_sftp_protocol_config, create_sftp_loader

# Create SFTP protocol configuration
sftp_config = create_sftp_protocol_config(
    config_name="example_sftp",
    connect_timeout=20.0,
    rate_limit_requests_per_second=2.0,
    max_retries=3
)

# Create loader with ProtocolConfig
loader = create_sftp_loader(
    sftp_config=sftp_config,
    meta_load_name="sftp_loader",
)
```

## Features

- **File Download**: Downloads files from SFTP servers
- **Progress Tracking**: Monitors download progress and file sizes
- **Error Handling**: Handles connection issues and file access errors
- **Streaming**: Streams large files to avoid memory issues
- **Retry Logic**: Automatic retry for failed downloads

## Usage in Configuration

The SftpBundleLoader is used in SFTP configurations like `us-fl` to handle file downloads from remote SFTP servers.

## Configuration Requirements

- **SftpProtocolConfig**: Protocol configuration with connection settings
- **Authentication**: SSH keys or username/password authentication via credential provider
- **Network Access**: Connection to SFTP server

## Error Handling

The loader handles various error scenarios:
- **Connection Timeouts**: Automatic reconnection with backoff
- **File Access Errors**: Retry with different permissions
- **Network Issues**: Connection retry with timeout
- **Storage Errors**: Retry with different storage backend

## Related Components

- **[DirectorySftpBundleLocator](../locators/generic_directory_bundle_locator.md)** - Handles directory-based file discovery
- **[FileSftpBundleLocator](../locators/generic_file_bundle_locator.md)** - Handles specific file path discovery
- **[US_FL - US Florida SFTP](../../../us_fl_sftp.md)** - Configuration using this loader
- **[Creating a Recipe](../../../creating_a_recipe.md)** - How to create custom loaders
