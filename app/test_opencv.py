import importlib.util

import pytest


missing = [name for name in ("cv2", "numpy") if importlib.util.find_spec(name) is None]

if missing:
    pytest.skip(
        f"Missing dependencies: {', '.join(missing)}; skipping OpenCV tests.",
        allow_module_level=True,
    )

import cv2
import numpy as np


def test_cv2_reports_version():
    assert cv2.__version__


def test_can_encode_blank_frame():
    frame = np.zeros((10, 10, 3), dtype=np.uint8)

    success, buffer = cv2.imencode(".jpg", frame)

    assert success
    assert buffer.size > 0
