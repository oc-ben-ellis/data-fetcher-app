# Component Relationships

The component relationships diagram provides a detailed view of how all components interact with each other, organized by functional layers. It shows the dependencies between components and how data flows through the system, from the core orchestration layer down to the supporting infrastructure components.

## Visual Architecture Diagram

![Component Relationships](../diagrams/png/component_relationships.png)

The component relationships diagram provides a detailed view of how all components interact with each other, organized by functional layers. It shows the dependencies between components and how data flows through the system, from the core orchestration layer down to the supporting infrastructure components.

**Key Components**:

- **Core Layer** - Fetcher, Context, and Plan components that orchestrate the entire system
- **Bundle Locators Layer** - Bundle Locators that generate URLs (SFTP Directory/File, Generic Directory/File, API Pagination bundle locators)
- **Loader Layer** - Bundle Loaders that fetch data from endpoints (HttpxStreaming, SFTP, API)
- **Storage Layer** - Base storage implementations and decorators for data transformation
- **Supporting Systems** - Cross-cutting concerns including protocol management, caching, logging, and configuration

## Component Layers

### **Core Layer**
The core layer contains the main orchestration components:

- **Fetcher**: Main orchestrator that coordinates all components
- **FetchContext**: Configuration and state management for all components
- **FetchPlan**: Execution plan with concurrency settings and request metadata

### **Frontier Layer**
The frontier layer contains components that generate URLs for processing:

- **SFTPDirectoryBundleLocator**: Generates SFTP URLs for remote directories
- **SFTPFileBundleLocator**: Generates SFTP URLs for individual files
- **GenericDirectoryBundleLocator**: Generates URLs for generic directory structures
- **GenericFileBundleLocator**: Generates URLs for individual files
- **ApiPaginationBundleLocator**: Generates URLs for API pagination

### **Loader Layer**
The loader layer contains components that fetch data from endpoints:

- **HttpxStreamingLoader**: HTTP/HTTPS with streaming responses
- **SFTPLoader**: Enterprise SFTP with AWS integration
- **ApiLoader**: API endpoints with authentication support

### **Storage Layer**
The storage layer contains components that persist fetched data:

- **FileStorage**: Stores files on local disk
- **S3Storage**: Stores files in S3 with metadata
- **Storage Decorators**: Unzip, WARC, Bundle Resources decorators

### **Supporting Systems**
The supporting systems layer contains cross-cutting concerns:

- **Protocol Managers**: Rate limiting and scheduling (HTTP/SFTP managers)
- **Key-Value Store**: Caching and state management (Redis/In-Memory)
- **Structured Logging**: Context variables and JSON output
- **Application Configuration**: System-wide configuration management

## Component Dependencies

### **Fetcher Dependencies**
- **Fetcher** → **FetchContext**: Uses context for configuration and state
- **Fetcher** → **FetchPlan**: Uses plan for execution parameters
- **Fetcher** → **Bundle Locators**: Orchestrates URL generation
- **Fetcher** → **Bundle Loaders**: Orchestrates data fetching
- **Fetcher** → **Storage**: Uses storage for data persistence
- **Fetcher** → **Supporting Systems**: Uses for logging, caching, and configuration

### **Bundle Locator Dependencies**
- **SFTP Locators** → **SftpManager**: Use for SFTP connections and rate limiting
- **Generic Locators** → **HttpManager**: Use for HTTP connections and rate limiting
- **API Locators** → **HttpManager**: Use for API connections and rate limiting

### **Bundle Loader Dependencies**
- **HttpxStreamingLoader** → **HttpManager**: Uses for HTTP connections and rate limiting
- **SFTPLoader** → **SftpManager**: Uses for SFTP connections and rate limiting
- **ApiLoader** → **HttpManager**: Uses for API connections and rate limiting
- **All Loaders** → **Storage**: Stream data to storage

### **Storage Dependencies**
- **Storage Decorators** → **Base Storage**: Decorators wrap base storage implementations
- **S3Storage** → **AWS Services**: Uses AWS S3 for data persistence

## Data Flow Relationships

### **URL Generation Flow**
1. **Fetcher** calls **Bundle Locators** to generate URLs
2. **Bundle Locators** use **Protocol Managers** for connections and rate limiting
3. **Fetcher** adds URLs to processing queue

### **Data Fetching Flow**
1. **Fetcher** calls **Bundle Loaders** to fetch data
2. **Bundle Loaders** use **Protocol Managers** for connections and rate limiting
3. **Bundle Loaders** stream data to **Storage**
4. **Storage** processes data through **Decorators** if configured

### **Supporting Flow**
1. **Fetcher** uses **Structured Logging** for operation logging
2. **Fetcher** uses **Key-Value Store** for caching and state
3. **Fetcher** uses **Application Configuration** for system settings

## Key Architectural Patterns

### **Dependency Injection**
- Components receive their dependencies through constructor injection
- Allows for easy testing and configuration changes
- Promotes loose coupling between components

### **Decorator Pattern**
- Storage decorators can be stacked for different processing needs
- Each decorator adds specific functionality while maintaining the same interface
- Allows for flexible storage configurations

### **Strategy Pattern**
- Different bundle locators and loaders can be used interchangeably
- Protocol managers provide different strategies for rate limiting and scheduling
- Allows for protocol-specific optimizations

### **Observer Pattern**
- Bundle locators are notified when URLs are processed
- Allows locators to update their state and generate new URLs
- Enables dynamic URL generation based on processing results

## Extensibility Points

### **Adding New Protocols**
1. Create new **Protocol Manager** for the protocol
2. Create new **Bundle Loader** that uses the protocol manager
3. Create new **Bundle Locator** if needed for URL generation
4. Register components in the configuration system

### **Adding New Storage Backends**
1. Implement the **Storage** interface
2. Add any necessary **Storage Decorators**
3. Register the storage backend in the configuration system

### **Adding New Features**
1. Extend **FetchContext** with new configuration options
2. Add new **Supporting Systems** for cross-cutting concerns
3. Update **Fetcher** to use new features
4. Provide configuration options for enabling/disabling features
