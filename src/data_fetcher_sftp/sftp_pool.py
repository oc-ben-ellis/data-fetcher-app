"""SFTP connection pool implementation.

This module provides the `SftpConnectionPool` class which manages a pool of
SFTP connections with retry logic, rate limiting, and optional gating strategy,
along with an `SftpConnection` wrapper that callers can lease and release.
"""

import asyncio
import contextlib
import os
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

import pysftp
import structlog

from data_fetcher_core.retry import create_retry_engine
from data_fetcher_sftp.sftp_config import SftpProtocolConfig

if TYPE_CHECKING:
    from data_fetcher_app.app_config import FetcherConfig
    from data_fetcher_core.strategy_types import GatingStrategy
    from data_fetcher_sftp.sftp_credentials import SftpCredentialsWrapper


logger = structlog.get_logger(__name__)


class SftpConnection:
    """A leased SFTP connection wrapper.

    Delegates operations through the pool to enforce gating, rate limiting,
    and retry, and supports async context management for automatic release.
    """

    def __init__(self, pool: "SftpConnectionPool", inner: pysftp.Connection) -> None:
        self._pool = pool
        self._inner = inner

    async def release(self) -> None:
        await self._pool.release(self._inner)

    async def __aenter__(self) -> "SftpConnection":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        await self.release()

    async def request(self, operation: str, *args: object, **kwargs: object) -> object:
        return await self._pool.request_with_existing(
            self._inner, operation, *args, **kwargs
        )

    # Convenience methods
    async def listdir(self, path: str) -> list[str]:
        return cast("list[str]", await self.request("listdir", path))

    async def stat(self, path: str) -> os.stat_result:  # type: ignore[name-defined]
        return cast("os.stat_result", await self.request("stat", path))

    async def open(self, path: str, mode: str = "r") -> object:
        return await self.request("open", path, mode)

    async def exists(self, path: str) -> bool:
        return cast("bool", await self.request("exists", path))

    async def isdir(self, path: str) -> bool:
        return cast("bool", await self.request("isdir", path))

    async def isfile(self, path: str) -> bool:
        return cast("bool", await self.request("isfile", path))


