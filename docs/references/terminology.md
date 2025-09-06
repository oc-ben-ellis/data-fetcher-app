# Terminology

This document defines key terms and concepts used throughout the Data Fetcher framework documentation.

## Core Concepts

### Bundle

A **Bundle** is a collection of related data resources that are fetched and stored together as a unit. Bundles provide:

- **Logical Grouping**: Related resources (e.g., files from the same API call, or files from the same directory) are grouped together
- **Atomic Operations**: All resources in a bundle are processed together and share the same lifecycle
- **Metadata Management**: Bundle-level metadata is preserved and organized
- **Storage Organization**: Bundles are stored with unique Bundle IDs (BIDs) for time-based organization and tracing
- **Streaming Support**: Large bundles can be processed without loading entire contents into memory

Bundles are managed through `BundleStorageContext` objects that handle the complete lifecycle from creation to completion.

### Resource

A **Resource** is an individual piece of data that has been fetched from a remote source. Resources contain:

- **Data Content**: The actual data payload (files, API responses, etc.)
- **Metadata**: Information about the resource including URL, content type, HTTP status, headers, and notes
- **Streaming Support**: Resources can be streamed directly to storage without buffering in memory

Resources are represented by `ResourceMeta` objects and are added to bundles through the `BundleStorageContext.add_resource()` method.

### Recipe

A **Recipe** is a predefined configuration that defines how the Data Fetcher framework behaves for a specific data source or jurisdiction. Recipes provide a declarative way to configure all components of the fetcher, including:

- **Bundle Locators**: Components that generate URLs or file paths for processing
- **Bundle Loaders**: Components that fetch data from endpoints and stream it to storage
- **ProtocolConfig**: Protocol-specific settings for connection management, rate limiting, and authentication
- **Storage Configuration**: Where and how to store the retrieved data

Recipes are implemented as setup functions that return a `FetcherRecipe` object, allowing for flexible composition of components without rigid class hierarchies. Each recipe is registered with a unique identifier (e.g., `us-fl`, `fr`) and can be executed using the command line interface.

### Bundle Locator

A **Bundle Locator** is a component responsible for generating URLs or file paths that need to be processed. Locators implement the `BundleLocator` protocol and provide a standardized interface for URL generation across different protocols and data sources. They handle:

- URL generation and discovery
- Progress tracking and state management
- Completion callbacks when URLs are successfully processed

Examples include `DirectorySftpBundleLocator`, `FileSftpBundleLocator`, and `PaginationHttpBundleLocator`.

### Bundle Loader

A **Bundle Loader** is a component responsible for fetching data from endpoints and streaming it to storage. Loaders implement the `BundleLoader` protocol and handle:

- Data retrieval from remote endpoints
- Streaming large payloads directly to storage
- Protocol-specific concerns (HTTP, SFTP, etc.)
- Connection management and authentication
- Rate limiting and error handling

Examples include `StreamingHttpBundleLoader`, `SftpBundleLoader`, and `HttpBundleLoader`.

### ProtocolConfig

A **ProtocolConfig** is a configuration object that defines protocol-specific settings for connection management, rate limiting, and authentication. ProtocolConfig objects enable multiple connection pools per manager and provide:

- Connection timeout and retry settings
- Rate limiting configuration
- Authentication mechanisms
- Protocol-specific parameters

Examples include `HttpProtocolConfig` and `SftpProtocolConfig`.

### FetcherRecipe

A **FetcherRecipe** is the main configuration object that defines a complete fetcher setup. It contains:

- Bundle locators for URL generation
- Bundle loaders for data fetching
- Storage configuration
- Protocol-specific settings

FetcherRecipe objects are created using the builder pattern with `create_fetcher_config()`.

### Fetcher

The **Fetcher** is the main orchestrator class that coordinates all components in the framework. It:

- Manages the execution pipeline
- Coordinates between locators, loaders, and storage
- Handles concurrency and queue management
- Provides the main `run()` method for execution

### BundleRef

A **BundleRef** is a reference to a bundle of data that has been processed and stored. It contains:

- Primary URL or identifier
- Resource count
- Metadata about the bundle

BundleRef objects are returned by loaders and used for tracking and notifications.

### FetchPlan

A **FetchPlan** is an execution plan that contains:

- The FetcherRecipe to execute
- Run context and configuration
- Concurrency settings
- Queue size parameters

### FetchRunContext

A **FetchRunContext** contains the runtime context for a fetch operation, including:

- Unique run ID for tracking
- Application configuration
- Error tracking
- State management

## Protocol-Specific Terms

### HTTP/API Terms

- **PaginationHttpBundleLocator**: Handles API endpoints with pagination support
- **SingleHttpBundleLocator**: Handles single API endpoint calls
- **ComplexPaginationHttpBundleLocator**: Handles complex pagination scenarios
- **ReversePaginationHttpBundleLocator**: Handles reverse pagination patterns
- **StreamingHttpBundleLoader**: High-performance HTTP loader with streaming support
- **HttpBundleLoader**: Basic HTTP loader for API endpoints
- **TrackingHttpBundleLoader**: HTTP loader with tracking capabilities

### SFTP Terms

- **DirectorySftpBundleLocator**: Scans SFTP directories for files matching patterns
- **FileSftpBundleLocator**: Processes specific SFTP file paths
- **SftpBundleLoader**: Handles SFTP file downloads and streaming

## Storage Terms

### Storage Types

- **File Storage**: Local file system storage
- **Pipeline Storage**: AWS S3-based storage with SQS notifications
- **Storage Decorators**: Components that modify storage behavior (e.g., Unzip, Bundle Resources)

### Storage Context

- **BundleStorageContext**: Manages bundle lifecycle during storage operations
- **Bundle Completion**: Process of finalizing a bundle and triggering notifications

## State Management Terms

- **Key-Value Store**: Persistent storage for state management (Redis or in-memory)
- **State Management Prefix**: Unique identifier for tracking state across runs
- **Persistence**: Ability to track progress and resume operations

## Authentication Terms

- **Credential Provider**: System for managing authentication credentials
- **OAuth Authentication**: OAuth 2.0 authentication mechanism
- **API Key Authentication**: API key-based authentication
- **AWS Secrets Manager**: AWS service for secure credential storage

## Related Documentation

- **[Architecture Overview](../architecture/README.md)** - System architecture and design
- **[Creating a Recipe](../configurations/creating_a_recipe.md)** - How to create new recipes
- **[Factory Functions](factory_functions.md)** - Component creation functions
- **[Naming Conventions](naming_conventions.md)** - Class and component naming standards
