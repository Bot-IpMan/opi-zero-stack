from contextlib import asynccontextmanager
import json
import logging
import os
import time
from typing import List, Optional

import numpy as np
import paho.mqtt.client as mqtt
import serial
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

MODEL_PATH = os.getenv("MODEL_PATH", "/app/model.tflite")
SERIAL_DEV = os.getenv("SERIAL_DEV", "/dev/ttyACM0")
USE_DUMMY = os.getenv("DUMMY_MODEL", "0") == "1"

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("opi_zero_app")

SERIAL_ACK_TIMEOUT = float(os.getenv("SERIAL_ACK_TIMEOUT", "1.0"))
SERIAL_ACK_POLL = float(os.getenv("SERIAL_ACK_POLL", "0.05"))
SERIAL_INIT_TIMEOUT = float(os.getenv("SERIAL_INIT_TIMEOUT", "5.0"))

interp = None
inp = out = None
ser = None
m = None


def _wait_for_arduino_ready(timeout: float = SERIAL_INIT_TIMEOUT) -> bool:
    """Wait for Arduino to send READY signal after boot."""
    if ser is None:
        return False
    
    log.info("Waiting for Arduino READY signal (timeout: %.1fs)...", timeout)
    deadline = time.perf_counter() + timeout
    lines_received = []
    
    while time.perf_counter() < deadline:
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode(errors="ignore").strip()
                if line:  # Ігноруємо порожні рядки
                    lines_received.append(line)
                    log.info("Arduino init: %s", line)
                    if "READY" in line:
                        log.info("✓ Arduino READY")
                        return True
        except Exception as exc:
            log.warning("Error reading Arduino init: %s", exc)
        
        time.sleep(0.1)
    
    log.warning("Arduino did not send READY within %.1fs", timeout)
    if lines_received:
        log.warning("Received %d lines from Arduino: %s", len(lines_received), lines_received)
    else:
        log.error("No data received from Arduino at all - check wiring and sketch upload")
    return False


def _read_serial_ack() -> List[str]:
    """Read acknowledgement lines from the serial port within the timeout window."""
    if ser is None or SERIAL_ACK_TIMEOUT <= 0:
        return []

    deadline = time.perf_counter() + SERIAL_ACK_TIMEOUT
    lines: List[str] = []

    while time.perf_counter() <= deadline:
        try:
            waiting = getattr(ser, "in_waiting", 0)
        except Exception as exc:
            log.warning("Serial in_waiting check failed: %s", exc)
            break

        if waiting:
            try:
                raw = ser.readline()
            except Exception as exc:
                log.warning("Serial readline failed: %s", exc)
                break

            if not raw:
                continue

            decoded = raw.decode(errors="ignore").strip()
            if decoded:
                lines.append(decoded)
                log.debug("Arduino ack: %s", decoded)
                
                # Якщо отримали OK або ERR — це остаточна відповідь
                if decoded.startswith("OK") or decoded.startswith("ERR"):
                    break
                
                if len(lines) >= 5:
                    break

            # якщо ще є дані в буфері — дочекаємося наступного циклу без сну
            continue

        # нема що читати — невелика пауза перед наступною перевіркою
        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            break
        time.sleep(min(SERIAL_ACK_POLL, remaining))

    return lines


@asynccontextmanager
async def lifespan(app: FastAPI):
    global interp, inp, out, ser, m
    
    # Serial
    log.info("Opening serial port %s at 115200 baud", SERIAL_DEV)
    ser = serial.Serial(SERIAL_DEV, 115200, timeout=0.2)
    
    # Arduino Mega перезавантажується при відкритті послідовного порту —
    # даємо йому час закінчити bootloader і wiggle сервоприводів
    log.info("Waiting for Arduino boot (2s)...")
    time.sleep(2.0)
    
    # Чистимо буфери
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    
    # Чекаємо на READY сигнал
    arduino_ready = _wait_for_arduino_ready()
    if not arduino_ready:
        log.warning("Arduino may not be fully initialized - continuing anyway")
    
    # MQTT
    mqtt_host = os.getenv("MQTT_HOST", "localhost")
    mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
    log.info("Connecting to MQTT broker at %s:%d", mqtt_host, mqtt_port)
    m = mqtt.Client(client_id="opiz")
    m.connect(mqtt_host, mqtt_port, 60)
    m.loop_start()
    
    # Model (не падаємо, якщо файла нема)
    if not USE_DUMMY and os.path.exists(MODEL_PATH):
        log.info("Loading TFLite model from %s", MODEL_PATH)
        from tflite_runtime.interpreter import Interpreter
        interp = Interpreter(model_path=MODEL_PATH)
        interp.allocate_tensors()
        inp, out = interp.get_input_details()[0], interp.get_output_details()[0]
        log.info("✓ Model loaded: input_shape=%s output_shape=%s", 
                 inp["shape"], out["shape"])
    elif USE_DUMMY:
        log.info("Using DUMMY model (passthrough mode)")
    else:
        log.warning("Model file not found at %s", MODEL_PATH)
    
    yield
    
    # Cleanup
    log.info("Shutting down...")
    if m is not None:
        m.loop_stop()
        m.disconnect()
    if ser is not None and ser.is_open:
        ser.close()


