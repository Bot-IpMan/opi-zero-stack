#!/usr/bin/env python3
"""Orange Pi Zero: виконавець команд від ПК з локальною логікою."""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import cv2

import numpy as np
import paho.mqtt.client as mqtt
import serial
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

from actuators import ActuatorManager
from pc_client import PCClient
from sensors import SensorManager
from mqtt_logger import MQTTLogger
from vision_control_loop import VisionControlLoop

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
APPROVAL_TIMEOUT = int(os.getenv("APPROVAL_TIMEOUT", "20"))

DECISIONS_TOPIC = "greenhouse/decisions"
APPROVALS_TOPIC = "greenhouse/approvals"

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


def init_camera() -> cv2.VideoCapture:
    cap = cv2.VideoCapture(CAMERA_DEVICE)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, 30)

    # КРИТИЧНО: Налаштування експозиції та яскравості
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)  # Manual mode
    cap.set(cv2.CAP_PROP_EXPOSURE, 150)
    cap.set(cv2.CAP_PROP_BRIGHTNESS, 128)
    cap.set(cv2.CAP_PROP_CONTRAST, 32)
    cap.set(cv2.CAP_PROP_SATURATION, 64)
    cap.set(cv2.CAP_PROP_GAIN, 50)

    return cap


cap = init_camera()
mqtt_logger = MQTTLogger(MQTT_HOST)


