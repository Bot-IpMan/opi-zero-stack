"""Менеджер асинхронного опитування датчиків."""

import asyncio
import time
from collections import deque
from typing import Deque, Dict, Optional

from . import SensorReading
from .analog import ArduinoAnalogSensor
from .bme280 import BME280Sensor
from .ir_sensor import IRSensor
from .vl53l0x import VL53L0XSensor


class SensorManager:
    """Керує усіма сенсорами, історією та калібруванням."""

    def __init__(self, history_size: int = 100):
        self.bme280 = BME280Sensor()
        self.vl53 = VL53L0XSensor()
        self.ir = IRSensor()
        self.analog = ArduinoAnalogSensor()
        self.history: Deque[Dict[str, object]] = deque(maxlen=history_size)

    def calibrate_environment(
        self,
        temperature_offset: float = 0.0,
        humidity_offset: float = 0.0,
        pressure_offset: float = 0.0,
    ) -> None:
        self.bme280.calibrate(temperature_offset, humidity_offset, pressure_offset)

    def calibrate_distance(self, offset_mm: float = 0.0) -> None:
        self.vl53.calibrate(offset_mm)

    def calibrate_analog(self, moisture_offset: float = 0.0, light_offset: float = 0.0) -> None:
        self.analog.calibrate(moisture_offset, light_offset)

    async def read_all(self) -> Dict[str, object]:
        """Асинхронно читає усі сенсори та зберігає історію."""

        readings = await asyncio.gather(
            self._read_sensor("environment", self.bme280.read_async),
            self._read_sensor("distance_mm", self.vl53.read_async),
            self._read_sensor("obstacle", self.ir.read_async),
            self._read_sensor("analog", self.analog.read_async),
        )

        payload: Dict[str, object] = {item.name: item.payload for item in readings}
        flattened = {
            "timestamp": time.time(),
            "environment": payload.get("environment", {}),
            "distance_mm": payload.get("distance_mm"),
            "obstacle": payload.get("obstacle"),
            "soil_moisture": payload.get("analog", {}).get("soil_moisture"),
            "light_level": payload.get("analog", {}).get("light_level"),
        }
        self.history.append(flattened)
        return flattened

    async def _read_sensor(self, name: str, reader) -> SensorReading:
        try:
            result = await reader()
        except Exception as exc:  # noqa: BLE001 - upstream error already descriptive
            return SensorReading(name=name, payload={"error": str(exc)})
        return SensorReading(name=name, payload=result if isinstance(result, dict) else {"value": result})

    def last(self) -> Optional[Dict[str, object]]:
        return self.history[-1] if self.history else None

    def get_history(self, limit: Optional[int] = None):
        if limit is None or limit >= len(self.history):
            return list(self.history)
        return list(list(self.history)[-limit:])
