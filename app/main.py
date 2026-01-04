#!/usr/bin/env python3
"""
Orange Pi Zero: RL Inference + YOLO Integration
"""

import os
import json
import time
import asyncio
import logging
import tflite_runtime.interpreter as tflite
import serial
import paho.mqtt.client as mqtt
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from threading import Thread, Lock

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфіг
MODEL_PATH = os.getenv("MODEL_PATH", "/app/model.tflite")
SERIAL_DEV = os.getenv("SERIAL_DEV", "/dev/ttyACM0")
MQTT_HOST = os.getenv("MQTT_HOST", "mqtt")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
DUMMY_MODEL = os.getenv("DUMMY_MODEL", "0") == "1"

app = FastAPI(title="Robot Arm RL Controller")


class DummyInterpreter:
    """Проста модель-заглушка для тестування без реальної TFLite моделі."""

    def __init__(self, input_shape: tuple[int, ...] = (1, 9), output_shape: tuple[int, ...] = (1, 6)):
        self.input_details = [{"index": 0, "shape": np.array(input_shape, dtype=np.int32)}]
        self.output_details = [{"index": 0, "shape": np.array(output_shape, dtype=np.int32)}]
        self._input = np.zeros(input_shape, dtype=np.float32)
        self._output = np.zeros(output_shape, dtype=np.float32)

    def allocate_tensors(self):
        return None

    def get_input_details(self):
        return self.input_details

    def get_output_details(self):
        return self.output_details

    def set_tensor(self, index, value):
        self._input = np.array(value, dtype=np.float32)

    def invoke(self):
        # Вихід – віднормовані перші 6 значень
        if self._input.ndim == 2:
            base = self._input[:, :6]
        else:
            base = self._input[:6]
        self._output = np.clip(base, 0.0, 1.0).reshape(1, -1)

    def get_tensor(self, index):
        return self._output

class YOLODetection(BaseModel):
    objects: list
    timestamp: float
    inference_time_ms: float

class RobotState(BaseModel):
    joint_angles: list[float]
    target_object: Optional[dict] = None
    action: Optional[list[float]] = None
    serial_ack: Optional[str] = None

