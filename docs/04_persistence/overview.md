# Persistence Overview

The OC Fetcher framework provides comprehensive persistence capabilities for caching, state management, and data storage. The persistence system is designed to be flexible, scalable, and efficient, supporting both local and distributed storage backends.

## Persistence Principles

### 1. **Multi-Level Caching**
- In-memory caching for fast access to frequently used data
- Persistent storage for long-term data retention
- Distributed caching for multi-instance deployments

### 2. **State Management**
- Persistent state across fetcher runs
- Transactional operations for data consistency
- Automatic state recovery and cleanup

### 3. **Scalability**
- Support for distributed storage backends
- Horizontal scaling capabilities
- Performance optimization for large datasets

## Persistence Components

### [KV Store](kv_store.md)
Key-value store for caching and state management with support for Redis and in-memory backends.

### [Features](features.md)
Advanced persistence features including state persistence, error tracking, processing statistics, and resume capabilities.

### **Storage Backends**
- **File Storage**: Local file-based persistence
- **Pipeline Storage**: Cloud-based object storage
- **Database Storage**: Relational and NoSQL database support

### **Caching Layers**
- **In-Memory Cache**: Fast access to frequently used data
- **Distributed Cache**: Shared cache across multiple instances
- **Persistent Cache**: Long-term data retention

## Key Features

### **Flexible Storage**
- Multiple storage backend options
- Automatic backend selection based on configuration
- Easy migration between storage backends

### **Performance Optimization**
- Intelligent caching strategies
- Lazy loading of data
- Compression and deduplication

### **Data Consistency**
- Transactional operations
- Automatic data validation
- Conflict resolution mechanisms

### **Monitoring and Observability**
- Built-in metrics and monitoring
- Performance tracking
- Error reporting and alerting

## Usage Examples

### **Basic KV Store Usage**
```python
from data_fetcher_core.kv_store import get_kv_store

# Get KV store instance
kv_store = get_kv_store()

# Store data
await kv_store.set("key", "value")

# Retrieve data
value = await kv_store.get("key")
```

### **Storage Configuration**
```python
from data_fetcher_core.storage import FileStorage, PipelineStorage

# Local file storage
storage = FileStorage("data/")

# S3 storage
storage = PipelineStorage("my-bucket", "prefix/")
```

### **Caching Configuration**
```python
from data_fetcher_core.global_kv_store import configure_application_kv_store

# Configure application key-value store
configure_application_kv_store()
config.cache.enabled = True
config.cache.backend = "redis"
config.cache.ttl = 3600  # 1 hour
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
```

### **Cache Configuration**
```yaml
cache:
  enabled: true
  backend: redis
  ttl: 3600
  max_size: 1000
  redis:
    host: localhost
    port: 6379
    db: 0
```

### **Persistence Configuration**
```yaml
persistence:
  state_backend: redis
  cache_backend: memory
  cleanup_interval: 86400  # 24 hours
```

## Key Benefits

- **Performance**: Fast access to frequently used data through caching
- **Scalability**: Support for distributed storage and caching
- **Reliability**: Robust error handling and data consistency
- **Flexibility**: Multiple storage backend options
- **Monitoring**: Built-in metrics and observability
- **Ease of Use**: Simple API for common persistence operations
