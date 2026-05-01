from __future__ import annotations

from types import TracebackType

import httpx
from fastapi import FastAPI


class AsyncASGITestClient:
    """Small async ASGI client that avoids Starlette TestClient's thread portal."""

    def __init__(
        self,
        app: FastAPI,
        *,
        raise_app_exceptions: bool = True,
    ) -> None:
        self._app = app
        self._raise_app_exceptions = raise_app_exceptions
        self._lifespan = None
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "AsyncASGITestClient":
        self._lifespan = self._app.router.lifespan_context(self._app)
        await self._lifespan.__aenter__()
        transport = httpx.ASGITransport(
            app=self._app,
            raise_app_exceptions=self._raise_app_exceptions,
        )
        self._client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
        await self._client.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._client is not None:
            await self._client.__aexit__(exc_type, exc, traceback)
        if self._lifespan is not None:
            await self._lifespan.__aexit__(exc_type, exc, traceback)

    async def get(self, url: str, **kwargs) -> httpx.Response:
        return await self._request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        return await self._request("POST", url, **kwargs)

    async def patch(self, url: str, **kwargs) -> httpx.Response:
        return await self._request("PATCH", url, **kwargs)

    async def delete(self, url: str, **kwargs) -> httpx.Response:
        return await self._request("DELETE", url, **kwargs)

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        if self._client is None:
            raise RuntimeError("AsyncASGITestClient must be used as an async context manager.")
        return await self._client.request(method, url, **kwargs)
