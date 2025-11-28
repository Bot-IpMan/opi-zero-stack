"""YOLOv8n TFLite inference loop that publishes MQTT messages."""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, List

import cv2
import numpy as np
import paho.mqtt.publish as publish

try:
    from tflite_runtime.interpreter import Interpreter
except Exception:  # pragma: no cover - optional dependency
    Interpreter = None  # type: ignore


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger("yolo_detector")

MODEL_PATH = Path(os.getenv("MODEL_PATH", "models/yolov8n.tflite"))
BROKER_HOST = os.getenv("MQTT_HOST", "localhost")
BROKER_TOPIC = os.getenv("BROKER_TOPIC", "arm/vision/objects")
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
FRAME_SHAPE = (240, 320)
SLEEP_BETWEEN_FRAMES = float(os.getenv("FRAME_SLEEP", "0.05"))
DUMMY_MODE = os.getenv("DUMMY_DETECTIONS", "0") == "1"


def load_model(model_path: Path) -> Any:
    if DUMMY_MODE:
        log.warning("Running in dummy detection mode")
        return None

    if Interpreter is None:
        raise SystemExit(
            "tflite_runtime is not available. Install it or set DUMMY_DETECTIONS=1 "
            "to run in placeholder mode."
        )

    if not model_path.exists():
        raise SystemExit(
            f"YOLO model not found at {model_path}. Provide a valid model file or set "
            "DUMMY_DETECTIONS=1 for synthetic detections."
        )

    interpreter = Interpreter(model_path=str(model_path))
    interpreter.allocate_tensors()
    log.info("Loaded YOLO model %s", model_path)
    return interpreter


def _capture_frame(cap: cv2.VideoCapture) -> np.ndarray:
    ok, frame = cap.read()
    if not ok:
        raise RuntimeError("Failed to read frame from camera")
    frame = cv2.resize(frame, FRAME_SHAPE[::-1])
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)


def _preprocess(frame: np.ndarray, input_details: dict) -> np.ndarray:
    height, width = input_details["shape"][1:3]
    resized = cv2.resize(frame, (width, height))
    arr = resized.astype(np.float32) / 255.0
    return np.expand_dims(arr, axis=0)


def _parse_outputs(interpreter: Any) -> List[dict]:
    outputs = []
    for detail in interpreter.get_output_details():
        tensor = interpreter.get_tensor(detail["index"])
        outputs.append(tensor)
    # Very small heuristic parser
    detections: List[dict] = []
    if outputs:
        raw = outputs[0].reshape(-1, outputs[0].shape[-1])
        for row in raw[:5]:
            if row.shape[-1] < 6:
                continue
            confidence = float(row[4]) if row.shape[-1] > 4 else 0.0
            if confidence <= 0:
                continue
            detections.append(
                {
                    "bbox": [float(x) for x in row[:4]],
                    "confidence": confidence,
                    "class_id": int(row[5]) if row.shape[-1] > 5 else 0,
                }
            )
    return detections


def run_inference(interpreter: Any, frame: np.ndarray) -> dict[str, Any]:
    if interpreter is None:
        h, w, _ = frame.shape
        return {"detections": [], "note": "dummy-mode", "frame_size": [h, w]}

    input_details = interpreter.get_input_details()[0]
    preprocessed = _preprocess(frame, input_details)
    interpreter.set_tensor(input_details["index"], preprocessed)
    interpreter.invoke()
    detections = _parse_outputs(interpreter)
    return {"detections": detections, "frame_size": list(frame.shape)}


def publish_detections(payload: dict[str, Any]) -> None:
    message = json.dumps(payload)
    try:
        publish.single(BROKER_TOPIC, payload=message, hostname=BROKER_HOST)
        log.info(
            "Published detections to %s (%d detections)",
            BROKER_TOPIC,
            len(payload.get("detections", [])),
        )
    except Exception:
        # Падіння брокера не має зупиняти детектор — просто попереджаємо користувача.
        log.exception("Failed to publish detections to MQTT broker %s", BROKER_HOST)


def main() -> None:
    interpreter = load_model(MODEL_PATH)
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        log.warning("Camera index %s unavailable; using synthetic frames", CAMERA_INDEX)
        cap = None

    try:
        while True:
            if cap is None:
                frame = np.zeros((FRAME_SHAPE[0], FRAME_SHAPE[1], 3), dtype=np.uint8)
                cv2.circle(frame, (FRAME_SHAPE[1] // 2, FRAME_SHAPE[0] // 2), 20, (0, 0, 255), -1)
            else:
                frame = _capture_frame(cap)

            payload = run_inference(interpreter, frame)
            payload.update({"ts": time.time()})
            publish_detections(payload)
            time.sleep(SLEEP_BETWEEN_FRAMES)
    except KeyboardInterrupt:
        log.info("Stopping YOLO detector")
    except Exception:
        log.exception("YOLO detector crashed")
        sys.exit(1)
    finally:
        if cap is not None:
            cap.release()


if __name__ == "__main__":
    main()
