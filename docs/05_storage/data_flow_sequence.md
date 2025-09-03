# Storage Architecture

The framework uses a composable storage architecture with two base storage implementations and three decorators:

## Base Storage Implementations

1. **FileStorage** (`oc_fetcher/storage/file_storage.py`): Stores files on local disk
   - Simple file-based persistence
   - Supports custom output directories
   - No external dependencies

2. **S3Storage** (`oc_fetcher/storage/s3_storage.py`): Stores files in S3
   - Direct S3 upload with metadata
   - Supports environment-specific bucket naming
   - Requires boto3 and AWS credentials

## Storage Decorators

Storage decorators are located in `oc_fetcher/storage/decorators/` and modify streams being passed to storage implementations:

1. **UnzipResourceDecorator** (`unzip_resource.py`): Automatically decompresses gzip and zip resources
2. **ApplyWARCDecorator** (`apply_warc.py`): Formats resources as WARC records for web archiving
3. **BundleResourcesDecorator** (`bundle_resources.py`): Collects all resources in a bundle and creates a single zip file

## Usage Examples

```python
from oc_fetcher.storage import FileStorage, S3Storage, ApplyWARCDecorator, BundleResourcesDecorator

# Basic file storage
storage = FileStorage("output/files")

# File storage with WARC formatting
base_storage = FileStorage("output/warc")
storage = ApplyWARCDecorator(base_storage)

# S3 storage with resource bundling
base_storage = S3Storage("my-bucket", "prefix/")
storage = BundleResourcesDecorator(base_storage)

# Complex storage stack
base_storage = FileStorage("output/complex")
storage = create_storage_stack(
    base_storage=base_storage,
    use_warc=True,
    bundle_resources=True,
    unzip_resources=True,
)
```
