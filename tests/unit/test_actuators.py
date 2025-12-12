from unittest.mock import MagicMock

from app.actuators.manager import ActuatorManager


def test_actuator_manager_updates_states():
    gpio_driver = MagicMock()
    manager = ActuatorManager({"light": 1, "fan": 2, "pump": 3}, gpio_driver=gpio_driver)

    assert manager.set_light(True) is True
    assert manager.set_fan(False) is False
    assert manager.set_pump(True) is True

    gpio_driver.write.assert_any_call(1, True)
    gpio_driver.write.assert_any_call(2, False)
    gpio_driver.write.assert_any_call(3, True)

    states = manager.states()
    assert states == {"light": True, "fan": False, "pump": True}

    manager.safe_shutdown()
    assert manager.states() == {"light": False, "fan": False, "pump": False}
