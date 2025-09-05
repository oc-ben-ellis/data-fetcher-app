"""HTTP protocol manager and connection handling.

This module provides the HTTPManager class for managing HTTP connections,
including rate limiting, retry logic, and connection pooling.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import cast

import httpx

from data_fetcher_core.utils.retry import create_retry_engine
from data_fetcher_sftp.authentication import (
    AuthenticationMechanism,
    NoAuthenticationMechanism,
)


@dataclass
class HttpManager:
    """HTTP connection manager with rate limiting and scheduling."""

    timeout: float = 30.0
    default_headers: dict[str, str] | None = None
    rate_limit_requests_per_second: float = 10.0
    max_retries: int = 3
    authentication_mechanism: AuthenticationMechanism | None = None

    def __post_init__(self) -> None:
        """Initialize the HTTP manager with default values and internal state."""
        if self.default_headers is None:
            self.default_headers = {"User-Agent": "OCFetcher/1.0"}

        if self.authentication_mechanism is None:
            self.authentication_mechanism = NoAuthenticationMechanism()

        self._last_request_time = 0.0
        self._rate_limit_lock = asyncio.Lock()

        # Create retry engine for HTTP operations with configured max_retries
        self._retry_engine = create_retry_engine(max_retries=self.max_retries)

    async def request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
        """Make an HTTP request with rate limiting and authentication."""
        async with self._rate_limit_lock:
            # Rate limiting
            now = time.time()
            time_since_last = now - self._last_request_time
            min_interval = 1.0 / self.rate_limit_requests_per_second

            if time_since_last < min_interval:
                await asyncio.sleep(min_interval - time_since_last)

            self._last_request_time = time.time()

        # Make the request with retry logic
        async def _make_request() -> httpx.Response:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Ensure we have valid headers to unpack
                request_headers = kwargs.get("headers", {}) or {}
                default_headers = self.default_headers or {}
                headers = {**default_headers, **request_headers}  # type: ignore[dict-item]

                # Apply authentication
                if self.authentication_mechanism:
                    headers = await self.authentication_mechanism.authenticate_request(
                        headers
                    )
                kwargs["headers"] = headers

                return await client.request(method, url, **kwargs)  # type: ignore[arg-type]

        # Execute with retry logic using the unified retry engine
        result = await self._retry_engine.execute_with_retry_async(_make_request)
        # Return the result with explicit typing for mypy
        return cast("httpx.Response", result)
