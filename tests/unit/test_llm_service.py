import importlib.util
from pathlib import Path

import pytest

httpx = pytest.importorskip("httpx")

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "pc-llm-service" / "llm_service.py"

spec = importlib.util.spec_from_file_location("llm_service", MODULE_PATH)
llm_service = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(llm_service)  # type: ignore[arg-type]


class DummyAsyncClient:
    def __init__(self, response_json):
        self._client = httpx.AsyncClient(transport=httpx.MockTransport(self._handler))
        self.response_json = response_json

    def _handler(self, request: httpx.Request):
        return httpx.Response(200, json=self.response_json)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self._client.aclose()

    async def post(self, url: str, json=None):  # noqa: A002
        return await self._client.post(url, json=json)


@pytest.mark.asyncio
async def test_chat_returns_response(monkeypatch):
    service = llm_service.LLMService(base_url="http://llm", model="test-model")
    dummy_client = DummyAsyncClient({"response": "ok"})
    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout=60: dummy_client)

    result = await service.chat("hello")
    assert result == "ok"


@pytest.mark.asyncio
async def test_summarize_wraps_prompt(monkeypatch):
    captured_payload = {}

    async def handler(request: httpx.Request):
        captured_payload.update(request.json())
        return httpx.Response(200, json={"response": "summary"})

    transport = httpx.MockTransport(handler)

    class WrapperClient:
        def __init__(self):
            self.client = httpx.AsyncClient(transport=transport)

        async def __aenter__(self):
            return self.client

        async def __aexit__(self, exc_type, exc, tb):
            await self.client.aclose()

    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout=60: WrapperClient())
    service = llm_service.LLMService(base_url="http://llm", model="test-model")

    summary = await service.summarize("data")
    assert summary == "summary"
    assert "Стисло підсумуй" in captured_payload.get("prompt", "")
