"""
MQTT логування для real-time моніторингу
"""

import json
from datetime import datetime

import paho.mqtt.client as mqtt


class MQTTLogger:
    def __init__(self, broker_host, base_topic="arm/logs"):
        self.client = mqtt.Client()
        self.client.connect(broker_host, 1883, 60)
        self.client.loop_start()
        self.base_topic = base_topic

    def log(self, category, data):
        """
        Логувати подію
        category: camera, llm, robot, execution, error
        """
        message = {
            "timestamp": datetime.now().isoformat(),
            "category": category,
            "data": data,
        }
        topic = f"{self.base_topic}/{category}"
        self.client.publish(topic, json.dumps(message, indent=2))

    def log_camera(self, image_quality, settings):
        self.log("camera", {
            "quality": image_quality,
            "settings": settings,
        })

    def log_llm_decision(self, decision):
        self.log("llm", decision)

    def log_robot_action(self, command, result):
        self.log("robot", {
            "command": command,
            "result": result,
        })

    def log_error(self, error_msg, traceback=None):
        self.log("error", {
            "message": error_msg,
            "traceback": traceback,
        })
