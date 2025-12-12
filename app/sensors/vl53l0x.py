"""VL53L0X distance sensor wrapper."""

import random
from typing import Callable, Optional

from . import SensorError


class VL53L0XSensor:
    def __init__(
        self,
        reader: Optional[Callable[[], float]] = None,
        offset_mm: float = 0.0,
    ):
        self.reader = reader or self._mock_read
        self.offset_mm = offset_mm

    def calibrate(self, offset_mm: float = 0.0) -> None:
        self.offset_mm = offset_mm

    def _mock_read(self) -> float:
        return round(200 + random.random() * 30, 2)

    def read(self) -> float:
        try:
            value = float(self.reader())
        except Exception as exc:  # noqa: BLE001 - propagate upstream failure as sensor error
            raise SensorError(f"VL53L0X read failed: {exc}") from exc
        return round(max(0.0, value + self.offset_mm), 2)

    async def read_async(self) -> float:
        from asyncio import to_thread

        return await to_thread(self.read)
