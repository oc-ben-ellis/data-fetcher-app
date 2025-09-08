"""Recipe registry and fetcher factory.

This module manages the registry of available fetcher recipes and provides
functions to retrieve and instantiate fetchers based on recipe names.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from data_fetcher_core.config_factory import FetcherConfig

from data_fetcher_core.core import FetcherRecipe
from data_fetcher_core.exceptions import ConfigurationError
from data_fetcher_core.fetcher import Fetcher

# Get logger for this module
logger = structlog.get_logger(__name__)

# Recipe registry
_RECIPES: dict[str, Callable[[], FetcherRecipe]] = {}


def register_recipe(name: str, setup_func: Callable[[], FetcherRecipe]) -> None:
    """Register a recipe setup function."""
    _RECIPES[name] = setup_func


def get_fetcher(recipe_name: str, app_config: "FetcherConfig | None" = None) -> Fetcher:
    """Get a fetcher with the specified recipe.

    Args:
        recipe_name: Name of the recipe to use.
        app_config: Application configuration containing credential provider,
                   key-value store, and storage config.

    Returns:
        Configured Fetcher instance.

    Raises:
        ConfigurationError: If recipe is not found or configuration fails.
    """
    if recipe_name not in _RECIPES:
        error_message = "Recipe not found"
        raise ConfigurationError(error_message, "recipe_registry")

    try:
        # Call the setup function
        setup_func = _RECIPES[recipe_name]
        ctx = setup_func()

        logger.debug("Recipe setup completed", recipe_name=recipe_name)

        # Update the context with app_config if provided
        if app_config is not None:
            _configure_recipe_with_app_config(ctx, app_config)

        logger.debug("Fetcher configuration completed", recipe_name=recipe_name)
        return Fetcher()

    except Exception as e:
        if isinstance(e, ConfigurationError):
            raise
        error_message = "Failed to configure recipe"
        raise ConfigurationError(error_message, "recipe_configuration") from e


def _configure_recipe_with_app_config(
    ctx: FetcherRecipe, app_config: "FetcherConfig"
) -> None:
    """Configure recipe components with app_config.

    Args:
        ctx: The fetcher recipe context to configure.
        app_config: Application configuration to apply.

    Raises:
        ConfigurationError: If configuration fails.
    """
    try:
        # Note: FetcherRecipe doesn't have app_config or storage attributes
        # These are handled at the Fetcher level through the FetchRunContext
        # We just need to configure the components with the app_config

        # Configure bundle locators
        for i, locator in enumerate(ctx.bundle_locators):
            try:
                _configure_component_with_app_config(
                    locator, app_config, f"locator_{i}"
                )
            except (AttributeError, TypeError, ValueError) as e:
                logger.warning(
                    "Failed to configure bundle locator",
                    locator_index=i,
                    locator_type=type(locator).__name__,
                    error=str(e),
                )

        # Configure bundle loader
        if ctx.bundle_loader:
            try:
                _configure_component_with_app_config(
                    ctx.bundle_loader, app_config, "bundle_loader"
                )
            except (AttributeError, TypeError, ValueError) as e:
                logger.warning(
                    "Failed to configure bundle loader",
                    loader_type=type(ctx.bundle_loader).__name__,
                    error=str(e),
                )

    except Exception as e:
        error_message = "Failed to configure recipe with app_config"
        raise ConfigurationError(error_message, "recipe_configuration") from e


def _configure_component_with_app_config(
    component: object, app_config: "FetcherConfig", component_name: str
) -> None:
    """Configure a single component with app_config.

    Args:
        component: The component to configure.
        app_config: Application configuration to apply.
        component_name: Name of the component for logging.
    """
    # Set app_config if component supports it
    if hasattr(component, "set_app_config"):
        try:
            component.set_app_config(app_config)
            logger.debug("Set app_config on component", component_name=component_name)
        except (AttributeError, TypeError, ValueError) as e:
            logger.warning(
                "Failed to set app_config on component",
                component_name=component_name,
                error=str(e),
            )

    # Update credential providers in HTTP managers
    if hasattr(component, "http_manager") and hasattr(
        component.http_manager, "update_credential_provider"
    ):
        try:
            component.http_manager.update_credential_provider(
                app_config.credential_provider
            )
            logger.debug(
                "Updated HTTP manager credential provider",
                component_name=component_name,
            )
        except (AttributeError, TypeError, ValueError) as e:
            logger.warning(
                "Failed to update HTTP manager credential provider",
                component_name=component_name,
                error=str(e),
            )

    # Update credential providers in SFTP managers
    if hasattr(component, "sftp_manager") and hasattr(
        component.sftp_manager, "update_credential_provider"
    ):
        try:
            component.sftp_manager.update_credential_provider(
                app_config.credential_provider
            )
            logger.debug(
                "Updated SFTP manager credential provider",
                component_name=component_name,
            )
        except (AttributeError, TypeError, ValueError) as e:
            logger.warning(
                "Failed to update SFTP manager credential provider",
                component_name=component_name,
                error=str(e),
            )


def list_recipes() -> list[str]:
    """List all available recipes."""
    return list(_RECIPES.keys())


def get_recipe_setup_function(recipe_name: str) -> Callable[[], FetcherRecipe]:
    """Get the setup function for a recipe.

    Args:
        recipe_name: Name of the recipe to get setup function for.

    Returns:
        The setup function for the recipe.

    Raises:
        ConfigurationError: If recipe is not found.
    """
    if recipe_name not in _RECIPES:
        error_message = "Recipe not found"
        raise ConfigurationError(error_message, "recipe_registry")
    return _RECIPES[recipe_name]
