# DirectorySftpBundleLocator

## Overview

The DirectorySftpBundleLocator provides directory-based file discovery for SFTP-based data sources. It scans directories for files matching specified patterns and applies filtering criteria.

## Implementation

```python
from data_fetcher_core.factory import create_directory_provider
from data_fetcher_core.factory import create_sftp_protocol_config

# Create protocol configuration
sftp_config = create_sftp_protocol_config(
    config_name="example_sftp",
    connect_timeout=20.0,
    rate_limit_requests_per_second=2.0
)

# Create locator using factory function
daily_provider = create_directory_provider(
    sftp_config=sftp_config,
    remote_dir="/data/exports",
    filename_pattern="*.txt",
    max_files=None,
    file_filter=daily_file_filter,
    sort_key=lambda file_path, mtime: mtime,
    sort_reverse=True,
)
```

## Features

- **Pattern Matching**: Supports glob patterns (e.g., `*.txt`, `*.csv`)
- **File Filtering**: Custom filter functions for date-based or other criteria
- **Sorting**: Configurable sorting by modification time or other attributes
- **Recursive Scanning**: Can scan subdirectories
- **Progress Tracking**: Tracks discovered files across runs
- **Error Handling**: Graceful handling of missing files

## Configuration Options

- `remote_dir`: Base directory to scan
- `filename_pattern`: Glob pattern for file matching
- `max_files`: Maximum number of files to process
- `file_filter`: Custom filter function
- `sort_key`: Sorting function
- `sort_reverse`: Reverse sort order
- `persistence_prefix`: Prefix for progress tracking

## Usage in Configuration

The DirectorySftpBundleLocator is used in SFTP configurations like `us-fl` to:
1. **Daily Files**: Discover and process daily data files
2. **File Filtering**: Apply date-based or other filtering criteria
3. **Directory Scanning**: Automatically discover files in remote directories

## Related Components

- **[SftpBundleLoader](../loaders/sftp_loader.md)** - Handles file downloads
- **[FileSftpBundleLocator](generic_file_bundle_locator.md)** - Handles specific file paths
- **[US_FL - US Florida SFTP](../../../us_fl_sftp.md)** - Configuration using these locators
- **[Creating a Recipe](../../../creating_a_recipe.md)** - How to create custom locators
