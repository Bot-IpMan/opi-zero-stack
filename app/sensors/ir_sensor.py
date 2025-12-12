import random


class IRSensor:
    def read(self) -> bool:
        return bool(random.getrandbits(1))
