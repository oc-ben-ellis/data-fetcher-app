# FileSftpBundleLocator

## Overview

The FileSftpBundleLocator is used for processing specific file paths in SFTP configurations. It handles predefined file paths rather than directory scanning.

## Implementation

```python
from data_fetcher_core.factory import create_file_provider
from data_fetcher_core.factory import create_sftp_protocol_config

# Create protocol configuration
sftp_config = create_sftp_protocol_config(
    config_name="example_sftp",
    connect_timeout=20.0,
    rate_limit_requests_per_second=2.0
)

# Create locator using factory function
quarterly_provider = create_file_provider(
    sftp_config=sftp_config,
    file_paths=[
        "/data/exports/daily/companies.csv",
        "/data/exports/daily/officers.csv",
    ],
)
```

## Features

- **Specific File Paths**: Processes predefined list of file paths
- **Batch Processing**: Handles multiple files in a single operation
- **Error Handling**: Graceful handling of missing files
- **Persistence**: Tracks progress across runs

## Usage in Configuration

The FileSftpBundleLocator is used in SFTP configurations like `us-fl` to:
- Process specific quarterly archive files
- Handle predefined file paths
- Process files that don't follow directory scanning patterns

## Configuration Options

- `file_paths`: List of specific file paths to process
- `persistence_prefix`: Prefix for progress tracking

## Related Components

- **[DirectorySftpBundleLocator](generic_directory_bundle_locator.md)** - Directory-based file discovery
- **[SftpBundleLoader](../loaders/sftp_loader.md)** - Handles file downloads
- **[US_FL - US Florida SFTP](../../../us_fl_sftp.md)** - Configuration using this locator
