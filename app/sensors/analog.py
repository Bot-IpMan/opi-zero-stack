"""Analog sensor readers via Arduino serial or mock values."""

import random
from typing import Callable, Dict, Optional

from . import SensorError


class ArduinoAnalogSensor:
    """Represents analog sensors connected through an Arduino helper."""

    def __init__(
        self,
        soil_channel: int = 0,
        light_channel: int = 1,
        reader: Optional[Callable[[int], float]] = None,
        moisture_offset: float = 0.0,
        light_offset: float = 0.0,
    ):
        self.soil_channel = soil_channel
        self.light_channel = light_channel
        self.reader = reader or self._mock_reader
        self.moisture_offset = moisture_offset
        self.light_offset = light_offset

    def calibrate(self, moisture_offset: float = 0.0, light_offset: float = 0.0) -> None:
        self.moisture_offset = moisture_offset
        self.light_offset = light_offset

    def _mock_reader(self, channel: int) -> float:
        base = 600 if channel == self.soil_channel else 400
        return float(base + random.randint(-50, 50))

    def read(self) -> Dict[str, float]:
        try:
            soil_raw = float(self.reader(self.soil_channel))
            light_raw = float(self.reader(self.light_channel))
        except Exception as exc:  # noqa: BLE001 - upstream exceptions need wrapping
            raise SensorError(f"Analog reader failed: {exc}") from exc

        return {
            "soil_moisture": max(0.0, soil_raw + self.moisture_offset),
            "light_level": max(0.0, light_raw + self.light_offset),
        }

    async def read_async(self) -> Dict[str, float]:
        from asyncio import to_thread

        return await to_thread(self.read)
