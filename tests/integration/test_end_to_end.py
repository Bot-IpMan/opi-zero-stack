import pytest

httpx = pytest.importorskip("httpx")
AsyncClient = httpx.AsyncClient
ASGITransport = httpx.ASGITransport

if getattr(httpx, "__is_stub__", False):
    pytest.skip("httpx stubbed; integration tests skipped", allow_module_level=True)


@pytest.mark.asyncio
async def test_decision_and_emergency_flow(patched_main, mock_data):
    main, fake_serial, _ = patched_main

    # Inject deterministic sensor data and decision response
    main.ctx.sensors.read_all = lambda: mock_data["sensors"]  # type: ignore[assignment]
    async def fake_decision(_):
        return mock_data["decision"]
    main.ctx.pc_client.request_decision = fake_decision  # type: ignore[assignment]

    async with AsyncClient(
        transport=ASGITransport(app=main.app), base_url="http://test"
    ) as client:
        decide_resp = await client.post("/decide")
        assert decide_resp.status_code == 200
        body = decide_resp.json()
        assert body["sensors"]["environment"]["humidity"] == 48.2
        assert body["decision"] == mock_data["decision"]

        emergency_resp = await client.post("/emergency_stop")
        assert emergency_resp.status_code == 200
        assert main.ctx.emergency is True

    fake_serial.write.assert_called_with(b'{"cmd": "emergency_stop"}\n')
    assert main.ctx.actuators.states() == {"light": False, "fan": False, "pump": False}
