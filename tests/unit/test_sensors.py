import asyncio
from unittest.mock import AsyncMock

from app.sensors.analog import ArduinoAnalogSensor
from app.sensors.bme280 import BME280Sensor
from app.sensors.manager import SensorManager
from app.sensors.vl53l0x import VL53L0XSensor


def test_sensor_manager_collects_history():
    analog = ArduinoAnalogSensor(reader=lambda channel: 500 if channel == 0 else 300)
    bme = BME280Sensor(reader=lambda: {"temperature": 20, "humidity": 40, "pressure": 1000})
    distance = VL53L0XSensor(reader=lambda: 200)

    manager = SensorManager()
    manager.analog = analog
    manager.bme280 = bme
    manager.vl53 = distance

    reading = asyncio.run(manager.read_all())
    assert reading["soil_moisture"] == 500
    assert reading["environment"]["humidity"] == 40
    assert manager.last() is not None


def test_sensor_error_is_captured():
    failing_reader = AsyncMock(side_effect=RuntimeError("failed"))
    manager = SensorManager()
    manager.bme280.read_async = failing_reader  # type: ignore[assignment]
    manager.vl53.read_async = AsyncMock(return_value=123.0)  # type: ignore[assignment]
    manager.ir.read_async = AsyncMock(return_value=True)  # type: ignore[assignment]
    manager.analog.read_async = AsyncMock(return_value={"soil_moisture": 1, "light_level": 1})  # type: ignore[assignment]

    reading = asyncio.run(manager.read_all())
    assert "error" in reading["environment"]
    assert reading["distance_mm"] == 123.0
