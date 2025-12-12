import logging

logger = logging.getLogger(__name__)


class Relay:
    def __init__(self, name: str, pin: int):
        self.name = name
        self.pin = pin
        self.state = False

    def set_state(self, on: bool):
        self.state = on
        logger.info("Реле %s (pin %s) => %s", self.name, self.pin, "ON" if on else "OFF")
        return self.state
