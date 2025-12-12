import logging
from typing import Any, Dict

import cv2
import httpx
import numpy as np

logger = logging.getLogger(__name__)


class CameraError(RuntimeError):
    """Помилка доступу до відеопристрою."""


def analyze_frame(frame) -> Dict[str, Any]:
    """Проста обробка кадру: оцінка яскравості та різкості.

    Цю функцію можна замінити на повну модель детекції, але базова метрика
    вже дозволяє LLM приймати рішення щодо освітлення/фокусу.
    """
    if frame is None:
        raise CameraError("frame_not_available")

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    brightness = float(gray.mean())
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    logger.debug("Frame stats: brightness=%.2f, sharpness=%.2f", brightness, laplacian_var)
    return {
        "brightness": brightness,
        "sharpness": laplacian_var,
    }


def capture_single(device: str = "/dev/video0"):
    """Return a single frame or raise CameraError."""

    if device.startswith("http://") or device.startswith("https://"):
        try:
            resp = httpx.get(device, timeout=5)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("Не вдалося завантажити кадр з %s: %s", device, exc)
            raise CameraError(f"camera_unavailable:{device}") from exc

        frame = cv2.imdecode(np.frombuffer(resp.content, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            raise CameraError("empty_frame")
        return frame

    cap = cv2.VideoCapture(device)
    if not cap.isOpened():
        logger.warning("Не вдалося відкрити камеру %s", device)
        raise CameraError(f"camera_unavailable:{device}")

    ret, frame = cap.read()
    cap.release()
    if not ret:
        raise CameraError("empty_frame")
    return frame
