"""
MQTT логування для real-time моніторингу
"""

import json
import logging
from datetime import datetime

import paho.mqtt.client as mqtt


logger = logging.getLogger(__name__)


class MQTTLogger:
    def __init__(self, broker_host, base_topic: str = "arm/logs"):
        self.base_topic = base_topic.rstrip("/")
        self.client: mqtt.Client | None = None

        if not broker_host:
            logger.warning("MQTT logger disabled — брокер не вказано")
            return

        try:
            self.client = mqtt.Client()
            self.client.connect(broker_host, 1883, 60)
            self.client.loop_start()
            logger.info("MQTT logger підключено до %s", broker_host)
        except Exception as exc:  # noqa: BLE001
            self.client = None
            logger.warning(
                "Не вдалося підключитись до MQTT брокера %s: %s. Логування MQTT вимкнено",
                broker_host,
                exc,
            )

    def log(self, category, data):
        """
        Логувати подію
        category: camera, llm, robot, execution, error
        """
        if not self.client:
            logger.debug("Пропущено MQTT log %s — клієнт не підключений", category)
            return

        message = {
            "timestamp": datetime.now().isoformat(),
            "category": category,
            "data": data,
        }
        topic = f"{self.base_topic}/{category}"
        self.client.publish(topic, json.dumps(message, indent=2))

    def log_camera(self, image_quality, settings):
        self.log(
            "camera",
            {
                "quality": image_quality,
                "settings": settings,
            },
        )

    def log_llm_decision(self, decision):
        self.log("llm", decision)

    def log_robot_action(self, command, result):
        self.log(
            "robot",
            {
                "command": command,
                "result": result,
            },
        )

    def log_error(self, error_msg, traceback=None):
        self.log(
            "error",
            {
                "message": error_msg,
                "traceback": traceback,
            },
        )