class RobotController:
    def __init__(self):
        # TFLite інтерпретатор
        self.interpreter = None
        self.input_details = None
        self.output_details = None
        self.load_model()
        
        # Serial комунікація
        self.serial_port = None
        self.serial_lock = Lock()
        self.init_serial()
        self.send_arm_command()
        
        # MQTT
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_message = self.on_mqtt_message
        self.mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
        self.mqtt_client.subscribe("arm/vision/objects")
        
        # Стан
        self.current_state = np.zeros(9, dtype=np.float32)  # [joints(6), yolo(3)]
        self.joint_angles = np.zeros(6, dtype=np.float32)
        self.yolo_target = np.zeros(3, dtype=np.float32)
        self.last_detection_time = 0
        self.last_serial_ack: Optional[str] = None
        
        # MQTT loop в окремому потоці
        mqtt_thread = Thread(target=self.mqtt_client.loop_forever, daemon=True)
        mqtt_thread.start()
        
        logger.info("✅ RobotController ініціалізовано")

    def load_model(self):
        """Завантажити TFLite модель"""
        if DUMMY_MODEL:
            logger.info("🔧 DUMMY_MODEL=1 - використовується dummy модель")
            self.interpreter = DummyInterpreter()
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            return
        
        try:
            self.interpreter = tflite.Interpreter(model_path=MODEL_PATH)
            self.interpreter.allocate_tensors()
            
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            
            logger.info(f"✅ Модель завантажена: {MODEL_PATH}")
        except Exception as e:
            logger.error(f"❌ Помилка завантаження моделі: {e}")
            raise

    @staticmethod
    def normalize_action(raw_action: np.ndarray) -> np.ndarray:
        """Нормалізувати дії до діапазону 0.0-1.0"""
        action = np.array(raw_action, dtype=np.float32).flatten()
        if action.size < 6:
            action = np.pad(action, (0, 6 - action.size))
        action = action[:6]
        action = (action + 1.0) / 2.0
        return np.clip(action, 0.0, 1.0)
    
    def init_serial(self):
        """Ініціалізація Serial портом"""
        try:
            self.serial_port = serial.Serial(
                SERIAL_DEV,
                baudrate=115200,
                timeout=1
            )
            time.sleep(2)  # Очікування Arduino ініціалізації
            self.serial_port.reset_input_buffer()
            self.serial_port.reset_output_buffer()
            logger.info(f"✅ Serial підключено: {SERIAL_DEV}")
        except Exception as e:
            logger.error(f"❌ Serial помилка: {e}")
            raise

    def send_arm_command(self) -> bool:
        """Відправити ARM команду після підключення."""
        if not self.serial_port:
            return False

        try:
            with self.serial_lock:
                self.serial_port.write(b'ARM\r\n')
                logger.info("🦾 ARM команда відправлена")
            return True
        except Exception as e:
            logger.error(f"❌ ARM send error: {e}")
            return False
    
    def on_mqtt_message(self, client, userdata, msg):
        """Обробка YOLO детекцій"""
        if msg.topic == "arm/vision/objects":
            try:
                data = json.loads(msg.payload)
                self.last_detection_time = time.time()
                
                # Витяг першого об'єкта
                if data.get("objects"):
                    obj = data["objects"][0]
                    self.yolo_target[0] = obj.get("x", 0.0)
                    self.yolo_target[1] = obj.get("y", 0.0)
                    self.yolo_target[2] = obj.get("confidence", 0.0)
                else:
                    self.yolo_target = np.zeros(3, dtype=np.float32)
                
                logger.debug(f"📷 YOLO target: {self.yolo_target}")
            except Exception as e:
                logger.error(f"❌ MQTT parse error: {e}")
    
    def predict(self, observation: np.ndarray) -> np.ndarray:
        """RL інференс"""
        try:
            # Нормалізація
            obs = observation.reshape(1, -1).astype(np.float32)

            # Інференс
            self.interpreter.set_tensor(
                self.input_details[0]['index'],
                obs
            )
            self.interpreter.invoke()

            action = self.interpreter.get_tensor(
                self.output_details[0]['index']
            )[0]
            return self.normalize_action(action)
        except Exception as e:
            logger.error(f"❌ Inference error: {e}")
            return np.zeros(6, dtype=np.float32)

    def send_action(self, action: np.ndarray) -> bool:
        """Відправка дії на Arduino"""
        if not self.serial_port:
            return False

        try:
            action_vec = np.array(action, dtype=np.float32).flatten()
            if action_vec.size < 6:
                action_vec = np.pad(action_vec, (0, 6 - action_vec.size))
            action_vec = np.clip(action_vec[:6], 0.0, 1.0)
            self.joint_angles = action_vec.copy()

            with self.serial_lock:
                command = {
                    "cmd": action_vec.tolist(),
                    "timestamp": time.time()
                }

                json_str = json.dumps(command) + '\r\n'
                self.serial_port.write(json_str.encode())

                # Очікування ACK
                ack_timeout = 0.75
                start = time.time()
                ack = ""
                
                while time.time() - start < ack_timeout:
                    if self.serial_port.in_waiting:
                        ack = self.serial_port.readline().decode().strip()
                        if ack:
                            break
                    time.sleep(0.05)

                if ack == "ACK":
                    logger.debug(f"✅ ACK отримано")
                    self.last_serial_ack = ack
                    return True
                else:
                    logger.warning(f"⚠️ Очікувалось ACK, отримано: {ack}")
                    self.last_serial_ack = ack or None
                    return False
        except Exception as e:
            logger.error(f"❌ Serial send error: {e}")
            return False

    def get_state(self) -> RobotState:
        """Отримати поточний стан"""
        try:
            return RobotState(
                joint_angles=self.joint_angles.tolist(),
                target_object={
                    "x": self.yolo_target[0],
                    "y": self.yolo_target[1],
                    "confidence": self.yolo_target[2]
                } if self.yolo_target[2] > 0.5 else None,
                serial_ack=self.last_serial_ack
            )
        except Exception as e:
            logger.error(f"❌ Get state error: {e}")
            return RobotState(joint_angles=self.joint_angles.tolist(), serial_ack=self.last_serial_ack)
    
    def control_loop(self):
        """Основний цикл керування"""
        logger.info("🚀 Запуск control loop...")
        
        loop_time = 0.05  # 20 Hz
        last_time = time.time()
        
        while True:
            try:
                start = time.time()
                
                # Оновлення спостереження
                self.current_state[:6] = self.joint_angles
                self.current_state[6:9] = self.yolo_target
                
                # RL інференс
                action = self.predict(self.current_state)
                
                # Відправка на Arduino
                success = self.send_action(action)
                
                # Читання стану
                state = self.get_state()
                
                # Частота
                elapsed = time.time() - start
                if elapsed < loop_time:
                    time.sleep(loop_time - elapsed)
                
                freq = 1.0 / (time.time() - start)
                print(f"🔄 Freq: {freq:.1f}Hz | YOLO conf: {self.yolo_target[2]:.2f}", end='\r')
            
            except KeyboardInterrupt:
                logger.info("🛑 Зупинка control loop...")
                break
            except Exception as e:
                logger.error(f"❌ Control loop error: {e}")
                time.sleep(0.1)

controller = None

@app.on_event("startup")
async def startup():
    global controller
    controller = RobotController()
    
    # Запуск control loop в окремому потоці
    control_thread = Thread(target=controller.control_loop, daemon=True)
    control_thread.start()

@app.get("/healthz")
async def healthz():
    """Health check"""
    return {
        "status": "ok",
        "model_loaded": controller.interpreter is not None,
        "serial_connected": controller.serial_port is not None,
        "mqtt_connected": controller.mqtt_client._sock is not None
    }

@app.get("/state")
async def get_robot_state():
    """Отримати поточний стан"""
    return controller.get_state()

@app.post("/predict")
async def predict(data: dict):
    """
    Ручний запит до RL моделі
    Input: {"x": [6 joint angles або 9: joints+yolo]}
    """
    try:
        obs = np.array(data.get("x", [0]*9), dtype=np.float32)
        if len(obs) == 6:
            # Доповнити YOLO даними
            obs = np.concatenate([obs, controller.yolo_target])
        
        action = controller.predict(obs)
        success = controller.send_action(action)
        
        state = controller.get_state()
        
        return {
            "action": action.tolist(),
            "serial_ack": "ACK" if success else "NACK",
            "robot_state": state.dict()
        }
    except Exception as e:
        logger.error(f"❌ Predict error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def metrics():
    """Метрики системи"""
    return {
        "yolo_target": controller.yolo_target.tolist(),
        "joint_angles": controller.joint_angles.tolist(),
        "last_detection": controller.last_detection_time
    }
