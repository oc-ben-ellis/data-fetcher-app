"""Storage decorators and middleware.

This module provides decorators that add functionality to storage operations,
including file decompression.
"""

from .tar_gz_resource import TarGzResourceDecorator
from .unzip_resource import UnzipResourceDecorator

__all__ = [
    "TarGzResourceDecorator",
    "UnzipResourceDecorator",
]
