import random
from typing import Dict


class BME280Sensor:
    """Заглушка для BME280. На Orange Pi заміни на реальне читання I2C."""

    def read(self) -> Dict[str, float]:
        return {
            "temperature": round(20 + random.random() * 5, 2),
            "humidity": round(50 + random.random() * 10, 2),
            "pressure": round(1000 + random.random() * 5, 2),
        }
