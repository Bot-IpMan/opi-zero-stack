import random


class VL53L0XSensor:
    def read(self) -> float:
        return round(200 + random.random() * 30, 2)
