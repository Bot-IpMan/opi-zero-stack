from typing import Dict

from .relay import Relay


class ActuatorManager:
    def __init__(self, pins: Dict[str, int]):
        self.relays = {
            "light": Relay("light", pins.get("light", 7)),
            "fan": Relay("fan", pins.get("fan", 8)),
            "pump": Relay("pump", pins.get("pump", 10)),
        }

    def set_light(self, on: bool):
        return self.relays["light"].set_state(on)

    def set_fan(self, on: bool):
        return self.relays["fan"].set_state(on)

    def set_pump(self, on: bool):
        return self.relays["pump"].set_state(on)

    def states(self):
        return {name: relay.state for name, relay in self.relays.items()}
