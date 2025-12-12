import asyncio
import importlib
import json
from pathlib import Path
from typing import Any, Dict, Tuple
from unittest.mock import MagicMock

import pytest

from app import pc_client as pc_client_module


class DummyPCClient:
    """Lightweight PC client used to avoid real network calls in tests."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.sent_status: list[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        self.decisions: list[Dict[str, Any]] = []

    async def send_status(self, sensors: Dict[str, Any], actuators: Dict[str, Any]):
        self.sent_status.append((sensors, actuators))

    async def request_decision(self, sensors: Dict[str, Any]):
        decision = {"action": "monitor", "sensors": sensors}
        self.decisions.append(decision)
        return decision


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def mock_data() -> Dict[str, Any]:
    data_path = Path(__file__).parent / "fixtures" / "mock_data.json"
    with data_path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


@pytest.fixture()
def patched_main(monkeypatch):
    import serial
    import paho.mqtt.client as mqtt

    fake_serial = MagicMock()
    fake_serial.is_open = True
    fake_serial.readline.return_value = b"ok\n"

    def fake_serial_factory(*args, **kwargs):
        return fake_serial

    fake_mqtt_client = MagicMock()
    fake_mqtt_client.is_connected.return_value = True

    monkeypatch.setattr(serial, "Serial", fake_serial_factory)
    monkeypatch.setattr(mqtt, "Client", lambda *args, **kwargs: fake_mqtt_client)
    monkeypatch.setattr(pc_client_module, "PCClient", DummyPCClient)

    import app.main as main

    importlib.reload(main)
    return main, fake_serial, fake_mqtt_client
