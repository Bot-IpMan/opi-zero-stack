import json
from typing import Any, Callable, Optional
import inspect


__is_stub__ = True


class HTTPStatusError(Exception):
    pass


class Request:
    def __init__(self, url: str, json: Optional[dict] = None):
        self.url = url
        self._json = json or {}

    def json(self) -> dict:
        return self._json


class Response:
    def __init__(self, status_code: int, json: Optional[dict] = None):
        self.status_code = status_code
        self._json = json or {}

    def json(self) -> dict:
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise HTTPStatusError(f"Status code {self.status_code}")


class MockTransport:
    def __init__(self, handler: Callable[[Request], Response]):
        self.handler = handler

    def __call__(self, request: Request) -> Response:
        return self.handler(request)


class ASGITransport:
    def __init__(self, app=None):
        self.app = app


class AsyncClient:
    def __init__(self, *, transport: Optional[MockTransport] = None, timeout: int = 60):
        self.transport = transport
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def aclose(self):
        return None

    async def post(self, url: str, json: Optional[dict] = None):  # noqa: A002
        if not self.transport:
            raise RuntimeError("No transport provided for AsyncClient")
        request = Request(url, json=json)
        response = self.transport(request)
        if inspect.isawaitable(response):
            response = await response
        return response


__all__ = [
    "AsyncClient",
    "ASGITransport",
    "HTTPStatusError",
    "MockTransport",
    "Request",
    "Response",
]