@dataclass
class SftpConnectionPool:
    """SFTP connection pool for a specific configuration."""

    config: SftpProtocolConfig
    _last_request_time: float = 0.0
    _rate_limit_lock: asyncio.Lock | None = None
    _retry_engine: Any = None
    _idle: asyncio.Queue[pysftp.Connection] | None = None
    _total: int = 0

    def __post_init__(self) -> None:
        """Initialize the connection pool."""
        if self._rate_limit_lock is None:
            self._rate_limit_lock = asyncio.Lock()

        if self._retry_engine is None:
            self._retry_engine = create_retry_engine(
                max_retries=self.config.max_retries
            )
        if self._idle is None:
            self._idle = asyncio.Queue()

    async def _create_inner_connection(
        self,
        app_config: "FetcherConfig",
        credentials_provider: "SftpCredentialsWrapper",
    ) -> pysftp.Connection:
        async def _create() -> pysftp.Connection:
            # Update credentials provider with app_config
            credentials_provider.update_credential_provider(
                app_config.credential_provider
            )
            credentials = await credentials_provider.get_credentials()

            # Configure connection options to allow unknown hosts
            cnopts = pysftp.CnOpts()
            cnopts.hostkeys = None  # Disable host key checking for testing

            return pysftp.Connection(
                host=credentials.host,
                username=credentials.username,
                password=credentials.password,
                port=credentials.port,
                cnopts=cnopts,
            )

        result = await self._retry_engine.execute_with_retry_async(_create)
        return cast("pysftp.Connection", result)

    async def wait_for_gates(self) -> None:
        """Wait for configured gates to allow execution."""
        gate: GatingStrategy | None = getattr(self.config, "gating_strategy", None)
        if gate is not None:
            await gate.wait_if_needed()

    async def request(
        self,
        app_config: "FetcherConfig",
        credentials_provider: "SftpCredentialsWrapper",
        operation: str,
        *args: object,
        **kwargs: object,
    ) -> object:
        """Compatibility helper: acquire, perform operation, and release."""
        conn_wrapper = await self.acquire(app_config, credentials_provider)
        try:
            return await conn_wrapper.request(operation, *args, **kwargs)
        finally:
            await conn_wrapper.release()

    async def request_with_existing(
        self,
        inner: pysftp.Connection,
        operation: str,
        *args: object,
        **kwargs: object,
    ) -> object:
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

            method = getattr(inner, operation)
            return method(*args, **kwargs)

        return await self._retry_engine.execute_with_retry_async(_make_request)

    async def _health_check(self, inner: pysftp.Connection) -> bool:
        try:
            _ = inner.pwd  # access property to ensure connection is alive
        except Exception as e:  # noqa: BLE001
            logger.warning("SFTP connection health check failed", error=str(e))
            return False
        else:
            return True

    async def _ensure_baseline(
        self,
        inner: pysftp.Connection,
        app_config: "FetcherConfig",
        credentials_provider: "SftpCredentialsWrapper",
    ) -> pysftp.Connection:
        # If base_dir configured, ensure we're in it
        if self.config.base_dir:
            try:
                inner.chdir(self.config.base_dir)
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "Failed to chdir to base_dir; attempting to recreate connection",
                    base_dir=self.config.base_dir,
                    error=str(e),
                )
                with contextlib.suppress(Exception):
                    inner.close()
                # Recreate fresh connection
                inner = await self._create_inner_connection(
                    app_config, credentials_provider
                )
                if self.config.base_dir:
                    inner.chdir(self.config.base_dir)
        return inner

    async def acquire(
        self,
        app_config: "FetcherConfig",
        credentials_provider: "SftpCredentialsWrapper",
    ) -> SftpConnection:
        # Fast path: try idle queue first
        while True:
            try:
                inner = self._idle.get_nowait()  # type: ignore[union-attr]
            except asyncio.QueueEmpty:
                inner = None  # type: ignore[assignment]

            if inner is not None:
                healthy = await self._health_check(inner)
                if not healthy:
                    with contextlib.suppress(Exception):
                        inner.close()
                    self._total = max(0, self._total - 1)
                    continue
                inner = await self._ensure_baseline(
                    inner, app_config, credentials_provider
                )
                return SftpConnection(self, inner)

            # No idle connection available; create if under limit
            if self._total < self.config.pool_max_size:
                inner = await self._create_inner_connection(
                    app_config, credentials_provider
                )
                self._total += 1
                inner = await self._ensure_baseline(
                    inner, app_config, credentials_provider
                )
                return SftpConnection(self, inner)

            # At capacity; block until one is released
            inner = await self._idle.get()  # type: ignore[union-attr]
            healthy = await self._health_check(inner)
            if not healthy:
                with contextlib.suppress(Exception):
                    inner.close()
                self._total = max(0, self._total - 1)
                continue
            inner = await self._ensure_baseline(inner, app_config, credentials_provider)
            return SftpConnection(self, inner)

    async def release(self, inner: pysftp.Connection) -> None:
        # Cleanup to baseline and verify health before returning to queue
        ok = True
        if self.config.base_dir:
            try:
                inner.chdir(self.config.base_dir)
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to reset chdir on release", error=str(e))
                ok = False
        if ok:
            ok = await self._health_check(inner)

        if ok:
            await self._idle.put(inner)  # type: ignore[union-attr]
        else:
            with contextlib.suppress(Exception):
                inner.close()
            self._total = max(0, self._total - 1)

    async def close(self) -> None:
        """Close all idle SFTP connections with retry logic."""

        async def _close_all() -> None:
            try:
                # Drain queue
                while True:
                    inner = self._idle.get_nowait()  # type: ignore[union-attr]
                    try:
                        inner.close()
                    finally:
                        self._total = max(0, self._total - 1)
            except asyncio.QueueEmpty:
                pass

        await self._retry_engine.execute_with_retry_async(_close_all)

    async def reset_connection(self) -> None:
        """Reset the pool by closing all idle connections."""
        await self.close()

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
                conn = await self.acquire(app_config, credentials_provider)
                try:
                    _ = await conn.request("listdir", ".")
                finally:
                    await conn.release()
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
