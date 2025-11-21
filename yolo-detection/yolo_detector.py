"""YOLOv8n TFLite inference placeholder that publishes MQTT messages."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import paho.mqtt.publish as publish

MODEL_PATH = Path("models/yolov8n.tflite")
BROKER_HOST = "localhost"
BROKER_TOPIC = "robot_arm/detections"


def load_model(model_path: Path) -> Any:
    """Load a YOLOv8n TFLite model (placeholder)."""
    if not model_path.exists():
        raise FileNotFoundError(model_path)
    return model_path.read_text()


def run_inference(model: Any) -> dict[str, Any]:
    """Return a fake detection payload."""
    _ = model
    return {"detections": [], "note": "placeholder inference"}


def publish_detections(payload: dict[str, Any]) -> None:
    message = json.dumps(payload)
    publish.single(BROKER_TOPIC, payload=message, hostname=BROKER_HOST)
    print(f"Published detections to {BROKER_TOPIC}: {message}")


def main() -> None:
    model = load_model(MODEL_PATH)
    payload = run_inference(model)
    publish_detections(payload)


if __name__ == "__main__":
    main()
