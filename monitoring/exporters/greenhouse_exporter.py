"""Prometheus exporter for greenhouse telemetry and device status."""
from __future__ import annotations

import random
import threading
import time

from prometheus_client import Counter, Gauge, start_http_server

# Environmental metrics
TEMPERATURE = Gauge(
    "greenhouse_temperature_celsius",
    "Current greenhouse temperature in Celsius",
)
HUMIDITY = Gauge(
    "greenhouse_humidity_percent",
    "Current greenhouse humidity in percent",
)
PRESSURE = Gauge(
    "greenhouse_pressure_pascal",
    "Current greenhouse pressure in Pascals",
)

# Sensor and device status (1 = healthy/on, 0 = failed/off)
SENSOR_STATE = Gauge(
    "sensor_state",
    "Health status of sensors",
    labelnames=["sensor"],
)
DEVICE_STATUS = Gauge(
    "device_status",
    "Operational status of greenhouse devices",
    labelnames=["device"],
)

# Robotic arm metrics
ROBOARM_COMMAND_TOTAL = Counter(
    "roboarm_commands_total",
    "Total number of robotic arm commands processed",
    labelnames=["type", "result"],
)
ROBOARM_COMMAND_ERRORS = Counter(
    "roboarm_command_errors_total",
    "Total errors produced by the robotic arm",
)
LAST_ROBOARM_COMMAND_TS = Gauge(
    "roboarm_last_command_timestamp_seconds",
    "Unix timestamp of the last robotic arm command",
)

# LLM decision and logging metrics
LLM_DECISIONS_TOTAL = Counter(
    "llm_decisions_total",
    "Total LLM decisions recorded",
    labelnames=["action"],
)
LLM_DECISION_WARNINGS_TOTAL = Counter(
    "llm_decision_warnings_total",
    "LLM decision log warnings",
)

# Error and warning counters
GREENHOUSE_ERRORS_TOTAL = Counter(
    "greenhouse_errors_total",
    "Total number of errors detected across devices and sensors",
    labelnames=["component"],
)
GREENHOUSE_WARNINGS_TOTAL = Counter(
    "greenhouse_warnings_total",
    "Total number of warnings detected across devices and sensors",
    labelnames=["component"],
)


class GreenhouseMetrics:
    """Generates demo greenhouse metrics for monitoring dashboards."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._seed_data()

    def _seed_data(self) -> None:
        TEMPERATURE.set(24.5)
        HUMIDITY.set(55)
        PRESSURE.set(101325)

        SENSOR_STATE.labels(sensor="temperature").set(1)
        SENSOR_STATE.labels(sensor="humidity").set(1)
        SENSOR_STATE.labels(sensor="pressure").set(1)

        DEVICE_STATUS.labels(device="lights").set(1)
        DEVICE_STATUS.labels(device="fans").set(1)
        DEVICE_STATUS.labels(device="pump").set(1)

        LAST_ROBOARM_COMMAND_TS.set_to_current_time()

    def update_environment(self) -> None:
        with self._lock:
            temperature = TEMPERATURE._value.get() + random.uniform(-0.4, 0.5)  # type: ignore[attr-defined]
            humidity = HUMIDITY._value.get() + random.uniform(-1.0, 1.0)  # type: ignore[attr-defined]
            pressure = PRESSURE._value.get() + random.uniform(-18, 20)  # type: ignore[attr-defined]

            TEMPERATURE.set(round(max(15, min(temperature, 40)), 2))
            HUMIDITY.set(round(max(20, min(humidity, 90)), 2))
            PRESSURE.set(round(max(98000, min(pressure, 104000)), 2))

    def update_sensors(self) -> None:
        with self._lock:
            # Simulate occasional sensor dropouts
            for sensor in ["temperature", "humidity", "pressure"]:
                state = 1 if random.random() > 0.05 else 0
                SENSOR_STATE.labels(sensor=sensor).set(state)
                if state == 0:
                    GREENHOUSE_WARNINGS_TOTAL.labels(component=sensor).inc()

    def update_devices(self) -> None:
        with self._lock:
            for device in ["lights", "fans", "pump"]:
                # Devices are mostly healthy but can go offline
                status = 1 if random.random() > 0.02 else 0
                DEVICE_STATUS.labels(device=device).set(status)
                if status == 0:
                    GREENHOUSE_ERRORS_TOTAL.labels(component=device).inc()

    def record_roboarm_activity(self) -> None:
        with self._lock:
            command_type = random.choice(["move", "grip", "release"])
            result = "ok" if random.random() > 0.1 else "error"

            ROBOARM_COMMAND_TOTAL.labels(type=command_type, result=result).inc()
            LAST_ROBOARM_COMMAND_TS.set_to_current_time()

            if result == "error":
                ROBOARM_COMMAND_ERRORS.inc()
                GREENHOUSE_ERRORS_TOTAL.labels(component="roboarm").inc()

    def record_llm_decision(self) -> None:
        with self._lock:
            action = random.choice(
                [
                    "adjust_lighting",
                    "increase_humidity",
                    "decrease_temperature",
                    "inspect_plant",
                ]
            )
            LLM_DECISIONS_TOTAL.labels(action=action).inc()

            # Log occasional warnings for visibility
            if random.random() > 0.85:
                LLM_DECISION_WARNINGS_TOTAL.inc()
                GREENHOUSE_WARNINGS_TOTAL.labels(component="llm").inc()

    def run(self, interval: float = 5.0) -> None:
        while True:
            self.update_environment()
            self.update_sensors()
            self.update_devices()
            self.record_roboarm_activity()
            self.record_llm_decision()
            time.sleep(interval)


def main() -> None:
    start_http_server(9100)
    metrics = GreenhouseMetrics()
    metrics_thread = threading.Thread(target=metrics.run, daemon=True)
    metrics_thread.start()

    # Keep the main thread alive to serve metrics
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
