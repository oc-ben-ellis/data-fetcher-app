"""Storage decorators and middleware.

This module provides decorators that add functionality to storage operations,
including WARC file creation, resource bundling, and file decompression.
"""

from .apply_warc import ApplyWARCDecorator
from .bundle_resources import BundleResourcesDecorator
from .unzip_resource import UnzipResourceDecorator

__all__ = [
    "ApplyWARCDecorator",
    "BundleResourcesDecorator",
    "UnzipResourceDecorator",
]
