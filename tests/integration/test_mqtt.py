import importlib.util
import json
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "pc-llm-service" / "mqtt_client.py"

spec = importlib.util.spec_from_file_location("mqtt_client", MODULE_PATH)
mqtt_client_module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mqtt_client_module)  # type: ignore[arg-type]
MQTTClient = mqtt_client_module.MQTTClient


def test_mqtt_publish_and_loop(monkeypatch):
    fake_client = MagicMock()

    import paho.mqtt.client as mqtt

    monkeypatch.setattr(mqtt, "Client", lambda *args, **kwargs: fake_client)

    client = MQTTClient(host="localhost", port=1883, topic_prefix="tests")
    client.loop_background()
    client.publish_state("status", {"ok": True})

    fake_client.loop_start.assert_called_once()
    fake_client.publish.assert_called_once_with("tests/status", json.dumps({"ok": True}), qos=0)
