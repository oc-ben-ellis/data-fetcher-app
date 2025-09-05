# Component Interactions

The OC Fetcher framework coordinates three main components: **Bundle Locators**, **Bundle Loaders**, and **Storage**. The main `Fetcher` class orchestrates these components in a two-phase pipeline. **Protocol Managers** handle connection management, rate limiting, and scheduling.

## Component Interfaces

### 1. Bundle Locators

**Purpose**: Generate the next URLs to be processed
**Interface**: `BundleLocator` protocol with two main methods:

```
BundleLocator Interface:
- get_next_urls(context) -> List[URLs]
  - Generate and return next URLs to be processed
  - Called during initialization and when queue is empty

- handle_url_processed(request, bundle_references, context) -> None
  - Called when a URL has been successfully processed
  - Allows locator to update its state or generate new URLs
  - Optional method - not all locators implement this
```

**Available Locators**:

- `SFTPDirectoryBundleLocator`: Generate SFTP URLs for remote directories
- `SFTPFileBundleLocator`: Generate SFTP URLs for individual files
- `GenericDirectoryBundleLocator`: Generate URLs for generic directory structures
- `GenericFileBundleLocator`: Generate URLs for individual files
- `ApiPaginationBundleLocator`: Generate URLs for API pagination

### 2. Bundle Loaders

**Purpose**: Fetch data from endpoints and stream to storage
**Interface**: `BundleLoader` protocol with `load()` method

**Available Bundle Loaders**:

- `HttpxStreamingLoader`: HTTP/HTTPS with streaming responses
- `SFTPLoader`: Enterprise SFTP with AWS integration
- `ApiLoader`: API endpoints with authentication support

### 3. Protocol Managers

**Purpose**: Handle connection management, rate limiting, and scheduling
**Available Managers**:

- `HttpManager`: HTTP connection management with rate limiting and scheduling
- `SftpManager`: SFTP connection management with rate limiting and scheduling

### 4. Storage

**Purpose**: Persist fetched data with streaming support
**Interface**: `Storage` protocol with streaming capabilities:

```
Storage Interface:
- open_bundle(bundle_id, metadata) -> Stream
  - Creates a new bundle for writing data
  - Returns a writable stream for the bundle
  - Handles metadata storage and organization

- close_bundle(stream) -> None
  - Finalizes the bundle and commits data
  - Ensures data is properly persisted
```

**Base Storage Implementations**:

- `FileStorage`: Stores files on local disk
- `PipelineStorage`: Stores files in S3 with metadata

**Storage Decorators** (modify streams being passed to storage):

- `UnzipResourceDecorator`: Unzips any zipped resources

- `BundleResourcesDecorator`: Zips resources into a single zip file

## Component Relationships

### **Fetcher Orchestration**
- **Fetcher** coordinates all components through the two-phase pipeline
- **FetchContext** holds configuration and state for all components
- **FetchPlan** defines execution parameters like concurrency

### **Bundle Locator Usage**
- **Fetcher** calls `get_next_urls()` on all locators during initialization
- **Fetcher** calls `get_next_urls()` when queue is empty
- **Fetcher** calls `handle_url_processed()` after successful processing

### **Bundle Loader Usage**
- **Fetcher** calls `load()` on the configured loader for each request
- **Loader** uses **Protocol Managers** for rate limiting and scheduling
- **Loader** streams data directly to **Storage**

### **Storage Usage**
- **Loader** calls `open_bundle()` to create a new bundle
- **Loader** streams data to the bundle
- **Loader** calls `close_bundle()` to finalize the bundle

### **Protocol Manager Usage**
- **Bundle Loaders** use protocol managers for actual data fetching
- **Bundle Locators** use protocol managers for URL discovery (SFTP)
- **Protocol Managers** provide rate limiting and scheduling services

## Data Flow

1. **URL Generation**: Bundle Locators generate URLs to be processed
2. **Request Processing**: Fetcher coordinates workers to process requests
3. **Data Loading**: Bundle Loaders fetch data using Protocol Managers
4. **Data Storage**: Data is streamed to Storage with optional decorators
5. **Notification**: Locators are notified of completed requests
6. **Completion**: Process continues until no more URLs are available

## Key Features

- **Concurrent Processing**: Multiple workers process requests simultaneously
- **Queue-Based URL Generation**: New URLs are generated only when the queue is empty
- **Thread-Safe Coordination**: Proper locking prevents race conditions
- **Completion Coordination**: Workers coordinate shutdown when no more URLs are available
- **URL Processing Callbacks**: Bundle locators are notified when URLs are successfully processed
- **Protocol-Level Rate Limiting**: Rate limiting is handled at the protocol level for better performance
- **Scheduling Support**: Built-in support for daily and interval-based scheduling
