"""Data storage and persistence implementations.

This module provides storage implementations for persisting fetched data,
including local file storage, S3 integration, and WARC file support.
"""

from .decorators import (
    ApplyWARCDecorator,
    BundleResourcesDecorator,
    UnzipResourceDecorator,
)
from .file_storage import FileStorage
from .s3_storage import S3Storage

__all__ = [
    "FileStorage",
    "S3Storage",
    "ApplyWARCDecorator",
    "BundleResourcesDecorator",
    "UnzipResourceDecorator",
]
