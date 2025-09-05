"""Predefined fetcher configurations.

This module contains predefined fetcher configurations for various data sources
and jurisdictions/registries, including France API and US Florida SFTP
configurations.
"""

# Import configuration modules to ensure they are registered
# Import the main configuration functions from registry
from data_fetcher_core.registry import get_fetcher, list_configurations

from . import (
    fr,
    us_fl,
)

__all__ = ["get_fetcher", "list_configurations"]
