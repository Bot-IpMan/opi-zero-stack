"""
Цикл: Камера → LLM аналіз → Команда роборуці → Виконання → Повтор
"""

import asyncio
import base64
import json
from datetime import datetime

import httpx


class VisionControlLoop:
    def __init__(self, robot_url, llm_url, mqtt_client):
        self.robot_url = robot_url  # http://localhost:8000
        self.llm_url = llm_url  # http://192.168.1.152:8080
        self.mqtt = mqtt_client

    async def get_snapshot(self):
        """Отримати знімок з камери"""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.robot_url}/camera/snapshot")
            return base64.b64encode(resp.content).decode()

    async def get_robot_state(self):
        """Отримати стан роборуки"""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.robot_url}/robot/state")
            return resp.json()

    async def ask_llm(self, image_b64, robot_state, task):
        """Запитати LLM що робити"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.llm_url}/vision/analyze",
                json={
                    "image": image_b64,
                    "robot_state": robot_state,
                    "task": task,
                },
            )
            return resp.json()

    async def execute_command(self, command):
        """Виконати команду на роборуці"""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.robot_url}/robot/command",
                json=command,
            )
            return resp.json()

    async def run_loop(self, task="Навчитися рухати роборукою", iterations=100):
        """Основний цикл навчання"""
        for i in range(iterations):
            start_time = datetime.now()

            # 1. Отримати дані
            image = await self.get_snapshot()
            state = await self.get_robot_state()

            # Опублікувати в MQTT для моніторингу
            self.mqtt.publish(
                "arm/logs/iteration",
                json.dumps(
                    {
                        "iteration": i,
                        "timestamp": start_time.isoformat(),
                        "state": state,
                    }
                ),
            )

            # 2. Запитати LLM
            decision = await self.ask_llm(image, state, task)

            # Опублікувати рішення LLM
            self.mqtt.publish("arm/logs/llm_decision", json.dumps(decision))

            # 3. Виконати команду
            if "command" in decision:
                result = await self.execute_command(decision["command"])

                # Опублікувати результат
                self.mqtt.publish(
                    "arm/logs/execution",
                    json.dumps(
                        {
                            "command": decision["command"],
                            "result": result,
                            "duration_ms": (datetime.now() - start_time).total_seconds()
                            * 1000,
                        }
                    ),
                )

            # 4. Пауза перед наступною ітерацією
            await asyncio.sleep(2)