class ExecutorContext:
    def __init__(self):
        self.sensors = SensorManager()
        self.actuators = ActuatorManager(PINS)
        self.serial_lock = asyncio.Lock()
        self.serial_port = serial.Serial(SERIAL_DEV, baudrate=115200, timeout=1)
        self.loop = asyncio.get_event_loop()
        self.mqtt = mqtt.Client()
        self.mqtt.reconnect_delay_set(min_delay=1, max_delay=60)
        self.mqtt.on_connect = self._on_connect
        self.mqtt.on_message = self._on_message
        try:
            self.mqtt.connect(MQTT_HOST, MQTT_PORT, 60)
        except OSError as exc:
            logger.warning(
                "Не вдалося підключитися до MQTT %s:%s при старті: %s. Повторю спроби у фоні.",
                MQTT_HOST,
                MQTT_PORT,
                exc,
            )
            self.mqtt.connect_async(MQTT_HOST, MQTT_PORT, 60)
        self.mqtt.loop_start()
        self.pc_client = PCClient(PC_HOST, PC_PORT)
        self.command_cache: list[Dict[str, Any]] = []
        self.emergency = False
        self.last_schedule_trigger: Dict[str, str] = {}
        self.irrigation_schedule: List[Tuple[str, int]] = self._load_schedule(IRRIGATION_SCHEDULE)
        self.pending_decisions: Dict[str, Dict[str, Any]] = {}
        self.approval_timeout = APPROVAL_TIMEOUT
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

    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: Any, rc: int):
        if rc == 0:
            client.subscribe(DECISIONS_TOPIC)
            client.subscribe(APPROVALS_TOPIC)
            logger.info("Підписано на %s та %s", DECISIONS_TOPIC, APPROVALS_TOPIC)
        else:
            logger.warning("MQTT rc=%s при підключенні", rc)

    def _on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage):
        if not self.loop.is_running():
            logger.debug("MQTT подія до запуску подієвого циклу, пропускаю")
            return

        try:
            payload = json.loads(msg.payload.decode())
        except Exception:
            logger.warning("Неочікуваний MQTT payload у темі %s", msg.topic)
            return

        if msg.topic == DECISIONS_TOPIC:
            asyncio.run_coroutine_threadsafe(self._handle_decision(payload), self.loop)
        elif msg.topic == APPROVALS_TOPIC:
            decision_id = payload.get("id")
            if not decision_id:
                return
            asyncio.run_coroutine_threadsafe(
                self._handle_approval(decision_id, payload), self.loop
            )

    async def _handle_decision(self, payload: Dict[str, Any]):
        decision_id = payload.get("id") or f"auto-{int(time.time() * 1000)}"
        approval_future = self.loop.create_future()
        record = {
            "id": decision_id,
            "payload": payload,
            "received_at": time.time(),
            "future": approval_future,
        }
        self.pending_decisions[decision_id] = record
        logger.info("Отримано рішення %s, очікую підтвердження", decision_id)
        asyncio.create_task(self._await_approval(record))

    async def _await_approval(self, record: Dict[str, Any]):
        try:
            approved = await asyncio.wait_for(record["future"], timeout=self.approval_timeout)
        except asyncio.TimeoutError:
            logger.warning("Підтвердження для рішення %s не отримано вчасно", record["id"])
            self.pending_decisions.pop(record["id"], None)
            return
        except Exception:
            logger.exception("Помилка очікування підтвердження рішення %s", record["id"])
            self.pending_decisions.pop(record["id"], None)
            return

        self.pending_decisions.pop(record["id"], None)
        if approved:
            await self._execute_decision(record["payload"])
        else:
            logger.info("Рішення %s відхилено оператором", record["id"])

    async def _handle_approval(self, decision_id: str, payload: Dict[str, Any]):
        approved = payload.get("approved")
        if approved is None:
            status = payload.get("status")
            approved = status == "approved" if status in {"approved", "rejected"} else None

        record = self.pending_decisions.get(decision_id)
        if record is None or approved is None:
            logger.debug("Немає відкладеного рішення %s для підтвердження", decision_id)
            return

        future: asyncio.Future = record["future"]
        if not future.done():
            future.set_result(bool(approved))

    async def _execute_decision(self, payload: Dict[str, Any]):
        if self.emergency:
            logger.warning("Пропущено виконання рішення: аварійний режим")
            return

        action = payload.get("action") or payload.get("cmd") or payload.get("name")
        params = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
        params = params or {}
        logger.info("Виконання затвердженого рішення %s з дією %s", payload.get("id"), action)

        if action in {"light", "set_light"}:
            state = params.get("on", payload.get("on"))
            if state is not None:
                self.cache_command("light", {"on": bool(state), "source": "mqtt_decision"})
                self.actuators.set_light(bool(state))
        elif action in {"fan", "set_fan"}:
            state = params.get("on", payload.get("on"))
            if state is not None:
                self.cache_command("fan", {"on": bool(state), "source": "mqtt_decision"})
                self.actuators.set_fan(bool(state))
        elif action in {"pump", "set_pump"}:
            duration = params.get("duration") or payload.get("duration")
            state = params.get("on", payload.get("on"))
            if duration:
                await self._run_pump_safely(int(duration), reason="approved_decision")
            elif state is not None:
                self.cache_command("pump", {"on": bool(state), "source": "mqtt_decision"})
                self.actuators.set_pump(bool(state))
        elif action == "emergency_stop":
            await self.emergency_stop()
        else:
            logger.info("Невідома дія рішення %s: %s", payload.get("id"), action)

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
            sensor_data = await self.sensors.read_all()
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
control_loop: VisionControlLoop | None = None
control_loop_task: asyncio.Task | None = None


@app.on_event("startup")
async def startup():
    global control_loop, control_loop_task
    ctx.loop = asyncio.get_running_loop()
    asyncio.create_task(ctx.scheduler_loop())
    control_loop = VisionControlLoop(
        robot_url="http://localhost:8000",
        llm_url=os.getenv("LLM_URL", "http://192.168.1.152:8080"),
        mqtt_client=ctx.mqtt,
        mqtt_logger=mqtt_logger,
    )
    control_loop_task = asyncio.create_task(control_loop.run_loop())


@app.post("/control/start")
async def start_control(task: str = "Навчитися рухати роборукою"):
    global control_loop_task
    if control_loop is None:
        raise HTTPException(status_code=503, detail="control_loop_unavailable")

    control_loop_task = asyncio.create_task(control_loop.run_loop(task=task))
    return {"status": "started"}


@app.post("/control/stop")
async def stop_control():
    global control_loop_task
    if control_loop_task and not control_loop_task.done():
        control_loop_task.cancel()
        try:
            await control_loop_task
        except asyncio.CancelledError:
            pass
        control_loop_task = None
        return {"status": "stopped"}

    return {"status": "idle"}


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
    return await ctx.sensors.read_all()


@app.post("/emergency_stop")
async def emergency_stop():
    await ctx.emergency_stop()
    return {"status": "stopped"}


