"""Predefined fetcher recipes.

This module contains predefined fetcher recipes for various data sources
and jurisdictions/registries, including France API and US Florida SFTP
recipes.
"""

# Import recipe modules to ensure they are registered
# Import the main recipe functions from recipebook
from data_fetcher_core.recipebook import get_fetcher, list_recipes

from . import (
    fr,
    us_fl,
)

__all__ = ["get_fetcher", "list_recipes"]
