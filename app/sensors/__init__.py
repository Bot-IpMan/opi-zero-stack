"""Sensor package exposing managers and shared helpers."""

from dataclasses import dataclass
from typing import Any, Dict


class SensorError(Exception):
    """Raised when a sensor fails to provide a valid reading."""


@dataclass
class SensorReading:
    name: str
    payload: Dict[str, Any]


__all__ = ["SensorManager", "SensorError", "SensorReading"]

from .manager import SensorManager  # noqa: E402  # isort:skip
