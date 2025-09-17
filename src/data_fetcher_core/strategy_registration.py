"""Strategy registration for the fetcher service.

This module provides a centralized way to register all strategy factories
with the StrategyFactoryRegistry, enabling YAML-based configuration loading.
"""

from oc_pipeline_bus.strategy_registry import StrategyFactoryRegistry

from data_fetcher_core.strategies.filter_factories import register_filter_strategies
from data_fetcher_http_api.fr_strategy_factories import register_fr_strategies
from data_fetcher_http_api.strategy_factories import register_http_strategies
from data_fetcher_sftp.strategy_factories import register_sftp_strategies


def create_strategy_registry(
    sftp_manager: object, http_manager: object
) -> StrategyFactoryRegistry:
    """Create and register all available strategy factories with a new registry.

    Returns:
        Registry with all strategies registered
    """
    registry = StrategyFactoryRegistry()

    # Register all strategy types
    register_sftp_strategies(registry, sftp_manager=sftp_manager)
    register_http_strategies(registry, http_manager=http_manager)
    register_fr_strategies(registry, http_manager=http_manager)
    register_filter_strategies(registry)

    return registry
