import pytest

httpx = pytest.importorskip("httpx")
AsyncClient = httpx.AsyncClient
ASGITransport = httpx.ASGITransport


@pytest.mark.asyncio
async def test_device_control_and_cache(patched_main):
    main, _, _ = patched_main

    async with AsyncClient(
        transport=ASGITransport(app=main.app), base_url="http://test"
    ) as client:
        resp = await client.post("/devices/light", json={"on": True})
        assert resp.status_code == 200
        assert resp.json()["state"] is True

        resp = await client.post("/devices/fan", json={"on": False})
        assert resp.status_code == 200
        assert resp.json()["state"] is False

        cache_resp = await client.get("/cache")
        commands = cache_resp.json()
        assert any(cmd["name"] == "light" for cmd in commands)
        assert any(cmd["name"] == "fan" for cmd in commands)

        health_resp = await client.get("/healthz")
        assert health_resp.status_code == 200
        health = health_resp.json()
        assert health["mqtt"] is True
        assert health["serial"] is True
