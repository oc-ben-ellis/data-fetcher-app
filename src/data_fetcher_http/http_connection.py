from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from data_fetcher_app.app_config import FetcherConfig
    from data_fetcher_http.http_pool import HttpConnectionPool


class HttpConnection:
    """A leased HTTP connection wrapper using httpx.AsyncClient."""

    def __init__(
        self,
        pool: "HttpConnectionPool",
        client: httpx.AsyncClient,
        app_config: "FetcherConfig",
    ) -> None:
        self._pool = pool
        self._client = client
        self._app_config = app_config

    async def __aenter__(self) -> "HttpConnection":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        await self.release()

    async def release(self) -> None:
        await self._pool.release(self._client)

    async def request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
        request_headers = kwargs.get("headers", {}) or {}
        headers = await self._pool._apply_auth_headers(
            self._app_config, request_headers
        )  # type: ignore[attr-defined]
        kwargs["headers"] = headers
        return await self._pool.request_with_existing(
            self._client, method, url, **kwargs
        )

    # Convenience methods
    async def get(self, url: str, **kwargs: object) -> httpx.Response:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: object) -> httpx.Response:
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs: object) -> httpx.Response:
        return await self.request("PUT", url, **kwargs)

    async def delete(self, url: str, **kwargs: object) -> httpx.Response:
        return await self.request("DELETE", url, **kwargs)
