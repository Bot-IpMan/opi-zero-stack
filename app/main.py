#!/usr/bin/env python3
"""Orange Pi Zero: виконавець команд від ПК з локальною логікою."""

import asyncio
import json
import logging
import os
import subprocess
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import paho.mqtt.client as mqtt
import serial
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

from actuators import ActuatorManager
from pc_client import PCClient
from sensors import SensorManager

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

MODEL_PATH = os.getenv("MODEL_PATH", "")
SERIAL_DEV = os.getenv("SERIAL_DEV", "/dev/ttyACM0")
CAMERA_DEVICE = os.getenv("CAMERA_DEVICE", "/dev/video0")
CAMERA_WIDTH = int(os.getenv("CAMERA_WIDTH", "640"))
CAMERA_HEIGHT = int(os.getenv("CAMERA_HEIGHT", "480"))
MQTT_HOST = os.getenv("MQTT_HOST", "mqtt")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
PC_HOST = os.getenv("PC_HOST", "pc")
PC_PORT = int(os.getenv("PC_PORT", 8080))

PINS = {
    "light": int(os.getenv("RELAY_LIGHT_PIN", "7")),
    "fan": int(os.getenv("RELAY_FAN_PIN", "8")),
    "pump": int(os.getenv("RELAY_PUMP_PIN", "10")),
}

# JSON з розкладом поливу вигляду [{"time": "07:30", "duration": 10}]
IRRIGATION_SCHEDULE = os.getenv("IRRIGATION_SCHEDULE", "[]")


class DeviceRequest(BaseModel):
    on: bool
    reason: Optional[str] = None


class ArmMoveRequest(BaseModel):
    angles: list[float]


app = FastAPI(title="Orange Pi Zero Executor")


class ExecutorContext:
    def __init__(self):
        self.sensors = SensorManager()
        self.actuators = ActuatorManager(PINS)
        self.serial_lock = asyncio.Lock()
        self.serial_port = serial.Serial(SERIAL_DEV, baudrate=115200, timeout=1)
        self.mqtt = mqtt.Client()
        self.mqtt.connect(MQTT_HOST, MQTT_PORT, 60)
        self.mqtt.loop_start()
        self.pc_client = PCClient(PC_HOST, PC_PORT)
        self.command_cache: list[Dict[str, Any]] = []
        self.emergency = False
        self.last_schedule_trigger: Dict[str, str] = {}
        self.irrigation_schedule: List[Tuple[str, int]] = self._load_schedule(IRRIGATION_SCHEDULE)
        logger.info(
            "Executor готовий. PC=%s:%s MQTT=%s:%s, розклад=%s",
            PC_HOST,
            PC_PORT,
            MQTT_HOST,
            MQTT_PORT,
            self.irrigation_schedule,
        )

    def cache_command(self, name: str, payload: Dict[str, Any]):
        self.command_cache.append({"name": name, "payload": payload, "ts": time.time()})
        self.command_cache = self.command_cache[-50:]

    def _load_schedule(self, schedule_json: str) -> List[Tuple[str, int]]:
        """Завантаження розкладу поливу з env (HH:MM, тривалість у секундах)."""
        try:
            parsed = json.loads(schedule_json)
            return [
                (item["time"], int(item.get("duration", 0)))
                for item in parsed
                if "time" in item and "duration" in item
            ]
        except Exception:
            logger.warning("Не вдалося розпарсити розклад поливу")
            return []

    async def safe_serial_write(self, payload: dict):
        async with self.serial_lock:
            data = json.dumps(payload) + "\n"
            self.serial_port.write(data.encode())
            return self.serial_port.readline().decode().strip()

    async def emergency_stop(self):
        self.emergency = True
        await self.safe_serial_write({"cmd": "emergency_stop"})
        self.actuators.set_fan(False)
        self.actuators.set_light(False)
        self.actuators.set_pump(False)
        logger.warning("Аварійна зупинка активована")

    async def scheduler_loop(self):
        while True:
            if self.emergency:
                await asyncio.sleep(1)
                continue
            sensor_data = self.sensors.read_all()
            # Локальна логіка: перевірка вологості + розклад поливу
            humidity = sensor_data.get("environment", {}).get("humidity", 100)
            try:
                if humidity < 45:
                    await self._run_pump_safely(5, reason="low_humidity")
                await self._run_schedule()
            except Exception:
                logger.exception("Помилка в автоматичній логіці, зупинка для безпеки")
                await self.emergency_stop()

            await self.pc_client.send_status(sensor_data, self.actuators.states())
            await asyncio.sleep(10)

    async def _run_pump_safely(self, duration: int, reason: str):
        """Безпечний запуск помпи з кешуванням команди."""
        if self.emergency:
            return
        self.actuators.set_pump(True)
        self.cache_command("pump_auto", {"duration": duration, "reason": reason})
        await asyncio.sleep(duration)
        self.actuators.set_pump(False)

    async def _run_schedule(self):
        """Виконання поливу за розкладом (раз на хвилину перевіряємо час)."""
        if not self.irrigation_schedule:
            return
        now_dt = datetime.now()
        now = now_dt.strftime("%H:%M")
        for slot_time, duration in self.irrigation_schedule:
            last_tag = self.last_schedule_trigger.get(slot_time)
            today_tag = now_dt.strftime("%Y-%m-%d")
            if slot_time == now and duration > 0 and last_tag != today_tag:
                await self._run_pump_safely(duration, reason="scheduled")
                self.last_schedule_trigger[slot_time] = today_tag


