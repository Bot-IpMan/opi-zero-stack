"""Менеджер керування GPIO-пристроями."""

from typing import Dict, Optional

from .relay import Relay


class ActuatorManager:
    def __init__(self, pins: Optional[Dict[str, int]] = None, gpio_driver: Optional[object] = None):
        pins = pins or {}
        self.relays = {
            "light": Relay("light", pins.get("light", 7), gpio_driver),
            "fan": Relay("fan", pins.get("fan", 8), gpio_driver),
            "pump": Relay("pump", pins.get("pump", 10), gpio_driver),
        }

    def set_light(self, on: bool):
        return self.relays["light"].set_state(on)

    def set_fan(self, on: bool):
        return self.relays["fan"].set_state(on)

    def set_pump(self, on: bool):
        return self.relays["pump"].set_state(on)

    def states(self):
        return {name: relay.state for name, relay in self.relays.items()}

    def safe_shutdown(self):
        for relay in self.relays.values():
            relay.off()
        return self.states()
