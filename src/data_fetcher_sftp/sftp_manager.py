"""SFTP protocol manager and connection handling.

This module provides the SFTPManager class for managing SFTP connections,
including authentication, file operations, and connection management with
support for multiple connection pools based on configuration.
"""

from typing import TYPE_CHECKING

from data_fetcher_sftp.sftp_config import SftpProtocolConfig
from data_fetcher_sftp.sftp_credentials import SftpCredentialsWrapper
from data_fetcher_sftp.sftp_pool import SftpConnection, SftpConnectionPool

if TYPE_CHECKING:
    from data_fetcher_core.core import FetchRunContext


# SftpConnectionPool moved to data_fetcher_sftp.sftp_pool


class SftpManager:
    """SFTP connection manager with support for multiple connection pools."""

    def __init__(self) -> None:
        """Initialize the SFTP manager with empty connection pools."""
        self._connection_pools: dict[str, SftpConnectionPool] = {}

    def _get_or_create_pool(
        self,
        config: SftpProtocolConfig,
    ) -> SftpConnectionPool:
        """Get or create a connection pool for the given configuration.

        Args:
            config: The SFTP protocol configuration.

        Returns:
            The connection pool for this configuration.
        """
        connection_key = config.get_connection_key()

        if connection_key not in self._connection_pools:
            self._connection_pools[connection_key] = SftpConnectionPool(
                config=config,
            )

        return self._connection_pools[connection_key]

    async def get_connection(
        self,
        config: SftpProtocolConfig,
        context: "FetchRunContext",
    ) -> SftpConnection:
        """Acquire an SFTP connection wrapper for the given configuration.

        Callers should release the connection when done, or use as an async
        context manager: `async with await manager.get_connection(...) as conn:`
        """
        pool = self._get_or_create_pool(config)
        credentials_provider = SftpCredentialsWrapper(
            config.config_name,
            context.app_config.credential_provider,  # type: ignore[union-attr]
        )
        return await pool.acquire(
            context.app_config,  # type: ignore[arg-type]
            credentials_provider,
        )

    async def close_all(self) -> None:
        """Close all SFTP connections."""
        for pool in self._connection_pools.values():
            await pool.close()

    async def reset_all_connections(self) -> None:
        """Reset all SFTP connections."""
        for pool in self._connection_pools.values():
            await pool.reset_connection()
