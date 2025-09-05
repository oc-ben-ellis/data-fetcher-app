# Storage Overview

The OC Fetcher framework uses a composable storage architecture that provides flexible, scalable, and efficient data storage capabilities. The storage system is designed to handle large datasets through streaming-first operations while maintaining data integrity and providing comprehensive metadata management.

## Storage Principles

### 1. **Streaming-First Design**
- Data flows through the system without loading entire files into memory
- Large payloads are processed efficiently through streaming operations
- Memory usage remains constant regardless of file size

### 2. **Composable Architecture**
- Storage decorators can be stacked for different processing needs
- Base storage implementations provide core persistence capabilities
- Easy to extend with custom storage backends and decorators

### 3. **Protocol Independence**
- Same storage interface regardless of data source protocol
- Storage components work with HTTP, SFTP, and other protocols
- Consistent behavior across different data sources

## Storage Components

### [Data Flow Sequence](data_flow_sequence.md)
Step-by-step data processing flow from source to final storage with detailed component interactions and storage architecture overview.

### [S3](s3.md)
AWS S3 storage integration with metadata management and environment-specific configurations.

### **Base Storage Implementations**
- **FileStorage**: Local file-based persistence
- **PipelineStorage**: Cloud-based object storage with metadata

### **Storage Decorators**
- **UnzipResourceDecorator**: Automatic decompression of compressed resources

- **BundleResourcesDecorator**: Resource bundling into single packages

## Storage Architecture

### **Composable Design**
The storage system uses a decorator pattern where each decorator adds specific functionality while maintaining the same storage interface:

```
Raw Data → Unzip Decorator → Bundle Decorator → Base Storage
```

### **Streaming Operations**
All storage operations are streaming-based, allowing efficient processing of large datasets:

1. **Data Reception**: Data is received as streams from bundle loaders
2. **Processing**: Decorators process data streams without loading into memory
3. **Storage**: Processed data is streamed to final storage destination
4. **Metadata**: Metadata is collected and stored alongside data

## Key Features

### **Flexible Storage Backends**
- **Local File Storage**: Simple file-based persistence
- **Pipeline Storage**: Cloud-based object storage
- **Extensible**: Easy to add new storage backends

### **Data Transformation**
- **Automatic Decompression**: Handles gzip, zip, and other compression formats

- **Resource Bundling**: Convenient packaging for downstream processing

### **Metadata Management**
- **Comprehensive Metadata**: URL, content type, status codes, timestamps
- **Custom Metadata**: Support for application-specific metadata
- **Metadata Storage**: Metadata is stored alongside data for easy retrieval

### **Performance Optimization**
- **Streaming Operations**: Constant memory usage regardless of file size
- **Parallel Processing**: Support for concurrent storage operations
- **Caching**: Intelligent caching of frequently accessed data

## Usage Examples

### **Basic File Storage**
```python
from data_fetcher_core.storage import FileStorage

# Create file storage
storage = FileStorage("output/files")

# Open bundle for writing
async with storage.open_bundle("bundle-1", {"source": "example.com"}) as bundle:
    await bundle.write_resource(
        url="https://example.com/data",
        content_type="application/json",
        status_code=200,
        stream=data_stream
    )
```

### **Pipeline Storage with Decorators**
```python
from data_fetcher_core.storage import PipelineStorage, create_storage_stack

# Create S3 storage with decorators
base_storage = PipelineStorage("my-bucket", "prefix/")
storage = create_storage_stack(
    base_storage=base_storage,

    bundle_resources=True,
    unzip_resources=True
)
```

### **Custom Storage Configuration**
```python
from data_fetcher_core.storage import FileStorage, BundleResourcesDecorator

# Custom storage configuration
base_storage = FileStorage("output/custom")
storage = BundleResourcesDecorator(base_storage)
```

## Configuration Options

### **Storage Configuration**
```yaml
storage:
  backend: s3
  s3:
    bucket: my-fetcher-bucket
    region: us-east-1
    prefix: data/
  file:
    path: ./data/
  decorators:
    unzip: true

    bundle: true
```

### **Environment-Specific Settings**
```yaml
environments:
  development:
    storage:
      backend: file
      path: ./dev-data/
  production:
    storage:
      backend: s3
      bucket: prod-fetcher-bucket
```

## Key Benefits

- **Scalability**: Handles large datasets efficiently through streaming
- **Flexibility**: Composable design allows custom storage configurations
- **Performance**: Streaming operations maintain constant memory usage

- **Extensibility**: Easy to add new storage backends and decorators
- **Reliability**: Robust error handling and data integrity
- **Monitoring**: Built-in metrics and observability