app = FastAPI(title="OPi Zero Inference", lifespan=lifespan)


class Obs(BaseModel):
    x: List[float]


@app.get("/healthz")
def healthz():
    return {
        "model_loaded": interp is not None,
        "model_path": MODEL_PATH,
        "serial_open": ser is not None and ser.is_open,
        "mqtt_connected": m is not None and m.is_connected(),
    }


@app.post("/predict")
def predict(o: Obs):
    if interp is None and not USE_DUMMY:
        raise HTTPException(status_code=503, detail=f"Model not loaded at {MODEL_PATH}")
    if ser is None or not ser.is_open:
        raise HTTPException(status_code=503, detail="Serial port is not available")
    
    # Inference
    if interp is None and USE_DUMMY:
        y, ms = o.x[:], 0.1  # «глушилка»: повертаємо вхід як вихід
        log.debug("DUMMY mode: passthrough input as output")
    else:
        arr = np.array([o.x], dtype="float32")
        # підженемо форму
        if tuple(arr.shape) != tuple(inp["shape"]):
            arr = arr.reshape(inp["shape"])
        t0 = time.perf_counter()
        interp.set_tensor(inp["index"], arr)
        interp.invoke()
        y = np.asarray(interp.get_output_tensor(out["index"])).tolist()[0]
        ms = (time.perf_counter() - t0) * 1000.0
    
    # Формуємо команду для Arduino
    pkt = {"seq": int(time.time() * 1000), "cmd": y}
    payload = json.dumps(pkt, separators=(',', ':'))  # Компактний JSON
    
    # Відправка на Arduino
    try:
        ser.reset_input_buffer()
    except Exception as exc:
        log.debug("Could not clear serial input buffer: %s", exc)
    
    # ВАЖЛИВО: Arduino очікує \n (не \r\n!)
    sent = ser.write((payload + "\n").encode())
    ser.flush()
    
    log.info(
        "→ Arduino seq=%s bytes=%d cmd=%s",
        pkt["seq"],
        sent,
        [round(v, 5) for v in y],
    )

    # Читаємо відповідь
    ack_lines = _read_serial_ack()
    ack_status = "unknown"
    
    if ack_lines:
        for line in ack_lines:
            log.info("← Arduino seq=%s ack=%s", pkt["seq"], line)
            if line.startswith("OK"):
                ack_status = "ok"
            elif line.startswith("ERR"):
                ack_status = "error"
                log.error("Arduino error: %s", line)
    else:
        log.warning("No ack received from Arduino for seq=%s", pkt["seq"])
        ack_status = "timeout"

    # Публікуємо метрики в MQTT
    if m is not None and m.is_connected():
        m.publish("arm/metrics", json.dumps({
            "latency_ms": ms,
            "seq": pkt["seq"],
            "ack_status": ack_status,
        }), qos=0)
    
    return {
        "seq": pkt["seq"],
        "action": y,
        "latency_ms": ms,
        "serial": {
            "bytes_written": int(sent),
            "ack": ack_lines,
            "status": ack_status,
        },
    }


@app.post("/test")
def test_arduino():
    """Тестовий ендпоінт для перевірки Arduino без моделі."""
    if ser is None or not ser.is_open:
        raise HTTPException(status_code=503, detail="Serial port is not available")
    
    # Нейтральна позиція (всі сервоприводи в центрі)
    test_cmd = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
    pkt = {"seq": int(time.time() * 1000), "cmd": test_cmd}
    payload = json.dumps(pkt, separators=(',', ':'))
    
    try:
        ser.reset_input_buffer()
    except Exception as exc:
        log.debug("Could not clear serial input buffer: %s", exc)
    
    sent = ser.write((payload + "\n").encode())
    ser.flush()
    
    log.info("→ Arduino TEST seq=%s bytes=%d", pkt["seq"], sent)
    
    ack_lines = _read_serial_ack()
    
    if ack_lines:
        for line in ack_lines:
            log.info("← Arduino TEST ack=%s", line)
    
    return {
        "seq": pkt["seq"],
        "command": test_cmd,
        "serial": {
            "bytes_written": int(sent),
            "ack": ack_lines,
        },
    }
