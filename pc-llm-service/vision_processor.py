import logging
from typing import Dict, Any
import cv2

logger = logging.getLogger(__name__)


def analyze_frame(frame) -> Dict[str, Any]:
    """Проста обробка кадру: оцінка яскравості та різкості.

    Цю функцію можна замінити на повну модель детекції, але базова метрика
    вже дозволяє LLM приймати рішення щодо освітлення/фокусу.
    """
    if frame is None:
        return {"error": "frame_not_available"}

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    brightness = float(gray.mean())
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    logger.debug("Frame stats: brightness=%.2f, sharpness=%.2f", brightness, laplacian_var)
    return {
        "brightness": brightness,
        "sharpness": laplacian_var,
    }


def capture_single(device: str = "/dev/video0"):
    cap = cv2.VideoCapture(device)
    if not cap.isOpened():
        logger.warning("Не вдалося відкрити камеру %s", device)
        return None
    ret, frame = cap.read()
    cap.release()
    return frame if ret else None
