import json

import pytest

httpx = pytest.importorskip("httpx")
AsyncClient = httpx.AsyncClient
ASGITransport = httpx.ASGITransport

if getattr(httpx, "__is_stub__", False):
    pytest.skip("httpx stubbed; integration tests skipped", allow_module_level=True)


@pytest.mark.asyncio
async def test_arm_move_triggers_serial(patched_main):
    main, fake_serial, _ = patched_main

    async with AsyncClient(
        transport=ASGITransport(app=main.app), base_url="http://test"
    ) as client:
        resp = await client.post("/arm/move", json={"angles": [0.1, 0.2, 0.3]})
        assert resp.status_code == 200
        assert resp.json()["ack"] == "ok"

    fake_serial.write.assert_called_once()
    payload_sent = json.loads(fake_serial.write.call_args.args[0].decode().strip())
    assert payload_sent == {"cmd": "move_servo", "angles": [0.1, 0.2, 0.3]}
