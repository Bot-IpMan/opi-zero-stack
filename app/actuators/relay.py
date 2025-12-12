"""GPIO relay control abstraction."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class Relay:
    def __init__(self, name: str, pin: int, gpio_driver: Optional[object] = None):
        self.name = name
        self.pin = pin
        self.state = False
        self.gpio_driver = gpio_driver

    def set_state(self, on: bool):
        self.state = on
        if self.gpio_driver:
            try:
                self.gpio_driver.write(self.pin, on)
            except Exception as exc:  # noqa: BLE001
                logger.error("Не вдалося встановити стан реле %s: %s", self.name, exc)
        logger.info("Реле %s (pin %s) => %s", self.name, self.pin, "ON" if on else "OFF")
        return self.state

    def off(self):
        return self.set_state(False)
