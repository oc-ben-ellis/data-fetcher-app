"""HTTP protocol manager and connection handling.

This module provides the HTTPManager class for managing HTTP connections,
including rate limiting, retry logic, and connection pooling with support
for multiple connection pools based on configuration.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

import httpx

from data_fetcher_core.protocol_config import HttpProtocolConfig
from data_fetcher_core.utils.retry import create_retry_engine

if TYPE_CHECKING:
    from data_fetcher_core.config_factory import FetcherConfig


@dataclass
class HttpConnectionPool:
    """HTTP connection pool for a specific configuration."""

    config: HttpProtocolConfig
    _last_request_time: float = 0.0
    _rate_limit_lock: asyncio.Lock | None = None
    _retry_engine: Any = None

    def __post_init__(self) -> None:
        """Initialize the connection pool."""
        if self._rate_limit_lock is None:
            self._rate_limit_lock = asyncio.Lock()

        if self._retry_engine is None:
            self._retry_engine = create_retry_engine(
                max_retries=self.config.max_retries
            )

    async def request(
        self, app_config: "FetcherConfig", method: str, url: str, **kwargs: object
    ) -> httpx.Response:
        """Make an HTTP request with rate limiting and authentication."""
        async with self._rate_limit_lock:  # type: ignore[union-attr]
            # Rate limiting
            now = time.time()
            time_since_last = now - self._last_request_time
            min_interval = 1.0 / self.config.rate_limit_requests_per_second

            if time_since_last < min_interval:
                await asyncio.sleep(min_interval - time_since_last)

            self._last_request_time = time.time()

        # Make the request with retry logic
        async def _make_request() -> httpx.Response:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                # Ensure we have valid headers to unpack
                request_headers = kwargs.get("headers", {}) or {}
                default_headers = self.config.default_headers or {}
                headers = {**default_headers, **request_headers}  # type: ignore[dict-item]

                # Apply authentication
                if self.config.authentication_mechanism:
                    headers = (
                        await self.config.authentication_mechanism.authenticate_request(
                            headers, app_config.credential_provider
                        )
                    )
                kwargs["headers"] = headers

                return await client.request(method, url, **kwargs)  # type: ignore[arg-type]

        # Execute with retry logic using the unified retry engine
        result = await self._retry_engine.execute_with_retry_async(_make_request)
        # Return the result with explicit typing for mypy
        return cast("httpx.Response", result)


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

    async def request(
        self,
        config: HttpProtocolConfig,
        app_config: "FetcherConfig",
        method: str,
        url: str,
        **kwargs: object,
    ) -> httpx.Response:
        """Make an HTTP request using the specified configuration.

        Args:
            config: The HTTP protocol configuration to use.
            app_config: The application configuration containing credential provider.
            method: HTTP method (GET, POST, etc.).
            url: The URL to request.
            **kwargs: Additional arguments to pass to the HTTP request.

        Returns:
            The HTTP response.
        """
        pool = self._get_or_create_pool(config)
        return await pool.request(app_config, method, url, **kwargs)
