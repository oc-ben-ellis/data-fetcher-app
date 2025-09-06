"""SFTP protocol manager and connection handling.

This module provides the SFTPManager class for managing SFTP connections,
including authentication, file operations, and connection management with
support for multiple connection pools based on configuration.
"""

import asyncio
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

import pysftp
import structlog

from data_fetcher_core.protocol_config import SftpProtocolConfig
from data_fetcher_core.utils.retry import create_retry_engine
from data_fetcher_sftp.sftp_credentials import SftpCredentialsWrapper

if TYPE_CHECKING:
    from data_fetcher_core.config_factory import FetcherConfig
    from data_fetcher_core.core import FetchRunContext

# Get logger for this module
logger = structlog.get_logger(__name__)


@dataclass
class ScheduledDailyGate:
    """Gate that only allows execution at a specific time of day."""

    time_of_day: str  # Format: "HH:MM"
    tz: str = "UTC"
    startup_skip_if_already_today: bool = True

    def __post_init__(self) -> None:
        """Initialize the scheduled daily gate state."""
        self._last_execution_date: object = None

    async def wait_if_needed(self) -> None:
        """Wait until the next scheduled time if needed."""
        now = datetime.now(UTC)
        today = now.date()

        # Check if we already executed today
        if self.startup_skip_if_already_today and self._last_execution_date == today:
            return

        # Parse target time
        hour, minute = map(int, self.time_of_day.split(":"))
        target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # If target time has passed today, wait until tomorrow
        if target_time <= now:
            target_time = target_time.replace(day=target_time.day + 1)

        # Wait until target time
        wait_seconds = (target_time - now).total_seconds()
        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)

        self._last_execution_date = today


@dataclass
class OncePerIntervalGate:
    """Gate that only allows execution once per interval."""

    interval_seconds: int
    jitter_seconds: int = 0

    def __post_init__(self) -> None:
        """Initialize the once per interval gate state."""
        self._last_execution_time = 0.0

    async def wait_if_needed(self) -> None:
        """Wait if the interval hasn't passed since last execution."""
        now = time.time()
        time_since_last = now - self._last_execution_time

        if time_since_last < self.interval_seconds:
            wait_time = self.interval_seconds - time_since_last

            # Add jitter
            if self.jitter_seconds > 0:
                import random  # noqa: PLC0415

                jitter = random.uniform(0, self.jitter_seconds)  # noqa: S311
                wait_time += jitter

            await asyncio.sleep(wait_time)

        self._last_execution_time = time.time()


