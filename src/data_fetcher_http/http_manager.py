"""HTTP protocol manager and connection handling.

This module provides the HTTPManager class for managing HTTP connections,
including rate limiting, retry logic, and connection pooling with support
for multiple connection pools based on configuration.
"""

from typing import TYPE_CHECKING

from data_fetcher_http.http_config import HttpProtocolConfig
from data_fetcher_http.http_connection import HttpConnection
from data_fetcher_http.http_pool import HttpConnectionPool

if TYPE_CHECKING:
    from data_fetcher_app.app_config import FetcherConfig


# HttpConnection and HttpConnectionPool moved to dedicated modules


class HttpManager:
    """HTTP connection manager with support for multiple connection pools."""

    def __init__(self) -> None:
        """Initialize the HTTP manager with empty connection pools."""
        self._connection_pools: dict[str, HttpConnectionPool] = {}

    def _get_or_create_pool(self, config: HttpProtocolConfig) -> HttpConnectionPool:
        """Get or create a connection pool for the given configuration.

        Args:
            config: The HTTP protocol configuration.

        Returns:
            The connection pool for this configuration.
        """
        connection_key = config.get_connection_key()

        if connection_key not in self._connection_pools:
            self._connection_pools[connection_key] = HttpConnectionPool(config=config)

        return self._connection_pools[connection_key]

    async def get_connection(
        self,
        config: HttpProtocolConfig,
        app_config: "FetcherConfig",
    ) -> HttpConnection:
        pool = self._get_or_create_pool(config)
        return await pool.acquire(app_config)

    async def close_all(self) -> None:
        for pool in self._connection_pools.values():
            await pool.close()

    async def reset_all_connections(self) -> None:
        await self.close_all()
