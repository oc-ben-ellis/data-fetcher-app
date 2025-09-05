# Module Hierarchy

This document describes the top-level module hierarchy of the Data Fetcher framework, showing how the different packages are organized and their relationships.

## Overview

The Data Fetcher framework is organized into focused, modular packages that follow a clear hierarchical structure:

```
data_fetcher_app (Application Layer)
├── data_fetcher_core (Core Framework)
├── data_fetcher_configs (Configuration Layer)
│   ├── data_fetcher_sftp (SFTP Protocol)
│   └── data_fetcher_http_api (HTTP API Protocol)
├── data_fetcher_http (HTTP Protocol)
└── data_fetcher_sftp (SFTP Protocol)
```

## Module Descriptions

### Application Layer

#### `data_fetcher_app`
- **Purpose**: Main application entry point and configuration files
- **Key Components**:
  - `main.py` - CLI interface and application entry point
  - Configuration loading and management
- **Dependencies**: All other modules

### Core Framework

#### `data_fetcher_core`
- **Purpose**: Core framework components and common utilities
- **Key Components**:
  - Fetcher orchestration
  - Registry system for component management
  - Global providers (credentials, storage, KV store)
  - Utilities and structured logging
  - Core abstractions and interfaces
- **Dependencies**: None (foundation layer)

### Configuration Layer

#### `data_fetcher_configs`
- **Purpose**: Predefined configurations for different data sources
- **Key Components**:
  - Country-specific configurations (us-fl, fr)
  - Configuration templates and presets
- **Dependencies**: Core framework and protocol implementations

### Protocol Implementations

#### `data_fetcher_sftp`
- **Purpose**: SFTP-specific classes and modules
- **Key Components**:
  - SFTP authentication and connection management
  - SFTP bundle locators for file discovery
  - SFTP loader for streaming file downloads
  - SFTP manager for protocol-level policies
- **Dependencies**: Core framework

#### `data_fetcher_http`
- **Purpose**: HTTP-specific classes and modules
- **Key Components**:
  - HTTP loader for basic HTTP requests
  - HTTP manager for protocol-level policies
  - Basic HTTP support and utilities
- **Dependencies**: Core framework

#### `data_fetcher_http_api`
- **Purpose**: HTTP API-specific classes and modules
- **Key Components**:
  - API bundle locators for API endpoint discovery
  - Pagination support for large datasets
  - Generic API patterns and abstractions
  - API-specific loaders and managers
- **Dependencies**: Core framework

## Dependency Flow

The dependency flow follows a clear hierarchy:

1. **Core Framework** (`data_fetcher_core`) is the foundation with no external dependencies
2. **Protocol Implementations** depend on the core framework
3. **Configuration Layer** depends on both core framework and protocol implementations
4. **Application Layer** depends on all other modules

## Usage Patterns

### Direct Usage
```python
from data_fetcher_core.registry import get_fetcher

# Get a predefined configuration
fetcher = get_fetcher("us-fl")
result = await fetcher.run(plan)
```

### Application Entry Point
```bash
# Run via CLI
poetry run python -m data_fetcher_app.main us-fl
```

## Benefits of This Structure

1. **Separation of Concerns**: Each module has a clear, focused responsibility
2. **Modularity**: Protocols can be developed and tested independently
3. **Extensibility**: New protocols can be added without affecting existing code
4. **Configuration-Driven**: Predefined configurations make the framework easy to use
5. **Clean Dependencies**: Clear dependency hierarchy prevents circular dependencies

## Visual Representation

![Module Hierarchy Diagram](../assets/module_hierarchy.png)

*Note: The diagram shows the relationships between modules, with arrows indicating dependencies. The core framework is at the center, with protocol implementations depending on it, and the application layer orchestrating everything.*
