"""Predefined fetcher configurations.

This module contains predefined fetcher configurations for various data sources
and jurisdictions/registries, including France API and US Florida SFTP
configurations.
"""

# Import configuration modules to ensure they are registered
# Import the main configuration functions from registry
from ..registry import get_fetcher, list_configurations
from . import (
    fr,  # noqa: F401
    us_fl,  # noqa: F401
)

__all__ = ["get_fetcher", "list_configurations"]
