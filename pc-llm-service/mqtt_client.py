import logging
import json
import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class MQTTClient:
    def __init__(
        self,
        host: str,
        port: int,
        topic_prefix: str = "greenhouse",
        enabled: bool = True,
    ):
        self.topic_prefix = topic_prefix.rstrip("/")
        self.client: mqtt.Client | None = None
        self.connected = False

        if not enabled:
            logger.info("MQTT вимкнено через конфігурацію")
            return

        try:
            self.client = mqtt.Client()
            self.client.on_connect = self._on_connect
            self.client.connect(host, port, 60)
            self.connected = True
            logger.info("MQTT підключено до %s:%s", host, port)
        except Exception as exc:
            # Залишаємо клієнт неактивним, щоб решта сервісу працювала без MQTT
            self.client = None
            logger.warning(
                "Не вдалося підключитись до MQTT брокера %s:%s: %s. MQTT вимкнено",
                host,
                port,
                exc,
            )

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            logger.info("MQTT успішно з'єднано")
        else:
            logger.warning("MQTT rc=%s", rc)

    def publish_state(self, topic: str, payload: dict):
        if not self.client or not self.connected:
            logger.debug("Пропущено MQTT publish %s — клієнт не підключений", topic)
            return
        full_topic = f"{self.topic_prefix}/{topic}"
        try:
            self.client.publish(full_topic, json.dumps(payload), qos=0)
            logger.debug("MQTT publish %s", full_topic)
        except Exception:
            logger.exception("Не вдалося відправити MQTT повідомлення")

    def loop_background(self):
        if not self.client or not self.connected:
            logger.debug("MQTT loop не запущено — клієнт не підключений")
            return
        self.client.loop_start()
