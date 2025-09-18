import asyncio
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

import httpx

from data_fetcher_core.retry import create_retry_engine
from data_fetcher_http.http_config import HttpProtocolConfig
from data_fetcher_http.http_connection import HttpConnection

if TYPE_CHECKING:
    from data_fetcher_app.app_config import FetcherConfig


@dataclass
class HttpConnectionPool:
    """HTTP connection pool for a specific configuration."""

    config: HttpProtocolConfig
    _last_request_time: float = 0.0
    _rate_limit_lock: asyncio.Lock | None = None
    _retry_engine: Any = None
    _idle: asyncio.Queue[httpx.AsyncClient] | None = None
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

    async def _create_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=self.config.timeout, base_url=self.config.base_url or None
        )

    async def _apply_auth_headers(
        self,
        app_config: "FetcherConfig",
        request_headers: dict[str, str],
    ) -> dict[str, str]:
        headers: dict[str, str] = {
            **(self.config.default_headers or {}),
            **request_headers,
        }
        if self.config.authentication_mechanism:
            headers = await self.config.authentication_mechanism.authenticate_request(
                headers, app_config.credential_provider
            )
        return headers

    async def request_with_existing(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        **kwargs: object,
    ) -> httpx.Response:
        async def _make_request() -> httpx.Response:
            async with self._rate_limit_lock:  # type: ignore[union-attr]
                now = time.time()
                time_since_last = now - self._last_request_time
                min_interval = 1.0 / self.config.rate_limit_requests_per_second
                if time_since_last < min_interval:
                    await asyncio.sleep(min_interval - time_since_last)
                self._last_request_time = time.time()

            return await client.request(method, url, **kwargs)  # type: ignore[arg-type]

        result = await self._retry_engine.execute_with_retry_async(_make_request)
        return cast("httpx.Response", result)

    async def acquire(self, app_config: "FetcherConfig") -> HttpConnection:
        while True:
            try:
                client = self._idle.get_nowait()  # type: ignore[union-attr]
            except asyncio.QueueEmpty:
                client = None  # type: ignore[assignment]

            if client is not None:
                if client.is_closed:
                    self._total = max(0, self._total - 1)
                    continue
                return HttpConnection(self, client, app_config)

            if self._total < self.config.pool_max_size:
                client = await self._create_client()
                self._total += 1
                return HttpConnection(self, client, app_config)

            client = await self._idle.get()  # type: ignore[union-attr]
            if client.is_closed:
                self._total = max(0, self._total - 1)
                continue
            return HttpConnection(self, client, app_config)

    async def release(self, client: httpx.AsyncClient) -> None:
        if client.is_closed:
            self._total = max(0, self._total - 1)
            return
        await self._idle.put(client)  # type: ignore[union-attr]

    async def close(self) -> None:
        try:
            while True:
                client = self._idle.get_nowait()  # type: ignore[union-attr]
                try:
                    await client.aclose()
                finally:
                    self._total = max(0, self._total - 1)
        except asyncio.QueueEmpty:
            pass
