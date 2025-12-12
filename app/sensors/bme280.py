"""BME280 sensor abstraction with calibration support."""

import random
from typing import Callable, Dict, Optional

from . import SensorError


class BME280Sensor:
    """Заглушка для BME280 з підтримкою калібрування та помилок."""

    def __init__(
        self,
        address: int = 0x76,
        reader: Optional[Callable[[], Dict[str, float]]] = None,
        temperature_offset: float = 0.0,
        humidity_offset: float = 0.0,
        pressure_offset: float = 0.0,
    ):
        self.address = address
        self.reader = reader or self._mock_read
        self.temperature_offset = temperature_offset
        self.humidity_offset = humidity_offset
        self.pressure_offset = pressure_offset

    def calibrate(
        self,
        temperature_offset: float = 0.0,
        humidity_offset: float = 0.0,
        pressure_offset: float = 0.0,
    ) -> None:
        self.temperature_offset = temperature_offset
        self.humidity_offset = humidity_offset
        self.pressure_offset = pressure_offset

    def _mock_read(self) -> Dict[str, float]:
        return {
            "temperature": round(20 + random.random() * 5, 2),
            "humidity": round(50 + random.random() * 10, 2),
            "pressure": round(1000 + random.random() * 5, 2),
        }

    def read(self) -> Dict[str, float]:
        try:
            data = dict(self.reader())
        except Exception as exc:  # noqa: BLE001 - propagate upstream failure as sensor error
            raise SensorError(f"BME280 read failed: {exc}") from exc

        data["temperature"] = round(data.get("temperature", 0.0) + self.temperature_offset, 2)
        data["humidity"] = round(data.get("humidity", 0.0) + self.humidity_offset, 2)
        data["pressure"] = round(data.get("pressure", 0.0) + self.pressure_offset, 2)
        return data

    async def read_async(self) -> Dict[str, float]:
        from asyncio import to_thread

        return await to_thread(self.read)
