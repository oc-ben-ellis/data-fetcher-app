"""Data storage and persistence implementations.

This module provides storage implementations for persisting fetched data,
including local file storage and S3 integration.
"""

from .bundle_storage_context import BundleStorageContext
from .decorators import (
    TarGzResourceDecorator,
    UnzipResourceDecorator,
)
from .factory import create_storage_config_instance
from .file_storage import FileStorage
from .pipeline_bus_storage import DataPipelineBusStorage
from .protocol import Storage
from .s3_storage import S3Storage
from .streaming import StreamingZipReader, TeeStream

__all__ = [
    "BundleStorageContext",
    "DataPipelineBusStorage",
    "FileStorage",
    "S3Storage",
    "Storage",
    "StreamingZipReader",
    "TarGzResourceDecorator",
    "TeeStream",
    "UnzipResourceDecorator",
    "create_storage_config_instance",
]
