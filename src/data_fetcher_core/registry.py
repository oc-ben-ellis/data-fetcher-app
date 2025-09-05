"""Configuration registry and fetcher factory.

This module manages the registry of available fetcher configurations and provides
functions to retrieve and instantiate fetchers based on configuration names.
"""

from collections.abc import Callable

from data_fetcher_core.core import FetchContext
from data_fetcher_core.fetcher import Fetcher

# Configuration registry
_CONFIGURATIONS: dict[str, Callable[[], FetchContext]] = {}


def register_configuration(name: str, setup_func: Callable[[], FetchContext]) -> None:
    """Register a configuration setup function."""
    _CONFIGURATIONS[name] = setup_func


def get_fetcher(config_name: str) -> Fetcher:
    """Get a fetcher with the specified configuration."""
    if config_name not in _CONFIGURATIONS:
        raise KeyError(f"Bad config: {config_name}")  # noqa: TRY003

    # Call the setup function
    setup_func = _CONFIGURATIONS[config_name]
    ctx = setup_func()

    return Fetcher(ctx)


def list_configurations() -> list[str]:
    """List all available configurations."""
    return list(_CONFIGURATIONS.keys())


def get_configuration_setup_function(config_name: str) -> Callable[[], FetchContext]:
    """Get the setup function for a configuration."""
    if config_name not in _CONFIGURATIONS:
        raise KeyError(f"Bad config: {config_name}")  # noqa: TRY003
    return _CONFIGURATIONS[config_name]