@dataclass
class SftpConnectionPool:
    """SFTP connection pool for a specific configuration."""

    config: SftpProtocolConfig
    daily_gate: ScheduledDailyGate | None = None
    interval_gate: OncePerIntervalGate | None = None
    _last_request_time: float = 0.0
    _rate_limit_lock: asyncio.Lock | None = None
    _connection: pysftp.Connection | None = None
    _retry_engine: Any = None

    def __post_init__(self) -> None:
        """Initialize the connection pool."""
        if self._rate_limit_lock is None:
            self._rate_limit_lock = asyncio.Lock()

        if self._retry_engine is None:
            self._retry_engine = create_retry_engine(
                max_retries=self.config.max_retries
            )

    async def get_connection(
        self,
        app_config: "FetcherConfig",
        credentials_provider: "SftpCredentialsWrapper",
    ) -> pysftp.Connection:
        """Get or create SFTP connection with retry logic."""

        async def _create_connection() -> pysftp.Connection:
            if self._connection is None:
                # Update credentials provider with app_config
                credentials_provider.update_credential_provider(
                    app_config.credential_provider
                )
                credentials = await credentials_provider.get_credentials()

                # Configure connection options to allow unknown hosts
                cnopts = pysftp.CnOpts()
                cnopts.hostkeys = None  # Disable host key checking for testing

                self._connection = pysftp.Connection(
                    host=credentials.host,
                    username=credentials.username,
                    password=credentials.password,
                    port=credentials.port,
                    cnopts=cnopts,
                )
            return self._connection

        # Execute with retry logic using the unified retry engine
        result = await self._retry_engine.execute_with_retry_async(_create_connection)
        return cast("pysftp.Connection", result)

    async def wait_for_gates(self) -> None:
        """Wait for all gates to allow execution."""
        if self.daily_gate:
            await self.daily_gate.wait_if_needed()

        if self.interval_gate:
            await self.interval_gate.wait_if_needed()

    async def request(
        self,
        app_config: "FetcherConfig",
        credentials_provider: "SftpCredentialsWrapper",
        operation: str,
        *args: object,
        **kwargs: object,
    ) -> object:
        """Make an SFTP request with rate limiting and retry logic."""

        async def _make_request() -> object:
            # Wait for gates
            await self.wait_for_gates()

            # Rate limiting
            async with self._rate_limit_lock:  # type: ignore[union-attr]
                now = time.time()
                time_since_last = now - self._last_request_time
                min_interval = 1.0 / self.config.rate_limit_requests_per_second

                if time_since_last < min_interval:
                    await asyncio.sleep(min_interval - time_since_last)

                # Update last request time after any sleep
                self._last_request_time = time.time()

            # Execute operation
            conn = await self.get_connection(app_config, credentials_provider)
            method = getattr(conn, operation)
            return method(*args, **kwargs)

        # Execute with retry logic using the unified retry engine
        return await self._retry_engine.execute_with_retry_async(_make_request)

    async def close(self) -> None:
        """Close the SFTP connection with retry logic."""

        async def _close_connection() -> None:
            if self._connection:
                self._connection.close()
                self._connection = None

        # Execute with retry logic using the unified retry engine
        await self._retry_engine.execute_with_retry_async(_close_connection)

    async def reset_connection(self) -> None:
        """Reset the SFTP connection, useful after connection errors."""
        if self._connection:
            try:
                self._connection.close()
            except Exception as e:
                # Ignore errors during close
                logger.exception(
                    "Error closing SFTP connection",
                    error=str(e),
                )
            finally:
                self._connection = None

    async def test_connection(
        self,
        app_config: "FetcherConfig",
        credentials_provider: "SftpCredentialsWrapper",
    ) -> bool:
        """Test the SFTP connection with retry logic.

        Returns:
            True if connection is working, False otherwise.
        """

        async def _test_connection() -> bool:
            try:
                conn = await self.get_connection(app_config, credentials_provider)
                # Try a simple operation to test the connection
                _ = conn.pwd  # Test connection by accessing pwd attribute
            except Exception as e:
                logger.exception(
                    "Error testing SFTP connection",
                    error=str(e),
                )
                return False
            else:
                return True

        # Execute with retry logic using the unified retry engine
        result = await self._retry_engine.execute_with_retry_async(_test_connection)
        return cast("bool", result)


