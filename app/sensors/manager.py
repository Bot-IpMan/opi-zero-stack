import time
from typing import Dict

from .bme280 import BME280Sensor
from .vl53l0x import VL53L0XSensor
from .ir_sensor import IRSensor


class SensorManager:
    """Менеджер асинхронного опитування датчиків."""

    def __init__(self):
        self.bme280 = BME280Sensor()
        self.vl53 = VL53L0XSensor()
        self.ir = IRSensor()
        self.last_read = {}

    def read_all(self) -> Dict[str, float]:
        now = time.time()
        self.last_read = {
            "timestamp": now,
            "environment": self.bme280.read(),
            "distance_mm": self.vl53.read(),
            "obstacle": self.ir.read(),
        }
        return self.last_read
