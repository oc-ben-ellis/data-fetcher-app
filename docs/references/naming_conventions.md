# Naming Conventions

## Overview

This document outlines the naming conventions used throughout the data-fetcher-sftp project for classes, modules, and components.

## Class Naming Convention

### Locators and Loaders

The naming convention for locators and loaders follows the pattern:

```
<UseCase><Protocol>BundleLocator/BundleLoader
```

Where:
- **UseCase**: Describes the specific use case or functionality (e.g., `Directory`, `File`, `Pagination`, `Single`)
- **Protocol**: Indicates the communication protocol (e.g., `Sftp`, `Http`, `Api`)
- **BundleLocator/BundleLoader**: Specifies the component type

### Examples

#### SFTP Bundle Locators
- `DirectorySftpBundleLocator` - Handles directory-based file discovery for SFTP
- `FileSftpBundleLocator` - Handles specific file path processing for SFTP

#### HTTP Bundle Locators
- `PaginationHttpBundleLocator` - Handles HTTP API pagination
- `SingleHttpBundleLocator` - Handles single HTTP API endpoint calls
- `ComplexPaginationHttpBundleLocator` - Handles complex HTTP API pagination
- `ReversePaginationHttpBundleLocator` - Handles reverse HTTP API pagination

#### Bundle Loaders
- `SftpBundleLoader` - Handles SFTP file downloads
- `HttpBundleLoader` - Handles HTTP API data fetching
- `TrackingHttpBundleLoader` - HTTP API loader with tracking capabilities
- `StreamingHttpBundleLoader` - HTTP streaming loader

## Migration to New Naming Convention

The project has been updated to follow the new `<UseCase><Protocol>BundleLocator/BundleLoader` naming convention:

| Old Name | New Name | Reason |
|----------|----------|---------|
| `SFTPDirectoryBundleLocator` | `DirectorySftpBundleLocator` | Use case first, protocol second |
| `SFTPFileBundleLocator` | `FileSftpBundleLocator` | Use case first, protocol second |
| `ApiPaginationBundleLocator` | `PaginationHttpBundleLocator` | Use case first, protocol second |
| `SingleApiBundleLocator` | `SingleHttpBundleLocator` | Use case first, protocol second |
| `ComplexPaginationBundleLocator` | `ComplexPaginationHttpBundleLocator` | Use case first, protocol second |
| `ReversePaginationBundleLocator` | `ReversePaginationHttpBundleLocator` | Use case first, protocol second |
| `SFTPLoader` | `SftpBundleLoader` | Consistent with BundleLoader suffix |
| `ApiLoader` | `HttpBundleLoader` | Consistent with BundleLoader suffix |
| `TrackingApiLoader` | `TrackingHttpBundleLoader` | Consistent with BundleLoader suffix |
| `HttpxStreamingLoader` | `StreamingHttpBundleLoader` | Consistent with BundleLoader suffix |

## Benefits of the New Convention

1. **Clarity**: Class names clearly indicate their purpose and protocol
2. **Consistency**: Follows a predictable pattern across the codebase
3. **Maintainability**: Easier to understand and maintain
4. **Extensibility**: Easy to add new protocols and use cases

## Implementation Guidelines

When creating new locators or loaders:

1. **Identify the Use Case**: What specific functionality does it provide?
2. **Identify the Protocol**: What communication protocol does it use?
3. **Choose the Type**: Is it a locator or loader?
4. **Apply the Pattern**: Combine them in the format `<UseCase><Protocol><Type>`

### Examples for New Components

- `DatabaseSftpBundleLocator` - For database-backed SFTP file discovery
- `CsvFileBundleLoader` - For CSV file processing
- `JsonHttpBundleLoader` - For JSON API data fetching
- `BatchPaginationHttpBundleLocator` - For batch-based pagination

## File Organization

Classes are organized in packages based on their protocol:

- `data_fetcher_sftp/` - SFTP-related components
- `data_fetcher_http_api/` - HTTP API-related components
- `data_fetcher_core/` - Core framework components

This organization makes it easy to find components by protocol and maintains clear separation of concerns.