class SftpManager:
    """SFTP connection manager with support for multiple connection pools."""

    def __init__(self) -> None:
        """Initialize the SFTP manager with empty connection pools."""
        self._connection_pools: dict[str, SftpConnectionPool] = {}

    def _get_or_create_pool(
        self,
        config: SftpProtocolConfig,
        daily_gate: ScheduledDailyGate | None = None,
        interval_gate: OncePerIntervalGate | None = None,
    ) -> SftpConnectionPool:
        """Get or create a connection pool for the given configuration.

        Args:
            config: The SFTP protocol configuration.
            daily_gate: Optional daily scheduling gate.
            interval_gate: Optional interval scheduling gate.

        Returns:
            The connection pool for this configuration.
        """
        connection_key = config.get_connection_key()

        if connection_key not in self._connection_pools:
            self._connection_pools[connection_key] = SftpConnectionPool(
                config=config,
                daily_gate=daily_gate,
                interval_gate=interval_gate,
            )

        return self._connection_pools[connection_key]

    async def close_all(self) -> None:
        """Close all SFTP connections."""
        for pool in self._connection_pools.values():
            await pool.close()

    async def reset_all_connections(self) -> None:
        """Reset all SFTP connections."""
        for pool in self._connection_pools.values():
            await pool.reset_connection()

    # Direct SFTP operation methods
    async def listdir(
        self,
        config: SftpProtocolConfig,
        context: "FetchRunContext",
        path: str,
        daily_gate: ScheduledDailyGate | None = None,
        interval_gate: OncePerIntervalGate | None = None,
    ) -> list[str]:
        """List directory contents."""
        pool = self._get_or_create_pool(config, daily_gate, interval_gate)
        credentials_provider = SftpCredentialsWrapper(
            config.config_name,
            context.app_config.credential_provider,  # type: ignore[union-attr]
        )
        return await pool.request(  # type: ignore[return-value]
            context.app_config,  # type: ignore[arg-type]
            credentials_provider,
            "listdir",
            path,
        )

    async def stat(
        self,
        config: SftpProtocolConfig,
        context: "FetchRunContext",
        path: str,
        daily_gate: ScheduledDailyGate | None = None,
        interval_gate: OncePerIntervalGate | None = None,
    ) -> os.stat_result:
        """Get file/directory statistics."""
        pool = self._get_or_create_pool(config, daily_gate, interval_gate)
        credentials_provider = SftpCredentialsWrapper(
            config.config_name,
            context.app_config.credential_provider,  # type: ignore[union-attr]
        )
        return await pool.request(  # type: ignore[return-value]
            context.app_config,  # type: ignore[arg-type]
            credentials_provider,
            "stat",
            path,
        )

    async def open(
        self,
        config: SftpProtocolConfig,
        context: "FetchRunContext",
        path: str,
        mode: str = "r",
        daily_gate: ScheduledDailyGate | None = None,
        interval_gate: OncePerIntervalGate | None = None,
    ) -> object:
        """Open a file for reading/writing."""
        pool = self._get_or_create_pool(config, daily_gate, interval_gate)
        credentials_provider = SftpCredentialsWrapper(
            config.config_name,
            context.app_config.credential_provider,  # type: ignore[union-attr]
        )
        return await pool.request(
            context.app_config,  # type: ignore[arg-type]
            credentials_provider,
            "open",
            path,
            mode,
        )

    async def exists(
        self,
        config: SftpProtocolConfig,
        context: "FetchRunContext",
        path: str,
        daily_gate: ScheduledDailyGate | None = None,
        interval_gate: OncePerIntervalGate | None = None,
    ) -> bool:
        """Check if file/directory exists."""
        pool = self._get_or_create_pool(config, daily_gate, interval_gate)
        credentials_provider = SftpCredentialsWrapper(
            config.config_name,
            context.app_config.credential_provider,  # type: ignore[union-attr]
        )
        return await pool.request(  # type: ignore[return-value]
            context.app_config,  # type: ignore[arg-type]
            credentials_provider,
            "exists",
            path,
        )

    async def isdir(
        self,
        config: SftpProtocolConfig,
        context: "FetchRunContext",
        path: str,
        daily_gate: ScheduledDailyGate | None = None,
        interval_gate: OncePerIntervalGate | None = None,
    ) -> bool:
        """Check if path is a directory."""
        pool = self._get_or_create_pool(config, daily_gate, interval_gate)
        credentials_provider = SftpCredentialsWrapper(
            config.config_name,
            context.app_config.credential_provider,  # type: ignore[union-attr]
        )
        return await pool.request(  # type: ignore[return-value]
            context.app_config,  # type: ignore[arg-type]
            credentials_provider,
            "isdir",
            path,
        )

    async def isfile(
        self,
        config: SftpProtocolConfig,
        context: "FetchRunContext",
        path: str,
        daily_gate: ScheduledDailyGate | None = None,
        interval_gate: OncePerIntervalGate | None = None,
    ) -> bool:
        """Check if path is a file."""
        pool = self._get_or_create_pool(config, daily_gate, interval_gate)
        credentials_provider = SftpCredentialsWrapper(
            config.config_name,
            context.app_config.credential_provider,  # type: ignore[union-attr]
        )
        return await pool.request(  # type: ignore[return-value]
            context.app_config,  # type: ignore[arg-type]
            credentials_provider,
            "isfile",
            path,
        )