def ensure_camera_ready() -> cv2.VideoCapture:
    global cap

    if cap is None or not cap.isOpened():
        logger.warning("Камеру не відкрито, ініціалізую повторно")
        cap = init_camera()
        mqtt_logger.log_camera("reinitialized", {
            "width": cap.get(cv2.CAP_PROP_FRAME_WIDTH),
            "height": cap.get(cv2.CAP_PROP_FRAME_HEIGHT),
            "fps": cap.get(cv2.CAP_PROP_FPS),
            "exposure": cap.get(cv2.CAP_PROP_EXPOSURE),
            "brightness": cap.get(cv2.CAP_PROP_BRIGHTNESS),
            "contrast": cap.get(cv2.CAP_PROP_CONTRAST),
            "saturation": cap.get(cv2.CAP_PROP_SATURATION),
            "gain": cap.get(cv2.CAP_PROP_GAIN),
        })

    return cap


def capture_snapshot() -> bytes:
    """Захопити одиночний кадр з локальної камери через OpenCV."""

    camera = ensure_camera_ready()
    ret, frame = camera.read()

    if not ret or frame is None:
        mqtt_logger.log_error("camera_unavailable during snapshot")
        raise HTTPException(status_code=503, detail="camera_unavailable")

    success, buffer = cv2.imencode(".jpg", frame)
    if not success:
        mqtt_logger.log_error("camera_encode_failed")
        raise HTTPException(status_code=500, detail="camera_encode_failed")

    return buffer.tobytes()


@app.get("/camera/snapshot")
async def camera_snapshot():
    frame = capture_snapshot()
    return Response(content=frame, media_type="image/jpeg")


@app.get("/camera/settings")
async def get_camera_settings():
    """Показати поточні налаштування камери."""

    camera = ensure_camera_ready()
    settings = {
        "width": camera.get(cv2.CAP_PROP_FRAME_WIDTH),
        "height": camera.get(cv2.CAP_PROP_FRAME_HEIGHT),
        "fps": camera.get(cv2.CAP_PROP_FPS),
        "exposure": camera.get(cv2.CAP_PROP_EXPOSURE),
        "brightness": camera.get(cv2.CAP_PROP_BRIGHTNESS),
        "contrast": camera.get(cv2.CAP_PROP_CONTRAST),
        "saturation": camera.get(cv2.CAP_PROP_SATURATION),
        "gain": camera.get(cv2.CAP_PROP_GAIN),
    }
    mqtt_logger.log_camera("read", settings)
    return settings


@app.post("/camera/settings")
async def update_camera_settings(settings: Dict[str, float]):
    """Змінити налаштування камери в реальному часі."""

    camera = ensure_camera_ready()

    if "exposure" in settings:
        camera.set(cv2.CAP_PROP_EXPOSURE, settings["exposure"])
    if "brightness" in settings:
        camera.set(cv2.CAP_PROP_BRIGHTNESS, settings["brightness"])
    if "contrast" in settings:
        camera.set(cv2.CAP_PROP_CONTRAST, settings["contrast"])
    if "saturation" in settings:
        camera.set(cv2.CAP_PROP_SATURATION, settings["saturation"])
    if "gain" in settings:
        camera.set(cv2.CAP_PROP_GAIN, settings["gain"])
    if "fps" in settings:
        camera.set(cv2.CAP_PROP_FPS, settings["fps"])
    if "width" in settings:
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, settings["width"])
    if "height" in settings:
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, settings["height"])

    updated = await get_camera_settings()
    mqtt_logger.log_camera("updated", updated)
    return {"status": "updated", "settings": updated}


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
    sensors = await ctx.sensors.read_all()
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


# ==================== ЗАПУСК СЕРВЕРА ====================

if __name__ == "__main__":
    import os
    from waitress import serve

    # Забороняємо багатопоточність (для Orange Pi Zero 512MB RAM)
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"

    logger.info("🚀 RobotController запускається на waitress (Orange Pi Zero)")
    logger.info("🌐 Слухаю на http://0.0.0.0:8000")

    serve(
        app,
        host="0.0.0.0",
        port=8000,
        threads=1,
        _quiet=True
    )