ctx = ExecutorContext()


@app.on_event("startup")
async def startup():
    asyncio.create_task(ctx.scheduler_loop())


@app.post("/devices/light")
async def control_light(req: DeviceRequest):
    ctx.cache_command("light", req.dict())
    return {"state": ctx.actuators.set_light(req.on)}


@app.post("/devices/fan")
async def control_fan(req: DeviceRequest):
    ctx.cache_command("fan", req.dict())
    return {"state": ctx.actuators.set_fan(req.on)}


@app.post("/devices/pump")
async def control_pump(req: DeviceRequest):
    ctx.cache_command("pump", req.dict())
    return {"state": ctx.actuators.set_pump(req.on)}


@app.post("/arm/move")
async def move_arm(req: ArmMoveRequest):
    if ctx.emergency:
        raise HTTPException(status_code=400, detail="Аварійний режим активний")
    payload = {"cmd": "move_servo", "angles": req.angles}
    ack = await ctx.safe_serial_write(payload)
    ctx.cache_command("arm_move", payload)
    return {"ack": ack or "no_ack"}


@app.get("/sensors/all")
async def read_sensors():
    return ctx.sensors.read_all()


@app.post("/emergency_stop")
async def emergency_stop():
    await ctx.emergency_stop()
    return {"status": "stopped"}


def capture_snapshot() -> bytes:
    """Захопити одиночний кадр з локальної камери через ffmpeg."""

    cmd = [
        "ffmpeg",
        "-f",
        "v4l2",
        "-video_size",
        f"{CAMERA_WIDTH}x{CAMERA_HEIGHT}",
        "-i",
        CAMERA_DEVICE,
        "-vframes",
        "1",
        "-f",
        "image2pipe",
        "-vcodec",
        "mjpeg",
        "-",
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=8,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="camera_timeout") from exc

    if result.returncode != 0 or not result.stdout:
        logger.error(
            "ffmpeg camera error: rc=%s, stderr=%s", result.returncode, result.stderr.decode()
        )
        raise HTTPException(status_code=503, detail="camera_unavailable")

    return result.stdout


@app.get("/camera/snapshot")
async def camera_snapshot():
    frame = capture_snapshot()
    return Response(content=frame, media_type="image/jpeg")


@app.get("/healthz")
async def healthz():
    return {
        "serial": ctx.serial_port.is_open,
        "camera_device": CAMERA_DEVICE,
        "mqtt": ctx.mqtt.is_connected(),
        "emergency": ctx.emergency,
        "cache_size": len(ctx.command_cache),
    }


@app.get("/cache")
async def cache():
    return ctx.command_cache


@app.post("/decide")
async def delegate_decision():
    sensors = ctx.sensors.read_all()
    decision = await ctx.pc_client.request_decision(sensors)
    return {"sensors": sensors, "decision": decision}


# Опційний RL інференс, якщо модель існує
if MODEL_PATH and os.path.exists(MODEL_PATH):
    import tflite_runtime.interpreter as tflite

    interpreter = tflite.Interpreter(model_path=MODEL_PATH)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    def rl_inference(observation: np.ndarray) -> np.ndarray:
        obs = observation.reshape(1, -1).astype(np.float32)
        interpreter.set_tensor(input_details[0]["index"], obs)
        interpreter.invoke()
        return interpreter.get_tensor(output_details[0]["index"])[0]
else:
    def rl_inference(observation: np.ndarray) -> np.ndarray:  # type: ignore
        return observation


@app.post("/rl_infer")
async def rl_infer(payload: Dict[str, Any]):
    obs = np.array(payload.get("observation", [0] * 6), dtype=np.float32)
    return {"action": rl_inference(obs).tolist()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000)
