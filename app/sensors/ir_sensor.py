"""Infrared obstacle sensor via GPIO."""

import random
from typing import Callable, Optional

from . import SensorError


class IRSensor:
    def __init__(self, reader: Optional[Callable[[], bool]] = None):
        self.reader = reader or self._mock_read

    def _mock_read(self) -> bool:
        return bool(random.getrandbits(1))

    def read(self) -> bool:
        try:
            return bool(self.reader())
        except Exception as exc:  # noqa: BLE001 - propagate upstream failure as sensor error
            raise SensorError(f"IR sensor read failed: {exc}") from exc

    async def read_async(self) -> bool:
        from asyncio import to_thread

        return await to_thread(self.read)
